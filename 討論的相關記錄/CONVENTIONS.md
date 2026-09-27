# 專案共用命名與資料規範

> 適用技術：Python、FastAPI、MongoDB、Firebase Authentication、Firebase Hosting、Cloud Run／Cloud Functions

## 1. 命名規範

| 對象 | 統一規則 | 範例 |
|---|---|---|
| Python 變數、函式 | `snake_case` | `user_id`、`get_product()` |
| Python 類別 | `PascalCase` | `ProductService`、`OrderDocument` |
| Python 常數 | `UPPER_SNAKE_CASE` | `MAX_LOGIN_ATTEMPTS` |
| Python 私有成員 | 前綴 `_` | `_build_query()` |
| MongoDB Collection | 複數 `snake_case` | `users`、`order_items` |
| MongoDB 欄位 | `snake_case` | `created_at`、`total_amount` |
| MongoDB 文件主鍵 | `_id` | `_id: ObjectId(...)` |
| 業務關聯 ID | `{對象}_id` | `user_id`、`product_id` |
| Firebase Auth 使用者 ID | `firebase_uid` | `firebase_uid: "abc123"` |
| Pydantic Schema | `PascalCase`＋用途後綴 | `ProductCreate` |
| Enum 類別 | `PascalCase` | `OrderStatus` |
| Enum 值 | 小寫 `snake_case` | `pending_payment` |
| API 路徑 | 複數、小寫、連字號 | `/api/order-items` |
| JSON Key | `snake_case` | `stock_quantity` |
| 環境變數 | `UPPER_SNAKE_CASE` | `MONGODB_URI` |
| Git 分支 | `{類型}/{功能}` | `feature/product-crud` |

## 2. 專案統一詞彙

| 概念 | 統一名稱 | 禁止混用 |
|---|---|---|
| 使用者 | `user` | `member`、`customer`、`account` |
| 商品 | `product` | `item`、`goods` |
| 商品分類 | `category` | `product_type` |
| 購物車 | `cart` | `basket` |
| 訂單 | `order` | `purchase` |
| 訂單明細 | `order_item` | `order_detail` |
| 使用者行為 | `user_event` | `activity`、`action_log` |
| AI 請求 | `ai_request` | `ai_data`、`llm_result` |
| API 模型 | `api` | `cloud`、`online` |
| 本地模型 | `local` | `offline`、`ollama` |

## 3. Python／MongoDB 型別對照

| 資料用途 | Python／Pydantic | MongoDB BSON | 規範 |
|---|---|---|---|
| 文件主鍵 | `ObjectId`／字串輸出 | `ObjectId` | API 回傳時轉為字串 |
| Firebase UID | `str` | `String` | 建立唯一索引 |
| 一般文字 | `str` | `String` | 設定長度驗證 |
| 長文字 | `str` | `String` | 不另分 TEXT 型別 |
| 整數 | `int` | 32-bit／64-bit Integer | 數量不得小於 0 |
| 金額 | `Decimal` | `Decimal128` | 禁止使用 `float`／`Double` |
| 布林值 | `bool` | `Boolean` | 使用 `is_`、`has_`、`can_` 前綴 |
| 日期時間 | UTC aware `datetime` | BSON Date | 一律儲存 UTC |
| 列舉 | `str` Enum | `String` | 僅允許已定義值 |
| 陣列 | `list[T]` | `Array` | 限制元素型別與最大數量 |
| 結構化物件 | Pydantic Model | Embedded Document | 只嵌入有界且隨父文件讀取的資料 |
| 彈性附加資訊 | `dict[str, Any]` | Object | 僅用於非核心、非主要查詢欄位 |
| 可空值 | `T \| None` | `null`／欄位不存在 | 同一欄位統一採一種策略 |

## 4. Collection 欄位規範

### `users`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | MongoDB 內部識別碼 |
| `firebase_uid` | String | 是 | Unique | Firebase Authentication UID |
| `email` | String | 是 | Unique、lowercase | 登入信箱 |
| `display_name` | String | 是 | Max 100 | 顯示名稱 |
| `role` | String Enum | 是 | Index | `customer`、`admin` |
| `is_active` | Boolean | 是 | Default `true` | 帳號狀態 |
| `created_at` | Date | 是 | UTC | 建立時間 |
| `updated_at` | Date | 是 | UTC | 修改時間 |

| 禁止欄位 | 原因 |
|---|---|
| `password` | 密碼交由 Firebase Authentication 管理 |
| `password_hash` | 應用程式資料庫不另存 Firebase 使用者密碼 |

