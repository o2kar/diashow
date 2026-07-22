from flask import Blueprint, abort, jsonify, render_template, send_from_directory, url_for

from . import storage

bp = Blueprint("player", __name__)


@bp.route("/show/<slug>")
def show_player(slug):
    if not storage.slideshow_exists(slug):
        abort(404)
    return render_template("player.html", slug=slug)


@bp.route("/api/show/<slug>")
def show_data(slug):
    try:
        slideshow = storage.get_slideshow(slug)
    except storage.SlideshowNotFound:
        abort(404)

    media = sorted(slideshow["media"], key=lambda m: m["position"])
    return jsonify(
        {
            "name": slideshow["name"],
            "image_duration_seconds": slideshow["image_duration_seconds"],
            "media": [
                {
                    "id": m["id"],
                    "type": m["type"],
                    "url": url_for("player.media_file", slug=slug, filename=m["filename"]),
                    "position": m["position"],
                }
                for m in media
            ],
        }
    )


@bp.route("/media/<slug>/<filename>")
def media_file(slug, filename):
    try:
        slideshow = storage.get_slideshow(slug)
    except storage.SlideshowNotFound:
        abort(404)

    if not any(m["filename"] == filename for m in slideshow["media"]):
        abort(404)

    response = send_from_directory(storage.media_dir(slug), filename)
    response.headers["Cache-Control"] = "public, max-age=604800"
    return response


@bp.route("/healthz")
def healthz():
    return "OK", 200
