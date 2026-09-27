# 完整 Schema v4 實際驗證與逐欄位字典

查核時間：2026-09-18T16:07:11.040893+00:00

**27 集合、27 strict/error validators、59 自訂索引、86 總索引；自訂唯一索引 24 個。**

TTL 僅：ai_insights, request_limits。新事件、評價、首推快照及統計集合不自動刪除。

新版測試：66 passed，耗時 58.969 秒；[JUnit XML](complete_v4_test_results.xml)。此結果是 Complete Schema v4 測試，不是之前的同數量 v2/v3 測試。

## 資料與遷移紀錄

|集合|定位|文件數|合規數|自訂索引|
|---|---|---|---|---|
|users|新版核心 v4|0|0|3|
|categories|新版核心 v4|0|0|2|
|products|新版核心 v4|0|0|4|
|carts|新版核心 v4|0|0|4|
|orders|新版核心 v4|0|0|5|
|user_events|保留既有|0|0|4|
|ai_requests|保留既有|0|0|2|
|product_embeddings|保留既有|0|0|1|
|recommendations|保留既有|0|0|1|
|ai_insights|保留既有|0|0|1|
|ai_usage|保留既有|0|0|0|
|request_limits|保留既有|0|0|1|
|schema_migrations|保留既有|4|4|0|
|cart_events|新版核心 v4|0|0|6|
|brands|新版核心 v4|0|0|2|
|product_skus|新版核心 v4|0|0|2|
|product_reviews|新版核心 v4|0|0|2|
|order_items|新版核心 v4|0|0|4|
|behavior_events|新版核心 v4|0|0|5|
|user_preference_scores|新版核心 v4|0|0|1|
|product_repurchase_stats|新版核心 v4|0|0|1|
|cross_category_rules|新版核心 v4|0|0|2|
|product_purchase_sequences|新版核心 v4|0|0|1|
|recommendation_pools|新版核心 v4|0|0|1|
|first_member_recommendations|新版核心 v4|0|0|1|
|recommendation_logs|新版核心 v4|0|0|2|
|system_configs|新版核心 v4|1|1|1|

建立前 6 個重設計集合均為空；沒有猜測舊 SKU、分類、評價或訂單關聯。只新增 1 筆文件明列的推薦政策設定，不生成假評價、歷史交易、推薦結果或統計。測試資料按測試專用 ObjectId 清除，最终數量如上表。

|Migration|狀態|Checksum|
|---|---|---|
|20260916_01_initial_schema_v2|succeeded|3478559fd54fbc72d3ba095eb22163600aa988a870cc31c1d29241206c59de5d|
|20260916_02_cart_state_events_v3|succeeded|12728b76700f6d26ab29f6df9cdbcbf4bf1dad725608c4a7a7dc3455f71fcf4c|
|20260918_03_schema_document_constraints|succeeded|29aa95e0c03db30c3c4891dbe6712ff21f7c7364de4ae40eb2eabccbcf862e05|
|20260918_04_complete_catalog_schema_v4|succeeded|543eb3d495f9e5a3cef51ad38fda18a3d89b51a0659526b822ce4df37fd3e676|

## 本次驗證涵蓋

- 全部 27 集合的有效文件可寫入，缺少 schema_version 被拒，寫入測試均回滾。
- 偏好分數 70／30 上限、評價 1～5 整數、SKU Decimal128、available_quantity 一致性。
- 預設4.0與實際評價分離；13/3 顯示4.4，錯誤4.3被拒。
- 推薦6／4筆上限與首次推薦4.5門檻的文件驗證。
- 同商品多SKU可同車、結帳重新驗價、重送不重扣、獨立order_items與每商品一筆PURCHASE。
- 任一SKU失敗整筆回滾、兩位會員搶最後一件僅一單成功。
- 未送達／未完成訂單不可評價，同會員同明細只能一次；第一筆有效評價不計預設4.0。

## 來源與界線

依據 [完整規格來源](13_完整Schema_v1.0_來源快照.md)，SHA-256：`760d2639b828d614d46d264efcd77ec3b1789451e75bd09dd63231f01d9f6686`。

