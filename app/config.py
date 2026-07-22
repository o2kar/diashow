import os
from pathlib import Path


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

    DATA_DIR = Path(os.environ.get("DATA_DIR", "./data")).resolve()
    SLIDESHOWS_DIR = DATA_DIR / "slideshows"

    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4"}
    ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

    DEFAULT_IMAGE_DURATION_SECONDS = 8

    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30  # 30 days

    WTF_CSRF_TIME_LIMIT = None
