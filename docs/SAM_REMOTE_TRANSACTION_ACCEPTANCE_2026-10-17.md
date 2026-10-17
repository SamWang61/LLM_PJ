# SAM／REN 代理遠端交易驗收｜2026-10-17

**16:06 後續結果**：最小權限帳號、隔離 Atlas 交易、私有瀏覽器／HTTP 驗收及正式服務 100% 流量切換已完成；請以[最新正式部署與驗收紀錄](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)為現況。下文各段是操作當時的歷史快照，不應沿用其中「尚未合併／未寫入／未切流量」作現況。

本頁逐步記錄 [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21) 的獨立驗收環境。使用者已允許建立只限驗收的 Atlas 帳號、私有 Cloud Run 服務和少量測試資料；**截至本次紀錄尚未寫入 Atlas，也尚未通過遠端角色／交易驗收。** 正式網站、D1～D4、額外兩筆示範訂單與主站流量不改。

## 已建立與讀回

| 項目 | 2026-10-17 當次證據 |
|---|---|
| 同版建置 | PR #21 程式提交 `2251c88a250c1001942960230f691c2acea10803`；47/47 封裝檔與 Git blob 相同；本機 Docker OCI index digest `sha256:b79b972bf116359619219cdee03d750067e6fd80d177571ed8432d78d6c318ae`，推送 Artifact Registry 的同 tag digest 相同。 |
| 私有服務 | `asia-east1/vibecart-acceptance-pr21` 與專用服務身分已建立；修訂 `vibecart-acceptance-pr21-00001-657` 的 Cloud Run 管理端顯示 Ready、映像 amd64 manifest `sha256:2710f45b7c465ee5164ef1b29c4d6f9f8b3700bf582d5d3575b07f69c5934f62`、來源 SHA label 相同。服務 IAM 只列專用服務身分的 `roles/run.invoker`，無 `allUsers`；匿名 `/health/live` 為 403。 |
| 初始唯讀模式 | 服務目前使用無憑證的假 Atlas URI 與獨立 Secret Manager session 密鑰；`CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`。授權身分的 `/health/live` 200、`/health/ready` 503（預期尚無資料庫憑證）、`/auth/login` 403。此修訂只是私有服務與 IAM 啟動核對，不是可寫交易驗收。 |
| 密鑰權限 | 驗收專用 Mongo URI 與 session 密鑰容器已建立；兩者 IAM 只授予上述服務身分 `secretAccessor`。Mongo URI 密鑰**仍無版本**。操作者暫時獲得該服務身分的短期 token 核發權，驗收結束需撤銷。本文不記錄任何密鑰值。 |
| 主站隔離 | `vibecart-web-00007-m9k` 仍承接原服務 100% 正式流量；新驗收服務是不同名稱，未改 Firebase Hosting rewrite。 |

## 尚未滿足的遠端驗收閘門

Atlas 連接器建立資料庫帳號時要求額外操作確認，當次未獲該確認，故帳號**未建立**。不能把正式庫使用者或正式 Mongo URI 密鑰拿來頂替。取得獨立 `vibecart_acceptance_pr21` 的最小權限帳號後，才可寫入 Mongo URI 密鑰，改修訂為受限可寫模式並讀回 IAM、修訂、資料庫名及空集合。接著按[前置與清理清單](SAM_REMOTE_TRANSACTION_PREFLIGHT_2026-10-17.md)驗角色、跨裝置、SKU cart、checkout、事件與寫後讀回。正式 D4 consumer 閘門獨立存在，仍不得 apply；PR #21 維持草稿，不合併 main。

## 後續同版核對

REN 的 R08 重新登入修正、事件驗證，以及 D4 未部署 consumer 門檻已併入 PR #21。2026-10-17 本機整合提交 `afbc913d53ba086842f3e51f2d68451c1936e2f0` 已推送；GitHub 遠端 head SHA 相同，Repository validation 兩次均為 success，文件政策檢查為 298 檔、0 錯誤，D4 匯入門檻測試為 4 passed，Git LFS fsck 通過。先前以 MongoDB replica set 執行的網站完整測試為 183 passed、0 skipped，但該次測試所對應的提交早於 D4 門檻整合。

在前述時間點，私有服務仍是較早的 `2251c88a250c1001942960230f691c2acea10803`，不能用它宣稱最新 PR #21 的遠端交易驗收。當時 Atlas 連接器尚未建立驗收帳號，Docker Desktop daemon 亦未啟動；正式主站流量及資料保持不變。後續變化見下節。

## Docker 恢復後的最新預覽（2026-10-17）

使用者回報 Docker 已啟動；本輪讀回 Docker Engine `29.6.1`。以 PR #21 提交 `5da34e6f748c31fa9410082fdd943a86ef54297a` 封裝，47/47 個白名單檔案與 Git blob 位元組相同，tar SHA-256 為 `c0f9d1e621575a34d006f86515ef73adf2e60d95084835fc3146779965be5664`。Docker build 成功，映像 OCI index digest `sha256:f680bb4afc2401d2e4fe1c230c088341d5554f8e9e04abda58f4322371894815`；同 tag 已推送 Artifact Registry。使用無憑證假 URI 與本機專用測試密鑰進行唯讀容器 boot，`/health/live` 200、`/health/ready` 503（預期尚無資料庫）、`/auth/login` 403、`/admin/` 403；容器已停止。

