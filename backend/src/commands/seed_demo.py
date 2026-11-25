import asyncio
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from src.core.settings import settings
from src.database.session import AsyncSessionLocal, engine
from src.modules.catalog.models.genre_model import Genre
from src.modules.catalog.models.item_model import Item, ItemKind, item_genres
from src.modules.catalog.models.language_model import ItemLanguage
from src.modules.loan.loan_rules import library_today
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.user.models.user_model import User, UserRole
from src.security.passwords import hash_password

# The password of the demo accounts. Only in development: the command refuses to run in production
DEMO_PASSWORD = "vidal-demo-2026"
# The two accounts to sign in with, one of each role
DEMO_ACCOUNTS = [
    ("biblioteca@vidal.example", "Ana Puig", UserRole.LIBRARIAN),
    ("lector@vidal.example", "Pau Ferrer", UserRole.READER),
]
# Readers with loans of their own, so the desk has more than one name
OTHER_READERS = [
    ("marta@vidal.example", "Marta Roig"),
    ("joan@vidal.example", "Joan Pons"),
    ("laia@vidal.example", "Laia Serra"),
]

# The genres of each kind and the languages of the works
GENRES = {
    ItemKind.BOOK: ["Novel·la", "Clàssic", "Poesia", "Juvenil", "Ciència-ficció", "Assaig"],
    ItemKind.FILM: ["Drama", "Comèdia", "Animació", "Documental"],
    ItemKind.BOARD_GAME: ["Estratègia", "Cooperatiu", "Família", "Cartes"],
}
LANGUAGES = ["Català", "Castellà", "Anglès", "Francès"]

