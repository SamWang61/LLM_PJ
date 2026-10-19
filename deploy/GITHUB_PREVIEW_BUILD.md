# GitHub 自動建置與零流量私有候選 / GitHub preview build

## 用途與範圍

設定：[cloudbuild-github-preview.json](cloudbuild-github-preview.json)。既有Cloud Build trigger `d0b39103-7508-451d-b3e6-6c251f82855d`（vibecart-llmai／global）沿用原GitHub main事件與原service account，改讀此檔；不重建trigger或改IAM。

- 只接受私有 `vibecart-acceptance-pr21` 目標；Prepare階段先檢查目標服務代號。
- 用本次COMMIT_SHA及既有 `scripts/prepare_cloud_source.py` 選取Git已提交部署檔，排除未追蹤內容與秘密，再解出獨立Docker context。
- 容器依既有網站Dockerfile建置，INSTALL_AI=false；目前正式AI開關關閉，本流程不新增模型啟用。
- 容器在 `--network=none`、無憑證URI與一次性測試secret下執行health/live，失敗即停止；不連正式Atlas。
- 映像名稱使用固定小寫私有服務路徑，避免GitHub大寫repo名稱造成Docker命名問題。
- 部署階段僅建立零流量私有候選，明確 `--no-traffic --tag=github-preview`，清除舊command／args以使用映像預設，保留既有env／secret／VPC。固定tag只提供仍受私有IAM保護的候選入口，服務預設入口原revision維持100%。**不自動提升候選流量，不更動公開vibecart-web或Hosting。**
- 必須再由SAM核候選Ready、來源、digest及相應測試，才可另行決定提升。建置成功不是人員或全站簽收。

## 觸發檔案

雲端trigger的includedFiles為：網站app目錄、Dockerfile、.dockerignore、requirements-cloud*.txt、cloud_runtime.py、VibeCart_AI/services、prepare_cloud_source.py與本JSON。純文件或截圖變更不啟動建置。trigger讀取main中的JSON，因此修改本檔也會建立新候選。

修改雲端trigger前先保存完整原設定於本機私有位置，重新比對GitHub來源、目標服務、原build及service account；不同就停止。更新後讀回filename、8個includedFiles與service account。原回復設定不得直接拿來部署：舊版沒有白名單context與零流量保護，應先設disabled=true並重新審查。

## 失敗來源與驗證

10/19 main `ac45394` 的GitHub Actions [CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39230941471)成功，但外部Cloud Build `4d3d7372-26b0-4cd2-a5df-9619eec9845d` 的Docker步驟失敗。原設定在repo根目錄執行 `docker build . -f Dockerfile`，根目錄沒有Dockerfile，且沒有現行白名單封裝。修復驗證的來源／build／candidate／流量及結果另記專項報告，不抹去舊失敗。

首輪修復build `81a8fb22-9c79-4c88-9ea7-5a3a21f888a7`五步SUCCESS且流量保持，但沒有tag的新revision直接退休，不能將服務Ready或映像匯入成功視為候選已實際啟動。故補固定私有tag，後續核對新revision的ContainerHealthy與Ready、原100%流量及IAM；原首輪只記離線容器啟動和零流量匯入成功。

[trigger更新API](https://docs.cloud.google.com/build/docs/api/reference/rest/v1/projects.triggers/patch)允許更新既有設定；[Cloud Run參考](https://docs.cloud.google.com/sdk/gcloud/reference/run/services/update)說明零流量選項；[容器命令設定](https://docs.cloud.google.com/run/docs/configuring/services/containers)說明空command／args回復映像預設。本輪legacy部分欄位patch曾回400；完整讀回後只調整列明欄位，再以完整mutable設定更新成功並逐項讀回。未因重試更改IAM。

English: Build committed allowlisted monorepo source, perform an offline boot check, and stage only a zero-traffic private candidate. The existing active production and private revisions retain their traffic. Source/config changes trigger builds; documentation-only changes do not. Human acceptance and promotion remain separate.