### `categories`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | 分類 ID |
| `name` | String | 是 | Unique | 分類名稱 |
| `slug` | String | 是 | Unique | URL 識別字 |
| `description` | String | 否 |  | 分類說明 |
| `is_active` | Boolean | 是 | Default `true` | 是否啟用 |
| `created_at` | Date | 是 | UTC | 建立時間 |
| `updated_at` | Date | 是 | UTC | 修改時間 |

### `products`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | 商品 ID |
| `category_id` | ObjectId | 是 | Index | 對應 `categories._id` |
| `name` | String | 是 | Max 200、Text Index | 商品名稱 |
| `description` | String | 是 | Text Index | 商品說明 |
| `sku` | String | 是 | Unique | 商品識別碼 |
| `price` | Decimal128 | 是 | `>= 0` | 原價 |
| `sale_price` | Decimal128／null | 否 | `>= 0` | 特價 |
| `stock_quantity` | Integer | 是 | `>= 0` | 現有庫存 |
| `safety_stock` | Integer | 是 | `>= 0` | 安全庫存 |
| `tags` | Array[String] | 是 | Default `[]` | 商品標籤 |
| `image_urls` | Array[String] | 是 | Default `[]` | Firebase Storage 檔案 URL |
| `is_active` | Boolean | 是 | Index | 是否上架 |
| `created_at` | Date | 是 | UTC | 建立時間 |
| `updated_at` | Date | 是 | UTC | 修改時間 |

### `carts`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | 購物車 ID |
| `user_id` | ObjectId | 是 | Unique | 一名使用者一個有效購物車 |
| `items` | Array[Embedded] | 是 | Default `[]` | 購物車商品 |
| `items[].product_id` | ObjectId | 是 |  | 商品 ID |
| `items[].quantity` | Integer | 是 | `>= 1` | 數量 |
| `items[].added_at` | Date | 是 | UTC | 加入時間 |
| `updated_at` | Date | 是 | UTC | 修改時間 |

### `orders`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | 訂單 ID |
| `order_number` | String | 是 | Unique | 對外顯示編號 |
| `user_id` | ObjectId | 是 | Index | 下單使用者 |
| `status` | String Enum | 是 | Index | 訂單狀態 |
| `payment_status` | String Enum | 是 | Index | 付款狀態 |
| `items` | Array[Embedded] | 是 | 至少 1 筆 | 訂單明細快照 |
| `subtotal_amount` | Decimal128 | 是 | `>= 0` | 商品小計 |
| `discount_amount` | Decimal128 | 是 | `>= 0` | 折扣金額 |
| `shipping_fee` | Decimal128 | 是 | `>= 0` | 運費 |
| `total_amount` | Decimal128 | 是 | `>= 0` | 最終金額 |
| `created_at` | Date | 是 | UTC、Index | 建立時間 |
| `updated_at` | Date | 是 | UTC | 修改時間 |

### `orders.items[]` 訂單快照

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---:|---|
| `product_id` | ObjectId／null | 否 | 原商品可能已刪除 |
| `product_name` | String | 是 | 下單時名稱快照 |
| `sku` | String | 是 | 下單時 SKU 快照 |
| `unit_price` | Decimal128 | 是 | 下單時成交單價 |
| `quantity` | Integer | 是 | 購買數量 |
| `subtotal_amount` | Decimal128 | 是 | 明細小計 |

### `user_events`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | 事件 ID |
| `user_id` | ObjectId／null | 否 | Index | 未登入事件可空 |
| `session_id` | String | 是 | Index | 瀏覽工作階段 |
| `event_type` | String Enum | 是 | Index | 行為類型 |
| `product_id` | ObjectId／null | 否 | Index | 相關商品 |
| `search_query` | String／null | 否 |  | 搜尋文字 |
| `event_metadata` | Object | 是 | Default `{}` | 非核心附加資料 |
| `created_at` | Date | 是 | UTC、TTL 可選 | 發生時間 |

### `ai_requests`

