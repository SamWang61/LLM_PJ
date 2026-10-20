# SAM GitHub 自動建置修復｜2026-10-19

## 問題及修復

PR #115 已合併 main `ac45394`，GitHub Actions [39230941471](https://github.com/SamWang61/LLM_PJ/actions/runs/39230941471)成功，但外部 Cloud Build check 失敗。兩套檢查分開記錄，不把 Actions 成功稱為全部 CI 通過。

原 trigger 在 repo 根目錄使用 `Dockerfile`；根目錄沒有該檔，網站 Dockerfile 需使用現行部署白名單產生的 monorepo context。原自動部署亦缺零流量保護。現在沿用原 trigger、main 事件及 service account，改用受版本控管的 [建置設定](../deploy/cloudbuild-github-preview.json)；完整操作與觸發範圍見[部署說明](../deploy/GITHUB_PREVIEW_BUILD.md)。

流程先依固定 COMMIT_SHA 封裝 Git 已提交的 56 個部署檔，再建置映像、斷網執行 `/health/live`、推映像，最後以 `--no-traffic --tag=github-preview` 建立私有候選。清除歷史臨時 command／args，保持正常映像啟動方式；不啟用正式 AI、不變更正式 Atlas、不切換任何原100%服務流量。

## 逐輪驗證

1. 原 build `4d3d7372-26b0-4cd2-a5df-9619eec9845d` 的 Docker 步驟失敗，保留原紀錄；未取得原始錯誤文字，不臆填完整錯誤。
2. 來源 `51a616f` 的 build `81a8fb22-9c79-4c88-9ea7-5a3a21f888a7` 五步 SUCCESS，離線容器啟動通過。新 revision 沒有流量或 tag 而直接退休，故只證明映像匯入，不能當雲端容器啟動驗收。
3. 補固定私有 tag 後，以 `4137b39` 重跑 build `96d30223-b6d8-471f-862a-8dbc44c94b89`，17:51:33 SUCCESS；17:51:58回讀候選 `vibecart-acceptance-pr21-00035-nex` 的 ContainerHealthy、Active、Ready 均成功，digest `eb8793b4…`、正常command／args及固定VPC。候選0%、原兩個revision各100%，私有服務無公開invoker、候選匿名403；正式五入口各200。[完整去敏讀回與日誌摘要](inventory/SAM_CLOUD_BUILD_PREVIEW_REPAIR_2026-10-19.json)。

本機來源白名單／交付稽核5項 passed；PR #116提交證據後文件政策798檔／625 UTF-8文字／0錯誤，diff檢查通過。PR #116固定HEAD `5bcebb6519a9456f7465aa227ecedb67fe2f591b` 的兩項offline成功後，17:55合併main `5d4cc2ea4a597ab322ee1c3f7153b313caabb7aa`。

## main 自動觸發實證

main合併事件自動產生build `b3a59ff3-59b1-43f0-9a5a-7e44e68aa76a`，17:57:26完成五步SUCCESS；這輪不是手動補跑。17:58:02讀回新私有候選 `vibecart-acceptance-pr21-00036-hed`，source `5d4cc2e`、digest `f721cacb…`，Ready／Active／ContainerHealthy成功，`github-preview` 0%，原正式及私有294c各100%。正常command／args及固定VPC保持；匿名候選403、公開五入口200。[去敏main讀回](inventory/SAM_CLOUD_BUILD_MAIN_READBACK_2026-10-19.json)同時記錄[main Actions](https://github.com/SamWang61/LLM_PJ/actions/runs/39233679421)和外部Cloud Build check均success。

依貢獻指南刷新[檔案清冊](inventory/files.csv)及[統計](inventory/summary.json)，範圍是本工作樹可讀的專案文件／附件，排除inventory自身、依賴、秘密與快取；不宣稱是原機所有檔案的備份。本輪另修正清冊工具：跳過worktree `.git`指標／symlink，Firebase Admin SDK檔僅列機密metadata、不讀內容。既有歷史清冊仍可由Git回查；沒有刪除任何附件。

## 驗收界線

原正式 `vibecart-web-n06-294c-1019` 與私有 `vibecart-acceptance-pr21-n06-294c-1019` 的100%預設流量保持。新候選使用獨立 digest、0%預設流量；這次沒有在新候選重做會員／交易／AI或本人操作驗收，不能把原已驗版本的結果套到新候選。正式 Hosting 發布版本保持。

17:07:34～17:51:27 的正式修訂版日誌完整25筆／1頁，HTTP 5xx及各資料庫錯誤類別均0；五個公開入口均200。此為觀察區間，不保證未來或未測路徑零錯誤。三人本人接收、完整實機／異機證據、Drive 可逆 ACL 與其他待辦依[本輪追蹤](SAM_ONLINE_FOLLOWUP_2026-10-19.md)，V5仍2/14。

English: The GitHub Actions job passed while the separate legacy Cloud Build check failed. The repaired trigger builds only committed allowlisted source, performs an offline boot check, and stages a private tagged candidate with zero default traffic. Existing production traffic remains pinned. Runtime startup, source/digest, checks, and human acceptance are recorded separately.