資料庫模型已更新；完整推薦候選產生、跨集合首推資格與marker交易、分數衰減批次、補貨統計批次、關聯規則探勘及排程尚未部署。Schema 約束只能驗證文件形狀與本文件內的計算，不能代替跨集合資格檢查、模型執行或排程。Flask原網站尚未接上新服務。

Atlas外掛本次仍要求OAuth重新登入；實際寫入與讀回使用先前授權的PyMongo帳號，沒有變更Cluster方案。

## 逐欄位定義

### users

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|display_name|string|是|{"maxLength": 100, "minLength": 1}|
|email|string|是|{"pattern": "^[^\\sA-Z]+$", "minLength": 1}|
|auth_provider|enum|是|{"enum": ["local"]}|
|password_hash|string|是|{"minLength": 1}|
|firebase_uid|string/null|是|—|
|role|enum|是|{"enum": ["customer", "admin"]}|
|is_active|bool|是|—|
|preferences|object|是|{"additionalProperties": false}|
|preferences.category_ids|array|是|{"minItems": 0, "maxItems": 10, "uniqueItems": true}|
|preferences.tags|array|是|{"minItems": 0, "maxItems": 20, "uniqueItems": true}|
|preferences.budget_min|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|preferences.budget_max|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|preferences.updated_at|date/null|是|—|
|status|enum|是|{"enum": ["active", "inactive"]}|
|member_level|string|是|{"maxLength": 50, "minLength": 1}|
|registered_at|date|是|—|
|first_recommendation_generated_at|date/null|是|—|
|last_login_at|date/null|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### products

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|product_code|string|是|{"maxLength": 100, "minLength": 1}|
|product_name|string|是|{"maxLength": 200, "minLength": 1}|
|product_aliases|array|是|{"minItems": 0, "uniqueItems": true}|
|brand_id|objectId/null|是|—|
|major_category_id|objectId|是|—|
|minor_category_id|objectId|是|—|
|category_path|array|是|{"minItems": 2, "uniqueItems": false, "maxItems": 2}|
|summary|string|是|{"maxLength": 1000, "minLength": 1}|
|description|string|是|{"maxLength": 5000, "minLength": 1}|
|usage_scenarios|array|是|{"minItems": 0, "uniqueItems": true}|
|target_segments|array|是|{"minItems": 0, "uniqueItems": true}|
|product_tags|array|是|{"minItems": 0, "uniqueItems": true}|
|status|enum|是|{"enum": ["active", "inactive", "draft"]}|
|is_ai_recommendable|bool|是|—|
|image_urls|array|是|{"minItems": 0, "uniqueItems": false, "maxItems": 10}|
|shipping_profile_id|objectId/string/null|是|—|
|rating_status|enum|是|{"enum": ["DEFAULT", "ACTUAL"]}|
|rating_default_value|double/null|是|{"minimum": 1, "maximum": 5}|
|rating_sum|int|是|{"minimum": 0}|
|rating_count|int|是|{"minimum": 0}|
|average_rating_raw|double/null|是|{"minimum": 1, "maximum": 5}|
|average_rating_display|double|是|{"minimum": 1, "maximum": 5}|
|rating_distribution|object|是|{"additionalProperties": false}|
|rating_distribution.star_1|int|是|{"minimum": 0}|
|rating_distribution.star_2|int|是|{"minimum": 0}|
|rating_distribution.star_3|int|是|{"minimum": 0}|
|rating_distribution.star_4|int|是|{"minimum": 0}|
|rating_distribution.star_5|int|是|{"minimum": 0}|
|product_lifecycle_type|enum|是|{"enum": ["consumable", "durable"]}|
|replenishment_enabled|bool|是|—|
|expected_repurchase_interval_days|int/null|是|{"minimum": 1}|
|expected_purchase_frequency_year|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|minimum_repeat_frequency_year|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|replenishment_basis|enum|是|{"enum": ["category_benchmark", "historical"]}|
|replenishment_confidence|double|是|{"minimum": 0, "maximum": 1}|
|repeat_purchase_rate_12m|double/null|是|{"minimum": 0, "maximum": 1}|
|repeat_customer_count_12m|int|是|{"minimum": 0}|
|unique_buyer_count_12m|int|是|{"minimum": 0}|
|order_count_12m|int|是|{"minimum": 0}|
|avg_purchase_frequency_12m|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|median_repurchase_interval_days|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|last_repurchase_calculated_at|date/null|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### product_skus

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|product_id|objectId|是|—|
|sku_code|string|是|{"maxLength": 100, "minLength": 1}|
|variant_attributes|object|是|{"additionalProperties": {"bsonType": "string", "maxLength": 100}}|
|price|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|cost_price|decimal/null|是|{"minimum": {"$numberDecimal": "0"}}|
|currency|enum|是|{"enum": ["TWD"]}|
|stock_quantity|int|是|{"minimum": 0}|
|reserved_quantity|int|是|{"minimum": 0}|
|available_quantity|int|是|{"minimum": 0}|
|safety_stock|int|是|{"minimum": 0}|
|stock_status|enum|是|{"enum": ["in_stock", "low_stock", "out_of_stock"]}|
|barcode|string/null|是|{"maxLength": 100}|
|weight_grams|int/null|是|{"minimum": 0}|
|status|enum|是|{"enum": ["active", "inactive"]}|
|created_at|date|是|—|
|updated_at|date|是|—|

