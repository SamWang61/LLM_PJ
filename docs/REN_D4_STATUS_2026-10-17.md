# REN 代班與 D4 狀態｜2026-10-17 14:17（台灣時間）

**後續結果：2026-10-18 00:41** 已完成 [D4 同版隔離與正式合成批次驗收](D4_IMPORT_ACCEPTANCE_2026-10-18.md)，1,240 筆、verify 缺漏 0、重送新增 0；探針清理／撤權及 D1～D3 保留均留證。本頁其餘內容為 10/17 14:17 快照，不再代表目前 D4 匯入狀態；REN 11:10 到期交回仍須另行盤點。

本頁依 [專案工作清單](../專題進度/專案工作清單_2026-10-17.md) 記錄最新可核對進度。SAM 於 10/17 11:10～10/18 11:10 暫代 REN，提交使用實際 GitHub 身分，不冒用 REN 帳號。本頁為當時快照；部署、Atlas 與 PR 狀態在執行下一步前須重新讀回。

## GitHub 與測試

- [PR #25](https://github.com/SamWang61/LLM_PJ/pull/25)、[PR #28](https://github.com/SamWang61/LLM_PJ/pull/28) 及 [PR #29](https://github.com/SamWang61/LLM_PJ/pull/29) 已整合進 [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21)；PR #21 於 13:36 合併 `main`，merge SHA `2fd43557bac0148e02fa427163a9657a13c7ae23`。本次讀回的 `main` head 為文件提交 `d97942c`。上述三項整合提交均可在 `main` 祖先鏈找到。
- 一次性 localhost MongoDB replica set 的網站完整測試為 **183 passed／0 skipped**；D4 匯入定向測試 **27 passed**。這些是本機證據，不是 Atlas、遠端角色或交易驗收。合併與 CI 依[遠端驗收紀錄](SAM_REMOTE_TRANSACTION_ACCEPTANCE_2026-10-17.md)查核。

## 14:17 雲端唯讀讀回

| 項目 | 讀回結果 | 邊界 |
|---|---|---|
| 正式 Cloud Run `vibecart-web` | 最新 Ready 修訂 `00011-dx2` 的來源 label 是 `2fd43557bac0148e02fa427163a9657a13c7ae23`，設定為唯讀、checkout 關閉；流量仍由舊 `00007-m9k` 承接 **100%**。 | 已合併程式並有零流量預覽，不代表正式新版本上線或交易簽收。 |
| 私有 `vibecart-acceptance-pr21` | 最新 Ready `00002-n5g`，來源 label `5da34e6f748c31fa9410082fdd943a86ef54297a`；假 Mongo URI、唯讀、checkout 關閉。 | 尚不能驗證 Atlas 寫入、角色、會員交易或事件 consumer。 |
| Atlas 專用帳號 | 專案 `6aa9bd20af3f21039447a5c0` 仍只讀回原有 3 個帳號，沒有 `vibecart_acceptance_pr21` 專用帳號。 | 不得借用正式資料庫帳號或 Atlas 管理員憑證。 |
| 驗收 Mongo URI secret | `vibecart-pr21-acceptance-mongo-uri` 已建立，但 **0 個 ENABLED 版本**。 | 無可用驗收連線。 |

## D4 匯入判定與下一步

**D4 尚未達到可匯入條件，不得 apply。** [consumer 盤點](D4_DEPLOYED_CONSUMER_INVENTORY_2026-10-17.md)可把未部署的計分排程與正式歸因列為帶雲端清單證據的 `not_deployed`；已部署的後台監控與前台推薦仍需在同版遠端環境驗證合成事件於排序／limit 前排除、正常事件可見，並核對輸出及清理。正式 `00007` 的來源與行為也尚未核實，不能把零流量唯讀修訂的結果當成正式流量驗收。

建立只限 `vibecart_acceptance_pr21` 的最小權限 Atlas 帳號時，連接器自動核准審查回覆「User did not confirm」，**操作未執行**。需取得對該具體帳號與權限的明確確認，再建立 secret 版本、驗證專用 DB 權限，部署私有可寫入同版服務，執行少量可清理資料的角色／交易／事件及 consumer 對照。完成後再核對正式流量版本、重新盤點部署資產，才可產生 D4 匯入證據並考慮交易 dry-run、apply、讀回與冪等重送。保留 D1～D3，不重匯。

## 15:58 後續讀回（台灣時間）

上段缺少帳號／secret 是 **14:17 的歷史快照**。Atlas 專案後來出現 `sam_pr21_acceptance_20261017`，角色僅 `readWrite@vibecart_acceptance_pr21`，範圍僅 `vibecart-ai-free`；Secret Manager `vibecart-pr21-acceptance-mongo-uri` 已有 1 個啟用版本。僅在程序記憶體核對 URI 的主機、帳號與資料庫路徑，沒有印出或保存密碼。使用該帳號對驗收庫 `ping` 成功，讀取正式 `vibecart_ai.users` 被 Atlas 拒絕（錯誤碼 8000），證明本次測試連線無正式庫讀取權限。

私有 Cloud Run `vibecart-acceptance-pr21-00003-8hr` 已引用上述 secret、設定 `CLOUD_ACCEPTANCE_MODE=true`、`CLOUD_ACCEPTANCE_DB=vibecart_acceptance_pr21`、唯讀關閉及 demo checkout 開啟；授權 `/health/live` 與 `/health/ready` 均為 200，匿名 `/health/live` 為 403。驗收庫已有少量測試商品及部分集合，其他工作正進行遠端交易驗收；本次只讀取集合與筆數，未增刪其資料。正式服務仍由 `vibecart-web-00007-m9k` 承接 100% 流量，新 main 修訂仍為零流量唯讀。D4 指定 batch 的正式庫 `behavior_events` 唯讀計數仍是 **0**。

本次再查 Cloud Run 全區服務僅正式與私有驗收兩項；`asia-east1` Jobs、Pub/Sub 訂閱／主題為空，Scheduler／Functions API 停用。這只更新了部分部署範圍；正式流量 consumer 的同版 synthetic／正常事件對照、輸出讀回和完整資產清單仍未完成。**D4 閘門維持關閉，不得 apply。**

## 16:05 資料層 preflight

[正式庫唯讀 preflight 紀錄](REN_D4_PREFLIGHT_2026-10-17.md)已確認 D4 validator、索引及 D1～D3 來源參照可用，以最多 100 筆來源訂單規劃 **1,240 筆**事件；`existing=0`、`missing=1240`、`committed=false`、`inserted=0`。事後 Atlas 唯讀計數 D4 仍為 0，原批訂單／明細仍為 3,000／8,969。這只解除資料層前置疑點，**沒有**解除遠端 consumer 隔離閘門；正式 apply 仍禁止。

## 18:44 接續核對與下一關（台灣時間）

[PR #38 正式部署／隔離交易紀錄](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)已合併 `main`，本地 `origin/main` 為 `9afd5fb372c24346b1f98232792f2740a1e1f73c`。該紀錄於 16:06 讀回正式 Cloud Run `vibecart-web-00012-85f` 承接 **100%** 流量、映像 digest `sha256:d933a5d8bf3f9264beac3bc9738e2bb84d11cf92e1b8ce097b0cd3000be40b91`，來源為 PR #21 merge SHA `2fd43557bac0148e02fa427163a9657a13c7ae23`；私有驗收 `vibecart-acceptance-pr21-00003-8hr` 使用同一映像，隔離 Atlas 的遠端登入、角色、demo checkout、重送及庫存交易已留下讀回證據。上文 13:39 的 `00007` 正式流量與 14:17 的帳號缺失都是**歷史快照**。本次僅在 Google Cloud 控制台再次看見兩項 Cloud Run 服務可用，沒有重新讀回正式 revision 流量分配，故以 #38 的 16:06 證據標明時間，不把它寫成 18:44 即時流量驗證。

這個部署進展讓正式與私有服務可比對相同映像，但 **D4 仍不可匯入**。缺的是同版私有服務對管理員推薦監控與會員前台推薦的實際 HTTP 對照：先讀正常事件，再加入超過監控 1,000 筆與前台 50 筆 limit 的合成事件，確認正常事件仍可見且 synthetic 不影響兩端輸出，最後只清除本次探針資料並讀回 0。私有驗收庫在 #38 留有一件 active 商品，其他測試商品已停用；對照推薦排序時須在隔離庫增建第二件完整、可清理的 active 商品／SKU，不能暫時改動其他人的夾具。先前供遠端交易測試使用的 `serviceAccountTokenCreator` 已在 #38 完成後撤銷；本機 Firebase CLI 當前沒有登入帳號，故本次未取得私有服務 ID token，也**未寫入任何測試事件或帳號**。不以本機模擬或 200 健康檢查冒充這項遠端驗收。

下一次取得短期授權後，先重查服務 revision／digest、IAM 與全部部署 consumer；於獨立驗收庫完成上述正常／合成對照與清理，再核對正式服務同版行為及最新資產清單，產出帶時間、SHA、HTTP 輸出、資料讀回及 GitHub 文件位置的正式隔離證據。只有所有已部署 consumer 通過，才填入 D4 閘門欄位，依序執行交易 dry-run、apply、讀回與重送冪等；不重匯 D1～D3。
