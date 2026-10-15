# 網站客戶與訂單測試資料規範 / Customer and order test-data specification

版本：1.0；日期：2026-10-05（Asia/Taipei）；負責：SAM（資料庫與測試）。

## 目的與適用環境 / Purpose and target

依使用者指定，寫入現有 Atlas `vibecart-ai-free` 的 `vibecart_ai`，不是另建隔離資料庫。使用既有超市 336 商品／336 SKU；本批不增加、改價或扣減商品庫存。不抓取真實客戶、電話或訂單，不代表零售商歷史銷售。

固定批次 `sam-synthetic-20261005-v1`，亂數種子 20261005，資料截止為台北 2026-10-05 08:00。每一筆會員、訂單、明細均有 `synthetic_batch_id`；所有訂單 `is_demo=true`。共享資料庫不放入偽裝為正式交易的 `is_demo=false` 測試訂單。排除示範時，本批應貢獻 0 筆、0 元；若需混合非示範情境，另用隔離測試庫。

English: Generate synthetic customer/order fixtures against the existing catalog. The explicitly authorized target is the shared vibecart_ai database. Every order is marked demo; existing catalog, stock, and other data are preserved.

## 資料量與人口欄位 / Population and fields

|項目|規範|
|---|---|
|會員|600 位，姓名「測試會員0001」等，Email 為 `sam-test-0001@example.com` 等|
|性別|male／female 各 300 位；schema 另支援 unspecified|
|年齡層|18–24、25–34、35–44、45–54、55–64、65–79；以 2026-10-05 計算，每層 100 位|
|婚姻別|single、married、divorced、widowed、unspecified，各 120 位|
|交叉分布|2 性別 × 6 年齡層 × 5 婚姻別 × 10 人 = 600；僅為測試覆蓋，不是人口統計|
|生日|合法日期 `YYYY-MM-DD`；保留生日而非隨時間失真的固定年齡|
|會員狀態|全部 customer／inactive／is_active=false；不可登入的 password_hash，無共用密碼；會員等級只是合成測試值|
|無訂單客戶|每個十人組保留一人不下單，至少 60 人；其餘可能依亂數再產生零單會員|
|訂單|3,000 筆，2024-01-01 至 2026-10-05，涵蓋 34 個年月|
|明細|每單 1–5 個不同 SKU，每 SKU 數量 1–5；實際總筆數以 manifest 為準|

人口組合獨立於商品挑選及消費金額，不把性別、年齡或婚姻別推定為偏好。`demographics.marital_status` 代表截止日的合成狀態，沒有婚姻變動歷史；不得宣稱為下單當日狀態。年齡可按下單日重新計算，每筆訂單會員須滿 18 歲且已註冊。

English: Balanced demographic coverage is synthetic, not a representative population or recommendation rule. Accounts are disabled; login testing requires separately provisioned credentials. Marital status is an as-of snapshot, not historical marital status.

## 結構與關聯 / Schema and relationships

- 保持 v4；新增 `test_data/schema_test_profile.py` overlay，不改寫歷史 schema 與 migration。
- 新遷移 `20261005_05_synthetic_profile_v4` 只擴充 users、orders、order_items 的可選批次欄位，以及 users 的可選 demographics。既有 required、索引、strict/error 規則保留；舊文件不需補假人口資料。
- demographics 一旦提供，必須包含 gender、birth_date、marital_status、as_of_date。日期字串格式由 schema 檢查，合法曆日、年齡及時間關聯由生成驗證器檢查。
- 穩定 ObjectId 由批次／類型／流水號雜湊產生。Email、訂單號、checkout_id 使用本批固定命名；重跑遇其他文件的唯一鍵衝突即停止。
- order_items.user_id 必須等於 orders.user_id；SKU 必須屬於 product；分類快照必須對應該商品。
- 商品名稱、價格與分類採 2026-10-05 既有資料快照，用來構造合成歷史，**不是 2024／2025 的真實歷史售價或上架證據**。

## 訂單狀態與金額 / States and money

每 10 筆：4 筆完成已付款、1 筆出貨已付款、1 筆確認已付款、1 筆待付、1 筆付款失敗、1 筆取消已退款、1 筆取消未付款。因此有效訂單共 1,800 筆。退款不納入有效營收，已付且未取消才計入。運費 80 元、折後滿 1,500 免運；每十筆一筆 10% 測試折扣。此為測試政策，並非正式商業規則。

