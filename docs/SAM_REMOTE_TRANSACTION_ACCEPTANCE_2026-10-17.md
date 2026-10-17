# SAM／REN 代理遠端交易驗收｜2026-10-17

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
