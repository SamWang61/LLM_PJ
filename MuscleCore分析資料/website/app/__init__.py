import os
from flask import Flask
from dotenv import load_dotenv

from .db import init_db


def create_app(test_config=None):
    # Select an ignored local profile explicitly without replacing the legacy .env.
    profile = os.getenv("APP_ENV_FILE")
    if profile:
        from pathlib import Path
        if not Path(profile).is_file():
            raise ValueError("APP_ENV_FILE does not exist")
    load_dotenv(dotenv_path=profile)
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-secret"),
        MONGO_URI=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
        MONGO_DB=os.getenv("MONGO_DB", "musclecore"),
        DATA_MODE=os.getenv("DATA_MODE", "legacy"),
        ENABLE_CHECKOUT=os.getenv("ENABLE_CHECKOUT", "false").lower() == "true",
        AI_RECOMMENDATIONS_ENABLED=os.getenv("AI_RECOMMENDATIONS_ENABLED", "false").lower() == "true",
        AI_SUMMARY_ENABLED=os.getenv("AI_SUMMARY_ENABLED", "false").lower() == "true",
        BGE_MODEL=os.getenv("BGE_MODEL", "BAAI/bge-small-zh-v1.5"),
        ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY", ""),
        CLAUDE_MODEL=os.getenv("CLAUDE_MODEL", ""),
        AI_INSIGHT_RATE_LIMIT=int(os.getenv("AI_INSIGHT_RATE_LIMIT", "6")),
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    init_db(app)
    if app.config["DATA_MODE"] not in {"legacy", "v4"}:
        raise ValueError("DATA_MODE must be legacy or v4")
    from .security import init_security
    init_security(app)
    from pymongo.errors import PyMongoError

    @app.errorhandler(PyMongoError)
    def database_unavailable(error):
        app.logger.warning("Database request unavailable (%s)", type(error).__name__)
        return {"error": "資料庫暫時無法使用，請稍後重試。"}, 503

    from .auth import bp as auth_bp
    if app.config["DATA_MODE"] == "v4":
        from .store_v4 import bp as store_bp
    else:
        from .store import bp as store_bp
    from .admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(admin_bp)

    return app
