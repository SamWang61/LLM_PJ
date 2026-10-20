# Cluster 實際設定與查核

> 2026-09-19：資料庫已更新為 Complete Schema v4，最新查核見 [16](16_完整Schema_v4驗證與欄位字典.md)。下列部署與帳號資訊保留原日期讀回；Network Access 已於 2026-10-19 透過 Atlas 外掛重新查核，詳見該節。

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

### 2026-10-19 實際查核（Asia/Taipei）

**結論：`0.0.0.0/0` 不在目前 Access List，不能確認為已生效的全 IPv4 開放規則。** 本次 Atlas 管理外掛已恢復連線，使用 `atlas_inspect_access_list` 唯讀查詢 Project `6aa9bd20af3f21039447a5c0`，成功回傳 `totalCount=4`：

|CIDR|Atlas 原始註解|
|---|---|
|`35.229.228.204/32`|VibeCart 專用 NAT|
|`180.177.10.68/32`|VibeCart development workstation cart validation 2026-09-17|
|`101.10.106.152/32`|空白|
|`180.177.24.85/32`|VibeCart development workstation 2026-09-16|

這次讀回確認的是規則存在與否及註解；外掛沒有提供逐筆 Active 狀態或到期時間，不能推定「永久有效」。本次沒有新增、移除或修改任何規則，也未執行網站端資料庫讀寫測試；不推定舊萬用規則的移除者或移除時間。

WEB 後端應使用獲准的來源 IPv4；使用專用 NAT 時，應確認實際出口為 `35.229.228.204`。開發電腦與 Compass 更換出口後，須重新核對來源是否在清單內，不能沿用「任意 IPv4 都可連線」的假設。連線仍需 Database User、密碼、TLS 與適當角色；連線字串僅置於後端秘密設定。

連線逾時時先核對實際出口與 Access List，再查 DNS/SRV、伺服器對外連線、防火牆、Cluster 與 TLS；驗證失敗則查帳號、密碼及角色。歷史查核報告保留原日期結果，不代表目前仍開放全網。

### 2026-10-05 使用者回報（歷史）

當時使用者回報新增 `0.0.0.0/0`，但外掛回覆 UNAUTHORIZED，未能獨立核實。該回報不作為現行設定；現行清單以上方 2026-10-19 實際讀回為準。

### 初始建置與歷史查核（2026-09-16～17）

|IP/CIDR|用途|註解|到期|
|---|---|---|---|
|180.177.24.85/32|本次開發電腦公網出口|VibeCart development workstation 2026-09-16|未設定自動到期|

2026-09-17 查核另有 101.10.106.152/32（既有，註解空白）；本次因本機出口改變新增 180.177.10.68/32，註解 VibeCart development workstation cart validation 2026-09-17。原先兩筆保留，未撤銷他人設定。當時未放行全網，本機出口 IP 改變需更新白名單，Cloud Run 出口尚未配置。這些是 2026-09-17 的歷史狀態，現行網路設定請以上方更新為準。

## Free 與 AI 配置

本期採 Free 固定容量，不啟用付費升級或額外模型服務。官方限制：0.5 GB 含文件與索引，一般每 Project 一個 Free Cluster，3 節點，無 Atlas 雲端備份與自動儲存擴容，最多 500 連線；30 天無連線可自動暫停。來源：[Atlas Free Cluster Limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/)（2026-09-16 查閱）。

BGE 512 維商品向量使用普通集合保存，由 Python 計算相似度；本次未建立 Atlas Vector Search 索引、未計算實際向量、未呼叫 Claude。圖片只存 URL／站內路徑。

## 工具與驗證證據

初始建置時，Atlas Free 建立工具建立 Cluster；管理工具建立帳號與單一 IP 白名單。2026-10-19 網路實際查核見上述 Network Access 區段。外掛 classic 索引工具不提供 unique／partial／TTL，集合工具不提供 validator，因此使用已授權的 PyMongo 4.14.1 完成這些約束，沒有以普通索引代替。

[完整 Schema 與索引讀回](05_實際Schema與索引.md) 包含每個 collection 的 options、validator、索引鍵與選項、筆數、遷移 checksum 及驗證 UTC 時間。[測試報告](06_實際驗證結果.md) 記錄 21 項通過結果。

## 歷史阻礙（已解除）

最初外掛只列出 SamWang_2026。使用者提供目標 ID 後，直接查詢曾回 INVALID_ARGUMENT：組織 MCP 存取停用。本次重試成功列出 LCCNET_LLM_2601 及其 vibecart_ai 專案，再開始建立資源；未繞過存取控制。

## 購物車更新

當時架構、31 個索引與生命週期見 [購物車 v3 設計](09_購物車架構與API整合.md)。更新前完整結構已保存；未改動原遷移 checksum，未重設任何配額。

## 2026-09-18 Schema 完整性查核

全部 14 集合的 validator、索引與既有文件合規性已重新查核，並完成 66 項測試；詳見 [當時完整報告](12_全部Schema文件對照與驗證.md)。Cluster 控制台中繼資料本次未重新查到：外掛 OAuth 需重新登入；實際 DB 查核走先前授權的 PyMongo 連線。

## Network Access update — English summary

Atlas read-back on 2026-10-19 returned four /32 entries, including the dedicated NAT 35.229.228.204/32, and no 0.0.0.0/0. Per-entry activation and expiry are not exposed by this tool. No access-list changes or website read/write tests were performed.
