# 現行分工與確認項目 / Current team ownership

更新日期：2026-10-07（Asia/Taipei）。以下依使用者最新決策，優先於舊四人分工表及先前的 SAM 後台交接描述。歷史提交的作者與合併事實不改寫。

| 範圍 / Area | 負責人 / Owner | 狀態與界線 / Status |
|---|---|---|
| 組長協調、資料庫與測試 | **SAM** | 已確認；目前執行 v4 檢查、資料庫回歸測試、驗證證據與文件 |
| AI／管理後台 | **JEFF** | 已確認；功能、模型、計分、推薦池與後台需求由 JEFF 負責 |
| 前台／RWD 介面 | **SAM** | 2026-10-07 組長指示：非 HEN/JEFF 範圍由 SAM 承接；本次交付超市瀏覽前台，完整手機驗收待辦 |
| 會員／購物流程（B） | **仁千 HEN** | 2026-10-05 已確認；使用 `feature/auth-order`，見 [分支交接](HEN_AUTH_ORDER.md) |
| 跨模組整合驗證與最終驗收 | **SAM** | 2026-10-07 指名；須等 JEFF/HEN 對應功能先交付，資料庫測試不等於全站驗收 |

SAM owns database/testing and team coordination. JEFF owns AI/admin. HEN confirmed option B (auth/order) on October 5 and uses feature/auth-order. As of October 7, SAM owns frontend/RWD and final integration acceptance under the team lead instruction.

## SAM 現在可執行 / SAM's current work

1. v4 validator、索引、遷移狀態、有效政策與資料關聯的只讀檢查。
2. 資料庫測試：格式拒絕、Decimal128、SKU 庫存、交易 rollback／併發、訂單與評價契約。
3. 建立具日期的驗證證據與測試操作說明，保留歷史報告。
4. 提供其他組別資料契約與缺口清單；需求涉及 Schema 時另做版本化遷移，不重寫舊 migration。

執行與驗證詳見 [SAM 資料庫與測試](SAM_DATABASE_TESTING.md)。跨模組 Flask／AI／RWD 新功能與驗收不在本輪擴大執行。

## 已存在工作如何處理 / Existing work

- PR #2／#3／#4 已合併的程式與文件保留，完成事實見 [合併紀錄](MERGE_RECORD_2026-10-02.md)。
- [PR #5](https://github.com/SamWang61/LLM_PJ/pull/5) 是確認分工前產生的行為計分候選實作，已轉為草稿，**未合併且不算 SAM 正式交付**。分支內原有 SAM 分工文字已由本文件取代；是否採用由 JEFF 後續決定。
- 2026-10-05 已由組長確認 HEN 選擇會員／購物流程；GitHub 存取狀態另見分支交接，分工確認不等於邀請已接受。

Previously merged work remains intact. PR #5 is parked as an unmerged draft; HEN ownership is confirmed by the team lead, while GitHub invitation acceptance is tracked separately.

## 2026-10-07 最新核對與待辦

HEN（1dcvgieok4gm）及 JEFF（jeff841117）均已具 Write 權限，pending invitations 為零。此為目前狀態，舊 10/5 邀請紀錄保留。詳細先後順序與單一負責人見 [專案進度盤點](PROJECT_PROGRESS_2026-10-07.md) 與 [具名殘留問題](PROJECT_BLOCKERS_2026-10-07.md)。所有非 JEFF AI/後台、非 HEN 會員/購物的工作由 SAM 負責；跨組驗收由 SAM 統整，前置完成責任分別列出。