# The works: (kind, title, creator, year, language, genres, copies, synopsis)
WORKS = [
    (ItemKind.BOOK, "La plaça del Diamant", "Mercè Rodoreda", 1962, "Català", ["Novel·la", "Clàssic"], 3,
     "La Natàlia, la Colometa, explica la seva vida a la Barcelona de la República, la guerra i la postguerra."),
    (ItemKind.BOOK, "Mirall trencat", "Mercè Rodoreda", 1974, "Català", ["Novel·la", "Clàssic"], 2,
     "Tres generacions d'una família burgesa i la torre de Sant Gervasi que ho veu tot."),
    (ItemKind.BOOK, "Solitud", "Víctor Català", 1905, "Català", ["Novel·la", "Clàssic"], 1,
     "La Mila puja amb el seu marit a una ermita de muntanya i s'hi troba sola davant de tot."),
    (ItemKind.BOOK, "Pedra de tartera", "Maria Barbal", 1985, "Català", ["Novel·la"], 2,
     "La Conxa recorda la seva vida al Pallars, de nena enviada a casa d'una tia fins a la vellesa a Barcelona."),
    (ItemKind.BOOK, "Jo confesso", "Jaume Cabré", 2011, "Català", ["Novel·la"], 1,
     "L'Adrià Ardèvol escriu, abans de perdre la memòria, la història d'un violí i de tot el mal que l'envolta."),
    (ItemKind.BOOK, "Les veus del Pamano", "Jaume Cabré", 2004, "Català", ["Novel·la"], 1, None),
    (ItemKind.BOOK, "Canto jo i la muntanya balla", "Irene Solà", 2019, "Català", ["Novel·la"], 2,
     "Una tempesta, unes bruixes, uns bolets i una família de muntanya expliquen el Pirineu a moltes veus."),
    (ItemKind.BOOK, "L'estrany cas del Dr. Jekyll i Mr. Hyde", "Robert Louis Stevenson", 1886, "Català",
     ["Clàssic", "Juvenil"], 2, None),
    (ItemKind.BOOK, "Don Quijote de la Mancha", "Miguel de Cervantes", 1605, "Castellà", ["Clàssic", "Novel·la"], 2,
     "Un hidalgo que ha llegit massa novel·les de cavalleries surt a desfer greuges amb el seu escuder."),
    (ItemKind.BOOK, "Cien años de soledad", "Gabriel García Márquez", 1967, "Castellà", ["Novel·la", "Clàssic"], 2,
     None),
    (ItemKind.BOOK, "Frankenstein", "Mary Shelley", 1818, "Anglès", ["Clàssic", "Ciència-ficció"], 1,
     "Victor Frankenstein dona vida a una criatura i després no sap què fer-ne."),
    (ItemKind.BOOK, "Fahrenheit 451", "Ray Bradbury", 1953, "Castellà", ["Ciència-ficció"], 2,
     "En un futur on els bombers cremen llibres, en Guy Montag comença a llegir-ne un."),
    (ItemKind.BOOK, "Poesia completa", "Gabriel Ferrater", 1968, "Català", ["Poesia"], 1, None),
    (ItemKind.BOOK, "El Petit Príncep", "Antoine de Saint-Exupéry", 1943, "Català", ["Juvenil", "Clàssic"], 3,
     "Un aviador perdut al desert coneix un nen vingut d'un asteroide no més gran que una casa."),
    (ItemKind.BOOK, "Una habitació pròpia", "Virginia Woolf", 1929, "Català", ["Assaig"], 1, None),
    (ItemKind.FILM, "Pa negre", "Agustí Villaronga", 2010, "Català", ["Drama"], 1,
     "A la Catalunya rural de la postguerra, l'Andreu troba dos cadàvers al bosc i comença a entendre els adults."),
    (ItemKind.FILM, "Estiu 1993", "Carla Simón", 2017, "Català", ["Drama"], 2,
     "La Frida, de sis anys, passa el primer estiu amb la seva nova família al camp."),
    (ItemKind.FILM, "Alcarràs", "Carla Simón", 2022, "Català", ["Drama"], 1, None),
    (ItemKind.FILM, "El viatge de Chihiro", "Hayao Miyazaki", 2001, "Català", ["Animació"], 2,
     "Una nena queda atrapada en un món d'esperits i ha de treballar en uns banys per salvar els seus pares."),
    (ItemKind.FILM, "Temps moderns", "Charles Chaplin", 1936, None, ["Comèdia"], 1, None),
    (ItemKind.FILM, "Amélie", "Jean-Pierre Jeunet", 2001, "Francès", ["Comèdia"], 1, None),
    (ItemKind.FILM, "Honeyland", "Ljubomir Stefanov", 2019, None, ["Documental"], 1, None),
    (ItemKind.BOARD_GAME, "Catan", "Klaus Teuber", 1995, "Català", ["Estratègia", "Família"], 2,
     "Colonitza una illa amb fusta, maó, llana, blat i pedra, i negocia amb els altres jugadors."),
    (ItemKind.BOARD_GAME, "Carcassonne", "Klaus-Jürgen Wrede", 2000, "Català", ["Família", "Estratègia"], 2, None),
    (ItemKind.BOARD_GAME, "Pandemic", "Matt Leacock", 2008, "Castellà", ["Cooperatiu", "Estratègia"], 1,
     "Quatre malalties s'escampen pel món: tot l'equip guanya o perd junt."),
    (ItemKind.BOARD_GAME, "Dixit", "Jean-Louis Roubira", 2008, "Català", ["Família", "Cartes"], 2, None),
    (ItemKind.BOARD_GAME, "Azul", "Michael Kiesling", 2017, "Català", ["Estratègia", "Família"], 1, None),
    (ItemKind.BOARD_GAME, "The Mind", "Wolfgang Warsch", 2018, None, ["Cooperatiu", "Cartes"], 1, None),
]


