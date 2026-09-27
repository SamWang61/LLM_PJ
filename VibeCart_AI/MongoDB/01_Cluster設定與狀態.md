# Cluster 實際設定與查核

> 2026-09-19：資料庫已更新為 Complete Schema v4，最新查核見 [16](16_完整Schema_v4驗證與欄位字典.md)。下列部署、帳號及網路資訊為原日期讀回；本次外掛 OAuth 失效，未重新核實控制台中繼資料。

初始建置日期：2026-09-16；購物車更新／查核：2026-09-17，Asia/Taipei。以下依 Atlas 外掛、PyMongo 與本機檔案實際查核。

## 身分與部署

|項目|實際值|
|---|---|
|Organization|LCCNET_LLM_2601|
|Organization ID|6aa9bcbb67ff2925383957b8|
|Project|vibecart_ai|
|Project ID|6aa9bd20af3f21039447a5c0|
|Project 建立時間|Atlas 回傳 9/15/2026, 9:48:19 PM（未標時區，保留原值）|
|Cluster 名稱|vibecart-ai-free|
|Cluster ID|目前外掛回應未提供；不以 Project ID 代替|
|instanceType|FREE|
|instanceSize|外掛回傳 N/A；方案確認為 FREE，對應 Free/M0|
|Provider|AWS|
|Region|AP_SOUTHEAST_1（新加坡）|
|state|IDLE|
|paused|false|
|MongoDB|8.0.32|
|Replica set|atlas-12d9tq-shard-0|
|Database|vibecart_ai|
|Schema|27 集合；19 個新版核心 v4 + 8 個保留集合；strict/error|
|索引|86 個總索引，含 59 個自訂索引|
|遷移識別|20260916_01_initial_schema_v2 與 20260916_02_cart_state_events_v3，加上 20260918_03_schema_document_constraints，再加上 20260918_04_complete_catalog_schema_v4，共四筆皆 succeeded|
|備份|Free 無 Atlas 雲端備份；人工備份尚未執行|

建立前目標 Project 無 Cluster、無 DB user；首次 PyMongo 連線的目標 DB 無任何集合。因此本次為空環境初始化，不涉及既有 musclecore 資料搬移。

## 連線位址（無密碼）

```text
mongodb+srv://vibecart-ai-free.odqe25w.mongodb.net

mongodb://ac-vg6ftlp-shard-00-00.odqe25w.mongodb.net:27017,ac-vg6ftlp-shard-00-01.odqe25w.mongodb.net:27017,ac-vg6ftlp-shard-00-02.odqe25w.mongodb.net:27017/?ssl=true&authSource=admin&replicaSet=atlas-12d9tq-shard-0
```

應用程式 URI 範例：

```dotenv
MONGO_URI=mongodb+srv://vibecart_app:<URL_ENCODED_PASSWORD>@vibecart-ai-free.odqe25w.mongodb.net/vibecart_ai?retryWrites=true&w=majority&authSource=admin
MONGO_DB=vibecart_ai
ENABLE_CHECKOUT=false
```

實際密碼由 Atlas 外掛安全產生，只存本機憑證檔，不在 MD 公開。

## 資料庫帳號

|帳號|角色|Database|Cluster scope|憑證|
|---|---|---|---|---|
|vibecart_app|readWrite|vibecart_ai|vibecart-ai-free|本目錄 .env|
|vibecart_schema_manager|readWrite、dbAdmin|vibecart_ai|vibecart-ai-free|本目錄 .env.schema|

兩帳號均已由 atlas-list-db-users 讀回核對。Schema 管理帳號目前仍存在，專供初始化及後續 schema 維護，不供 Flask 使用；未配置自動到期。若不再需要，可由 Atlas 管理員撤銷此帳號並清除對應本機憑證。不是跨 DB 的 atlasAdmin 帳號。

## Network Access

|IP/CIDR|用途|註解|到期|
|---|---|---|---|
|180.177.24.85/32|本次開發電腦公網出口|VibeCart development workstation 2026-09-16|未設定自動到期|

2026-09-17 查核另有 101.10.106.152/32（既有，註解空白）；本次因本機出口改變新增 180.177.10.68/32，註解 VibeCart development workstation cart validation 2026-09-17。原先兩筆保留，未撤銷他人設定。未放行全網。若本機出口 IP 改變需更新白名單；Cloud Run 出口尚未配置。

## Free 與 AI 配置

本期採 Free 固定容量，不啟用付費升級或額外模型服務。官方限制：0.5 GB 含文件與索引，一般每 Project 一個 Free Cluster，3 節點，無 Atlas 雲端備份與自動儲存擴容，最多 500 連線；30 天無連線可自動暫停。來源：[Atlas Free Cluster Limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)（2026-09-16 查閱）。

BGE 512 維商品向量使用普通集合保存，由 Python 計算相似度；本次未建立 Atlas Vector Search 索引、未計算實際向量、未呼叫 Claude。圖片只存 URL／站內路徑。

## 工具與驗證證據

Atlas Free 建立工具建立 Cluster；管理工具建立帳號與單一 IP 白名單。外掛 classic 索引工具不提供 unique／partial／TTL，集合工具不提供 validator，因此使用已授權的 PyMongo 4.14.1 完成這些約束，沒有以普通索引代替。

[完整 Schema 與索引讀回](05_實際Schema與索引.md) 包含每個 collection 的 options、validator、索引鍵與選項、筆數、遷移 checksum 及驗證 UTC 時間。[測試報告](06_實際驗證結果.md) 記錄 21 項通過結果。

## 歷史阻礙（已解除）

最初外掛只列出 SamWang_2026。使用者提供目標 ID 後，直接查詢曾回 INVALID_ARGUMENT：組織 MCP 存取停用。本次重試成功列出 LCCNET_LLM_2601 及其 vibecart_ai 專案，再開始建立資源；未繞過存取控制。

## 購物車更新

當時架構、31 個索引與生命週期見 [購物車 v3 設計](09_購物車架構與API整合.md)。更新前完整結構已保存；未改動原遷移 checksum，未重設任何配額。

## 2026-09-18 Schema 完整性查核

全部 14 集合的 validator、索引與既有文件合規性已重新查核，並完成 66 項測試；詳見 [當時完整報告](12_全部Schema文件對照與驗證.md)。Cluster 控制台中繼資料本次未重新查到：外掛 OAuth 需重新登入；實際 DB 查核走先前授權的 PyMongo 連線。
