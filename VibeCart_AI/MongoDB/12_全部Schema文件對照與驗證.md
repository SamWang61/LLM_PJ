> 歷史版本：2026-09-19 已更新為 Complete Schema v4。現行架構與執行入口以 [15](15_完整Schema_v4架構與遷移.md) 及 [16](16_完整Schema_v4驗證與欄位字典.md) 為準；以下數字與命令描述原查核時點。

# 全部 Schema 文件對照與實際查核

查核時間：2026-09-18T11:41:49.970264+00:00

**14/14 集合、14/14 strict/error validators、31 個自訂索引（含 12 個 unique、2 個 TTL），共 45 個索引，均已建立並讀回吻合。**

本次 66 項實際 Atlas 測試通過；失敗 0、錯誤 0，耗時 73.140 秒。含 51 項全集合與條件欄位測試、15 項購物車回歸測試。詳見 [原始測試結果](schema_complete_test_results.xml)。

Atlas 外掛本次回 UNAUTHORIZED（OAuth 需重新登入）；改用先前授權的 PyMongo 資料庫帳號實際查核與 collMod。未重試登入憑證、未更改 Atlas 組織／Cluster／方案。

## 文件依據與優先序

購物車更新文件優先覆蓋原 carts 設計；未衝突部分沿用整合 v1.1。兩份原始文件均完整保留，沒有為了讓查核通過而改寫來源規格。

- [02_專案整合規格_v1.1_來源快照.md](02_專案整合規格_v1.1_來源快照.md)，SHA-256：`62f0f095b84d913ca0010d4c312ae0066640db5eab10724ae375d6176d6c0ddc`
- [07_購物車更新規格_來源快照.md](07_購物車更新規格_來源快照.md)，SHA-256：`dd5c913e1da27a9db517e9df6be58a6b3990170de0ef04c8b35dd4be9a353a54`

## 集合完成清單

|集合|文件章節|版本|驗證|自訂索引|文件數／合規數|
|---|---|---|---|---|---|
|users|整合 v1.1 §5.1|2|strict/error，吻合|2|0/0|
|categories|整合 v1.1 §5.2|2|strict/error，吻合|2|0/0|
|products|整合 v1.1 §5.3|2|strict/error，吻合|3|0/0|
|carts|購物車更新 §4、§8|3|strict/error，吻合|4|0/0|
|orders|整合 v1.1 §5.5|2|strict/error，吻合|5|0/0|
|user_events|整合 v1.1 §5.6|2|strict/error，吻合|4|0/0|
|ai_requests|整合 v1.1 §5.7|2|strict/error，吻合|2|0/0|
|product_embeddings|整合 v1.1 §6.1|2|strict/error，吻合|1|0/0|
|recommendations|整合 v1.1 §6.2|2|strict/error，吻合|1|0/0|
|ai_insights|整合 v1.1 §6.3|2|strict/error，吻合|1|0/0|
|ai_usage|整合 v1.1 §6.4|2|strict/error，吻合|0|0/0|
|request_limits|整合 v1.1 §6.4|2|strict/error，吻合|1|0/0|
|schema_migrations|整合 v1.1 §6.4|2|strict/error，吻合|0|3/3|
|cart_events|購物車更新 §5、§8|3|strict/error，吻合|5|0/0|

額外集合：無。所有既有文件亦使用目前 validator 查詢核對，未發現不合規文件。

## 本次補強

- users：budget_min/max 非負、有限、最多兩位小數；保留 null 及 min≤max。
- user_events：recommendation_click 必須有 product_id。
- ai_requests：running 必須有 started_at；succeeded 必須有 started_at 與 actual_provider；實際模型執行須有非空 model_name/revision；Anthropic sales_summary 執行須有非空 Prompt 名稱／版本。執行前失敗仍允許未知模型與開始時間為 null。
- ai_requests：estimated_cost 拒絕 Infinity／NaN／負值，保留微小 USD 成本的小數精度，不硬四捨五入到分。
- recommendations：BGE 策略的 model/revision 不接受空字串。

