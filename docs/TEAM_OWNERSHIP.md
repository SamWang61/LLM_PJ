# 現行分工與確認項目 / Current team ownership

更新日期：2026-10-02（Asia/Taipei）。以下依使用者最新決策，優先於舊四人分工表及先前的 SAM 後台交接描述。歷史提交的作者與合併事實不改寫。

| 範圍 / Area | 負責人 / Owner | 狀態與界線 / Status |
|---|---|---|
| 組長協調、資料庫與測試 | **SAM** | 已確認；目前執行 v4 檢查、資料庫回歸測試、驗證證據與文件 |
| AI／管理後台 | **JEFF** | 已確認；功能、模型、計分、推薦池與後台需求由 JEFF 負責 |
| 前台／RWD 介面 | **HEN** | 暫定；2026-10-06（下週二）再次與 HEN 確認，尚未記為完成確認 |
| 會員／購物流程 | 待確認 | 不因 SAM 曾處理介接就推定為其長期分工 |
| 跨模組整合驗證與最終驗收 | 待確認 | SAM 尚需再確認；資料庫測試通過不等於全站整合驗收完成 |

SAM owns database/testing and team coordination. JEFF owns AI/admin. HEN provisionally owns frontend/RWD, to be confirmed on October 6. Auth/order ownership and cross-module acceptance ownership are not assigned by this record.

## SAM 現在可執行 / SAM's current work

1. v4 validator、索引、遷移狀態、有效政策與資料關聯的只讀檢查。
2. 資料庫測試：格式拒絕、Decimal128、SKU 庫存、交易 rollback／併發、訂單與評價契約。
3. 建立具日期的驗證證據與測試操作說明，保留歷史報告。
4. 提供其他組別資料契約與缺口清單；需求涉及 Schema 時另做版本化遷移，不重寫舊 migration。

執行與驗證詳見 [SAM 資料庫與測試](SAM_DATABASE_TESTING.md)。跨模組 Flask／AI／RWD 新功能與驗收不在本輪擴大執行。

## 已存在工作如何處理 / Existing work

- PR #2／#3／#4 已合併的程式與文件保留，完成事實見 [合併紀錄](MERGE_RECORD_2026-10-02.md)。
- [PR #5](https://github.com/SamWang61/LLM_PJ/pull/5) 是確認分工前產生的行為計分候選實作，已轉為草稿，**未合併且不算 SAM 正式交付**。分支內原有 SAM 分工文字已由本文件取代；是否採用由 JEFF 後續決定。
- 沒有替 JEFF 或 HEN 發送通知、指派任務或變更其分支；本文件記錄責任，不代表本人已簽核。

Previously merged work remains intact. PR #5 is parked as an unmerged draft; no teammate has been contacted or assigned through external messages.
