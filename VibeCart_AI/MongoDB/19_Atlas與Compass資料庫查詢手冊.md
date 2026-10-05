# MongoDB Atlas 與 Compass 資料庫查詢手冊

版本：1.0｜日期：2026-10-05（Asia/Taipei）｜對象：SAM、HEN、JEFF 與專題測試同學。

本手冊說明如何連到 VibeCart AI 的既有資料庫、搜尋商品與規格、查看分類、圖片、訂單、Schema 及索引。所有範例均為讀取；不需要重建集合、重新匯入或執行歷史遷移。本文按官方介面文件整理，資料筆數與查詢範例以 PyMongo 唯讀核對；不宣稱逐一操作過每位同學的 Atlas／Compass 畫面。

## 1. 先確認連到哪裡

|項目|本專案設定|
|---|---|
|Organization|LCCNET_LLM_2601|
|Organization ID|6aa9bcbb67ff2925383957b8|
|Project|vibecart_ai|
|Project ID|6aa9bd20af3f21039447a5c0|
|Cluster|vibecart-ai-free|
|Host|vibecart-ai-free.odqe25w.mongodb.net|
|Database|vibecart_ai|

Atlas 是雲端管理網站，Compass 是安裝在電腦上的資料庫工具；兩者連到上述同一個 Cluster／Database 時，查看的是同一份資料，不需要把資料再複製一份。`localhost:27017` 是本機 MongoDB，並非本專案 Atlas。

