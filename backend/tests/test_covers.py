import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import delete, select

from src.database.session import AsyncSessionLocal
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.catalog.cover import cover_image
from src.modules.catalog.models.item_model import Item, ItemKind
from src.modules.user.models.user_model import User, UserRole
from src.security.cookies import SESSION_DURATION
from src.security.tokens import new_token
from src.storage import files

HEADERS = {"Accept-Language": "ca"}


# The files go to a folder of the test, never to backend/data
@pytest.fixture
def storage(monkeypatch, tmp_path):
    monkeypatch.setattr(files, "ROOT", tmp_path)
    return tmp_path


def image(fmt="PNG", size=(1200, 1800)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, "#1e5a48").save(output, fmt)
    return output.getvalue()


async def signed_in(client, role=UserRole.LIBRARIAN) -> None:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        user = User(email="ana@vidal.cat", name="Ana Puig", role=role, password_hash="hash")
        db.add(user)
        await db.flush()
        db.add(AuthSession(user_id=user.id, token_hash=token_hash, ip="127.0.0.1",
                           expires_at=datetime.now(UTC) + SESSION_DURATION))
        await db.commit()
    client.cookies.set("session", token)


async def add_item() -> Item:
    async with AsyncSessionLocal() as db:
        item = Item(kind=ItemKind.BOOK, title="Aloma", creator="Mercè Rodoreda", copies=1)
        db.add(item)
        await db.commit()
        return item


async def cover_key(item_id) -> str | None:
    async with AsyncSessionLocal() as db:
        return await db.scalar(select(Item.cover_key).where(Item.id == item_id))


async def upload(client, item_id, content: bytes):
    return await client.put(f"/admin/catalog/items/{item_id}/cover", files={"cover": ("c.png", content)},
                            headers=HEADERS)


async def test_a_cover_is_kept_as_a_webp_that_fits_600_by_900_and_is_public(client, storage):
    await signed_in(client)
    item = await add_item()

    response = await upload(client, item.id, image())

    assert response.status_code == 200 and response.json() == {"message": "Portada desada"}
    key = await cover_key(item.id)
    assert key
    with Image.open(storage / key) as kept:
        assert kept.format == "WEBP" and kept.size == (600, 900)
    client.cookies.clear()
    listed = (await client.get("/catalog/items")).json()["items"]
    assert listed[0]["cover"] == Path(key).stem
    served = await client.get(f"/catalog/items/{item.id}/cover", params={"v": listed[0]["cover"]})
    assert served.status_code == 200 and served.headers["content-type"] == "image/webp"


# The version in the address lets the browser keep a cover for good: a new cover is a new version, a new address.
# Asked without it, or with an old one, the browser has to ask again each time
async def test_a_cover_is_kept_by_the_browser_only_at_its_version(client, storage):
    await signed_in(client)
    item = await add_item()
    await upload(client, item.id, image())
    old = Path(await cover_key(item.id) or "").stem
    await upload(client, item.id, image())
    new = Path(await cover_key(item.id) or "").stem

    current = await client.get(f"/catalog/items/{item.id}/cover", params={"v": new})
    stale = await client.get(f"/catalog/items/{item.id}/cover", params={"v": old})
    bare = await client.get(f"/catalog/items/{item.id}/cover")

    assert new != old
    assert current.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert stale.headers["cache-control"] == bare.headers["cache-control"] == "public, no-cache"


# A phone photo stores how it was held: a portrait one is stored sideways, and fits 600 x 900 once turned upright
async def test_a_photo_held_upright_is_turned_and_fills_its_box(client, storage):
    await signed_in(client)
    item = await add_item()
    exif = Image.Exif()
    exif[0x0112] = 6
    sideways = io.BytesIO()
    Image.new("RGB", (1600, 1200), "#1e5a48").save(sideways, "JPEG", exif=exif)

    await upload(client, item.id, sideways.getvalue())

    with Image.open(storage / (await cover_key(item.id) or "")) as kept:
        assert kept.size == (600, 800)


async def test_what_isnt_an_image_is_400(client, storage):
    await signed_in(client)
    item = await add_item()

    response = await upload(client, item.id, b"not an image")

    assert response.status_code == 400
    assert response.json() == {"detail": "La portada ha de ser una imatge PNG, JPEG o WebP de fins a 5 MB"}
    assert not await cover_key(item.id) and list(storage.iterdir()) == []


async def test_a_new_cover_removes_the_old_file(client, storage):
    await signed_in(client)
    item = await add_item()
    await upload(client, item.id, image())
    old = await cover_key(item.id)

    await upload(client, item.id, image("JPEG", (300, 300)))

    new = await cover_key(item.id)
    assert new != old and old and not (storage / old).exists() and new and (storage / new).exists()


async def test_removing_the_cover_and_deleting_the_work_remove_the_file(client, storage):
    await signed_in(client)
    item = await add_item()
    await upload(client, item.id, image())
    key = await cover_key(item.id)

    removed = await client.delete(f"/admin/catalog/items/{item.id}/cover", headers=HEADERS)
    await upload(client, item.id, image())
    second = await cover_key(item.id)
    await client.delete(f"/admin/catalog/items/{item.id}")

    assert removed.json() == {"message": "Portada eliminada"} and key and not (storage / key).exists()
    assert second and not (storage / second).exists()


# A change that fails once its file is saved (the commit, the disk) leaves no file nobody points to
async def test_a_failed_change_removes_the_new_file(client, storage, monkeypatch):
    await signed_in(client)
    item = await add_item()
    save = files.save_file

    async def save_and_fail(key: str, content: bytes) -> None:
        await save(key, content)
        raise OSError("disk full")

    monkeypatch.setattr(files, "save_file", save_and_fail)

    response = await upload(client, item.id, image())

    assert response.status_code == 500 and list(storage.rglob("*.webp")) == [] and not await cover_key(item.id)


# The work deleted while its new cover is being processed: the upload is a 404 and leaves no file behind
async def test_a_cover_for_a_work_deleted_meanwhile_saves_nothing(client, storage, monkeypatch):
    await signed_in(client)
    item = await add_item()
    read_cover = cover_image.read_cover

    async def read_and_delete(upload):
        cover = await read_cover(upload)
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Item).where(Item.id == item.id))
            await db.commit()
        return cover

    monkeypatch.setattr(cover_image, "read_cover", read_and_delete)

    response = await upload(client, item.id, image())

    assert response.status_code == 404 and list(storage.rglob("*.webp")) == []


async def test_a_reader_cant_change_a_cover(client, storage):
    await signed_in(client, role=UserRole.READER)
    item = await add_item()

    response = await upload(client, item.id, image())

    assert response.status_code == 403


async def test_a_work_without_a_cover_is_404(client, storage):
    item = await add_item()

    response = await client.get(f"/catalog/items/{item.id}/cover")

    assert response.status_code == 404