新遷移：20260918_03_schema_document_constraints；僅增加驗證規則，文件形狀與 schema_version 不變，舊兩筆遷移及其 checksum 不變。預檢後才套用；沒有回填／覆寫／刪除業務資料、没有重設配額。

## 明確採用的範圍解讀

- 購物車文件允許 ObjectId/String、Decimal/Double，本專案選用原整合規格較一致的 ObjectId＋Decimal128；沿用 20 品項及數量 1～99。
- 新資料環境使用 local 登入；Firebase 尚未啟用，local password_hash 必填。歷史訂單無商品、舊 AI 快取無請求關聯等例外屬舊資料遷移，不以放寬全部新文件 validator 代替；本次無此類既有資料。
- ai_usage、request_limits、schema_migrations 的時間欄位依 §6.4 技術集合專用字典，不額外發明歷史 created_at。
- cart_events 的事件代碼可擴充，已定義五種事件才有特定前後數量條件；事件本身無 TTL。

## Schema 與應用服務界線

此報告確認資料庫結構與可由 DB 驗證的規則；不代表全部網站或 AI 功能已完成。以下屬跨文件、來源真實性或流程規則，必須由應用服務保證：

- 參照的會員／商品／分類是否存在且有效、登入 owner／角色、密碼雜湊、CSRF、前端不能自填管理欄位。
- URL 與 metadata/input_summary/parameters 的語意白名單、資料去識別化；DB 已限制型別與文件規定的大小，但不會辨認個資語意。
- Prompt／模型 revision 真實性、embedding hash／模型版本一致性／正規化、推薦與行為權重、成本只統計 leaf。
- cart_events append-only 由服務遵守；目前 readWrite 帳號不是不可變稽核儲存，仍有更新／刪除權限。
- TTL 是背景清除，不保證瞬間刪除；快取與限流讀取仍須比較 expires_at。
- 舊 Flask 頁面與 Session 購物車尚未接線，不將 Schema 驗證通過宣稱為全站驗收。

## 後續唯一現行驗證入口

```powershell
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' 'VibeCart_AI\MongoDB\audit_schema.py'
```

現行定義為 schema_current.py。新環境依序執行 bootstrap_schema.py、migrate_cart_v3.py、migrate_schema_audit.py；已升級環境使用最後遷移與 audit_schema.py，不以歷史版本驗證器覆蓋現況。

## 逐欄位字典（由 Atlas 已吻合的現行定義輸出）

