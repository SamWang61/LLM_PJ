# VibeCart AI MongoDB 建置紀錄

**2026-10-21 最新正式讀回**：active contract 為 `v4-customer-session-audit-20261021`，**30 個集合、96 個索引、8 筆 succeeded migration**；12 項關聯檢查均 0 orphan。新增 `20261021_08_customer_session_audit_v4`，僅啟用一般會員裝置撤銷的同交易稽核與 180 天唯一收據；舊七筆 migration checksum 保留。正式部署與受控資料清理見[優化系統](../../docs/優化系統.md)及[去敏讀回](../../docs/inventory/jeff_production_20261021/release-evidence.json)。下方 27 集合／86 索引／4 migration 及未接線描述為 2026-10-05 的建置快照。

現行入口為 [schema_active_v4.py](schema_active_v4.py)、[check_v4_database.py](../../scripts/check_v4_database.py) 與 [admin_session_audit_schema.py](admin_session_audit_schema.py)。[migrate_admin_sessions.py](../../scripts/migrate_admin_sessions.py) 預設只做 preflight；`--apply` 會要求明確資料庫確認。D5 廣泛編輯草稿仍屬獨立契約，不因本次兩個稽核集合上線而全部啟用。

## 2026-10-05 建置快照

更新：2026-10-05（Asia/Taipei）。已依使用者指示重建 Schema 並匯入超市測試資料；[最新重建與匯入報告](18_2026-10-05_Schema重建與超市商品匯入.md)。原 Schema 依據不變。依新增的 VibeCart_AI_MongoDB_Complete_Schema.md，已完成指定 Atlas 資料庫的 Complete Schema v4 更新與實際驗證。

|項目|實際結果|
|---|---|
|Organization|LCCNET_LLM_2601 / 6aa9bcbb67ff2925383957b8|
|Project|vibecart_ai / 6aa9bd20af3f21039447a5c0|
|Cluster／資料庫|vibecart-ai-free / vibecart_ai|
|方案／地區|原建置 Free，AWS AP_SOUTHEAST_1；本次未變更部署方案|
|資料結構|19 個新版核心 v4 集合 + 8 個保留集合，共 27 個 strict/error validators|
|索引|59 個自訂索引 + 27 個 _id_，共 86 個；24 個自訂唯一索引、2 個 TTL|
|資料|商品 336、SKU 336、分類 32、品牌 128；schema_migrations 4 筆 succeeded、system_configs 1 筆；其餘集合 0 筆|
|驗證|歷史 v4 66 項測試通過；本次完整 Schema 讀回、832 筆文件精確比對與 Flask 336 商品讀取通過|

2026-10-05 Schema 重建與商品匯入時，Atlas 外掛 OAuth 失效，當時使用先前授權的 PyMongo 連線完成變更與讀回，未重新核實控制台部署中繼資料。2026-10-19 Atlas 外掛已恢復連線，Network Access 已透過該外掛成功讀回；本次結果見下節與 [Cluster 設定](01_Cluster設定與狀態.md)。

## Network Access 實際查核（2026-10-19）

2026-10-19 Atlas 實際查核：成功讀回 Project `vibecart_ai` 的 4 筆 Network Access 規則，全部為 `/32`，包含專用 NAT `35.229.228.204/32`；清單中沒有 `0.0.0.0/0`，目前不能按全 IPv4 開放設定使用。外掛未提供逐筆 Active／到期欄位，本次也未測試網站端讀寫。完整清單與查核界線見 [Cluster 設定](01_Cluster設定與狀態.md)。

WEB 後端、開發電腦或 Compass 的實際出口須符合清單；更換出口後需重新核對。帳密、TLS 與角色權限仍需通過。

English: Atlas read-back on 2026-10-19 returned four /32 entries, including the dedicated NAT 35.229.228.204/32, and no 0.0.0.0/0. Per-entry activation and expiry are not exposed by this tool. No access-list changes or website read/write tests were performed.