### product_reviews

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|product_id|objectId|是|—|
|user_id|objectId|是|—|
|order_id|objectId|是|—|
|order_item_id|objectId|是|—|
|rating|int|是|{"minimum": 1, "maximum": 5}|
|review_title|string|是|{"maxLength": 200}|
|review_content|string|是|{"maxLength": 8000}|
|verified_purchase|enum|是|{"enum": [true]}|
|status|enum|是|{"enum": ["pending", "published", "hidden", "rejected"]}|
|created_at|date|是|—|
|updated_at|date|是|—|

### product_repurchase_stats

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|product_id|objectId|是|—|
|major_category_id|objectId|是|—|
|minor_category_id|objectId|是|—|
|period_type|enum|是|{"enum": ["12m"]}|
|period_start|date|是|—|
|period_end|date|是|—|
|unique_buyer_count|int|是|{"minimum": 0}|
|repeat_customer_count|int|是|{"minimum": 0}|
|order_count|int|是|{"minimum": 0}|
|repeat_purchase_rate|double/null|是|{"minimum": 0, "maximum": 1}|
|avg_purchase_frequency|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|median_repurchase_interval_days|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|p25_repurchase_interval_days|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|p75_repurchase_interval_days|double/null|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|sample_size_status|enum|是|{"enum": ["insufficient", "adequate"]}|
|calculated_at|date|是|—|

### categories

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|category_code|string|是|{"maxLength": 100, "minLength": 1}|
|name|string|是|{"maxLength": 100, "minLength": 1}|
|level|int|是|{"enum": [1, 2]}|
|parent_id|objectId/null|是|—|
|path|array|是|{"minItems": 1, "uniqueItems": false, "maxItems": 2}|
|status|enum|是|{"enum": ["active", "inactive"]}|
|sort_order|int|是|{"minimum": 0}|
|created_at|date|是|—|
|updated_at|date|是|—|

### brands

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|brand_code|string|是|{"maxLength": 100, "minLength": 1}|
|name|string|是|{"maxLength": 100, "minLength": 1}|
|description|string/null|是|{"maxLength": 1000}|
|status|enum|是|{"enum": ["active", "inactive"]}|
|created_at|date|是|—|
|updated_at|date|是|—|

### orders

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|user_id|objectId|是|—|
|order_number|string|是|{"maxLength": 100, "minLength": 1}|
|status|enum|是|{"enum": ["pending", "confirmed", "shipping", "completed", "cancelled"]}|
|payment_status|enum|是|{"enum": ["unpaid", "paid", "failed", "refunded"]}|
|shipping_status|enum|是|{"enum": ["pending", "processing", "shipped", "delivered", "returned", "cancelled"]}|
|subtotal|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|shipping_fee|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|total_amount|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|ordered_at|date|是|—|
|completed_at|date/null|是|—|
|checkout_id|string|是|{"maxLength": 128, "minLength": 1}|
|request_hash|string|是|{"pattern": "^[a-f0-9]{64}$", "maxLength": 64, "minLength": 64}|
|is_demo|bool|是|—|
|currency|enum|是|{"enum": ["TWD"]}|
|paid_at|date/null|是|—|
|discount_amount|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|created_at|date|是|—|
|updated_at|date|是|—|

