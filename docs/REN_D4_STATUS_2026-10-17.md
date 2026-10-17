# REN 代班與 D4 狀態｜2026-10-17 14:17（台灣時間）

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
