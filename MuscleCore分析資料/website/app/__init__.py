import os
from flask import Flask
from dotenv import load_dotenv

from .db import init_db


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-secret"),
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
        MONGO_DB=os.getenv("MONGO_DB", "musclecore"),
    )
    if test_config:
        app.config.update(test_config)

    init_db(app)

    from .auth import bp as auth_bp
    from .store import bp as store_bp
    from .admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(admin_bp)

    return app