### order_items

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|order_id|objectId|是|—|
|user_id|objectId|是|—|
|product_id|objectId|是|—|
|sku_id|objectId|是|—|
|product_code_snapshot|string|是|{"maxLength": 100, "minLength": 1}|
|product_name_snapshot|string|是|{"maxLength": 200, "minLength": 1}|
|major_category_id_snapshot|objectId|是|—|
|minor_category_id_snapshot|objectId|是|—|
|quantity|int|是|{"minimum": 1, "maximum": 99}|
|unit_price|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|line_total|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|created_at|date|是|—|

### carts

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|user_id|objectId|是|—|
|status|enum|是|{"enum": ["active", "converted", "abandoned"]}|
|revision|int|是|{"minimum": 0}|
|items|array|是|{"minItems": 0, "maxItems": 20, "uniqueItems": false}|
|items[].product_id|objectId|是|—|
|items[].quantity|int|是|{"minimum": 1, "maximum": 99}|
|items[].price_snapshot|decimal|是|{"minimum": {"$numberDecimal": "0"}}|
|items[].added_at|date|是|—|
|items[].updated_at|date|是|—|
|items[].sku_id|objectId|是|—|
|created_at|date|是|—|
|updated_at|date|是|—|

### cart_events

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
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
|event_id|string|是|{"maxLength": 128, "minLength": 1}|
|sku_id|objectId/null|是|—|
|created_at|date|是|—|

### behavior_events

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|event_id|string|是|{"maxLength": 128, "minLength": 1}|
|user_id|objectId/null|是|—|
|anonymous_id|string/null|是|{"maxLength": 128}|
|session_id|string|是|{"maxLength": 128, "minLength": 1}|
|event_type|enum|是|{"enum": ["PURCHASE", "ADD_TO_CART", "SEARCH", "PRODUCT_VIEW"]}|
|product_id|objectId/null|是|—|
|major_category_id|objectId/null|是|—|
|minor_category_id|objectId/null|是|—|
|quantity|int|是|{"minimum": 1}|
|order_id|objectId/null|是|—|
|cart_id|objectId/null|是|—|
|search_query|string/null|是|{"maxLength": 200}|
|source|string|是|{"maxLength": 100, "minLength": 1}|
|recommendation_id|string/null|是|{"maxLength": 128}|
|event_at|date|是|—|
|score_version|int|是|{"minimum": 1}|
|processed_at|date/null|是|—|
|metadata|object|是|—|
|created_at|date|是|—|

