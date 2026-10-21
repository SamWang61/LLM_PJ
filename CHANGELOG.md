# 變更紀錄 / Changelog

## 2026-10-21 — JEFF 管理後台設計規格 v1.3 / Admin design v1.3

- 依 main `c66f731` 同步已合併實作：T5 真模型調整、線上 AI 開關與 AI 映像、v4 權重、個人推薦範圍、SAM 的 6＋4 與 #5 快照；更新現況、資料準備狀態、檔案對應與 D5 進度，新增第 13 節線上 AI 部署設定。Spec synced with merged work.
- 第 8 節改為 10/21 定案的淺色數據看板 token；原快照未改版的 CSS 由 #154 接續，實際部署另記優化系統文件。「分類營收占比」待定義資料來源。See [design spec](docs/JEFF_ADMIN_UI_DESIGN.md).

## 2026-10-21 — JEFF 前台使用回報 / Storefront issue report

- JEFF 以會員身分操作正式站，整理 12 項前台問題交 SAM：登入／登出重複送出造成 CSRF 400、約 2 秒回應與 MongoClient 生命週期疑點、庫存與規格、商品卡等。各項效能原因仍需獨立量測。見[歷史回報與現況界線](docs/JEFF_FRONTEND_ISSUES_2026-10-21.md)。Documentation only; latency causes remain unisolated.

## 2026-10-20 — PR #5 離線持久快照接續 / Offline scoring snapshots

- 現行請求時6＋4已接續前台需求；保留尚未被取代的明確會員離線快照工具，JEFF主責計分契約、SAM負責資料庫／測試／整合。見[操作與語義差異](docs/PREFERENCE_SCORING.md)。
- 快照version1保持分類raw權重70／30上限、商品逐事件衰減與明確ObjectId搜尋；採personalization先排synthetic再limit，真人有效示範購買可影響本人，正式歸因仍排除。預設dry-run，apply另驗唯一索引、會員／政策重讀與完整前像CAS。
- 本輪不接前台、不啟排程、不連線或寫入Atlas；原10/2的50項測試／Atlas證據維持歷史，新測試、CI及合併結果另由本輪交付報告記錄。

## 2026-10-18 — 最新main無流量預覽與私有真模型驗收

- [部署與驗收](docs/SAM_MAIN_PREVIEW_2026-10-18.md)：main20ee的52檔封裝與GCS實際讀回一致、Cloud Build三步SUCCESS；真BGE、四Claude問題／快取、角色／交易／1001 synthetic、停用規則退回及清理。
- 使用者建立Claude secret版本1 Enabled，私有tag明確引用；正式19／私有base11仍各100%、Hosting不變，自由提問關閉。新增密鑰操作文件、私有tag探針及22安全回歸；V5仍2/14，未宣稱正式切流量或全站簽收。

## 2026-10-18 — SAM 接手JEFF三PR整合與驗收

- [完整驗收](docs/SAM_JEFF_PR82_84_ACCEPTANCE_2026-10-18.md)：239／0真MongoDB回歸、32來源／fixture、52檔同版精簡與AI映像build／Gunicorn boot及真BGE斷網驗證。#83補7項錯誤政策與NaN／Infinity安全預設；#84改接main，個人示範購買與歸因隔離分開。
- 依使用者授權完成PR整合；正式服務未部署，線上AI仍關閉、Claude secret缺，V5仍2/14。保留REN／N14與其他修改，不代填具名簽收。



## 2026-10-18 — JEFF 示範結帳計入個人推薦 / Demo checkouts shape personal recommendations (B2)

- 新增 personalization 範圍：個人推薦只排除 synthetic 批次，真實會員的示範結帳會影響自己的推薦；推薦監控與歸因仍排除示範結帳。Attribution scope unchanged.
- 新增 7 項離線測試。See [dashboard handoff](docs/AI_DASHBOARD.md).


## 2026-10-18 — JEFF 規則推薦改用 v4 權重 / v4 recommendation weights (B1)

- 規則推薦由舊權重 1/3/4/8 改為 v4 政策 PURCHASE 4、ADD_TO_CART 3、SEARCH 2、PRODUCT_VIEW 1，v4 前台讀取資料庫政策；SEARCH 依搜尋字比對商品。Rule recommendations now follow the stored v4 policy.
- 新增 10 項離線測試。See [dashboard handoff](docs/AI_DASHBOARD.md).

