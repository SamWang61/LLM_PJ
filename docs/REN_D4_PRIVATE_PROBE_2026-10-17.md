# REN／SAM D4 私有 consumer 對照探針｜2026-10-17

狀態：**10/18 同版私有 consumer 對照、清理、正式 preflight 與回滾 dry-run 已通過；D4 apply 尚未執行。** SAM 在 REN 24 小時代班期間接續此項。以下 10/17 阻礙紀錄按當時時間解讀，D1～D3 不重匯。

## 2026-10-18 00:08～00:23（Asia/Taipei）實測

403 原因是驗收身分缺少 `iam.serviceAccounts.getOpenIdToken`。本次依使用者修正授權，僅在該 service account 上加入 `roles/iam.serviceAccountOpenIdTokenCreator`，限定目前操作帳號、20 分鐘到期；沒有建立憑證金鑰或擴大正式資料庫權限。第一輪 15 秒等待仍回 403，角色已撤銷；改依 [Google IAM 傳播說明](https://docs.cloud.google.com/iam/docs/access-change-propagation)作最多 8 分鐘的有界重試，第 9 次取得 ID token。完成後及獨立讀回均確認臨時 binding 為 0。

| 項目 | 驗收結果與證據 |
|---|---|
| 同版部署 | 正式 `vibecart-web-00013-ds5` 100%；私有更新為 `vibecart-acceptance-pr21-00004-9qr`，保留原隔離 env、runtime 身分及私有 invoker。兩者 source SHA=`80513a951d0dff67fd47a153a45918522b5ffbb5`，digest=`sha256:57c8fd038d7c231a4e417471a66b9c7996c296efd2d7b1ff70302c46a45f0fab`。[更新讀回](inventory/sam-d4-private-deployment-20261018.json)。 |
| 私有資料權限 | Atlas 管理端及探針的 `connectionStatus` 均確認只具 `readWrite@vibecart_acceptance_pr21`，限 `vibecart-ai-free`。 |
| 正常／synthetic 對照 | probe `ren-d4-41a7e6927cb6cc96`：管理員基線 13，正常事件後 14，加入 1,001 筆較新 synthetic 後仍 14；會員前台先因正常事件改變，synthetic 後與正常結果完全相同。[遠端報告](inventory/sam-d4-consumer-probe-20261018.json)。 |
| 清理 | 刪除本次 1,002 事件、2 session、2 帳號、2 SKU、2 商品；五集合剩餘均 0。另一 Atlas 連接器獨立複查亦為 0；session count 介面曾 internal error，改用 `$count` 聚合確認全集合為空。[獨立讀回](inventory/sam-d4-independent-readback-20261018.json)。 |
| IAM | `finally` 撤銷本次 binding；[獨立管理端讀回](inventory/sam-d4-iam-readback-20261018.json)顯示 service account binding 總數 0。撤銷 policy 不會立刻使已核發 token 失效；token 僅在本次程序記憶體使用，程序已結束。 |
| 全區盤點 | Cloud Run 列出 43 區，其中 42 區可讀、`me-central2` 明確回 `LOCATION_POLICY_VIOLATED`；可讀區只有上述兩個服務，Job 0，Pub/Sub topic／subscription 0，Scheduler／Functions／Workflows／Tasks API 未啟用。受限區沒有冒記為成功讀取。 |
| 正式 D4 | 正確 v4 環境下 [preflight](inventory/sam-d4-formal-preflight-20261018.json)與 [dry-run](inventory/sam-d4-formal-dry-run-20261018.json)均通過，規劃 1,240 事件，dataset SHA-256=`da6998425bc80746902b407336489f43bfcc77bc7f092d9ece5e3b02d1d0edea`；交易已 abort，committed=false、inserted=0。[測後獨立讀回](inventory/sam-d4-post-dry-run-readback-20261018.json)正式 batch 仍 0，D1～D3 訂單 3,000、額外 demo 2 保留。 |

報告位元組 SHA-256：遠端 probe `c9717b917146fe1f1fe5fcddc234a4c0aca6da56169e6a547ed0ac56286c8d98`；preflight `b18187c0442194965af14de95fcd02c6d6020c73bbd0d7d414b2d968b13e6954`；dry-run `f7cce0cb72b8ab9186b1fce0317298180995b0c591245a87d95d4c20add18279`。實際執行探針的[來源雜湊](inventory/sam-d4-probe-source-20261018.json)另存。舊 website `.env` 指向另一目標時，guard 在連線前拒絕；正式命令使用受控 v4 環境檔，未修改原檔。

目前完成的是同版隔離驗收、盤點與回滾預演；下一步將不可變 GitHub 證據填入正式 `consumer_checks`、重查部署範圍及受限區說明，再依閘門進行 apply／verify／重送。**本次未執行 D4 apply，也未將此結果當作真模型、付款或全站最終簽收。**

## 目標與資料範圍

本探針只允許連至 `vibecart-ai-free.odqe25w.mongodb.net/vibecart_acceptance_pr21`，帳號須為只對該庫具 `readWrite` 的 `sam_pr21_acceptance_20261017`；HTTP 目標只允許 `vibecart-acceptance-pr21-*.a.run.app` 私有服務。腳本在程序記憶體接收短期 ID token 與 Mongo URI，不接受正式 `vibecart_ai` URI，也不將憑證寫入檔案、命令列或輸出。

隔離庫現有一件 active 商品但 SKU 庫存已為 0，因此探針會**新增兩件自己標記的可販售商品／SKU**，沿用既有驗收分類 ID，不修改其他夾具；另建一位測試會員、一位測試管理員。先讀管理員推薦監控和會員前台推薦基線，再加一筆正常 `PRODUCT_VIEW`，確認管理員計數加一、前台推薦改變。之後加 **1,001 筆較新的 synthetic `PRODUCT_VIEW`** 到另一商品，超過監控的 1,000 筆和前台的 50 筆 limit；兩端結果都必須維持正常事件之後的值，證明查詢在排序／limit 前排除合成事件。任何錯誤都嘗試依唯一 `probe_id` 與新建 ID 刪除本次事件、session、帳號、SKU、商品，並讀回殘留數。清理未證實為 0 時必須標為 `cleanup_failed`，先處理隔離庫殘留，不得繼續 D4。

## 執行前置與命令

1. 重查正式與私有 Cloud Run revision、映像 digest、私有 invoker、全部部署 consumer／Job／Scheduler 清單。需確認私有服務與正式站承接的 consumer 為同版；先前 [PR #38](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)只記錄 16:06 的部署快照。
2. 預設 `node scripts/run_remote_d4_consumer_probe.cjs` 只讀盤點，驗證實際承接 100% 流量的 revision，而非 `latestReadyRevision`；要求正式／私有 pinned digest 一致、私有 invoker 和隔離庫設定正確。
3. 已獲准隔離驗收時，以 `node scripts/run_remote_d4_consumer_probe.cjs --run-isolated` 執行。程式在單一 service account 加入上述限時窄角色，只在記憶體讀 Secret Manager `vibecart-pr21-acceptance-mongo-uri` 版本 1，再以 stdin 交給 Python；無論探針結果如何均嘗試撤權並讀回。可設定 `REN_PYTHON` 指向已安裝網站 `requirements-test.txt` 的 Python；不要把 URI／token 放入環境變數或命令列參數。
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

10/18 新增 Node guard 測試 **3 passed**、Python 範圍／權限／清理測試 **5 passed**；已加入 GitHub CI。測試拒絕正式 URI、非驗收服務、可變映像、廣權限及公開 invoker，並檢查零流量預覽不可代替正式流量、清理失敗不可標成功。上述離線測試與前節實際遠端對照分別留證。
