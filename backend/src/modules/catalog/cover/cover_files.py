import logging
import secrets
import uuid
from pathlib import PurePosixPath

from src.storage import files

logger = logging.getLogger(__name__)


# Key of a new cover of the work. New on every change: the old cover is never overwritten while the database still
# points to it, and the browser never shows an old one cached under the same name
def new_cover_key(item_id: uuid.UUID) -> str:
    return f"covers/{item_id}/{secrets.token_hex(16)}.webp"


# The version of a cover: the random name of its file, new on every change. The address of the image carries it
# (?v=), so the browser can keep each version for good and a new cover is a new address
def cover_version(key: str) -> str:
    return PurePosixPath(key).stem


# Removes the file of a cover the database doesn't point to: the old one after a change, the new one when the change
# failed, or the one of a deleted work. If it can't be removed it only stays behind: the change already went through,
# or the error of the change is the one that matters
async def remove_cover_file(key: str) -> None:
    try:
        await files.delete_file(key)
    except OSError as exc:
        logger.warning("Could not remove a cover file: %s", type(exc).__name__)
