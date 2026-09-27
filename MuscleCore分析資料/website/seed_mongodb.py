"""One command creates collections, validators, indexes, users and demo data."""
import os
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING, MongoClient
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("MONGO_DB", "musclecore")]
now = datetime.now(timezone.utc)

validators = {
    "users": {"$jsonSchema": {"bsonType": "object", "required": ["name", "email", "password_hash", "role"],
        "properties": {"role": {"enum": ["customer", "admin"]}, "email": {"bsonType": "string"}}}},
    "products": {"$jsonSchema": {"bsonType": "object", "required": ["sku", "name", "category", "price", "stock"],
        "properties": {"price": {"bsonType": ["int", "long", "double", "decimal"]}, "stock": {"bsonType": "int"}}}},
    "orders": {"$jsonSchema": {"bsonType": "object", "required": ["order_no", "user_id", "items", "total", "status"]}},
    "behavior_events": {"$jsonSchema": {"bsonType": "object", "required": ["user_id", "product_id", "event_type", "created_at"],
        "properties": {"event_type": {"enum": ["view", "favorite", "cart", "purchase"]}}}},
}
for name, validator in validators.items():
    if name not in db.list_collection_names():
        db.create_collection(name, validator=validator)
    else:
        db.command("collMod", name, validator=validator, validationLevel="moderate")

db.users.create_index([("email", ASCENDING)], unique=True)
db.products.create_index([("sku", ASCENDING)], unique=True)
db.products.create_index([("name", "text"), ("description", "text")])
db.products.create_index([("category", ASCENDING), ("is_active", ASCENDING)])
db.orders.create_index([("order_no", ASCENDING)], unique=True)
db.orders.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
db.behavior_events.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

users = [
    {"name": "MuscleCore 管理員", "email": "admin@musclecore.tw", "password": "Admin123!", "role": "admin"},
    {"name": "示範會員", "email": "demo@musclecore.tw", "password": "Demo123!", "role": "customer"},
]
for u in users:
    db.users.update_one({"email": u["email"]}, {"$setOnInsert": {"name": u["name"], "email": u["email"],
        "password_hash": generate_password_hash(u["password"]), "role": u["role"], "is_active": True,
        "preferences": {"categories": [], "goals": []}, "created_at": now, "updated_at": now}}, upsert=True)

products = [
    ("MC-DB-001", "六角包膠啞鈴 10KG", "重量訓練", 1280, 18, 4.9, 186, "防滾六角造型，居家與健身房皆適用。"),
    ("MC-KB-001", "競技壺鈴 16KG", "重量訓練", 1680, 4, 4.8, 142, "穩定握把與標準尺寸，適合擺盪及全身訓練。"),
    ("MC-YG-001", "專業止滑瑜珈墊", "瑜珈健身", 990, 26, 4.7, 121, "高密度緩衝，乾濕止滑，附收納背帶。"),
    ("MC-RB-001", "五段式阻力帶組", "機能配件", 680, 42, 4.6, 98, "五種阻力可自由組合，適合熱身與肌力恢復。"),
    ("MC-SH-001", "疾速緩震訓練鞋", "運動鞋款", 2380, 12, 4.8, 210, "穩定支撐與回彈中底，支援多方向訓練。"),
    ("MC-WB-001", "保冷運動水壺 750ml", "機能配件", 520, 3, 4.5, 75, "食品級不鏽鋼，長效保冷與單手快開。"),
]
for sku, name, category, price, stock, rating, sales, description in products:
    db.products.update_one({"sku": sku}, {"$setOnInsert": {"sku": sku, "name": name, "category": category,
        "price": price, "stock": stock, "low_stock_threshold": 5, "rating": rating, "sales_count": sales,
        "description": description, "is_active": True, "created_at": now, "updated_at": now}}, upsert=True)

print("MuscleCore MongoDB 初始化完成：4 個集合、索引、2 個帳號、6 項商品。")
client.close()

