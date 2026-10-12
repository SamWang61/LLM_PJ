"""Local anonymous QA server; image fault injection changes HTML, never Atlas."""
import argparse
import os
from pathlib import Path
import re
import secrets
import sys

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "MuscleCore分析資料" / "website"))
from cloud_runtime import create_cloud_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=5093)
    parser.add_argument("--break-images", action="store_true")
    args = parser.parse_args()
    os.environ["MONGO_URI"] = dotenv_values(args.env_file).get("MONGO_URI", "")
    os.environ["SECRET_KEY"] = secrets.token_hex(32)
    os.environ["CLOUD_PREVIEW_READ_ONLY"] = "true"
    app = create_cloud_app()

    if args.break_images:
        @app.after_request
        def break_image_sources(response):
            if response.mimetype == "text/html":
                response.set_data(re.sub(
                    r'(<img\b[^>]*\bsrc=")[^"]+("[^>]*>)',
                    r'\1/static/qa-intentionally-missing.jpg\2',
                    response.get_data(as_text=True),
                ))
            return response

    app.run(host="127.0.0.1", port=args.port, debug=False)


if __name__ == "__main__":
    main()
