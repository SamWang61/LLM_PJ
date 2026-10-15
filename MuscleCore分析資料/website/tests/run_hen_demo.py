"""Local browser QA only: isolated in-memory store, never a real database."""
from test_v4_routes import shop

if __name__ == "__main__":
    app, _, _, _, _, _ = shop.__wrapped__()
    app.config.update(ENABLE_CHECKOUT=True, BEHAVIOR_SYNTHETIC_BATCH="hen-browser-20261014")
    app.run(host="127.0.0.1", port=5084, use_reloader=False)
