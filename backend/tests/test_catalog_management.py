import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DBAPIError

from src.database.session import AsyncSessionLocal
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.catalog.models.genre_model import Genre
from src.modules.catalog.models.item_model import Item, ItemKind, item_genres
from src.modules.catalog.models.language_model import ItemLanguage
from src.modules.catalog.repositories import genre_repository, item_repository, language_repository
from src.modules.catalog.services import catalog_management_service
from src.modules.user.models.user_model import User, UserRole
from src.security.cookies import SESSION_DURATION
from src.security.tokens import new_token

HEADERS = {"Accept-Language": "ca"}
BOOK = {"kind": "book", "title": " Aloma ", "creator": "Mercè Rodoreda", "year": 1938, "copies": 2}


# A browser signed in with this role: the librarian by default
async def signed_in(client, role=UserRole.LIBRARIAN, email="ana@vidal.cat") -> User:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        user = User(email=email, name="Ana Puig", role=role, password_hash="hash")
        db.add(user)
        await db.flush()
        db.add(AuthSession(user_id=user.id, token_hash=token_hash, ip="127.0.0.1",
                           expires_at=datetime.now(UTC) + SESSION_DURATION))
        await db.commit()
    client.cookies.set("session", token)
    return user


async def add_genre(name: str, kind=ItemKind.BOOK) -> Genre:
    async with AsyncSessionLocal() as db:
        genre = Genre(kind=kind, name=name)
        db.add(genre)
        await db.commit()
        return genre


async def add_language(name: str) -> ItemLanguage:
    async with AsyncSessionLocal() as db:
        language = ItemLanguage(name=name)
        db.add(language)
        await db.commit()
        return language


async def rows(model) -> list:
    async with AsyncSessionLocal() as db:
        return list(await db.scalars(select(model)))


async def genre_ids_of(item_id) -> set:
    async with AsyncSessionLocal() as db:
        return set(await db.scalars(select(item_genres.c.genre_id).where(item_genres.c.item_id == item_id)))


async def test_a_librarian_adds_a_work_with_its_genres_and_language(client):
    await signed_in(client)
    novel = await add_genre("Novel·la")
    catalan = await add_language("Català")

    response = await client.post(
        "/admin/catalog/items",
        json={**BOOK, "genre_ids": [str(novel.id)], "language_id": str(catalan.id), "synopsis": "  "},
        headers=HEADERS,
    )

    assert response.status_code == 201 and response.json()["message"] == "Obra afegida al catàleg"
    [item] = await rows(Item)
    assert str(item.id) == response.json()["id"]
    assert (item.title, item.copies, item.language_id, item.synopsis) == ("Aloma", 2, catalan.id, None)
    assert await genre_ids_of(item.id) == {novel.id}


@pytest.mark.parametrize("role", [UserRole.READER, None], ids=["reader", "signed out"])
async def test_only_a_librarian_can_change_the_catalog(client, role):
    if role:
        await signed_in(client, role=role)

    response = await client.post("/admin/catalog/items", json=BOOK)

    assert response.status_code == (403 if role else 401) and await rows(Item) == []


async def test_a_genre_of_another_kind_is_refused(client):
    await signed_in(client)
    strategy = await add_genre("Estratègia", kind=ItemKind.BOARD_GAME)
    body = {**BOOK, "genre_ids": [str(strategy.id)]}

    response = await client.post("/admin/catalog/items", json=body, headers=HEADERS)

    assert response.status_code == 400
    assert response.json() == {"detail": "Algun gènere triat ja no existeix o és d'un altre tipus d'obra"}
    assert await rows(Item) == []


async def test_an_unknown_genre_or_language_is_refused(client):
    await signed_in(client)

    unknown_genre = await client.post("/admin/catalog/items", json={**BOOK, "genre_ids": [str(uuid.uuid4())]})
    unknown_language = await client.post("/admin/catalog/items", json={**BOOK, "language_id": str(uuid.uuid4())})

    assert unknown_genre.status_code == 400 and unknown_language.status_code == 400 and await rows(Item) == []


async def test_the_same_genre_twice_counts_once(client):
    await signed_in(client)
    novel = await add_genre("Novel·la")

    response = await client.post("/admin/catalog/items", json={**BOOK, "genre_ids": [str(novel.id)] * 2})

    assert response.status_code == 201 and await genre_ids_of(uuid.UUID(response.json()["id"])) == {novel.id}