## 文件與程式入口

- [完整規格來源快照](13_完整Schema_v1.0_來源快照.md)
- [v4 架構、設計決策與遷移](15_完整Schema_v4架構與遷移.md)
- [v4 驗證結果與全部欄位字典](16_完整Schema_v4驗證與欄位字典.md)
- [Atlas 實際 Schema 與索引讀回](05_實際Schema與索引.md)
- [更新前結構](14_完整Schema更新前結構.md)
- [現行 active Schema](schema_active_v4.py)、[現行完整唯讀查核](../../scripts/check_v4_database.py)；[Complete v4 初始定義](schema_complete_v4.py)、[初始 v4 遷移](migrate_complete_v4.py)及[當時查核](audit_complete_v4.py)保留為歷史來源
- [SKU 購物車服務](../services/sku_cart_service.py)、[評價服務](../services/review_service.py)
- [新版整合測試](test_complete_v4.py)、[JUnit 結果](complete_v4_test_results.xml)

商品主檔與 SKU 分離，SKU 保存價格與庫存；訂單主檔與明細分離。購物車操作改傳 sku_id，結帳交易同步扣庫存、建立明細與行為事件。評價需驗證本人已完成／送達的訂單明細，實際評價取代預設 4.0，顯示分數無條件進位至一位小數。推薦與統計集合、6+4 政策、70/30 分數上限及時間衰減設定已建立。

## 執行與歷史版本

目前在專案根目錄使用 active checker；`--env-file` 指向既有受保護設定檔，報告路徑必須尚不存在，且連線出口需已授權：

```powershell
python scripts/check_v4_database.py --env-file .env --report private-active-schema-readback.json --relationships
```

歷史 v4 初始建置依序使用 bootstrap_schema.py、migrate_cart_v3.py、migrate_schema_audit.py、migrate_complete_v4.py；這四步不涵蓋後續裝置 Session、評價、雙角色登入與本輪稽核遷移。以 active checker 的完整 migration 清單核對環境，遷移前先執行相應 preflight。遷移以 checksum 保護，不得修改已執行版本；含舊業務資料的環境須另做明確映射，不能重跑舊建置覆蓋正式資料。

02～12 號文件保存歷史規格與驗證；schema_current.py、audit_schema.py、test_schema_complete.py、test_cart_v3.py 為舊階段版本。舊測試只供相應版本環境使用。原 services/cart_service.py 保留作歷史服務及交易輔助基底，新環境入口為 services/sku_cart_service.py。

## 憑證與完成範圍

本機應用憑證在 .env，Schema 管理憑證在 .env.schema；已由 .gitignore 排除並設定 Windows ACL。Markdown 不含密碼。連線維運歷史見 [04](04_連線與維運.md)。

2026-10-05 當時已完成資料庫、索引、驗證規則、政策設定與必要 SKU／評價服務；當時 Flask 尚未接線、ENABLE_CHECKOUT 為 false。後續前台 6＋4、示範結帳、後台與 scoped 裝置撤銷已由各輪正式發布接續，最新行為請讀本頁頂端與優化系統文件。離線快照排程、完整 D5 編輯及本人驗收的完成狀態仍各自列管。

## English summary

This directory preserves immutable migrations and dated Atlas evidence. The current active contract has 30 collections, 96 indexes and 8 migrations, verified on 2026-10-21; use schema_active_v4.py and scripts/check_v4_database.py. Documents 15–17, the 66-test result and the initial 27-collection structure are historical. Session-revocation auditing is a scoped release; broader D5 editing remains separate. Use sku_cart_service.py for the SKU cart interface, and do not rerun historical initialization against a populated production database.

- [Atlas／Compass 資料庫查詢手冊](19_Atlas與Compass資料庫查詢手冊.md)：連線、商品與 SKU 搜尋、分類、示範訂單及 Schema 查閱。