| 欄位 | 型別 | 必填 | 索引／限制 | 說明 |
|---|---|---:|---|---|
| `_id` | ObjectId | 是 | Primary | AI 請求 ID |
| `user_id` | ObjectId／null | 否 | Index | 發起使用者 |
| `task_type` | String Enum | 是 | Index | 任務類型 |
| `execution_mode` | String Enum | 是 | Index | `api`、`local`、`hybrid` |
| `requested_provider` | String Enum | 是 |  | 預定 Provider |
| `actual_provider` | String Enum | 是 | Index | 實際 Provider |
| `model_name` | String | 是 |  | 模型名稱 |
| `prompt_name` | String | 是 |  | Prompt 名稱 |
| `prompt_version` | String | 是 |  | Prompt 版本 |
| `input_text` | String | 是 |  | 輸入內容 |
| `output_text` | String／null | 否 |  | 輸出內容 |
| `is_success` | Boolean | 是 | Index | 是否成功 |
| `latency_ms` | Integer | 是 | `>= 0` | 回應時間 |
| `token_count` | Integer／null | 否 | `>= 0` | Token 數量 |
| `estimated_cost` | Decimal128／null | 否 | `>= 0` | 預估成本 |
| `fallback_reason` | String／null | 否 |  | 切換原因 |
| `error_code` | String／null | 否 |  | 錯誤代碼 |
| `created_at` | Date | 是 | UTC、Index | 建立時間 |

## 5. 共用 Enum

| Enum | 允許值 |
|---|---|
| `UserRole` | `customer`、`admin` |
| `OrderStatus` | `pending`、`confirmed`、`shipping`、`completed`、`cancelled` |
| `PaymentStatus` | `unpaid`、`paid`、`failed`、`refunded` |
| `EventType` | `product_view`、`product_search`、`add_to_cart`、`remove_from_cart`、`purchase`、`recommendation_click` |
| `AITaskType` | `product_search`、`shopping_assistant`、`product_tagging`、`sales_summary`、`sentiment_analysis` |
| `LLMProviderType` | `api`、`local` |
| `LLMExecutionMode` | `api`、`local`、`hybrid` |

## 6. MongoDB 建模規則

| 項目 | 統一規範 |
|---|---|
| 嵌入文件 | 資料量有上限、通常隨父文件一起讀取時使用 |
| ID 參照 | 資料會獨立更新、被多處引用或可能持續增長時使用 |
| 訂單明細 | 嵌入 `orders.items`，保存下單當時快照 |
| 購物車明細 | 嵌入 `carts.items` |
| 商品分類 | `products.category_id` 參照 `categories._id` |
| 使用者資料 | 以 `firebase_uid` 對應 Firebase Auth；內部關聯使用 `users._id` |
| 關聯完整性 | MongoDB 不自動保證外鍵；由 Service 層檢查 |
| 多文件交易 | 結帳、扣庫存、建立訂單等一致性操作使用 transaction |
| 文件大小 | 單一文件不得接近 MongoDB 16 MB 限制 |
| 無限陣列 | 禁止嵌入持續增長的事件、紀錄或歷史資料 |
| Schema 驗證 | 使用 Pydantic，正式環境另設定 MongoDB JSON Schema Validator |
| 軟刪除 | 核心商業資料優先使用 `is_active` 或 `deleted_at` |
| 時間 | 儲存 UTC；顯示時轉換使用者時區 |
| 金額 | `Decimal`／`Decimal128`，禁止 `float`／`Double` |

## 7. 索引命名與必要索引

| Collection | 索引欄位 | 類型 |
|---|---|---|
| `users` | `firebase_uid` | Unique |
| `users` | `email` | Unique |
| `products` | `sku` | Unique |
| `products` | `category_id`, `is_active` | Compound |
| `products` | `name`, `description` | Text |
| `categories` | `slug` | Unique |
| `carts` | `user_id` | Unique |
| `orders` | `order_number` | Unique |
| `orders` | `user_id`, `created_at` | Compound |
| `orders` | `status`, `created_at` | Compound |
| `user_events` | `user_id`, `event_type`, `created_at` | Compound |
| `ai_requests` | `task_type`, `actual_provider`, `created_at` | Compound |

| 索引名稱格式 | 範例 |
|---|---|
| `idx_{collection}_{fields}` | `idx_orders_user_id_created_at` |
| `uq_{collection}_{fields}` | `uq_users_firebase_uid` |
| `ttl_{collection}_{field}` | `ttl_user_events_created_at` |

## 8. Pydantic 與 Repository 命名

| 類別／後綴 | 用途 | 範例 |
|---|---|---|
| `Document` | MongoDB 文件模型 | `ProductDocument` |
| `Create` | 新增輸入 | `ProductCreate` |
| `Update` | 修改輸入 | `ProductUpdate` |
| `Response` | API 回傳 | `ProductResponse` |
| `Filter` | 查詢條件 | `ProductFilter` |
| `Summary` | 統計摘要 | `SalesSummary` |
| `Result` | 程式處理結果 | `RecommendationResult` |
| `Repository` | MongoDB 資料存取 | `ProductRepository` |
| `Service` | 商業邏輯 | `OrderService` |

