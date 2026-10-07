# 超級市場測試商品資料（2026-10-05）

> **已於 2026-10-05 依使用者指示重建並重新匯入。** 目前 27 集合、336 商品、336 SKU、8 大類、24 小類；832 筆文件逐筆比對及 Flask 讀取通過。先前集合消失的歷史狀態已封存，最新結果見 [latest_status.json](latest_status.json) 與 [重建報告](../18_2026-10-05_Schema重建與超市商品匯入.md)。

已匯入指定 Atlas `vibecart-ai-free` 的 `vibecart_ai`，採用既有 Complete Schema v4，未修改 validators、索引或歷史遷移。

## 交付結果

|項目|結果|
|---|---|
|商品|336 個不同商品頁、336 個不同名稱|
|SKU|336 筆；256 種來源規格文字，每項對應原網站的販售規格|
|分類|8 大類、24 小類，每小類 14 項、每大類 42 項|
|品牌|128 筆，僅使用來源明示品牌；未列品牌者保留 null|
|圖片|336 個來源照片網址，逐項 HEAD 回應 200 且 Content-Type 為 image；不另存圖片檔|
|價格|來源頁擷取時的 TWD 參考價，以 Decimal128 儲存；不保證日後即時價格|
|描述|自行撰寫的測試摘要，保留原名稱、規格及商品來源連結；未複製原站描述 HTML|
|庫存|模擬值，包含正常、低庫存及缺貨情境；不是零售商即時庫存|
|評價|DEFAULT 4.0、rating_count=0；不製造真實評價或交易紀錄|

來源入口為 [家樂福原公開商城網址](https://online.carrefour.com.tw/zh/homepage/)。本次實際請求轉址至 [現行公開商城](https://online.uni-prosperity.com.tw/)，頁面標題顯示「萬家福」。逐項實際商品網址、圖片網址、來源分類、規格、價格及 UTC 擷取時間均保存在 source_catalog.json。這批資料不代表與來源商家合作或實際販售。

|大類|小類（各 14 項）|商品數|
|---|---|---|
|乳品與蛋品|鮮乳．調味乳、優酪乳．優格、雞蛋．豆製品|42|
|冷凍與冷藏食品|水餃 麵食、冰淇淋 雪糕、包子饅頭 餡餅|42|
|飲料與飲用水|礦泉水、綠茶．烏龍茶．其他茶飲、蔬果汁|42|
|餅乾與休閒零食|鹹餅乾、甜餅乾、堅果類|42|
|米麵與食用油|米、泡麵、食用油|42|
|調味與沖泡食品|罐頭、調味品、茶包|42|
|家庭清潔與紙品|抽取式．平板．滾筒、洗衣精 洗衣球、洗碗精|42|
|個人清潔與護理|口腔清潔用品、沐浴用品、洗護造型|42|

## 檔案與驗證證據

- [商品預覽 CSV](catalog_preview.csv)：UTF-8 BOM，可用試算表查看名稱、分類、規格、價格、來源與圖片。
- [來源清單 JSON](source_catalog.json)：336 筆經逐頁核對的來源事實與時間。
- [v4 MongoDB Extended JSON](catalog_v4.extjson)：依集合分類，保留 ObjectId、Decimal128、BSON 日期型別；建議以匯入腳本寫入，而非直接整檔 mongoimport。
- [驗證報告](validation_report.json)：先在 Atlas 交易內試寫 32 分類、128 品牌、336 商品、336 SKU，全部通過後回滾，原資料數不變。
- [首次匯入歷史報告](initial_import_report.json)：集合消失前的交易一次提交 832 筆文件。
- [本次重建後匯入報告](import_report.json)：重新提交 832 筆文件。先前新增 0 筆的重跑報告封存在 recovery_20261005/before/import_report.json。
- [Flask 實際讀取報告](storefront_report.json)：連到真實 Atlas，336 項皆可透過 14 頁讀取，8 大類／24 小類篩選、24 個代表商品詳情、照片及來源連結、關鍵字搜尋通過。匿名唯讀，不新增使用者或行為事件。

網站 32 項自動測試通過，包括超過 200 項的分頁、搜尋、照片與來源連結，以及既有登入、CSRF、SKU 購物車與結帳控制。這是本機程式整合驗證，尚未取得公開網站網址，不能視為已部署或完成遠端瀏覽器驗收。

## 使用與重跑

在專案根目錄 `C:/LLM/LLM_PJ` 執行：

```powershell
# 預設只試寫並回滾；不永久新增
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' 'VibeCart_AI\MongoDB\supermarket\import_catalog.py'

# 正式匯入；已經執行完成，通常無須再執行
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' 'VibeCart_AI\MongoDB\supermarket\import_catalog.py' --apply

# 用現有 Atlas 資料進行匿名唯讀網站驗證
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' 'VibeCart_AI\MongoDB\supermarket\verify_storefront.py'

# 啟動本機超市展示，網址 http://127.0.0.1:5000
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' 'MuscleCore分析資料\website\run_supermarket.py'
```

匯入器使用現有被忽略的 `MongoDB/.env`，確認 host 與 DB 後連線，不輸出 URI。來源商品 ID 對應穩定 ObjectId 與 `CF-`／`CF-SKU-` 代碼，分類使用 `SM-`。只以 `$setOnInsert` 新增；重跑不覆寫被測試者修改的庫存、價格、評價或訂單。不刪除其他資料，也不重新建立 schema。

collect_catalog.py 是重新擷取工具，非日常啟動必要步驟。其本機 detail_cache.json 是續跑快取，已忽略；需要刷新來源時另行規劃新批次，避免把新價格誤當成已更新到 DB。來源網址、產品分類和照片仍可能日後改變；圖片載入失敗時，網站顯示本機替代圖。

## 交給組員的連線設定

部署現有 Flask 程式時，在伺服器的秘密設定中提供 MONGO_URI、MONGO_DB=vibecart_ai、DATA_MODE=v4 及固定 SECRET_KEY；Atlas 的 Network Access 依 2026-10-05 使用者回報已新增 `0.0.0.0/0`，生效期間允許任意 IPv4 伺服器來源；本次外掛需重新登入，Active 與到期狀態尚未核實，詳見 [Cluster 設定](../01_Cluster設定與狀態.md)。勿把 URI 密碼放入前端 JavaScript、CSV、MD 或 Git。

本機 run_supermarket.py 明確採用 v4，關閉真實結帳及外部 AI 呼叫；未改寫原 Flask .env。它只監聽本機，不能把 127.0.0.1 連結分享給同學當作公開站。正式 WSGI 部署可使用 run_supermarket:app，並在伺服器設定固定 SECRET_KEY；若需其他模式，依現有 create_app 設定 DATA_MODE=v4。

目前可驗證商品瀏覽、分類、搜尋、規格、照片與來源資料；購物車需登入。完整首推要求實際評價，本批次不會偽造 ACTUAL 評價來填滿推薦池。需要公開測試時，仍需提供既有網站網址或部署目標，才能驗證同學從外部瀏覽器的完整流程。

## 本次資料交付範圍（2026-10-07）

本 worktree 僅交付商品資料／工具／歷史證據；run_supermarket 與前台模板修改仍在原工作目錄，未包含本次提交。上列 storefront／啟動指令需完整前台分支；請勿將歷史報告視為本次 main 前台通過證據。