@pytest.mark.parametrize("change", [
    {"copies": 0},
    {"copies": 101},
    {"year": 1200},
    {"title": "  "},
    {"title": "a\x00"},
], ids=["no copies", "too many copies", "too old", "empty title", "NUL"])
async def test_what_isnt_a_work_is_422(client, change):
    await signed_in(client)

    response = await client.post("/admin/catalog/items", json={**BOOK, **change})

    assert response.status_code == 422


async def test_saving_a_work_replaces_its_fields_and_its_genres(client):
    await signed_in(client)
    novel = await add_genre("Novel·la")
    classic = await add_genre("Clàssic")
    created = await client.post("/admin/catalog/items", json={**BOOK, "genre_ids": [str(novel.id)]})
    item_id = created.json()["id"]

    response = await client.put(
        f"/admin/catalog/items/{item_id}",
        json={**BOOK, "title": "Aloma (1969)", "copies": 3, "genre_ids": [str(classic.id)]},
        headers=HEADERS,
    )

    assert response.status_code == 200 and response.json() == {"message": "Obra desada"}
    [item] = await rows(Item)
    assert (item.title, item.copies) == ("Aloma (1969)", 3)
    assert await genre_ids_of(item.id) == {classic.id}


async def test_a_work_can_change_its_kind_with_genres_of_the_new_one(client):
    await signed_in(client)
    created = await client.post("/admin/catalog/items", json=BOOK)
    drama = await add_genre("Drama", kind=ItemKind.FILM)

    response = await client.put(
        f"/admin/catalog/items/{created.json()['id']}",
        json={**BOOK, "kind": "film", "genre_ids": [str(drama.id)]},
    )

    assert response.status_code == 200
    [item] = await rows(Item)
    assert item.kind == ItemKind.FILM


async def test_saving_or_deleting_a_work_that_doesnt_exist_is_404(client):
    await signed_in(client)

    saved = await client.put(f"/admin/catalog/items/{uuid.uuid4()}", json=BOOK, headers=HEADERS)
    deleted = await client.delete(f"/admin/catalog/items/{uuid.uuid4()}", headers=HEADERS)

    assert saved.status_code == 404 and saved.json() == {"detail": "Aquesta obra no és al catàleg"}
    assert deleted.status_code == 404


async def test_deleting_a_work_takes_its_genres_with_it(client):
    await signed_in(client)
    novel = await add_genre("Novel·la")
    created = await client.post("/admin/catalog/items", json={**BOOK, "genre_ids": [str(novel.id)]})

    response = await client.delete(f"/admin/catalog/items/{created.json()['id']}", headers=HEADERS)

    assert response.json() == {"message": "Obra eliminada del catàleg"}
    assert await rows(Item) == [] and await rows(Genre) != []


async def test_genres_are_created_renamed_and_deleted(client):
    await signed_in(client)

    created = await client.post("/admin/catalog/genres", json={"kind": "book", "name": " Novel·la "})
    genre_id = created.json()["id"]
    renamed = await client.put(f"/admin/catalog/genres/{genre_id}", json={"name": "Novel·la negra"}, headers=HEADERS)
    [genre] = await rows(Genre)
    deleted = await client.delete(f"/admin/catalog/genres/{genre_id}", headers=HEADERS)

    assert created.status_code == 201 and created.json()["name"] == "Novel·la"
    assert renamed.json() == {"message": "Gènere desat"} and genre.name == "Novel·la negra"
    assert deleted.json() == {"message": "Gènere eliminat"} and await rows(Genre) == []


# The same name in another kind is another genre
async def test_a_genre_name_repeats_only_in_another_kind(client):
    await signed_in(client)
    await add_genre("Clàssic")

    same_kind = await client.post("/admin/catalog/genres", json={"kind": "book", "name": "Clàssic"}, headers=HEADERS)
    other_kind = await client.post("/admin/catalog/genres", json={"kind": "film", "name": "Clàssic"})

    assert same_kind.status_code == 409 and same_kind.json() == {"detail": "Ja hi ha un gènere amb aquest nom"}
    assert other_kind.status_code == 201


async def test_renaming_a_genre_to_a_name_taken_is_409(client):
    await signed_in(client)
    await add_genre("Clàssic")
    novel = await add_genre("Novel·la")

    response = await client.put(f"/admin/catalog/genres/{novel.id}", json={"name": "Clàssic"})

    assert response.status_code == 409