## 9. Firebase／部署元件分工

| 元件 | 使用服務 | 規範 |
|---|---|---|
| 靜態前端 | Firebase Hosting | 不承載 FastAPI 程式 |
| 使用者登入 | Firebase Authentication | 後端驗證 Firebase ID Token |
| 圖片與檔案 | Firebase Storage | MongoDB 只保存檔案 URL／Path |
| FastAPI 後端 | Cloud Run | 容器化部署，前端透過 HTTPS API 呼叫 |
| 小型事件函式 | Cloud Functions | 僅放短時間、事件觸發工作 |
| 排程工作 | Cloud Scheduler＋Cloud Run／Functions | 不依賴前端觸發 |
| 機密資料 | Secret Manager／部署環境變數 | 禁止提交 Git |
| MongoDB | MongoDB Atlas | Firebase 不取代 MongoDB 資料庫 |

## 10. 環境變數

| 變數名稱 | 用途 | 可提交 Git |
|---|---|---:|
| `APP_ENV` | 執行環境 | 僅範例 |
| `MONGODB_URI` | MongoDB 連線字串 | 否 |
| `MONGODB_DATABASE` | 資料庫名稱 | 僅範例 |
| `FIREBASE_PROJECT_ID` | Firebase 專案 ID | 僅範例 |
| `FIREBASE_STORAGE_BUCKET` | Storage Bucket | 僅範例 |
| `GOOGLE_APPLICATION_CREDENTIALS` | 本機憑證路徑 | 否 |
| `LLM_MODE` | `api`／`local`／`hybrid` | 僅範例 |
| `API_LLM_MODEL` | API 模型名稱 | 僅範例 |
| `API_LLM_KEY` | API 金鑰 | 否 |
| `LOCAL_LLM_BASE_URL` | 本地模型 URL | 僅範例 |

## 11. Git 與版本更新規則

| 項目 | 規範 | 範例 |
|---|---|---|
| Feature 分支 | `feature/{功能}` | `feature/product-crud` |
| Fix 分支 | `fix/{問題}` | `fix/order-stock-deduction` |
| Refactor 分支 | `refactor/{範圍}` | `refactor/llm-router` |
| Schema 變更檔 | `migrations/{時間}_{名稱}.py` | `20260913_add_prompt_version.py` |
| Feature Commit | `feat: {內容}` | `feat: add product creation API` |
| Fix Commit | `fix: {內容}` | `fix: prevent negative stock` |
| Schema Commit | `db: {內容}` | `db: add prompt version field` |
| Test Commit | `test: {內容}` | `test: add checkout transaction tests` |
| Docs Commit | `docs: {內容}` | `docs: update MongoDB conventions` |

## 12. Schema 版本規則

| 規範 | 要求 |
|---|---|
| Schema 變更 | 必須附 migration／backfill 腳本 |
| 已合併腳本 | 禁止直接修改；新增下一版腳本 |
| 欄位改名 | 先新增新欄位、搬移資料、更新程式，再移除舊欄位 |
| 新增必填欄位 | 必須提供舊文件的預設值或回填方式 |
| 索引變更 | 使用獨立腳本建立／移除，並記錄名稱 |
| PR 範圍 | Model、驗證、索引、遷移與測試放在同一 PR |
| Collection Schema 版本 | 文件需要漸進式升級時加入 `schema_version` |

## 13. 禁止事項

| 禁止事項 | 正確作法 |
|---|---|
| 提交 `.env`、Service Account JSON、API Key | 僅提交 `.env.example` |
| 在 MongoDB 儲存 Firebase 密碼 | 僅保存 `firebase_uid` 與應用資料 |
| 金額使用 `float`／BSON Double | 使用 `Decimal`／`Decimal128` |
| 所有資料塞入單一 Collection | 依聚合邊界拆分 Collection |
| 所有附加資料塞入 `metadata` | 常用查詢與統計欄位正式建模 |
| 將事件紀錄嵌入 `users` | 使用獨立 `user_events` Collection |
| 在 Route 直接操作 MongoDB | 經由 Service 與 Repository |
| 各功能自行寫模型切換判斷 | 統一經過 `LLMRouter` |
| 依賴 MongoDB 自動檢查外鍵 | Service 層驗證參照存在性 |
| 直接在線上手動改文件結構 | 使用版本化 migration／backfill 腳本 |
| 使用模糊名稱 `data`、`info`、`item` | 使用明確商業名稱 |
