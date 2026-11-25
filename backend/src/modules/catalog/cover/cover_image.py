import asyncio
import io

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

# Biggest cover accepted, in bytes: a photo of a phone fits, anything bigger is not a cover
MAX_BYTES = 5 * 1024 * 1024
# Most pixels an image can have: a small file can unpack into a huge image (an image bomb) and fill the memory
MAX_PIXELS = 40_000_000
# Most pixels unpacked whole (2048 x 2048). A JPEG is unpacked already smaller, so a phone photo fits; a PNG or a WebP
# is unpacked whole first, and at 40 Mpx a WebP took 600 MB of memory
MAX_UNPACKED_PIXELS = 2048 * 2048
# Formats accepted, as Pillow names them
FORMATS = ("PNG", "JPEG", "WEBP")
# Biggest cover that is kept, in px: twice the cover of a work's page, sharp on a retina screen. Never cropped
MAX_WIDTH = 600
MAX_HEIGHT = 900
# EXIF tag of how a phone was held, and its values for a photo turned a quarter: its width is its height on screen
ORIENTATION = 0x0112
TURNED = (5, 6, 7, 8)
# Quality of the WebP kept, from 0 to 100: higher only makes the file bigger
QUALITY = 85


# The cover as it is kept: as big as MAX_WIDTH x MAX_HEIGHT allows without cropping it, and WebP. Saving it again drops
# the EXIF data (the GPS position of a phone photo). None when it isn't a PNG, JPEG or WebP, or is too big.
# Shrunk before anything else: turned and converted at full size, a phone photo took 600 MB of memory
def make_cover(content: bytes) -> bytes | None:
    try:
        with Image.open(io.BytesIO(content), formats=FORMATS) as image:
            # Only the header has been read: the size is checked before unpacking the pixels
            if image.width * image.height > MAX_PIXELS:
                return None
            # The box it has to fit in, on the sides as they are stored: a photo turned a quarter is turned upright only
            # after shrinking it, so the box is turned too
            turned = image.getexif().get(ORIENTATION) in TURNED
            width, height = (MAX_HEIGHT, MAX_WIDTH) if turned else (MAX_WIDTH, MAX_HEIGHT)
            # A JPEG is unpacked already smaller, never under the size that is kept
            image.draft("RGB", (width, height))
            # The size it will be unpacked at: the one of the file but for a JPEG
            if image.width * image.height > MAX_UNPACKED_PIXELS:
                return None
            # Any other one, shrunk once unpacked, keeping its shape
            scale = min(width / image.width, height / image.height)
            small = image.resize((round(image.width * scale), round(image.height * scale))) if scale < 1 else image
            # A phone photo stores how it was held: turned, or it could end up sideways
            upright = ImageOps.exif_transpose(small)
            output = io.BytesIO()
            upright.convert("RGBA").save(output, "WEBP", quality=QUALITY)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        # Not an image, a broken one (a broken part of a PNG is a SyntaxError), one with a part that unpacks too big
        # (ValueError) or one of the formats not accepted
        return None


# The uploaded cover as it is kept, or None if it can't be one (see make_cover). Read up to one byte over the limit:
# enough to know it's too big without reading the rest. Pillow works in a thread: unpacking an image takes a while
# and would stop the event loop
async def read_cover(upload: UploadFile) -> bytes | None:
    content = await upload.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        return None
    return await asyncio.to_thread(make_cover, content)