### users

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|display_name|string|是|{"maxLength": 100, "minLength": 1}|
|email|string|是|{"pattern": "^[^\\sA-Z]+$", "minLength": 1}|
|auth_provider|enum|是|{"enum": ["local"]}|
|password_hash|string|是|{"minLength": 1}|
|firebase_uid|string/null|是|—|
|role|enum|是|{"enum": ["customer", "admin"]}|
|is_active|bool|是|—|
|preferences|object|是|—|
|preferences.category_ids|array|是|{"minItems": 0, "maxItems": 10, "uniqueItems": true}|
|preferences.tags|array|是|{"minItems": 0, "maxItems": 20, "uniqueItems": true}|
|preferences.budget_min|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|preferences.budget_max|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|preferences.updated_at|date/null|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### categories

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|name|string|是|{"maxLength": 100, "minLength": 1}|
|slug|string|是|{"pattern": "^[a-z0-9-]+$", "maxLength": 100, "minLength": 1}|
|description|string/null|是|{"maxLength": 1000}|
|sort_order|int|是|{"minimum": 0}|
|is_active|bool|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### products

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|category_id|objectId|是|—|
|name|string|是|{"maxLength": 200, "minLength": 1}|
|description|string|是|{"maxLength": 5000, "minLength": 1}|
|sku|string|是|{"pattern": "^[^a-z\\s]+$", "maxLength": 64, "minLength": 1}|
|brand|string/null|是|{"maxLength": 100}|
|size|string/null|是|{"maxLength": 100}|
|color|string/null|是|{"maxLength": 100}|
|price|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|sale_price|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|currency|enum|是|{"enum": ["TWD"]}|
|stock_quantity|int|是|{"minimum": 0}|
|safety_stock|int|是|{"minimum": 0}|
|tags|array|是|{"minItems": 0, "maxItems": 20, "uniqueItems": true}|
|image_urls|array|是|{"minItems": 0, "maxItems": 10, "uniqueItems": false}|
|is_active|bool|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### carts

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [3]}|
|user_id|objectId|是|—|
|status|enum|是|{"enum": ["active", "converted", "abandoned"]}|
|revision|int|是|{"minimum": 0}|
|items|array|是|{"minItems": 0, "maxItems": 20, "uniqueItems": false}|
|items[].product_id|objectId|是|—|
|items[].quantity|int|是|{"minimum": 1, "maximum": 99}|
|items[].price_snapshot|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|items[].added_at|date|是|—|
|items[].updated_at|date|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### orders

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|order_number|string|是|{"minLength": 1}|
|user_id|objectId|是|—|
|checkout_id|string|是|{"minLength": 1}|
|request_hash|string|是|{"pattern": "^[a-f0-9]{64}$", "maxLength": 64, "minLength": 64}|
|status|enum|是|{"enum": ["pending", "confirmed", "shipping", "completed", "cancelled"]}|
|payment_status|enum|是|{"enum": ["unpaid", "paid", "failed", "refunded"]}|
|is_demo|bool|是|—|
|currency|enum|是|{"enum": ["TWD"]}|
|items|array|是|{"minItems": 1, "maxItems": 20, "uniqueItems": false}|
|items[].product_id|objectId|是|—|
|items[].product_name|string|是|{"maxLength": 200, "minLength": 1}|
|items[].sku|string|是|{"maxLength": 64, "minLength": 1}|
|items[].size|string/null|是|{"maxLength": 100}|
|items[].color|string/null|是|{"maxLength": 100}|
|items[].unit_price|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|items[].quantity|int|是|{"minimum": 1, "maximum": 99}|
|items[].subtotal_amount|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|subtotal_amount|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|discount_amount|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|shipping_fee|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|total_amount|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|shipping_address|null|是|—|
|paid_at|date/null|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### user_events

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|event_id|string|是|{"minLength": 1}|
|user_id|objectId/null|是|—|
|session_id|string|是|{"maxLength": 128, "minLength": 1}|
|event_type|enum|是|{"enum": ["product_view", "product_search", "add_to_cart", "remove_from_cart", "purchase", "recommendation_impression", "recommendation_click"]}|
|product_id|objectId/null|是|—|
|order_id|objectId/null|是|—|
|recommendation_id|objectId/null|是|—|
|search_query|string/null|是|{"maxLength": 200, "minLength": 1}|
|event_metadata|object|是|—|
|created_at|date|是|—|

### ai_requests

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|user_id|objectId/null|是|—|
|parent_request_id|objectId/null|是|—|
|task_type|enum|是|{"enum": ["product_embedding", "product_recommendation", "sales_summary"]}|
|execution_mode|enum|是|{"enum": ["local", "api", "hybrid", "baseline"]}|
|requested_provider|enum|是|{"enum": ["huggingface", "anthropic", "rules", "pipeline"]}|
|actual_provider|enum|是|{"enum": ["huggingface", "anthropic", "rules", "pipeline", null]}|
|model_name|string/null|是|—|
|model_revision|string/null|是|—|
|prompt_name|string/null|是|—|
|prompt_version|string/null|是|—|
|status|enum|是|{"enum": ["queued", "running", "succeeded", "failed", "timeout"]}|
|is_success|bool/null|是|—|
|input_text|string/null|是|{"maxLength": 8000}|
|output_text|string/null|是|{"maxLength": 8000}|
|input_summary|object|是|—|
|parameters|object|是|—|
|latency_ms|int/null|是|{"minimum": 0}|
|input_tokens|int/null|是|{"minimum": 0}|
|output_tokens|int/null|是|{"minimum": 0}|
|token_count|int/null|是|{"minimum": 0}|
|estimated_cost|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|cost_currency|enum|是|{"enum": ["USD", null]}|
|is_cache_hit|bool|是|—|
|fallback_reason|string/null|是|—|
|error_code|string/null|是|—|
|started_at|date/null|是|—|
|completed_at|date/null|是|—|
|created_at|date|是|—|

