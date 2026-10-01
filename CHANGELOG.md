# 變更紀錄 / Changelog

## 2026-10-02 — SAM 行為計分 / Preference scoring

- 新增 v4 事件去重、70／30 上限與逐事件半衰期計算；讀取有效政策。Added policy-based member scoring.
- 提供預設只讀批次工具、會員限額、重跑與並行更新防護；未啟用排程。Added bounded dry-run/apply job.
- 50 項離線測試通過；真實 Atlas 嚴格格式、寫入與重跑通過且測試資料清理完成。See [verification](docs/SAM_SCORING_VERIFICATION.json).
- 新增 [SAM 執行清單](docs/SAM_WORK_PLAN.md) 與 [操作交接](docs/PREFERENCE_SCORING.md)。

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
