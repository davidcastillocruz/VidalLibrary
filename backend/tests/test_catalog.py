import uuid
from datetime import UTC, datetime, timedelta

from src.database.session import AsyncSessionLocal
from src.modules.catalog.models.genre_model import Genre
from src.modules.catalog.models.item_model import Item, ItemKind, item_genres
from src.modules.catalog.models.language_model import ItemLanguage
from src.modules.catalog.services import catalog_service


async def add_item(
    title: str,
    kind=ItemKind.BOOK,
    creator="Mercè Rodoreda",
    year: int | None = 1962,
    genres: tuple[Genre, ...] = (),
    language: ItemLanguage | None = None,
    created_at: datetime | None = None,
) -> Item:
    async with AsyncSessionLocal() as db:
        item = Item(kind=kind, title=title, creator=creator, year=year, copies=1,
                    language_id=language.id if language else None, created_at=created_at or datetime.now(UTC))
        db.add(item)
        await db.flush()
        for genre in genres:
            await db.execute(item_genres.insert().values(item_id=item.id, genre_id=genre.id))
        await db.commit()
        return item


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


async def titles(client, **params) -> list[str]:
    response = await client.get("/catalog/items", params=params)
    assert response.status_code == 200
    return [item["title"] for item in response.json()["items"]]


async def test_the_catalog_is_public_and_sorted_by_title(client):
    await add_item("Mirall trencat")
    await add_item("la plaça del Diamant")
    await add_item("Aloma")

    response = await client.get("/catalog/items")

    assert response.status_code == 200 and response.json()["total"] == 3
    assert [item["title"] for item in response.json()["items"]] == ["Aloma", "la plaça del Diamant", "Mirall trencat"]


async def test_it_filters_by_kind(client):
    await add_item("Aloma")
    await add_item("Pa negre", kind=ItemKind.FILM, creator="Agustí Villaronga")

    assert await titles(client, kind="film") == ["Pa negre"]


async def test_it_filters_by_genre_and_by_language(client):
    novel = await add_genre("Novel·la")
    catalan = await add_language("Català")
    await add_item("Aloma", genres=(novel,), language=catalan)
    await add_item("Mirall trencat", genres=(novel,))
    await add_item("Poesia completa", language=catalan)

    assert await titles(client, genre=str(novel.id)) == ["Aloma", "Mirall trencat"]
    assert await titles(client, language=str(catalan.id)) == ["Aloma", "Poesia completa"]
    assert await titles(client, genre=str(novel.id), language=str(catalan.id)) == ["Aloma"]


async def test_it_searches_the_title_and_the_creator_whatever_their_capitals(client):
    await add_item("Aloma")
    await add_item("Pa negre", kind=ItemKind.FILM, creator="Agustí Villaronga")

    assert await titles(client, q="  ALOM ") == ["Aloma"]
    assert await titles(client, q="villa") == ["Pa negre"]


# A % in the search is a %, not "anything"
async def test_a_wildcard_in_the_search_is_looked_for_as_it_is(client):
    await add_item("Aloma")
    await add_item("100% Barcelona")

    assert await titles(client, q="%") == ["100% Barcelona"]


async def test_it_sorts_by_newest_and_by_year(client):
    now = datetime.now(UTC)
    await add_item("Aloma", year=1938, created_at=now - timedelta(days=2))
    await add_item("Mirall trencat", year=1974, created_at=now - timedelta(days=1))
    await add_item("Sense any", year=None, created_at=now)

    assert await titles(client, sort="newest") == ["Sense any", "Mirall trencat", "Aloma"]
    assert await titles(client, sort="year") == ["Mirall trencat", "Aloma", "Sense any"]


async def test_it_pages_without_repeating_or_skipping(client, monkeypatch):
    monkeypatch.setattr(catalog_service, "PAGE_SIZE", 2)
    for n in range(5):
        await add_item(f"Obra {n}")

    pages = [await titles(client, page=page) for page in (1, 2, 3)]

    assert pages == [["Obra 0", "Obra 1"], ["Obra 2", "Obra 3"], ["Obra 4"]]


async def test_a_wrong_filter_is_422(client):
    response = await client.get("/catalog/items", params={"kind": "magazine", "page": 0})

    assert response.status_code == 422


async def test_a_work_has_its_page_with_its_language_and_genres(client):
    novel = await add_genre("Novel·la")
    classic = await add_genre("Clàssic")
    catalan = await add_language("Català")
    item = await add_item("Aloma", genres=(novel, classic), language=catalan)

    response = await client.get(f"/catalog/items/{item.id}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["title"] == "Aloma" and detail["creator"] == "Mercè Rodoreda" and detail["copies"] == 1
    assert detail["language"] == {"id": str(catalan.id), "name": "Català"}
    assert [genre["name"] for genre in detail["genres"]] == ["Clàssic", "Novel·la"]


async def test_a_work_that_doesnt_exist_is_404(client):
    response = await client.get(f"/catalog/items/{uuid.uuid4()}", headers={"Accept-Language": "ca"})

    assert response.status_code == 404 and response.json() == {"detail": "Aquesta obra no és al catàleg"}


async def test_the_genres_of_a_kind(client):
    await add_genre("Novel·la")
    await add_genre("Estratègia", kind=ItemKind.BOARD_GAME)

    response = await client.get("/catalog/genres", params={"kind": "board_game"})

    assert [genre["name"] for genre in response.json()] == ["Estratègia"]
    assert len((await client.get("/catalog/genres")).json()) == 2


async def test_the_languages_sorted_by_name(client):
    await add_language("English")
    await add_language("Català")

    response = await client.get("/catalog/languages")

    assert [language["name"] for language in response.json()] == ["Català", "English"]