### user_preference_scores

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|user_id|objectId|是|—|
|score_version|int|是|{"minimum": 1}|
|major_categories|object|是|{"additionalProperties": {"bsonType": "object", "required": ["raw_score", "score", "last_event_at"], "properties": {"raw_score": {"bsonType": "double", "minimum": 0, "maximum": 1.7976931348623157e+308}, "score": {"bsonType": "double", "minimum": 0, "maximum": 70}, "last_event_at": {"bsonType": "date"}}, "additionalProperties": false}}|
|major_categories.<key>.raw_score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|major_categories.<key>.score|double|是|{"minimum": 0, "maximum": 70}|
|major_categories.<key>.last_event_at|date|是|—|
|minor_categories|object|是|{"additionalProperties": {"bsonType": "object", "required": ["raw_score", "score", "last_event_at"], "properties": {"raw_score": {"bsonType": "double", "minimum": 0, "maximum": 1.7976931348623157e+308}, "score": {"bsonType": "double", "minimum": 0, "maximum": 30}, "last_event_at": {"bsonType": "date"}}, "additionalProperties": false}}|
|minor_categories.<key>.raw_score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|minor_categories.<key>.score|double|是|{"minimum": 0, "maximum": 30}|
|minor_categories.<key>.last_event_at|date|是|—|
|products|object|是|{"additionalProperties": {"bsonType": "object", "required": ["raw_score", "score", "last_event_at"], "properties": {"raw_score": {"bsonType": "double", "minimum": 0, "maximum": 1.7976931348623157e+308}, "score": {"bsonType": "double", "minimum": 0, "maximum": 1.7976931348623157e+308}, "last_event_at": {"bsonType": "date"}}, "additionalProperties": false}}|
|products.<key>.raw_score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|products.<key>.score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|products.<key>.last_event_at|date|是|—|
|cross_category_scores|object|是|{"additionalProperties": {"bsonType": "object", "required": ["raw_score", "score", "last_event_at"], "properties": {"raw_score": {"bsonType": "double", "minimum": 0, "maximum": 1.7976931348623157e+308}, "score": {"bsonType": "double", "minimum": 0, "maximum": 1.7976931348623157e+308}, "last_event_at": {"bsonType": "date"}}, "additionalProperties": false}}|
|cross_category_scores.<key>.raw_score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|cross_category_scores.<key>.score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|cross_category_scores.<key>.last_event_at|date|是|—|
|last_processed_event_at|date/null|是|—|
|updated_at|date|是|—|

### cross_category_rules

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|antecedent|object|是|{"additionalProperties": false}|
|antecedent.major_category_id|objectId|是|—|
|antecedent.minor_category_id|objectId|是|—|
|consequent|object|是|{"additionalProperties": false}|
|consequent.major_category_id|objectId|是|—|
|consequent.minor_category_id|objectId|是|—|
|window_days|int|是|{"minimum": 1}|
|support|double|是|{"minimum": 0, "maximum": 1}|
|confidence|double|是|{"minimum": 0, "maximum": 1}|
|lift|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|co_purchase_count|int|是|{"minimum": 0}|
|antecedent_customer_count|int|是|{"minimum": 0}|
|rule_score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|minimum_sample_size|int|是|{"minimum": 1}|
|source|enum|是|{"enum": ["historical_transactions"]}|
|status|enum|是|{"enum": ["active", "inactive"]}|
|calculated_at|date|是|—|

### product_purchase_sequences

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|user_id|objectId|是|—|
|first_product_id|objectId|是|—|
|next_product_id|objectId|是|—|
|first_order_id|objectId|是|—|
|next_order_id|objectId|是|—|
|days_between|int|是|{"minimum": 0}|
|window_days|int|是|{"minimum": 1}|
|first_major_category_id|objectId|是|—|
|next_major_category_id|objectId|是|—|
|created_at|date|是|—|

### recommendation_pools

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|pool_type|enum|是|{"enum": ["FIRST_MEMBER"]}|
|major_category_id|objectId|是|—|
|product_ids|array|是|{"minItems": 0, "uniqueItems": true}|
|filters|object|是|{"additionalProperties": false}|
|filters.rating_status|enum|是|{"enum": ["ACTUAL"]}|
|filters.average_rating_display_gte|double|是|{"minimum": 4.5, "maximum": 5}|
|filters.status|enum|是|{"enum": ["active"]}|
|filters.is_ai_recommendable|enum|是|{"enum": [true]}|
|generated_at|date|是|—|
|expires_at|date|是|—|

### first_member_recommendations

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|user_id|objectId|是|—|
|recommendation_session_id|string|是|{"maxLength": 128, "minLength": 1}|
|recommendation_type|enum|是|{"enum": ["FIRST_MEMBER"]}|
|items|array|是|{"minItems": 0, "uniqueItems": false}|
|items[].major_category_id|objectId|是|—|
|items[].product_id|objectId|是|—|
|items[].average_rating_display|double|是|{"minimum": 4.5, "maximum": 5}|
|items[].rating_count|int|是|{"minimum": 1}|
|items[].position|int|是|{"minimum": 1}|
|rule_version|int|是|{"minimum": 1}|
|random_seed|string|是|{"maxLength": 128, "minLength": 1}|
|created_at|date|是|—|

