from flask import Flask
from flask_wtf import CSRFProtect

from .config import Config

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.config["SLIDESHOWS_DIR"].mkdir(parents=True, exist_ok=True)

    csrf.init_app(app)

    from . import admin, auth, player

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(player.bp)

    from flask import redirect, url_for

    @app.route("/")
    def index():
        return redirect(url_for("admin.dashboard"))

    @app.errorhandler(404)
    def not_found(_e):
        from flask import render_template

        return render_template("404.html"), 404

    return app
