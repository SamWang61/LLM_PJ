# REN／SAM D4 私有 consumer 對照探針｜2026-10-17

最新狀態（2026-10-18）：**私有前台／管理監控對照已通過，探針資料已清理、臨時 IAM 已撤銷；D4 正式匯入仍待最終版本與部署盤點核對。** SAM 在 REN 24 小時代班期間接續此項。正式批次不可當探針，D1～D3 不重匯。

## 10/18 00:05～00:10 遠端結果（Asia/Taipei）

使用者明確允許臨時授予 `cashsam@gmail.com` 對驗收 service account 的 `roles/iam.serviceAccountTokenCreator`、最長 30 分鐘並於測後撤銷。本次設定 25 分鐘到期條件（00:30:36），00:05:36 開始，00:07:23 完成並撤銷；最後讀回直接 token creator 授權 **0**。憑證僅在記憶體傳遞。

- 私有 revision `vibecart-acceptance-pr21-00003-8hr`，映像 `sha256:d933a5d8bf3f9264beac3bc9738e2bb84d11cf92e1b8ce097b0cd3000be40b91`；正式 100% 流量 revision `vibecart-web-00012-85f` 使用同一映像。
- `probe_id=ren-d4-52ff2f677fe5bf8b`；管理監控基線 **13**，一筆正常事件後 **14**，再加入 **1,001** 筆較新 synthetic 事件後仍 **14**。會員前台推薦在正常事件後改變、目標商品居首；synthetic 加入後結果不變。
- 刪除本次事件 **1,002**、session／users／SKU／products 各 **2**，各集合讀回殘留 **0**、`verified=true`。隨後 Atlas 連接器獨立查詢上述 probe marker 及隔離庫 session，均為 **0**；商品查詢首次連接器內部錯誤，重試後確認 0。
- 完整無憑證輸出見 [探針與撤權報告](inventory/D4_PRIVATE_PROBE_2026-10-18.json)；[部署盤點](inventory/D4_CONSUMER_INVENTORY_2026-10-18.json) 與 [43 區 Jobs 盤點](inventory/D4_CLOUD_JOBS_2026-10-18.json) 同步留存。

00:10 盤點發現新零流量候選 `vibecart-web-00013-ds5`（來源 `80513a951d0dff67fd47a153a45918522b5ffbb5`、映像 `sha256:57c8fd038d7c231a4e417471a66b9c7996c296efd2d7b1ff70302c46a45f0fab`），當時正式 100% 仍為已受測的 `00012`。本次通過證據只對上述 `d933…` 映像負責；若正式版切換，需對最終版本重核。Cloud Run v1 全專案 services 清單只有上述兩個服務，Job／worker pool 清單皆空，三者均沒有 unreachable 或後續分頁。43 區 Jobs 查詢為 42 區空、`me-central2` 因 `LOCATION_POLICY_VIOLATED` 回 403；v2 全區服務查詢另列 5 個 unreachable location，均保留在診斷報告，並以 v1 全專案成功清單補足盤點。Scheduler／Functions／Workflows／Cloud Tasks API 未啟用，Pub/Sub topic／subscription 空。**本輪沒有執行正式 D4 dry-run／apply。**

**00:13:54 更新**：[正式流量重查](inventory/D4_PRODUCTION_CHANGE_2026-10-18.json) 已讀回 `00013-ds5` 承接 100%，映像為上述 `57c8…`；00:10 的零流量狀態已被取代。D4 尚欠新正式映像的同版隔離對照及最終證據整理，不能沿用 `00012` 的 image digest 聲稱新版本已通過。另一個 SAM 對話同時接續 PR #47 的驗收工作，本對話已先保存完成的結果並請求跨對話協調授權，避免重複部署及正式匯入。

## 目標與資料範圍

本探針只允許連至 `vibecart-ai-free.odqe25w.mongodb.net/vibecart_acceptance_pr21`，帳號須為只對該庫具 `readWrite` 的 `sam_pr21_acceptance_20261017`；HTTP 目標只允許 `vibecart-acceptance-pr21-*.a.run.app` 私有服務。腳本在程序記憶體接收短期 ID token 與 Mongo URI，不接受正式 `vibecart_ai` URI，也不將憑證寫入檔案、命令列或輸出。