### recommendation_logs

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|user_id|objectId|是|—|
|recommendation_id|string|是|{"maxLength": 128, "minLength": 1}|
|recommendation_type|enum|是|{"enum": ["PERSONALIZED", "CROSS_CATEGORY", "FIRST_MEMBER"]}|
|algorithm_version|string|是|{"maxLength": 100, "minLength": 1}|
|items|array|是|{"minItems": 0, "uniqueItems": false}|
|items[].product_id|objectId|是|—|
|items[].position|int|是|{"minimum": 1}|
|items[].score|double|是|{"minimum": 0, "maximum": 1.7976931348623157e+308}|
|items[].reason_code|string|是|{"maxLength": 100, "minLength": 1}|
|shown_at|date|是|—|
|clicked_product_ids|array|是|{"minItems": 0, "uniqueItems": true}|
|added_to_cart_product_ids|array|是|{"minItems": 0, "uniqueItems": true}|
|purchased_product_ids|array|是|{"minItems": 0, "uniqueItems": true}|
|created_at|date|是|—|

### system_configs

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|objectId|是|—|
|schema_version|int|是|{"enum": [4]}|
|config_key|enum|是|{"enum": ["recommendation_policy"]}|
|version|int|是|{"minimum": 1}|
|settings|object|是|{"additionalProperties": false}|
|settings.weights|object|是|{"additionalProperties": false}|
|settings.weights.PURCHASE|int|是|{"minimum": 0}|
|settings.weights.ADD_TO_CART|int|是|{"minimum": 0}|
|settings.weights.SEARCH|int|是|{"minimum": 0}|
|settings.weights.PRODUCT_VIEW|int|是|{"minimum": 0}|
|settings.half_life_days|object|是|{"additionalProperties": false}|
|settings.half_life_days.PURCHASE|int|是|{"minimum": 1}|
|settings.half_life_days.ADD_TO_CART|int|是|{"minimum": 1}|
|settings.half_life_days.SEARCH|int|是|{"minimum": 1}|
|settings.half_life_days.PRODUCT_VIEW|int|是|{"minimum": 1}|
|settings.major_score_cap|int|是|{"enum": [70]}|
|settings.minor_score_cap|int|是|{"enum": [30]}|
|settings.personalized_count|int|是|{"enum": [6]}|
|settings.cross_category_count|int|是|{"enum": [4]}|
|settings.first_member_min_rating|double|是|{"minimum": 4.5, "maximum": 5}|
|settings.default_product_rating|double|是|{"minimum": 4, "maximum": 4}|
|settings.cross_min_customers|int|是|{"minimum": 1}|
|settings.cross_min_co_purchases|int|是|{"minimum": 1}|
|settings.cross_min_confidence|double|是|{"minimum": 0, "maximum": 1}|
|settings.cross_min_lift|double|是|{"minimum": 1, "maximum": 1.7976931348623157e+308}|
|status|enum|是|{"enum": ["active", "inactive"]}|
|created_at|date|是|—|
|updated_at|date|是|—|

### user_events

|欄位|BSON型別|必填|限制|
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

|欄位|BSON型別|必填|限制|
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

|欄位|BSON型別|必填|限制|
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

|欄位|BSON型別|必填|限制|
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

|欄位|BSON型別|必填|限制|
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

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|count|int|是|{"minimum": 0}|
|updated_at|date|是|—|

### request_limits

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|count|int|是|{"minimum": 0}|
|expires_at|date|是|—|

### schema_migrations

|欄位|BSON型別|必填|限制|
|---|---|---|---|
|_id|string|是|{"minLength": 1}|
|schema_version|int|是|{"enum": [2]}|
|checksum|string|是|{"pattern": "^[a-f0-9]{64}$", "maxLength": 64, "minLength": 64}|
|status|enum|是|{"enum": ["running", "succeeded", "failed"]}|
|started_at|date|是|—|
|completed_at|date/null|是|—|
|counts|object|是|{"additionalProperties": false}|
|counts.source|int|是|{"minimum": 0}|
|counts.target|int|是|{"minimum": 0}|
|counts.errors|int|是|{"minimum": 0}|
|error_code|string/null|是|—|

