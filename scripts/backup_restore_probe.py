"""Container-only restored-source boot probe with disposable local BSON fixtures.

Run on a Docker internal network with read-only restored source mounts. This is
not an Atlas export, Atlas restoration, production acceptance or a cloud deploy.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from urllib.request import urlopen
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restored-root", type=Path, required=True)
    args = parser.parse_args()
    if not Path("/.dockerenv").exists() or os.environ.get("SAM_BACKUP_INTERNAL_PROBE") != "true":
        parser.error("Requires the dedicated internal Docker acceptance container")
    root = args.restored_root.resolve(strict=True)
    website = root / "MuscleCore分析資料/website"
    # Do not execute any .env, restored virtualenv, cloud factory or startup script.
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False
    sys.path[:0] = [str(website), str(root)]
    from bson import BSON, Decimal128, ObjectId, decode_all
    from bson.json_util import CANONICAL_JSON_OPTIONS, dumps
    from pymongo import MongoClient
    from werkzeug.serving import make_server
    import app as restored_app
    assert Path(restored_app.__file__).resolve().is_relative_to(website)
    name = "sam_backup_restore_" + uuid4().hex
    # Fixed network alias, no credentials, DNS SRV or configurable Atlas URI.
    client = MongoClient("mongodb://backup-db:27017/", serverSelectionTimeoutMS=5000)
    db = client[name]
    server = None
    report = {"target": "disposable internal Docker MongoDB",
              "scope": "historical restored source and three local fixture collections",
              "dotenv_loaded": False, "atlas_export_or_restore": False}

    def snapshot():
        return {coll: hashlib.sha256(dumps(list(db[coll].find().sort("_id")),
                    json_options=CANONICAL_JSON_OPTIONS, sort_keys=True).encode()).hexdigest()
                for coll in ("categories", "products", "product_skus")}

    try:
        category, product, sku = (ObjectId() for _ in range(3))
        fixtures = {
            "categories": [{"_id": category, "schema_version": 4,
                            "name": "Restored fixture", "status": "active"}],
            "products": [{"_id": product, "schema_version": 4,
                          "product_code": "BACKUP-ONLY", "product_name": "Restored fixture",
                          "major_category_id": category, "minor_category_id": category,
                          "category_path": ["restore", "test"], "status": "active",
                          "average_rating_display": 4.0, "description": "Local restore probe",
                          "is_ai_recommendable": False}],
            "product_skus": [{"_id": sku, "schema_version": 4, "product_id": product,
                              "sku_code": "BACKUP-ONLY-1", "variant_attributes": {},
                              "status": "active", "price": Decimal128("10.25"),
                              "available_quantity": 10, "stock_quantity": 10,
                              "reserved_quantity": 0, "safety_stock": 2}]}
        for coll, docs in fixtures.items():
            db[coll].insert_many(docs)
        db.product_skus.create_index("sku_code", unique=True, name="restore_sku_unique")
        before = snapshot()
        with tempfile.TemporaryDirectory(prefix="sam-backup-bson-") as temporary:
            export = Path(temporary)
            for coll in fixtures:
                (export / (coll + ".bson")).write_bytes(
                    b"".join(BSON.encode(doc) for doc in db[coll].find()))
            client.drop_database(name)
            assert name not in client.list_database_names()
            for coll in fixtures:
                db[coll].insert_many(decode_all((export / (coll + ".bson")).read_bytes()))
            db.product_skus.create_index("sku_code", unique=True, name="restore_sku_unique")
        assert snapshot() == before
        assert db.product_skus.index_information()["restore_sku_unique"]["unique"]
        report["bson_restore"] = {"collections": 3, "documents": 3,
                                  "hash_differences": 0, "unique_index_restored": True}
        app = restored_app.create_app({
            "TESTING": True, "DATA_MODE": "v4", "MONGO_DB": name,
            "MONGO_URI": "mongodb://backup-db:27017/", "SECRET_KEY": "isolated-backup-boot-only",
            "ENABLE_CHECKOUT": False, "AI_RECOMMENDATIONS_ENABLED": False,
            "AI_SUMMARY_ENABLED": False, "AI_FREE_QUESTION_ENABLED": False,
            "ANTHROPIC_API_KEY": ""})
        server = make_server("127.0.0.1", 0, app)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        status = {}
        for path in ("/", "/product/" + str(product), "/auth/login", "/static/css/main.css"):
            with urlopen("http://127.0.0.1:" + str(server.server_port) + path, timeout=10) as response:
                status[path.split(str(product))[0]] = response.status
                assert response.status == 200
                assert response.read()
        report["restored_http"] = status
        assert snapshot() == before
        report["boot_readback_differences"] = 0
        report["status"] = "passed"
    finally:
        if server:
            server.shutdown()
            server.server_close()
        client.drop_database(name)
        report["fixture_database_removed"] = name not in client.list_database_names()
        client.close()
    print(json.dumps(report))


if __name__ == "__main__":
    main()
