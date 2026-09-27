# VibeCart AI 資料層 / Data layer

本目錄包含新版 MongoDB Schema、遷移、稽核，以及購物車和評價服務。This component contains MongoDB schema definitions, migrations, audits, cart services and review services.

- [MongoDB 入口](MongoDB/README.md)：現行 v4 文件與歷史證據 / Current v4 guides and historical evidence.
- [SKU 購物車](services/sku_cart_service.py)：SKU 庫存、價格與交易式結帳 / SKU inventory, prices and transactional checkout.
- [評價服務](services/review_service.py)：購買驗證、唯一評價與評分更新 / Verified purchase, review uniqueness and rating updates.
- [舊購物車基底](services/cart_service.py)：歷史 v3 服務與共用交易輔助 / Historical v3 implementation and shared helpers.

Flask 展示網站位於其他目錄，尚未接線本服務。不要直接對正式 Atlas 執行舊版 seed 或測試。The Flask demo is not wired to these services; do not run legacy seeds or tests against production Atlas.
