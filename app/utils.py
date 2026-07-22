import re
import unicodedata

from flask import current_app


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "slideshow"


def allowed_filename(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def media_type_for_filename(filename: str) -> str:
    ext = filename.rsplit(".", 1)[1].lower()
    if ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return "image"
    return "video"


def extension_of(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower()
