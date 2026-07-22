from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from . import storage
from .auth import login_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
def dashboard():
    slideshows = storage.list_slideshows()
    return render_template("admin_dashboard.html", slideshows=slideshows)


@bp.route("/slideshows/new", methods=["GET"])
@login_required
def new_slideshow_form():
    return render_template(
        "admin_slideshow_form.html",
        default_duration=current_app.config["DEFAULT_IMAGE_DURATION_SECONDS"],
    )


@bp.route("/slideshows", methods=["POST"])
@login_required
def create_slideshow():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name darf nicht leer sein.", "error")
        return redirect(url_for("admin.new_slideshow_form"))
    duration = request.form.get("image_duration_seconds", type=int)
    slideshow = storage.create_slideshow(name, image_duration_seconds=duration)
    flash(f"Slideshow „{slideshow['name']}“ erstellt.", "success")
    return redirect(url_for("admin.edit_slideshow", slug=slideshow["slug"]))


@bp.route("/slideshows/<slug>", methods=["GET"])
@login_required
def edit_slideshow(slug):
    try:
        slideshow = storage.get_slideshow(slug)
    except storage.SlideshowNotFound:
        flash("Slideshow nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard"))
    slideshow["media"].sort(key=lambda m: m["position"])
    player_url = url_for("player.show_player", slug=slug, _external=True)
    return render_template("admin_slideshow_edit.html", slideshow=slideshow, player_url=player_url)


@bp.route("/slideshows/<slug>", methods=["POST"])
@login_required
def update_slideshow(slug):
    name = request.form.get("name", "").strip()
    duration = request.form.get("image_duration_seconds", type=int)
    try:
        storage.update_slideshow(slug, name=name or None, image_duration_seconds=duration)
        flash("Gespeichert.", "success")
    except storage.SlideshowNotFound:
        flash("Slideshow nicht gefunden.", "error")
    return redirect(url_for("admin.edit_slideshow", slug=slug))


@bp.route("/slideshows/<slug>/delete", methods=["POST"])
@login_required
def delete_slideshow(slug):
    try:
        storage.delete_slideshow(slug)
        flash("Slideshow gelöscht.", "success")
    except storage.SlideshowNotFound:
        flash("Slideshow nicht gefunden.", "error")
    return redirect(url_for("admin.dashboard"))


@bp.route("/slideshows/<slug>/media", methods=["POST"])
@login_required
def upload_media(slug):
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        flash("Keine Dateien ausgewählt.", "error")
        return redirect(url_for("admin.edit_slideshow", slug=slug))

    uploaded, rejected = 0, []
    for f in files:
        if not f or f.filename == "":
            continue
        try:
            storage.add_media(slug, f)
            uploaded += 1
        except storage.InvalidFile:
            rejected.append(f.filename)
        except storage.SlideshowNotFound:
            flash("Slideshow nicht gefunden.", "error")
            return redirect(url_for("admin.dashboard"))

    if uploaded:
        flash(f"{uploaded} Datei(en) hochgeladen.", "success")
    if rejected:
        flash(
            "Nicht unterstützter Dateityp (nur png, jpg, jpeg, mp4): " + ", ".join(rejected),
            "error",
        )
    return redirect(url_for("admin.edit_slideshow", slug=slug))


@bp.route("/slideshows/<slug>/media/<media_id>/delete", methods=["POST"])
@login_required
def delete_media(slug, media_id):
    try:
        storage.delete_media(slug, media_id)
        flash("Datei gelöscht.", "success")
    except (storage.SlideshowNotFound, storage.MediaNotFound):
        flash("Datei/Slideshow nicht gefunden.", "error")
    return redirect(url_for("admin.edit_slideshow", slug=slug))


@bp.route("/slideshows/<slug>/media/reorder", methods=["POST"])
@login_required
def reorder_media(slug):
    data = request.get_json(silent=True) or {}
    order = data.get("order")
    if not isinstance(order, list):
        return jsonify({"error": "invalid payload"}), 400
    try:
        storage.reorder_media(slug, order)
    except storage.SlideshowNotFound:
        return jsonify({"error": "slideshow not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})
