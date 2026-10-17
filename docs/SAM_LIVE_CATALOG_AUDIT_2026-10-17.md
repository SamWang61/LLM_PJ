# SAM 商品／SKU 與線上頁面唯讀對帳｜2026-10-17

核對完成時間：2026-10-17 19:05（Asia/Taipei；JSON `checked_at` 為 UTC）。以正式 Atlas `vibecart_ai` 中 `schema_version=4`、`status=active` 的商品與 active SKU 為基準，匿名讀取正式 [Firebase Hosting 商城](https://vibecart-llmai.web.app/)。全程只有 MongoDB 查詢與 HTTP GET，沒有登入、加購、結帳或資料庫寫入。

| 範圍 | 結果 |
|---|---|
| 商品／SKU | Atlas active 商品 336、active SKU 336 |
| 商城清單 | 14 頁逐頁核對商品總數、頁碼、商品 ID 與排序；差異 0 |
| 商品詳情 | 336 頁逐一核對顯示最低 active SKU 價格、合計可用庫存、SKU 選項 ID／代碼／價格／庫存；差異 0 |
| 搜尋 | 三筆資料來源商品名稱與一筆無結果邊界；頁面總數、頁碼及商品 ID 對應；差異 0 |

完整計數與差異清單見[機器報告](inventory/sam-live-catalog-20261017.json)，提交位元組 SHA-256 為 `ad843e32a074b724b5fdcc0f1ffd7e21dea574659390ea816c4937cc3eb790bd`。可用 `scripts/check_live_catalog.py --env-file <受控環境檔> --report <新的報告路徑>` 重現；環境須設定 `DATA_MODE=v4`，且程式只接受指定 Atlas 主機與 `vibecart_ai`。報告不含 Mongo URI、帳密、會員或訂單資料。單一商品的實際畫面、SKU 與 Atlas 對帳另見 [S03 截圖證據](../簡報文件/screenshots/S03-product-evidence.md)。

**驗收界線：**這是當時公開服務與 Atlas 的連續讀取，並非原子快照；查核期間若有他人交易，價格或庫存仍可能變動。本次沒有權限即時讀回 Cloud Run 流量 revision／映像 digest，因此尚不能把所有 336 頁宣稱為已證實的「同一部署 SHA」畫面。手機、鍵盤、登入後加購與結帳、S02／S03 最終簡報簽認仍須另驗。這些結果也不解除 D4 consumer 遠端隔離閘門。
