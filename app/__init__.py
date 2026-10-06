"""Application factory."""
import os
from flask import Flask, g
from config import Config
from . import api, auth, main, services
from .db import close_db, init_schema
from .security import check_csrf, csrf_token, load_user


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    if app.config["SECRET_KEY"] == "dev-only-change-me" and not app.config.get("TESTING"):
        app.logger.warning("Using the default SECRET_KEY - set the SECRET_KEY environment variable for real deployments.")

    if not os.path.exists(app.config["DATABASE"]):
        init_schema(app.config["DATABASE"])          # empty tables; run scripts/init_db.py to load books

    services.init_engine_state(app)
    app.teardown_appcontext(close_db)
    app.before_request(load_user)
    app.before_request(check_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.filters["pretty_action"] = lambda a: {"view": "Viewed", "rate": "Rated", "unrate": "Removed rating of",
                                                         "favorite": "Added to favourites", "unfavorite": "Removed from favourites"}.get(a, a)

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)
    main.register_error_handlers(app)
    return app