連線前需要：Atlas 網站登入與適當專案角色；使用 Compass 時，另需要資料庫帳號與密碼，以及符合 Atlas Network Access 設定的網路來源。Atlas 網站登入帳號和 Database User 是不同用途，不能直接互換密碼。僅查閱資料時請由管理員提供適當唯讀存取。[官方：Atlas 資料存取角色](https://www.mongodb.com/docs/atlas/atlas-ui/)、[Compass 連線](https://www.mongodb.com/docs/compass/connect/)。

## 2. 用 Atlas 網站找到資料庫

1. 開啟 [MongoDB Atlas](https://cloud.mongodb.com/)，登入自己的帳號。
2. 在 Organization 選 **LCCNET_LLM_2601**，Project 選 **vibecart_ai**。
3. 在左側 **Database → Data Explorer** 開啟資料瀏覽器。不同介面版本也可能從 Cluster 卡片的 **Browse Collections** 進入。
4. 核對選到 **vibecart-ai-free**，展開 **vibecart_ai**。
5. 點選 **products**，進入 **Documents** 或目前介面的文件瀏覽區。
6. 將 Filter 設為 `{}`，按 **Find**，即可顯示商品。使用下方分頁／載入更多查看其他文件，不能用畫面目前顯示的筆數當作全部筆數。
7. 點開文件或切換 JSON 檢視，展開 `image_urls`、`category_path` 等陣列。

如果看不到目標組織或專案，先確認登入帳號與專案邀請，而不是建立同名 Project。官方目前的導覽為 Data Explorer；介面名稱變動時，以 [Atlas 查詢步驟](https://www.mongodb.com/docs/atlas/atlas-ui/query/filter/) 為準。

## 3. 用 Compass 連線並瀏覽

1. 開啟 MongoDB Compass，點 **Add new connection／New Connection**；已保存連線可直接開啟。
2. 貼上管理員私下提供的完整 URI。以下只有格式，尖括號內容必須替換，不能直接照貼：

   ```text
   mongodb+srv://<DB_USER>:<URL_ENCODED_PASSWORD>@vibecart-ai-free.odqe25w.mongodb.net/vibecart_ai?authSource=admin&appName=VibeCartCompass
   ```

3. 若密碼包含 `@`、`:`、`/` 等特殊字元，URI 內需要正確 URL 編碼；也可使用 Compass 的進階驗證欄位輸入。不要把密碼寫進本手冊、GitHub Issue 或通知信。
4. 連線名稱可設為 **VibeCart AI－測試資料庫**，按 **Connect**。是否保存密碼依個人電腦管理方式決定。
5. 左側展開 **vibecart_ai**，點 **products → Documents**。
6. 在 **Filter** 輸入查詢物件，再按 **Find**。清除條件時輸入 `{}` 並重新查詢。
7. 使用 JSON／列表／表格等可用檢視方式閱讀。表格較適合比較商品名稱；JSON 較適合展開規格與巢狀欄位。

官方操作：[建立 Compass 連線](https://www.mongodb.com/docs/compass/connect/)、[Compass Filter 查詢](https://www.mongodb.com/docs/compass/query/filter/)。若只看到 admin、local，請先核對 Cluster、Database、權限及是否需要重新整理，不要直接按 Create Database 或 Drop。

## 4. 目前有哪些資料

以下為 **2026-10-05 本次唯讀查核快照**，後續新增或測試操作可能改變筆數。不是永遠固定的驗收值。

|集合|用途／重點欄位|查核筆數|
|---|---|---:|
|products|商品主檔：product_name、summary、description、image_urls|336|
|product_skus|規格與價格庫存：product_id、variant_attributes、price、available_quantity|336|
|categories|大類／小類：level、parent_id、name、category_code|32（8 大類＋24 小類）|
|brands|品牌：brand_code、name|128|
|users|合成測試會員；不是可直接拿來登入的帳號清單|600|
|orders|示範訂單主檔：order_number、ordered_at、payment_status、is_demo|3,000|
|order_items|訂單商品明細：order_id、product_id、sku_id、quantity、line_total|8,969|
|schema_migrations|結構變更紀錄，只查閱、不修改|5|

共有 27 個集合；部分事件、推薦、AI 集合可能尚無資料，空集合不一定代表故障。較早的 336 商品重建報告與後續合成訂單匯入是不同時間的快照，因此會員／訂單／遷移筆數可能與舊報告不同。

商品描述為自行改寫，價格為來源擷取時的參考價，庫存為模擬值；照片以來源網址保存。商品來源連結放在 `description` 的「商品來源：」段落，目前 Schema 沒有獨立的 `source_url` 欄位。來源網站、圖片可用性與價格可能日後改變。

## 5. 最常用的查詢（Atlas／Compass Filter）

每次先選對集合，再貼 **一個查詢物件**；不要把 `db.products.find(...)` 整段貼到 Filter。

### 5.1 商品名稱搜尋

選 `products`，查名稱含「鮮乳」的商品：

```json
{"product_name": {"$regex": "鮮乳"}}
```

2026-10-05 查核為 10 筆。中文關鍵字可換為「洗衣」、「水餃」等；欄位是 `product_name`，不是舊網站的 `name`。

查這批家樂福來源商品：

```json
{"product_code": {"$regex": "^CF-"}}
```

### 5.2 大類、小類與商品

選 `categories`：

```json
{"level": 1}
```

這是 8 大類；改為 `{"level": 2}` 可看 24 小類。`parent_id` 指向所屬大類，`path` 保存分類代碼。

例如選 `products` 查飲料與飲用水大類：

```json
{"category_path": "SM-DRINK"}
```

陣列條件會比對其中的分類代碼。此批其他大類代碼：`SM-DAIRY`、`SM-FROZEN`、`SM-SNACK`、`SM-GROCERY`、`SM-PANTRY`、`SM-HOME`、`SM-CARE`；分類中文名稱以 `categories` 為準。

### 5.3 找商品的 SKU、價格與庫存

1. 在 `products` 找到商品，複製 `_id` 的 24 位十六進位值。
2. 切換 `product_skus`，用 `product_id` 查詢。ObjectId 是型別，不只是字串。

下面是本次已核對的實例：

```javascript
{"product_id": ObjectId("52e459b771f6f22fad150af7")}
```

它對應商品代碼 `CF-1001000400106`。其他商品請替換為各自的 `_id`，不要在 ObjectId 外再加引號。若查詢編輯器不接受此寫法，先用下列已知 SKU 代碼查找，或查閱該版工具的 ObjectId／Extended JSON 支援：

```json
{"sku_code": "CF-SKU-1001000400106"}
```

`variant_attributes` 是規格；`price` 是 Decimal128 金額；`stock_quantity` 是總庫存、`reserved_quantity` 是保留量、`available_quantity` 是可售量。價格與庫存位於 SKU，不在商品主檔。

選 `product_skus` 查有庫存且價格不超過 100 元：

```json
{"status": "active", "available_quantity": {"$gt": 0}, "price": {"$lte": 100}}
```

查缺貨：

```json
{"available_quantity": 0}
```

需要價格排序時，在 **Options → Sort**（或介面顯示的 Sort）填 `{"price": 1}`；它是排序欄位，不是 Filter 的一部分。

### 5.4 查看照片、摘要與來源頁

在 `products` 展開 `image_urls`，複製第一個 HTTPS 網址到瀏覽器開啟。Compass 可能僅呈現網址，不會直接把每張圖片顯示成商品卡片。查看 `summary`／`description` 可讀取摘要，`description` 末端包含原商品頁連結。照片載入失敗不等於商品文件不存在。

### 5.5 查看合成訂單與明細

選 `orders`，僅查看本次合成批次：

```json
{"synthetic_batch_id": "sam-synthetic-20261005-v1", "is_demo": true}
```

僅查已付款、未取消的示範訂單：

```json
{"synthetic_batch_id": "sam-synthetic-20261005-v1", "is_demo": true, "payment_status": "paid", "status": {"$ne": "cancelled"}}
```

本批此口徑為 1,800 筆；`paid` 是測試狀態，不代表實際收款。選到一筆訂單後，複製 `_id`，到 `order_items` 查 `{"order_id": ObjectId("替換為訂單的24位ID")}`。此行是格式示意，必須先替換 ID 才能執行。

`users` 的本批合成資料可用 `{"synthetic_batch_id": "sam-synthetic-20261005-v1"}` 查詢；不要將停用的合成會員當成可登入的測試帳號。只需要人口資料時，在 Project／Projection 選項填 `{"_id": 1, "schema_version": 1, "synthetic_batch_id": 1}` 作為最小查閱起點，再按工作需要加入欄位，避免匯出完整驗證資訊。

## 6. 查看 Schema、驗證規則與索引

|Compass 分頁|用途|本專案閱讀重點|
|---|---|---|
|Documents|查看實際文件|確認欄位值與資料型別|
|Schema → Analyze|依抽樣文件分析欄位、型別和分布|結果不是完整 validator；空集合可能無法分析|
|Validation|查看伺服器上的驗證規則|`$jsonSchema`、required、bsonType，以及可能的額外條件|
|Indexes|查看索引鍵與選項|唯一索引、partial 條件、TTL；不按 Drop|

文件裡的 `schema_version` 也不等於整個資料庫版本。核心商品使用 v4，保留集合可能使用其他版本；後續測試資料增補欄位應以目前集合的 Validation 與最新遷移為準。不要因舊報告不同就覆寫規則。

官方：[Schema 抽樣分析](https://www.mongodb.com/docs/compass/schema/)、[Validation 驗證規則](https://www.mongodb.com/docs/compass/validation/)。本手冊只要求查看；不需要點 Update、Insert、Delete、Drop 或執行遷移。

## 7. 精確確認筆數（Compass 內建 mongosh，可選）

如果你的 Compass 版本提供內建 Shell，可執行下列唯讀命令；這些是 Shell 指令，不是 Filter：

```javascript
use vibecart_ai
db.getCollectionNames().length
db.products.countDocuments({})
db.product_skus.countDocuments({})
db.categories.countDocuments({level: 1})
db.categories.countDocuments({level: 2})
db.orders.countDocuments({synthetic_batch_id: "sam-synthetic-20261005-v1"})
```

本次快照依序為 27、336、336、8、24、3000。精確筆數會隨其他同學的操作變化；頁面抽樣、快取統計與當頁筆數不一定等於 `countDocuments` 結果。

## 8. 常見問題

|現象|優先確認|
|---|---|
|看不到 Organization／Project|Atlas 登入帳號、專案邀請與角色；請 SAM 核對存取資格|
|Compass Authentication failed|Database User／密碼、authSource=admin、URI 編碼；不要使用 Atlas 網站密碼代替|
|連線逾時／server selection timeout|Atlas Network Access 是否涵蓋目前出口 IP、網路是否可用、Cluster 是否可連；交由管理員核對，勿為排錯自行開放全網|
|只看到 admin、local 或 0 集合|確認指定 host、vibecart_ai、重新整理與權限；將結果回報 SAM，不自行建同名庫|
|查詢 0 筆|先用 `{}`、核對集合、欄位拼字、ObjectId 型別；也可能是正常空結果|
|商品沒有 price／stock|到 product_skus，以 product_id 關聯查看|
|「排除示範」後訂單是空的|目前本批訂單全部 is_demo=true，屬預期結果|
|看不到圖片縮圖|資料保存的是 image_urls，將網址另開瀏覽器；來源站也可能改網址|
|Schema 分頁沒有資料|它需要抽樣文件；改到 Validation 看規則|
|Codex Atlas 外掛要求重新登入|這是外掛授權狀態；不等同資料庫故障，Atlas 網站及 Compass 使用各自的授權與連線|

若「剛才有資料，現在整庫消失」，記錄台灣時間、host、Database 名稱與目前筆數，回報組長。先前本專案曾發生此狀況；不要自行執行 drop、重建或重匯來掩蓋原因。

## 9. 組員查閱完成清單

- 能確認 `vibecart-ai-free → vibecart_ai → products`。
- 能以「鮮乳」搜尋，並查看一項商品的摘要、圖片網址及來源頁。
- 能從商品 `_id` 找到 SKU，指出規格、價格與可售庫存。
- 能區分 8 大類與 24 小類。
- 能查看示範訂單及對應 order_items，理解 is_demo 與付款狀態的差異。
- 能區分 Schema 抽樣與 Validation 規則；完成後沒有修改資料、權限或索引。

遇到問題可提供「工具／版本、時間、Cluster、Database、集合、使用的查詢、錯誤文字」，不附密碼或完整帶帳密 URI。資料庫查詢成功也不代表網站部署、登入、結帳或 AI 推薦已完成驗收。

## 10. 維護與參考

本次 12 項唯讀查詢的結果與 UTC 查核時間見 [查詢驗證紀錄](../../docs/inventory/mongodb_query_manual_checks_2026-10-05.json)；未匯出會員個資或連線密碼。

本文件置於 `VibeCart_AI/MongoDB/`，與 [資料庫文件入口](README.md) 及 [v4 架構](15_完整Schema_v4架構與遷移.md) 一起維護。後續資料匯入、欄位更動或工具介面變更時，更新查核日期、筆數快照與範例。

官方參考（查閱日 2026-10-05）：

- [Atlas Data Explorer 與角色](https://www.mongodb.com/docs/atlas/atlas-ui/)
- [Atlas 查詢 Filter](https://www.mongodb.com/docs/atlas/atlas-ui/query/filter/)
- [Compass 連線](https://www.mongodb.com/docs/compass/connect/)
- [Compass 查詢 Filter](https://www.mongodb.com/docs/compass/query/filter/)
- [Compass Schema](https://www.mongodb.com/docs/compass/schema/)
- [Compass Validation](https://www.mongodb.com/docs/compass/validation/)

## English summary

Use Atlas Data Explorer or MongoDB Compass to inspect the same `vibecart_ai` database on `vibecart-ai-free`. Atlas website membership and database credentials are separate. Never publish a credential-bearing URI.

The read-only snapshot on 2026-10-05 contains 27 collections, 336 products, 336 SKUs, 8 major and 24 minor categories, 128 brands, 600 synthetic users, 3,000 demo orders and 8,969 order items. These counts are dated observations, not permanent invariants. All example searches are read-only; Filter takes a query object, while shell commands belong in mongosh.

Products contain names, rewritten summaries, image URLs and the source-page link inside description. Prices, variants and inventory belong to product_skus and join through ObjectId product_id. Synthetic order statuses are not real payments, and inactive synthetic users are not login accounts. Schema analysis samples data; Validation shows enforced rules. This guide does not authorize destructive actions or certify a public website deployment.