隔離庫現有一件 active 商品但 SKU 庫存已為 0，因此探針會**新增兩件自己標記的可販售商品／SKU**，沿用既有驗收分類 ID，不修改其他夾具；另建一位測試會員、一位測試管理員。先讀管理員推薦監控和會員前台推薦基線，再加一筆正常 `PRODUCT_VIEW`，確認管理員計數加一、前台推薦改變。之後加 **1,001 筆較新的 synthetic `PRODUCT_VIEW`** 到另一商品，超過監控的 1,000 筆和前台的 50 筆 limit；兩端結果都必須維持正常事件之後的值，證明查詢在排序／limit 前排除合成事件。任何錯誤都嘗試依唯一 `probe_id` 與新建 ID 刪除本次事件、session、帳號、SKU、商品，並讀回殘留數。清理未證實為 0 時必須標為 `cleanup_failed`，先處理隔離庫殘留，不得繼續 D4。

## 執行前置與命令

1. 重查正式與私有 Cloud Run revision、映像 digest、私有 invoker、全部部署 consumer／Job／Scheduler 清單。需確認私有服務與正式站承接的 consumer 為同版；先前 [PR #38](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)只記錄 16:06 的部署快照。
2. 本機 Firebase CLI 使用 `cashsam@gmail.com` 登入。10/17 的 ID token API 曾回 `HTTP 403`，於資料庫連線前停止；10/18 經使用者明確授權加入限時 IAM 後已成功執行，並於測後立即撤銷，詳見上方結果。未來再次執行時須核對當次授權範圍與撤銷紀錄。
3. 在乾淨工作樹執行 `node scripts/run_remote_d4_consumer_probe.cjs`。它只在記憶體讀 Secret Manager `vibecart-pr21-acceptance-mongo-uri` 版本 1、取得私有服務 ID token，再以 stdin 將憑證交給 `scripts/remote_d4_consumer_probe.py`。可設定 `REN_PYTHON` 指向已安裝 `requests`、`beautifulsoup4`、`pymongo`、`werkzeug` 的 Python；不要把 URI／token 放入環境變數或命令列參數。
4. 保存 JSON 輸出中的 revision、image、基線／正常／synthetic 計數、商品 ID、逐集合清理筆數與 `*_remaining=0`、`verified=true`；再以 Atlas 連接器唯讀複查 `probe_id`。報告沒有密碼、token、URI 或測試帳號密碼。

這支探針只檢查已部署的前台推薦與管理員監控；評分排程、正式歸因及其他 consumer 仍須用[部署清單](D4_DEPLOYED_CONSUMER_INVENTORY_2026-10-17.md)逐項重查。兩端通過也不直接授權 D4 apply；需先完成正式流量同版核對、全 consumer 隔離證據、正式 preflight、交易 dry-run，之後才可 apply、讀回與重送冪等驗證。

## 19:09 雲端唯讀重查（Asia/Taipei）

使用 Firebase CLI 現有登入讀取 Google Cloud Run、Service Usage、Pub/Sub、Run IAM 與 Firebase Hosting 管理 API，沒有修改雲端設定或 Atlas 資料：

| 項目 | 讀回 |
|---|---|
| 正式服務 | `vibecart-web-00012-85f` 承接 100% 流量，來源 label `2fd43557bac0148e02fa427163a9657a13c7ae23`。 |
| 私有驗收服務 | `vibecart-acceptance-pr21-00003-8hr` 承接其服務 100% 流量；其 invoker 只有 `vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com`。 |
| 映像 | 兩個 revision 都是 `sha256:d933a5d8bf3f9264beac3bc9738e2bb84d11cf92e1b8ce097b0cd3000be40b91`。 |
| 部署清單 | 全專案 Cloud Run 服務只有上述兩個；`asia-east1` Job 0，Pub/Sub topic／subscription 0；Cloud Scheduler、Cloud Functions、Workflows、Cloud Tasks API 未啟用。 |
| Hosting | live release `1791982222797000`，`**` rewrite 指向 `asia-east1/vibecart-web`。 |

此時可確認正式與隔離服務同映像，且部署清單沒有新增計分／歸因 worker；仍欠私有 HTTP 的正常／synthetic 對照結果。授權問題處理並完成對照前，D4 閘門保持關閉。

## 本次靜態檢查

`remote_d4_consumer_probe.py` 通過 `py_compile`，`run_remote_d4_consumer_probe.cjs` 通過 `node --check`；以錯誤的非驗收 URI 執行時在連線前退出，回報 `RuntimeError`，沒有資料庫操作。這些不是遠端 consumer 通過證據。
