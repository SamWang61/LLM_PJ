# D4 實際部署 consumer 盤點｜2026-10-17

查核時間：2026-10-17 11:38～11:40（Asia/Taipei）。SAM 代理 REN／JEFF 的 D4 前置盤點，以具雲端讀取權限的 Firebase CLI OAuth 登入，直接讀取 Google Cloud Run、Service Usage、Pub/Sub 與 Firebase Hosting 管理 API。查詢只讀；沒有讀出 Secret Manager 值、變更部署、建立測試帳號或寫入 Atlas。專案：`vibecart-llmai`（project number `278483818008`）。本頁是當時快照，D4 apply 前必須重查。

## 管理端讀回

| 範圍與查詢 | 結果 | D4 含義 |
|---|---|---|
| Cloud Run v2 `projects/vibecart-llmai/locations/-/services`，HTTP 200 | 只有 `asia-east1/vibecart-web`、`asia-east1/vibecart-acceptance-pr21` 兩個服務。 | 沒有獨立計分或歸因服務；仍須檢查網站服務內嵌路由。 |
| `vibecart-web` 服務／revisions／IAM，HTTP 200 | Hosting 指向該服務。正式流量 **100%** 為 `vibecart-web-00007-m9k`，image digest `sha256:5f148596fa8570fba21608d0e029b3fa6ed59f4c805d13f512deafcbd1998148`，`CLOUD_PREVIEW_READ_ONLY=false`、`ENABLE_CHECKOUT=true`；公開 invoker 為 `allUsers`。`00008`、`00009`、`00010` 是 0% 標籤預覽；`00010` 的 source label 為 `5f73fe6bd6f5d0496e61a593a31831bd38f0c378`，但唯讀、不可驗會員／寫入。 | 實際生產 consumer 仍在較舊 `00007`。該 revision 沒有可讀的完整來源 SHA 標籤，尚未完成同版 synthetic 對照驗證。 |
| `vibecart-acceptance-pr21` 服務／IAM，HTTP 200 | 私有 invoker 僅為 service account；`00001-657` source label `2251c88a250c1001942960230f691c2acea10803`，當時 `CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`。 | 獨立驗收服務已建立，但此快照時仍不可寫入，且版本早於 PR #25／#28 整合。不能當 consumer 通過證據。 |
| Cloud Run v1 `/apis/run.googleapis.com/v1/namespaces/vibecart-llmai/jobs`，HTTP 200 | `items=[]`。另以 v2 `asia-east1/jobs` 查得 0。 | 沒有實際部署的 Cloud Run 計分／歸因 Job。 |
| Service Usage `projects/278483818008/services?filter=state:ENABLED`，HTTP 200 | 45 個啟用 API；`run`、`firebasehosting`、`pubsub` 啟用，`cloudscheduler`、`cloudfunctions`、`workflows`、`cloudtasks` 未啟用。Scheduler、Functions 的管理 API 查詢各回 403 `SERVICE_DISABLED`。 | 沒有可執行的 Scheduler／Cloud Functions／Workflows／Cloud Tasks consumer；若未來啟用必須重新盤點。 |
| Pub/Sub `projects/vibecart-llmai/subscriptions` 與 `/topics`，HTTP 200 | 都是空清單。 | 沒有 Pub/Sub 驅動的排程／歸因訂閱。 |
| Firebase Hosting `sites/vibecart-llmai/releases?pageSize=1` 與版本配置，HTTP 200 | live release `1791982222797000`，2026-10-14T12:50:22.797Z；rewrite `**` → Cloud Run `asia-east1/vibecart-web`。 | 正式網站流量進入上述 `00007`，不是 PR #21／#25／#28 唯讀預覽。 |

以 PR #21 最新整合來源 `a909a1b2c80ea4f83a68a1925807091309aef8fe` 掃描執行程式，`user_preference_scores`、`recommendation_logs` 只出現在 schema／測試，沒有已交付的正式寫入 worker；執行中的事件讀取在 `app/services/dashboard.py`、`app/store_v4.py` 及 legacy `app/store.py`。這是原始碼盤點，不能代替 `00007` 容器來源與雲端行為證明。

## 閘門結論與下一步

計分排程與正式歸因目前可列為 **not_deployed**，但仍須把本頁的專案、範圍、檔案 SHA-256、查核時間及 GitHub URL 加入 `behavior_import.py` 的證據欄位，並在 apply 前重查。管理員監控與前台推薦屬**已部署**，不得標成 not_deployed。現行正式 revision 來源 SHA 未核實，也沒有隔離、可寫入的同版 synthetic／正常事件對照讀回，因此 **D4 尚未達到可匯入條件**。

SAM 下一步：固定最新整合 SHA，於獨立驗收資料庫及私有同版服務核對管理員監控和前台推薦在 sort／limit 前排除 synthetic 且正常事件可見；讀回 revision、映像 digest、事件／輸出及清理。再核對正式流量版本的同一行為或部署已驗版本、重查所有服務／Job／API／Hosting，才能填入正式隔離證據並進行 D4 preflight、交易 dry-run、apply、讀回及重送冪等驗證。不得用 D4 正式批次充當探針，也不重匯 D1～D3。