以一次性 localhost MongoDB 8 replica set `rsSAMpr21final`，設定 `HEN_TEST_MONGO_URI=mongodb://127.0.0.1:27017/?replicaSet=rsSAMpr21final`，在網站目錄重跑完整測試，結果 **183 passed、0 skipped（42.42 秒）**。測後資料庫只剩 `admin`、`config`、`local`，容器已停止。這是本機真交易與回歸證據，並非 Atlas 或遠端角色簽收。

私有 Cloud Run 服務已改用同版映像，管理端讀回修訂 `vibecart-acceptance-pr21-00002-n5g` Ready、source SHA 標籤與上述提交相同。此獨立服務仍唯讀且使用假 URI：授權請求 `/health/live` 200、`/health/ready` 503、`/auth/login` 與 `/admin/` 均 403；匿名 `/health/live` 403。服務 IAM 的 `run.invoker` 僅授予驗收服務身分。正式 `vibecart-web-00007-m9k` 仍承接主站 100% 流量。

使用者回報 Atlas 驗收帳號與密鑰已建立，但本輪以兩個 Atlas 連接讀回專案 `6aa9bd20af3f21039447a5c0`，仍只有原 3 個資料庫帳號，未見 `sam_pr21_acceptance_20261017`；Google Secret Manager `vibecart-pr21-acceptance-mongo-uri` 亦讀回 **0 個版本**。已請使用者核對專案及最後儲存步驟，不將回報取代遠端讀回。驗收資料庫未連接，角色、交易、畫面與 D4 consumer 遠端隔離尚未通過；PR #21 仍維持草稿，不合併 main。

完成唯讀預覽核對後，已撤回操作者對驗收服務身分的臨時 `roles/iam.serviceAccountTokenCreator`，IAM 讀回此角色綁定為 0。待隔離帳號與密鑰確實可讀後，須再以授權測試身分恢復短期測試權限，完成驗收後再次撤回。

## 13:39 合併與正式服務零流量修訂（2026-10-17，台灣時間）

- 使用者明確要求合併、部署與遠端驗收。[PR #21](https://github.com/SamWang61/LLM_PJ/pull/21) head `f4fc3c7cf48dd358a855663063e5d2d19904e106` 的兩次 CI success；相對上述 `5da34e6` 受測程式僅有文件變更。另以一次性、無憑證 localhost MongoDB replica set 重跑該程式版本，完整網站測試 **183 passed／0 skipped**。PR 已合併，`main` merge SHA `2fd43557bac0148e02fa427163a9657a13c7ae23`，[同版 main CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39006863627) success。main 與 PR head 在 Cloud Run 封裝範圍內無程式差異。
- Cloud Run 正式服務新增標籤 `main-2fd4355` 的**零流量唯讀**修訂 `vibecart-web-00011-dx2`。管理端讀回 Ready、source SHA label `2fd43557bac0148e02fa427163a9657a13c7ae23`、amd64 image manifest `sha256:d933a5d8bf3f9264beac3bc9738e2bb84d11cf92e1b8ce097b0cd3000be40b91`；`CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`，Mongo URI／session key 仍是 Secret Manager 參照。舊 `vibecart-web-00007-m9k` 保持 **100%** 正式流量。標籤網址的 `/health/live`、`/health/ready` 回 200，`/auth/login`、`/admin/` 與登入 POST 回 403；這是預覽隔離證據，不是交易簽收。
- Atlas 專案 `6aa9bd20af3f21039447a5c0` 唯讀重查仍只有原 3 個資料庫使用者，沒有 `sam_pr21_acceptance_20261017`；`vibecart_acceptance_pr21` 尚不存在，正式 `vibecart_ai` 的 D1～D3 訂單 3,000、額外 demo 訂單 2、D4 指定事件 0。Secret Manager `vibecart-pr21-acceptance-mongo-uri` 仍為 **0 個版本**。嘗試以最小權限 `readWrite@vibecart_acceptance_pr21` 建立專用 Atlas 使用者，連接器回覆「User did not confirm」，操作**未執行**；已請使用者完成該連接器確認。不得改用正式庫帳號或 Atlas admin 憑證代替。
- **仍未完成**：獨立驗收 DB 的少量資料及寫後讀回、私有服務可寫修訂、角色／跨裝置／SKU cart／checkout／事件遠端交易、測後撤權與清理、正式流量切換及具名簽收。待專用帳號與 secret 可讀後，按上方前置清單繼續；D4 全部 consumer 遠端隔離前不得 apply，D1～D3 不重匯。

## 15:10 Atlas 帳號與密鑰核對（2026-10-17，台灣時間）

Atlas 專案已出現 `sam_pr21_acceptance_20261017`，Secret Manager `vibecart-pr21-acceptance-mongo-uri` 版本 1 為 ENABLED。僅在程序記憶體解析密鑰，未顯示或記錄 URI／密碼；核對其 scheme 為 `mongodb+srv`、主機為既定 `vibecart-ai-free.odqe25w.mongodb.net`、使用者為上述帳號、路徑為 `/vibecart_acceptance_pr21`。**關鍵阻礙：帳號角色實際為 `atlasAdmin@admin`，資源範圍 All Resources。URI 指向獨立資料庫並不能限制此帳號寫正式庫。** 已在 Atlas 管理頁請使用者將其改為只限 `readWrite@vibecart_acceptance_pr21`、限定 `vibecart-ai-free` 叢集；在唯讀重查角色正確之前，不注入私有服務、不建立測試資料、不對 Atlas 寫入，也不切換正式流量。13:39 的「帳號／secret 版本不存在」為當時快照。