### product_embeddings

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|product_id|objectId|是|—|
|model|enum|是|{"enum": ["BAAI/bge-small-zh-v1.5"]}|
|revision|string|是|{"minLength": 1}|
|vector|array|是|{"minItems": 512, "maxItems": 512, "uniqueItems": false}|
|dimension|int|是|{"enum": [512]}|
|content_hash|string|是|{"pattern": "^[a-f0-9]{64}$", "maxLength": 64, "minLength": 64}|
|preprocessing_version|string|是|{"minLength": 1}|
|is_normalized|bool|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### recommendations

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [2]}|
|user_id|objectId/null|是|—|
|session_id|string|是|{"maxLength": 128, "minLength": 1}|
|source_product_id|objectId/null|是|—|
|ai_request_id|objectId|是|—|
|strategy|enum|是|{"enum": ["baseline", "bge_similar", "bge_personalized"]}|
|model|string/null|是|—|
|revision|string/null|是|—|
|items|array|是|{"minItems": 0, "maxItems": 10, "uniqueItems": false}|
|items[].product_id|objectId|是|—|
|items[].rank|int|是|{"minimum": 1, "maximum": 10}|
|items[].score|double|是|{"minimum": -1.7976931348623157e+308, "maximum": 1.7976931348623157e+308}|
|items[].reason|string|是|{"maxLength": 500, "minLength": 1}|
|created_at|date|是|—|

### ai_insights

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|ai_request_id|objectId|是|—|
|task_type|enum|是|{"enum": ["sales_summary"]}|
|period_start|date|是|—|
|period_end|date|是|—|
|report_timezone|enum|是|{"enum": ["Asia/Taipei"]}|
|is_demo|enum|是|{"enum": [true]}|
|input_summary|object|是|—|
|text|string|是|{"maxLength": 8000, "minLength": 1}|
|model|string|是|{"minLength": 1}|
|prompt_version|string|是|{"minLength": 1}|
|usage|object|是|—|
|elapsed_ms|int/null|是|{"minimum": 0}|
|expires_at|date|是|—|
|created_at|date|是|—|

### ai_usage

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|count|int|是|{"minimum": 0}|
|updated_at|date|是|—|

### request_limits

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|count|int|是|{"minimum": 0}|
|expires_at|date|是|—|

### schema_migrations

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|checksum|string|是|{"pattern": "^[a-f0-9]{64}$", "maxLength": 64, "minLength": 64}|
|status|enum|是|{"enum": ["running", "succeeded", "failed"]}|
|started_at|date|是|—|
|completed_at|date/null|是|—|
|counts|object|是|—|
|counts.source|int|是|{"minimum": 0}|
|counts.target|int|是|{"minimum": 0}|
|counts.errors|int|是|{"minimum": 0}|
|error_code|string/null|是|—|

### cart_events

|欄位|BSON 型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [3]}|
|cart_id|objectId|是|—|
|user_id|objectId|是|—|
|operation_id|string|是|{"maxLength": 128, "minLength": 1}|
|request_hash|string|是|{"pattern": "^[a-f0-9]{64}$", "maxLength": 64, "minLength": 64}|
|event_type|string|是|{"pattern": "^[A-Z][A-Z0-9_]*$", "maxLength": 40, "minLength": 1}|
|product_id|objectId/null|是|—|
|quantity_before|int/null|是|{"minimum": 0, "maximum": 99}|
|quantity_after|int/null|是|{"minimum": 0, "maximum": 99}|
|price_snapshot|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|event_at|date|是|—|
|metadata|object|是|—|
|created_at|date|是|—|

