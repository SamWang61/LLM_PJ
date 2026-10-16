# SAM 工作交接摘要 / SAM handoff

交接日期：2026-10-07，Asia/Taipei。目的：供新對話接續 SAM 未完成工作，減少重讀舊文件；不刪除任何歷史檔案。

## 接手方式 / Start here

先讀本頁與 [CURRENT_CONTEXT.md](CURRENT_CONTEXT.md)，再依當次任務讀必要來源。最新使用者決策優先；GitHub、工作樹、資料庫狀態在操作前重新核對。以下遠端／資料庫數字是先前 10/7 核對紀錄，本次製作交接沒有重新連線驗證。

使用者已要求「開始進行 SAM 遺漏的工作」。因上下文接近容量上限，暫停於前置檢查。本輪尚未修改功能程式、執行資料庫寫入、提交或推送 GitHub；此次僅新增交接文件與摘要入口。

## 分工與界線 / Ownership

- SAM：資料庫、測試、組長協調及交付文件。
- JEFF：AI／後台。PR #8 是設計文件，不是後台功能交付。
- HEN（@1dcvgieok4gm）：B 會員／購物流程，feature/auth-order；邀請接受與晚間確認仍待核實。
- 前台／RWD 需重新分配；最終整合驗收責任待確認。
- 不把同學工作算成 SAM 成果；未獲明確要求，不代發私人訊息或評論給同學。

## 保留中的工作 / Preserve local work

專案：`C:\LLM\LLM_PJ`，GitHub：`SamWang61/LLM_PJ`。

原工作目錄在 `feature/flask-sku-ai-integration`、bbb8e9c，含尚未提交的超市前台、商品匯入、test_data、測試證據及文件。不要在此直接切換分支、重設、清理或覆蓋。不要把 Gemini 匯出、Google Map 筆記等無關檔案混入提交。

可優先核對並重用本聊天附加的乾淨工作樹：`C:\Users\USER\.codex\worktrees\ai-dashboard\LLM_PJ`。上次檢查無未提交異動，分支 `codex/hen-auth-order`、cf5d76e；開始編輯前再查一次，從最新 origin/main 建立 codex/ 開頭的新分支。`mongodb-query-manual` 工作樹有另一項工作，勿干擾。

複製本機成果時比較來源基底與 main，以差異整合，避免整份舊檔覆蓋 main 較新的修正。新建 PR 必須附加到對話；交付報告區分本機、已推送、已合併及已驗收。

## 已有證據 / Recorded evidence

- 10/7 GitHub 快照：main 066e9da；PR #9 已合併。JEFF PR #8（e7df815）開啟中，只有四份 Markdown；PR #5 仍為 JEFF 的計分候選草稿，PR #10 尚未合併。
- Atlas `vibecart_ai`：336 商品、336 SKU、600 停用合成客戶、3,000 demo 訂單、8,969 明細；67 位客戶無訂單。
- 批次 `sam-synthetic-20261005-v1`，訂單跨 2024～2026。已完成匯入及讀回，不要再次匯入或重設庫存。
- 現行結構為原 v4 加 `VibeCart_AI/MongoDB/test_data/schema_test_profile.py` 的人口欄位／批次 overlay，共五筆成功 migration。第五筆為 `20261005_05_synthetic_profile_v4`。
- 歷史 migration 與 checksum 不得修改；第五筆 checksum 與 overlay 原始檔相關，修正檢查器時另設現行契約入口。
- 27 集合／86 索引完整驗證日期為 10/5；10/7 沒有重跑整套驗證。
- behavior_events、product_embeddings、ai_requests、recommendation_logs 在 10/7 為零；不等於已查明記憶體快取狀態。
- 事件政策 PURCHASE=4、ADD_TO_CART=3、SEARCH=2、PRODUCT_VIEW=1。

## 下一步，依序执行 / Execution order

1. **GitHub 交付**：審查本機 test_data、overlay、匯入證據及 SAM 文件；盤點超市成果，分範圍提交。排除私密設定、憑證、復原快照及不必要的大型產物。保持必要的測試依賴可重現。
2. **修正資料庫檢查器**：`scripts/check_v4_database.py` 仍以原 v4 validator 與四筆 migration 比較，會誤報。新增現行契約入口、回歸測試並唯讀核對 Atlas；不重跑舊 migration。
3. **補資料契約**：D5 包含商品／SKU 更新、訂單狀態轉移、會員停用、權限、CSRF、稽核、衝突與回滾。AI 白名單補商品庫存／促銷與期間比較欄位；明列需 JEFF／HEN 確認的提案，不能自行標示已接受。
4. **補 D4 與登入測試**：生成可辨識批次、合法參照及時間的合成行為事件；建立少量私有客戶／管理員測試帳號，不啟用全部 600 人，不提交密碼。
5. **驗證與交付證據**：核對同批標準答案、日期區間、demo、取消／退款、零資料及上限邊界。離線測試不代表 Atlas、模型、登入或瀏覽器 UAT 通過；尚未實作的 JEFF 畫面保持待驗收。

目前 JEFF 設計待釐清：有效訂單分子與全部範圍訂單分母；可售 SKU 的 active 條件與最低價；D1～D3 資料已有；本機推論仍可能依賴 Atlas／圖片網路。現有 summary_metrics 缺商品明細與比較期間，無法支援全部設計問答。

## 按需來源與工具 / References and tools

- [JEFF 推送審查](JEFF_PUSH_REVIEW_2026-10-07.md)
- [測試資料規範](TEST_DATA_SPEC.md)／[匯入結果](TEST_DATA_IMPORT_2026-10-05.md)
- [SAM 工作紀錄](../專題進度/至今SAM完成的工作與預計項目_2026-10-05.md)
- 生成與測試：`VibeCart_AI/MongoDB/test_data/`；商品來源：`VibeCart_AI/MongoDB/supermarket/`。
- 既有 Python：`C:\LLM\LLM_PJ\MuscleCore分析資料\website\.venv\Scripts\python.exe`。網站測試從 website 目錄執行；必要時設定 PYTHONIOENCODING=utf-8。
- 私有連線設定由既有 bootstrap_schema.py 載入；不得輸出或提交 URI。曾可用 PyMongo，Atlas 連接器曾需重新登入；操作時重新確認。
- GitHub 可使用 Git 與標準 credential helper 認證的 REST；憑證只留記憶體，不輸出。gh 先前不可用。
- 備份另依 [BACKUP.md](BACKUP.md)：私有／加密方案及可靠共用撤銷、恢復與雲端驗證仍待解決。本任務不改固定 Drive 連結、不自行啟動未符合條件的備份。

English: Resume SAM's database and testing backlog in the order above. Preserve the dirty source checkout and historical files. Verify mutable state before action; do not confuse imported fixtures, pushed code, merged PRs and live acceptance. No credentials belong in the handoff or repository.
