# 變更紀錄 / Changelog

## 2026-10-09 — JEFF 雲端洞察 / Cloud insight (T2, R09)

- 新增 `/admin/ai/insight`：依 AI 白名單 v1 由伺服器重新彙總本期與比較期資料；4 個預設 intent 加上有防護的自由提問（300 字、不可信輸入隔離、個資格式拒送、每分鐘限流）。Added the cloud insight page.
- 回覆標示模型、耗時、token 與「請人工核對」；預覽就是同一次請求實際送出的 JSON；失敗時退回規則答案。總覽摘要與洞察共用 Claude 呼叫邏輯。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新設定 `AI_INSIGHT_RATE_LIMIT`；新增 26 項離線測試（共 92 項）；真實模型尚未實測。

## 2026-10-09 — JEFF 後台共用版型 / Admin shared layout (T1, R05)

- 新增後台專用 `admin/layout.html`、`admin.css`、`admin.js`：側欄導覽、獨立頁首、系統狀態燈、平板分頁列、手機漢堡選單、懸浮提示；不修改前台 `base.html`／`main.css`。Added an admin-only layout.
- 營運總覽 KPI 改「有效／全部訂單」，零有效單客單為 null；每日營收加 CSS 長條圖；推薦監控改讀 v4 權重政策。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新增 11 項離線測試（共 66 項）。Offline tests only; no Atlas writes.

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