金額用 Decimal128、兩位小數：`line_total=unit_price×quantity`；`subtotal=明細加總`；`total_amount=subtotal-discount_amount+shipping_fee`。訂單時間以 UTC BSON Date 保存，分日／分月以 Asia/Taipei 計算。paid_at、completed_at 不得早於 ordered_at 或晚於截止時間。

合成歷史匯入不呼叫結帳、不扣現有庫存、不產生實際付款／物流、不造 ACTUAL 評價、推薦歸因或模型執行紀錄。庫存屬獨立的目前模擬快照，不能由本批歷史訂單回推庫存帳。

English: Decimal money and consistent references are mandatory. All revenue is simulated, valid only for paid/non-cancelled demo orders. Historical fixtures do not run checkout or mutate stock; they are not payment, fulfillment, inventory-ledger, or model-execution evidence.

## 生成與匯入順序 / Required sequence

1. 只讀核對目標、27 集合、validators、現存資料與商品／SKU；產生商品快照。
2. 固定種子生成 600 位會員，驗證人口分布與註冊日期。
3. 生成按時間排序的跨年訂單，選取當時已註冊且滿 18 歲的會員。
4. 建立 SKU 明細、價格及分類快照，再計算訂單合計與狀態時間。
5. 離線檢查關聯、重複、金額、人口、時間，輸出 Extended JSON、CSV、雜湊清冊、每日／每月／熱銷／人口標準答案。
6. 保存遷移前結構，新 migration 添加可選欄位並讀回；DDL 不是交易，失敗記 failed，停止後人工核查，不自動重建或刪除。
7. 在真實 Atlas transaction 內插入並回滾，驗證 strict validator 與唯一索引接受資料；確認筆數未改變。
8. 同批資料以單一 transaction 正式提交；既有同 ID 完全相同則跳過，內容不同即停止，不覆寫。
9. 逐筆讀回完整 BSON 並比對雜湊、重驗關聯及金額；MongoDB 另行聚合每月有效營收與訂單數，對照標準答案；核對所有其他集合筆數、商品快照及庫存未改變。
10. 執行唯讀 verify，保存完成證據。匯入成功不等於 JEFF 畫面串接或全站 UAT 通過。

## 重跑入口與產物 / Commands and artifacts

在專案根目錄，使用 website 的既有 Python 環境執行：

```powershell
python VibeCart_AI/MongoDB/test_data/workflow.py generate
python VibeCart_AI/MongoDB/test_data/workflow.py migrate
python VibeCart_AI/MongoDB/test_data/workflow.py dry-run
python VibeCart_AI/MongoDB/test_data/workflow.py apply
python VibeCart_AI/MongoDB/test_data/workflow.py verify
```

匯入器沿用受忽略的 MongoDB/.env；migration 沿用 .env.schema。URI 不進入文件或資料包。固定 host 與 database 檢查由既有 connect 提供；操作鎖阻止本機重疊執行。鎖檔因中斷殘留時先確認沒有執行中的工作，再人工處理。

產物位於 `VibeCart_AI/MongoDB/test_data/generated/`：manifest.json、expected_metrics.json、dataset.extjson、catalog_snapshot.extjson、users_preview.csv、orders_preview.csv，以及 migration／dry-run／apply／verify 報告。大型完整資料與 CSV 在該目錄 .gitignore 排除；規範、生成器、測試、清冊與摘要證據可提交。不要手動刪除／覆寫現有批次再重跑；需要新分布時使用新批次及重新審核的設定。

歷史 verify_complete 與舊只讀工具使用原 v4 validator，會將此新增 overlay 判為差異。新增人口欄位後應使用本批 verify 作為目前結構驗證；不得把舊 migration 重新套用或改 checksum。後續統一全站 schema 入口列入 SAM 待辦。

## 驗收與未包含項目 / Acceptance and limits

必測：台北跨年午夜、2024-02-29、每月與同期間比較、排除 demo 得零、非付／取消／退款排除、至少 60 位零單會員、既有商品庫存不變。另須用獨立情境測試 366 天／5,000 筆上限、空期間、衝突與並行寫入；3,000 筆跨三年的總清冊不應直接要求後台突破 366 天上限。

本批不刻意製造促銷季節性，也不宣稱真實客群／模型品質；若需因果分析教學，另建立有標籤、明確預期結果的新批次。JEFF 原型的篩選、推薦資格及請求預覽問題仍需接線後重測。
