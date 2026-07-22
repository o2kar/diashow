import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone

from flask import current_app

from .utils import allowed_filename, extension_of, media_type_for_filename, slugify

_locks_guard = threading.Lock()
_slug_locks: dict[str, threading.Lock] = {}


class SlideshowNotFound(Exception):
    pass


class MediaNotFound(Exception):
    pass


class InvalidFile(Exception):
    pass


def _lock_for(slug: str) -> threading.Lock:
    with _locks_guard:
        lock = _slug_locks.get(slug)
        if lock is None:
            lock = threading.Lock()
            _slug_locks[slug] = lock
        return lock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slideshows_dir():
    return current_app.config["SLIDESHOWS_DIR"]


def _slideshow_dir(slug: str):
    return _slideshows_dir() / slug


def _media_dir(slug: str):
    return _slideshow_dir(slug) / "media"


def _config_path(slug: str):
    return _slideshow_dir(slug) / "config.json"


def _write_json_atomic(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _read_config(slug: str) -> dict:
    path = _config_path(slug)
    if not path.exists():
        raise SlideshowNotFound(slug)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slideshow_exists(slug: str) -> bool:
    return _config_path(slug).exists()


def media_dir(slug: str):
    return _media_dir(slug)


def list_slideshows() -> list[dict]:
    slideshows_dir = _slideshows_dir()
    if not slideshows_dir.exists():
        return []
    results = []
    for entry in sorted(slideshows_dir.iterdir()):
        if entry.is_dir() and (entry / "config.json").exists():
            with _lock_for(entry.name):
                results.append(_read_config(entry.name))
    results.sort(key=lambda s: s["created_at"])
    return results


def get_slideshow(slug: str) -> dict:
    with _lock_for(slug):
        return _read_config(slug)


def _unique_slug(base: str) -> str:
    slug = base
    n = 2
    while slideshow_exists(slug):
        slug = f"{base}-{n}"
        n += 1
    return slug


def create_slideshow(name: str, image_duration_seconds: int | None = None) -> dict:
    base = slugify(name)
    slug = _unique_slug(base)
    lock = _lock_for(slug)
    with lock:
        now = _now()
        config = {
            "id": slug,
            "slug": slug,
            "name": name.strip() or slug,
            "image_duration_seconds": image_duration_seconds
            or current_app.config["DEFAULT_IMAGE_DURATION_SECONDS"],
            "created_at": now,
            "updated_at": now,
            "media": [],
        }
        _media_dir(slug).mkdir(parents=True, exist_ok=True)
        _write_json_atomic(_config_path(slug), config)
        return config


def update_slideshow(slug: str, name: str | None = None, image_duration_seconds: int | None = None) -> dict:
    with _lock_for(slug):
        config = _read_config(slug)
        if name is not None and name.strip():
            config["name"] = name.strip()
        if image_duration_seconds is not None:
            config["image_duration_seconds"] = max(1, int(image_duration_seconds))
        config["updated_at"] = _now()
        _write_json_atomic(_config_path(slug), config)
        return config


def delete_slideshow(slug: str) -> None:
    with _lock_for(slug):
        slideshow_dir = _slideshow_dir(slug)
        if not slideshow_dir.exists():
            raise SlideshowNotFound(slug)
        shutil.rmtree(slideshow_dir)
    with _locks_guard:
        _slug_locks.pop(slug, None)


def add_media(slug: str, file_storage) -> dict:
    filename = file_storage.filename or ""
    if not allowed_filename(filename):
        raise InvalidFile(filename)

    with _lock_for(slug):
        config = _read_config(slug)
        media_id = uuid.uuid4().hex
        ext = extension_of(filename)
        stored_filename = f"{media_id}.{ext}"
        media_dir = _media_dir(slug)
        media_dir.mkdir(parents=True, exist_ok=True)
        file_storage.save(media_dir / stored_filename)

        item = {
            "id": media_id,
            "filename": stored_filename,
            "original_name": filename,
            "type": media_type_for_filename(filename),
            "uploaded_at": _now(),
            "position": len(config["media"]),
        }
        config["media"].append(item)
        config["updated_at"] = _now()
        _write_json_atomic(_config_path(slug), config)
        return item


def delete_media(slug: str, media_id: str) -> None:
    with _lock_for(slug):
        config = _read_config(slug)
        item = next((m for m in config["media"] if m["id"] == media_id), None)
        if item is None:
            raise MediaNotFound(media_id)

        file_path = _media_dir(slug) / item["filename"]
        if file_path.exists():
            file_path.unlink()

        remaining = [m for m in config["media"] if m["id"] != media_id]
        remaining.sort(key=lambda m: m["position"])
        for i, m in enumerate(remaining):
            m["position"] = i
        config["media"] = remaining
        config["updated_at"] = _now()
        _write_json_atomic(_config_path(slug), config)


def reorder_media(slug: str, ordered_ids: list[str]) -> dict:
    with _lock_for(slug):
        config = _read_config(slug)
        existing_ids = {m["id"] for m in config["media"]}
        if set(ordered_ids) != existing_ids or len(ordered_ids) != len(config["media"]):
            raise ValueError("order must contain exactly the existing media ids")

        by_id = {m["id"]: m for m in config["media"]}
        new_media = []
        for i, media_id in enumerate(ordered_ids):
            item = by_id[media_id]
            item["position"] = i
            new_media.append(item)
        config["media"] = new_media
        config["updated_at"] = _now()
        _write_json_atomic(_config_path(slug), config)
        return config
