# VibeCart AI MongoDB 建置紀錄

更新：2026-09-19（Asia/Taipei）。依新增的 VibeCart_AI_MongoDB_Complete_Schema.md，已完成指定 Atlas 資料庫的 Complete Schema v4 更新與實際驗證。

|項目|實際結果|
|---|---|
|Organization|LCCNET_LLM_2601 / 6aa9bcbb67ff2925383957b8|
|Project|vibecart_ai / 6aa9bd20af3f21039447a5c0|
|Cluster／資料庫|vibecart-ai-free / vibecart_ai|
|方案／地區|原建置 Free，AWS AP_SOUTHEAST_1；本次未變更部署方案|
|資料結構|19 個新版核心 v4 集合 + 8 個保留集合，共 27 個 strict/error validators|
|索引|59 個自訂索引 + 27 個 _id_，共 86 個；24 個自訂唯一索引、2 個 TTL|
|資料|schema_migrations 4 筆 succeeded，system_configs 1 筆，其餘集合 0 筆；測試資料已清除|
|驗證|新版 66 項 Atlas 整合測試通過；遷移重跑及唯讀查核成功|

Atlas 外掛本次 OAuth 失效，使用先前授權的 PyMongo 連線完成實際變更與讀回。控制台部署中繼資料未重新核實；原始資訊見 [Cluster 設定](01_Cluster設定與狀態.md)。

## 現行文件與程式

- [完整規格來源快照](13_完整Schema_v1.0_來源快照.md)
- [v4 架構、設計決策與遷移](15_完整Schema_v4架構與遷移.md)
- [v4 驗證結果與全部欄位字典](16_完整Schema_v4驗證與欄位字典.md)
- [Atlas 實際 Schema 與索引讀回](05_實際Schema與索引.md)
- [更新前結構](14_完整Schema更新前結構.md)
- [現行 Schema 定義](schema_complete_v4.py)、[v4 遷移](migrate_complete_v4.py)、[現行唯讀查核](audit_complete_v4.py)
- [SKU 購物車服務](../services/sku_cart_service.py)、[評價服務](../services/review_service.py)
- [新版整合測試](test_complete_v4.py)、[JUnit 結果](complete_v4_test_results.xml)

商品主檔與 SKU 分離，SKU 保存價格與庫存；訂單主檔與明細分離。購物車操作改傳 sku_id，結帳交易同步扣庫存、建立明細與行為事件。評價需驗證本人已完成／送達的訂單明細，實際評價取代預設 4.0，顯示分數無條件進位至一位小數。推薦與統計集合、6+4 政策、70/30 分數上限及時間衰減設定已建立。

## 執行與歷史版本

在專案根目錄執行：

```powershell
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' 'VibeCart_AI\MongoDB\audit_complete_v4.py'
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' -m pytest 'VibeCart_AI\MongoDB\test_complete_v4.py' -q
```

新空環境依序執行 bootstrap_schema.py、migrate_cart_v3.py、migrate_schema_audit.py、migrate_complete_v4.py。遷移以 checksum 保護，不得修改已執行版本。含舊業務資料的環境需另做映射遷移，腳本不會猜測轉換。

02～12 號文件保存歷史規格與驗證；schema_current.py、audit_schema.py、test_schema_complete.py、test_cart_v3.py 為舊階段版本。舊測試只供相應版本環境使用。原 services/cart_service.py 保留作歷史服務及交易輔助基底，新環境入口為 services/sku_cart_service.py。

## 憑證與完成範圍

本機應用憑證在 .env，Schema 管理憑證在 .env.schema；已由 .gitignore 排除並設定 Windows ACL。Markdown 不含密碼。連線維運歷史見 [04](04_連線與維運.md)。

本次已完成資料庫、索引、驗證規則、政策設定與必要 SKU／評價服務。舊 Flask 網站尚未接線至新版；首推生成、6+4 排序、衰減計分、統計批次與排程尚未部署。ENABLE_CHECKOUT 保持 false；測試以明確啟用的服務實例驗證交易。資料結構完成不代表完整 AI 推薦及營運功能已上線。

## English summary

This directory preserves schema definitions, immutable migrations and dated Atlas evidence. Start with documents 15–17 for Complete Schema v4. The recorded 66 passing tests and 27 collections describe the September 19 validation, not a fresh run. Use sku_cart_service.py for the current SKU cart interface. Legacy tests target older schema versions. Do not run all historical migrations or tests against a populated production database without an explicit migration plan.
