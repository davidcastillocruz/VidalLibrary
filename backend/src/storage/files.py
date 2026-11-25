import asyncio
from pathlib import Path

from src.core.settings import BASE_DIR

# The files of the app (the covers...), each under a key like "covers/<item id>/<name>.webp".
# The rest of the code only uses the three functions of this file: moving to R2 (or any S3) only rewrites it.
# For now they live on the disk, in backend/data/files (outside git)
ROOT = BASE_DIR / "data" / "files"


# Where a key lives on the disk. The keys are made by the app, but a ".." must never leave ROOT
def _path(key: str) -> Path:
    path = (ROOT / key).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("The key of a file can't leave the storage")
    return path


# Saves the content under key, replacing what was there. The disk is used in a thread: it would stop the event loop
async def save_file(key: str, content: bytes) -> None:
    path = _path(key)

    # The folder of the key may not exist yet: the first cover of a work
    def write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await asyncio.to_thread(write)


# The content saved under key, or None if there is nothing
async def read_file(key: str) -> bytes | None:
    path = _path(key)
    try:
        return await asyncio.to_thread(path.read_bytes)
    except FileNotFoundError:
        return None


# Removes the file of key. A key without a file is not an error: what was asked is already true
async def delete_file(key: str) -> None:
    await asyncio.to_thread(_path(key).unlink, missing_ok=True)
