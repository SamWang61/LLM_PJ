# 變更紀錄 / Changelog

## 2026-10-09 — JEFF 設計規格 v1.1 與 D5／AI 契約回覆 / Design v1.1 and contract reply

- 依 SAM 審查修正：KPI 分子／分母、可售 SKU 候選與最低價、模型離線範圍、D1～D3 現況。Review fixes.
- 回覆 D5／AI 契約：接受白名單 v1；預設問題＋管理員自由輸入（防護待討論）；稽核保留 180 天；後台不能停用管理員；第一版寫入範圍不含退款。Contract decisions.
- 僅文件。Documentation only.

## 2026-10-05 — JEFF 管理後台設計規格 / Admin UI design

- 新增 [管理後台設計規格 v1.0](docs/JEFF_ADMIN_UI_DESIGN.md)：左側欄導覽、AI 板塊 A／B、AI 比較、推薦監控及商品／訂單／會員管理版面與決策紀錄。Admin layout and decisions.
- 線框圖不含示範數字；新增 v4 集合與欄位對照及資料需求 D1～D5，供資料庫對接。Field mapping replaces sample values.
- 僅文件，不修改程式、Schema 或憑證。Documentation only.

## 2026-10-05 — HEN 選擇會員／購物流程 / HEN auth-order ownership

- 仁千 HEN 已選 B，對應 `feature/auth-order`；前台／RWD 改為待重新分配。HEN now owns auth/order.
- 更新分工表、分支協作、首頁與 [HEN 交接文件](docs/HEN_AUTH_ORDER.md)。Access status is tracked separately from ownership.

## 2026-10-02 — 分工更正與資料庫測試 / Ownership and database checks

- 現行責任：SAM 資料庫／測試、JEFF AI／後台、HEN 前台／RWD（10/6 再確認）；整合驗證待確認。See [ownership](docs/TEAM_OWNERSHIP.md).
- PR #5 計分候選轉草稿，未合入 main；不列入本次 SAM 交付。The candidate scoring branch remains parked.
- 新增只讀檢查器與 17 項回歸案例；既有真實資料庫測試 66 項通過，測試前後集合筆數一致。See [database evidence](docs/SAM_DATABASE_TESTING.md).
- 不修改功能、Schema、migration、憑證或部署。No application, schema or credential changes.

## 2026-10-02 — 合併與連線紀錄 / Merge and connection record

- PR #3 先合入 SAM 整合分支，PR #2 再合入 main；合併後 CI 通過。Both PRs merged in dependency order; main CI passed.
- [完整修改與合併紀錄](docs/MERGE_RECORD_2026-10-02.md) 說明提交、驗證與既有 v4 資料庫選擇。Documented commits, verification and the existing database decision.
- 明確區分本機私有 URI、可提交範本與尚未配置的 GitHub Secrets；未提交帳密。Credentials remain outside Git.

## 2026-10-02 — SAM 後台與連線 / Dashboard and connection

- 建立依賴整合分支的 AI 後台：台北日期、示範訂單、營收與推薦行為監測。Added scoped dashboard queries and summary caching.
- 私有 v4 設定與可清理的真實交易驗證；38 項離線測試通過。Added a private profile and live verification evidence.
- 更新雙語分支規則、文件索引與交付清冊；保留既有架構。Updated ownership and navigation without moving existing files.

## 2026-09-27 — 倉庫整理 / Repository organization

- 新增中文優先的雙語首頁、文件索引、貢獻規範、安全政策與協作範本。Added Chinese-first bilingual navigation and collaboration documents.
- 保留原始程式路徑、歷史規格與遷移檔案。Preserved application paths and migration/source snapshots.
- 加入檔案清冊、Git 忽略規則、文字格式與離線 CI。Added file inventory, publication exclusions and offline checks.
- 記錄每日 23:30 備份需求及共用／機密資料前置條件。Documented backup timing and sharing prerequisites.

## 2026-09-19 — 既有里程碑 / Historical milestone

Complete Schema v4 的建置與測試證據保存在 [MongoDB 工作總結](VibeCart_AI/MongoDB/17_2026-09-19_MongoDB工作總結.md)。本次未重新執行 Atlas 遷移或整合測試。Historical evidence is retained without rerunning Atlas operations.