## 2026-10-18 — N14 最新來源／Atlas完整還原與JEFF準備

- [N14](docs/SAM_N14_CURRENT_ATLAS_2026-10-18.md)：原目錄13,976檔全量重建差異0；Atlas28集合／14,691筆／89索引／validator／3TTL完成雲端認證與隔離還原，82安全回歸；修正複合索引順序比較及目錄／檔案替換，重新匯出、雲端讀回並完整還原驗證。差異包依賴保留的25片歷史基底；異機key／每日固定流程未完成。
- [JEFF判斷與準備](docs/SAM_JEFF_AI_READINESS_2026-10-18.md)：讀交接與三PR，42項針對性測試；本機AI映像實際建置與斷網BGE通過，B3正式設定唯讀核實、API Key缺口保留；沒有啟用線上AI或切流量。


## 2026-10-18 — N14 私有加密與隔離復原

- 新增串流認證加密／解密與internal Docker還原來源啟動工具，46項安全回歸通過。歷史13,048檔逐檔還原差異0、三筆BSON fixture／索引復原及四HTTP讀回通過。
- [N14完整證據與未完成範圍](docs/SAM_N14_ENCRYPTED_RESTORE_2026-10-18.md)：25/25雲端分片完整SHA與私人ACL核對，重組密文／認證解密後ZIP與05:28原備份相同；雲端清冊原ID更新與內容核對通過。最新快照／正式Atlas／異機key／每日固定專案流程仍待辦，V5仍2完成／12待結案。

## 2026-10-18 — JEFF 線上 AI 啟用準備 / Online AI readiness (A1, A2)

- 雲端 runtime 的 AI 開關改讀環境變數（預設關閉、格式錯誤即拒絕啟動），不放寬既有安全檢查。Cloud AI flags now come from the environment.
- 新增可選的 AI 映像（`INSTALL_AI=true`：CPU 版 PyTorch、內建 BGE 模型、Cloud Build 離線載入檢查）；預設映像不變。尚未建置與部署，設定見 [dashboard handoff](docs/AI_DASHBOARD.md)。

## 2026-10-18 — D4 同版隔離與合成批次驗收 / Synthetic event acceptance

- 修復 PR #47 的限時 ID token 授權與 IAM 傳播等待，完成同映像 consumer 遠端對照、探針清理與撤權。
- 以不可變 GitHub 證據通過正式閘門，匯入 D4 合成事件 1,240 筆；verify 缺漏 0、重送新增 0，D1～D3 與額外 demo 訂單保留。詳見 [驗收紀錄](docs/D4_IMPORT_ACCEPTANCE_2026-10-18.md)。

## 2026-10-16 — 管理後台規格 v1.2 契約補定 / Admin contract decisions

- 專案負責人定案自由提問的獨立預設關閉旗標、權限與遠端驗收條件；四個固定 intent 可分開交付。Free questions remain gated until accepted.
- 稽核與獨立重送紀錄各保留 180 天；定義單筆、原子及逐筆批量 `request_id` 與重送規則。Audit retention does not substitute for idempotency records.
- 將 JEFF 設計規格重新對齊現行 `main` 文件入口；此為文件契約更新，不代表 D5 寫入或真模型已完成。

## 2026-10-12 — JEFF 真實模型實測 / Real model validation (T5, R09)

- BGE：324 筆可售商品，模型載入 5.0 秒、全部向量化 7.6 秒，相似查詢中位數 26.5 ms；Top 5 共 40 筆全部同大類、37 筆同小類。Measured on CPU with read-only Atlas data.
- Claude：共 3 回 9 次真實呼叫。修正回覆截斷（`max_tokens` 1200 並標示截斷）、輸入 token 由約 1.8 萬降到 0.5～1 萬（依 intent 限量商品、縮排 1）、日期照抄；補貨候選改由程式篩選，並禁止模型自行計算。10/17 第 3 回驗證補貨修正有效。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新增 4 項離線測試。

## 2026-10-09 — JEFF AI 比較 / AI comparison (T4, R09)