# Two requests at once with the same name: the database stops the second one, never a 500
async def test_the_same_genre_at_once_is_created_once(client):
    await signed_in(client)

    responses = await asyncio.gather(*(
        client.post("/admin/catalog/genres", json={"kind": "book", "name": "Poesia"}) for _ in range(3)
    ))

    assert sorted(response.status_code for response in responses) == [201, 409, 409]


async def test_deleting_a_genre_keeps_its_works(client):
    await signed_in(client)
    novel = await add_genre("Novel·la")
    created = await client.post("/admin/catalog/items", json={**BOOK, "genre_ids": [str(novel.id)]})

    await client.delete(f"/admin/catalog/genres/{novel.id}")

    assert len(await rows(Item)) == 1 and await genre_ids_of(uuid.UUID(created.json()["id"])) == set()


async def test_languages_are_created_renamed_and_deleted_and_their_works_stay(client):
    await signed_in(client)
    created = await client.post("/admin/catalog/languages", json={"name": "Catala"})
    language_id = created.json()["id"]
    await client.post("/admin/catalog/items", json={**BOOK, "language_id": language_id})

    renamed = await client.put(f"/admin/catalog/languages/{language_id}", json={"name": "Català"}, headers=HEADERS)
    repeated = await client.post("/admin/catalog/languages", json={"name": "Català"}, headers=HEADERS)
    deleted = await client.delete(f"/admin/catalog/languages/{language_id}", headers=HEADERS)

    assert renamed.json() == {"message": "Llengua desada"}
    assert repeated.status_code == 409 and repeated.json() == {"detail": "Ja hi ha una llengua amb aquest nom"}
    assert deleted.json() == {"message": "Llengua eliminada"}
    [item] = await rows(Item)
    assert item.language_id is None


@pytest.mark.parametrize("path", ["genres", "languages"])
async def test_a_genre_or_language_that_doesnt_exist_is_404(client, path):
    await signed_in(client)

    renamed = await client.put(f"/admin/catalog/{path}/{uuid.uuid4()}", json={"name": "X"})
    deleted = await client.delete(f"/admin/catalog/{path}/{uuid.uuid4()}")

    assert renamed.status_code == 404 and deleted.status_code == 404


# A genre and a language being given to a work stay locked until it is saved: deleting them at that moment waits,
# instead of the save failing on a genre that no longer exists (a 500)
@pytest.mark.parametrize("what", ["genre", "language"])
async def test_a_genre_or_language_being_given_cant_be_deleted_meanwhile(client, what):
    genre = await add_genre("Novel·la")
    catalan = await add_language("Català")
    async with AsyncSessionLocal() as saving, AsyncSessionLocal() as deleting:
        if what == "genre":
            await genre_repository.get_genres_by_ids(saving, [genre.id], lock=True)
        else:
            await language_repository.get_language_by_id(saving, catalan.id, lock=True)
        await deleting.execute(text("SET LOCAL lock_timeout = '200ms'"))
        model = Genre if what == "genre" else ItemLanguage
        row_id = genre.id if what == "genre" else catalan.id

        with pytest.raises(DBAPIError, match="lock timeout"):
            await deleting.execute(delete(model).where(model.id == row_id))


# Saving a work while its language is deleted: the deletion takes the works first, in the order of a save (the work,
# then its language), so it waits for the save instead of both waiting for each other (a deadlock, a 500)
async def test_deleting_a_language_waits_for_the_save_of_one_of_its_works(client):
    catalan = await add_language("Català")
    async with AsyncSessionLocal() as db:
        item = Item(kind=ItemKind.BOOK, title="Aloma", creator="Mercè Rodoreda", copies=1, language_id=catalan.id)
        db.add(item)
        await db.commit()

    async with AsyncSessionLocal() as saving, AsyncSessionLocal() as deleting:
        await item_repository.get_item_by_id(saving, item.id, lock=True)
        await deleting.execute(text("SET LOCAL lock_timeout = '5s'"))
        deletion = asyncio.create_task(catalog_management_service.delete_language(deleting, catalan.id, "ca"))
        await asyncio.sleep(0.3)

        # The deletion waits for the work, and hasn't touched the language yet: the save can take it
        await saving.execute(text("SET LOCAL lock_timeout = '300ms'"))
        assert await language_repository.get_language_by_id(saving, catalan.id, lock=True)
        assert not deletion.done()
        await saving.commit()
        await deletion

    assert await rows(ItemLanguage) == []