# Fills an empty development database with a catalog, two accounts to sign in with and loans in every status, to try
# the app and take its screenshots:
#   docker compose exec backend python -m src.commands.seed_demo
# Returns the exit code
async def seed() -> int:
    if settings.APP_MODE == "production":
        print("The demo data is only for development", file=sys.stderr)
        return 1
    async with AsyncSessionLocal() as db:
        if await db.scalar(select(func.count()).select_from(Item)):
            print("The catalog already has works: the demo data goes into an empty one", file=sys.stderr)
            return 1

        password_hash = await hash_password(DEMO_PASSWORD)
        users = {}
        for email, name, role in DEMO_ACCOUNTS:
            users[email] = await db.scalar(select(User).where(User.email == email)) or User(
                email=email, name=name, role=role, password_hash=password_hash,
            )
            db.add(users[email])
        for email, name in OTHER_READERS:
            users[email] = User(email=email, name=name, role=UserRole.READER, password_hash=password_hash)
            db.add(users[email])
        users["nou@vidal.example"] = User(email="nou@vidal.example", name="Biel Mas", role=UserRole.READER)
        db.add(users["nou@vidal.example"])

        genres = {(kind, name): Genre(kind=kind, name=name) for kind, names in GENRES.items() for name in names}
        languages = {name: ItemLanguage(name=name) for name in LANGUAGES}
        db.add_all([*genres.values(), *languages.values()])
        await db.flush()

        now = datetime.now(UTC)
        items = {}
        for age, (kind, title, creator, year, language, names, copies, synopsis) in enumerate(reversed(WORKS)):
            item = Item(
                kind=kind, title=title, creator=creator, year=year, copies=copies, synopsis=synopsis,
                language_id=languages[language].id if language else None, created_at=now - timedelta(days=age),
            )
            db.add(item)
            await db.flush()
            for name in names:
                await db.execute(item_genres.insert().values(item_id=item.id, genre_id=genres[(kind, name)].id))
            items[title] = item

        today = library_today()
        reader = users["lector@vidal.example"]
        loans = [
            (reader, "El viatge de Chihiro", LoanStatus.REQUESTED, {"requested_at": now - timedelta(hours=5)}),
            (reader, "La plaça del Diamant", LoanStatus.ACTIVE,
             {"requested_at": now - timedelta(days=13), "picked_up_at": now - timedelta(days=12),
             "due_on": today + timedelta(days=9)}),
            (reader, "Frankenstein", LoanStatus.RETURNED,
             {"requested_at": now - timedelta(days=42), "picked_up_at": now - timedelta(days=40),
             "due_on": today - timedelta(days=19), "returned_at": now - timedelta(days=20)}),
            (reader, "Catan", LoanStatus.CANCELLED,
             {"requested_at": now - timedelta(days=32), "cancelled_at": now - timedelta(days=30)}),
            (users["marta@vidal.example"], "Pa negre", LoanStatus.ACTIVE,
             {"requested_at": now - timedelta(days=26), "picked_up_at": now - timedelta(days=25),
             "due_on": today - timedelta(days=4)}),
            (users["marta@vidal.example"], "Pandemic", LoanStatus.REQUESTED, {"requested_at": now - timedelta(days=1)}),
            (users["joan@vidal.example"], "Solitud", LoanStatus.ACTIVE,
             {"requested_at": now - timedelta(days=20), "picked_up_at": now - timedelta(days=19),
             "due_on": today + timedelta(days=2)}),
            (users["joan@vidal.example"], "Dixit", LoanStatus.REQUESTED, {"requested_at": now - timedelta(days=2)}),
            (users["laia@vidal.example"], "Jo confesso", LoanStatus.ACTIVE,
             {"requested_at": now - timedelta(days=4), "picked_up_at": now - timedelta(days=3),
             "due_on": today + timedelta(days=18)}),
        ]
        for user, title, status, values in loans:
            db.add(Loan(user_id=user.id, item_id=items[title].id, status=status, **values))
        await db.commit()

    print(f"{len(WORKS)} works and {len(loans)} loans. Sign in as biblioteca@vidal.example or lector@vidal.example")
    return 0


# Runs seed() in its own event loop, and returns its exit code
def main() -> int:
    # One event loop for the command and for closing the connections of the pool
    async def run() -> int:
        try:
            return await seed()
        finally:
            await engine.dispose()

    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