- 新增 `/admin/ai/compare`：Local（BGE）與 Cloud（Claude）的延遲取最近 10 次實際呼叫的中位數，並顯示 Cloud 的平均 token；未量測時顯示「尚未量測」，不填示範數字。Added the measured comparison page.
- 只有設定 token 單價（`CLAUDE_INPUT_USD_PER_MTOK`／`CLAUDE_OUTPUT_USD_PER_MTOK`）時才估算成本；呼叫紀錄不含問題內容。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新增 11 項離線測試（共 115 項）。

## 2026-10-09 — JEFF Local 相似商品 / Local similar products (T3, R09)

- 新增 `/admin/ai/recommendation`：選一個可推薦且可購買的商品，以本機 BGE 計算 Top 5 相似商品，顯示 cosine 分數條、處理時間與快取命中；「更新商品向量」需 POST 並驗證 CSRF。Added the local similarity page.
- 模型未安裝或未下載時顯示安裝指令，不顯示假結果。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新增 12 項離線測試（共 104 項）；真實 BGE 待 T5 實測。

## 2026-10-09 — JEFF 雲端洞察 / Cloud insight (T2, R09)

- 新增 `/admin/ai/insight`：依 AI 白名單 v1 由伺服器重新彙總本期與比較期資料；4 個預設 intent 加上有防護的自由提問（300 字、不可信輸入隔離、個資格式拒送、每分鐘限流）。Added the cloud insight page.
- 回覆標示模型、耗時、token 與「請人工核對」；預覽就是同一次請求實際送出的 JSON；失敗時退回規則答案。總覽摘要與洞察共用 Claude 呼叫邏輯。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新設定 `AI_INSIGHT_RATE_LIMIT`；新增 26 項離線測試（共 92 項）；真實模型尚未實測。

## 2026-10-09 — JEFF 後台共用版型 / Admin shared layout (T1, R05)

- 新增後台專用 `admin/layout.html`、`admin.css`、`admin.js`：側欄導覽、獨立頁首、系統狀態燈、平板分頁列、手機漢堡選單、懸浮提示；不修改前台 `base.html`／`main.css`。Added an admin-only layout.
- 營運總覽 KPI 改「有效／全部訂單」，零有效單客單為 null；每日營收加 CSS 長條圖；推薦監控改讀 v4 權重政策。See [dashboard handoff](docs/AI_DASHBOARD.md).
- 新增 11 項離線測試（共 66 項）。Offline tests only; no Atlas writes.

## 2026-10-09 — JEFF 設計規格 v1.1 與 D5／AI 契約回覆 / Design v1.1 and contract reply

- 依 SAM 審查修正：KPI 分子／分母、可售 SKU 候選與最低價、模型離線範圍、D1～D3 現況。Review fixes.
- 回覆 D5／AI 契約：接受白名單 v1；預設問題＋管理員自由輸入（當時防護待討論，10/16 已補定）；稽核保留 180 天；後台不能停用管理員；第一版寫入範圍不含退款。Contract decisions.
- 僅文件。Documentation only.

## 2026-10-05 — JEFF 管理後台設計規格 / Admin UI design

- 新增 [管理後台設計規格 v1.0](docs/JEFF_ADMIN_UI_DESIGN.md)：左側欄導覽、AI 板塊 A／B、AI 比較、推薦監控及商品／訂單／會員管理版面與決策紀錄。Admin layout and decisions.
- 線框圖不含示範數字；新增 v4 集合與欄位對照及資料需求 D1～D5，供資料庫對接。Field mapping replaces sample values.
- 僅文件，不修改程式、Schema 或憑證。Documentation only.

## 2026-10-05 — REN 選擇會員／購物流程 / REN auth-order ownership

- 仁千 REN 已選 B，對應 `feature/auth-order`；前台／RWD 改為待重新分配。REN now owns auth/order.
- 更新分工表、分支協作、首頁與 [REN 交接文件](docs/REN_AUTH_ORDER.md)。Access status is tracked separately from ownership.

## 2026-10-02 — 分工更正與資料庫測試 / Ownership and database checks

- 現行責任：SAM 資料庫／測試、JEFF AI／後台、REN 前台／RWD（10/6 再確認）；整合驗證待確認。See [ownership](docs/TEAM_OWNERSHIP.md).
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
