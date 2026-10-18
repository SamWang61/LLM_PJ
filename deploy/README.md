# VibeCart Cloud Run／Firebase 展示部署

<!-- SAM REVIEWS PRODUCTION 20261019 -->
**2026/10/19 06:55 SAM商品評價／6＋4正式發布**：Cloud Run `vibecart-web-reviews-b038aaca`已100%，Firebase Hosting 06:48:42發布成功；正式網址Chrome不重載4.0／2筆→4.4／3筆、Atlas13／3讀回、六角色登入及清理驗證通過。275項本機測試0 skipped，同digest私有遠端4探針與高星6＋4排序通過；正式真實評價候選不足不補滿，測試商品不可推薦且已清除。[正式部署與驗收](../docs/SAM_REVIEWS_6PLUS4_PRODUCTION_2026-10-19.md)。下方較早狀態為各時點歷史；V5仍2／14，未代填真人簽收。

<!-- SAM PR95 PR96 REVIEW 20261019 BEGIN -->
**2026/10/19 06:30 SAM PR #95／#96覆核**：[同版測試與合併紀錄](../docs/SAM_PR95_PR96_MERGE_REVIEW_2026-10-19.md)。#95已合併main `8a29f5f`；275項真本機MongoDB測試0 skipped、完整56檔PR95私有0%預覽的四組探針與正式六角色登入均通過。正式仍登入增量576b474／100%，本輪未切正式流量；28集合／89索引／7 migration及關聯唯讀稽核通過。#96保留05:45歷史，舊修復憑證已由05:52固定雙角色規則接續，不回灌舊憑證。V5仍2/14；#96最終合併SHA／CI以GitHub紀錄為準。
<!-- SAM PR95 PR96 REVIEW 20261019 END -->

<!-- SAM PR93 MERGE 20261019 BEGIN -->
**2026/10/19 05:37 SAM PR #93 已合併**：[審查與主幹對帳](../docs/SAM_PR93_MERGE_REVIEW_2026-10-19.md)。PR HEAD `863e03e`，合併main `6fbaa0c`；46項安全與5項來源測試通過，main CI成功。既有4組同版遠端／畫面證據已重新核對，56個執行來源相同；正式19／私有base11仍各100%原版，新預覽各0%，本輪沒有重新部署或重寫Atlas。V5仍2/14，正式切換、實機與具名簽收待辦。
<!-- SAM PR93 MERGE 20261019 END -->

<!-- SAM REVIEWS PREVIEW 20261018 BEGIN -->
**2026/10/18 21:41 SAM商品評價／6＋4無流量預覽**：[同版遠端驗收](../docs/SAM_REVIEWS_6PLUS4_PREVIEW_2026-10-18.md)。固定main9a76b1d、56檔與GCS SHA一致；BGE／規則同digest各0%，最後4探針及真Atlas回滾／角色／交易通過。瀏覽器不重載4.0／2筆→4.4／3筆、DOM6＋4；fixture／索引／Job／暫時IAM清理。正式19／私有base11仍100%原版，Hosting未變，正式評價0、D4 synthetic1240不變。正式上線、效能SLO與具名簽收未完成；V5仍2/14。
<!-- SAM REVIEWS PREVIEW 20261018 END -->

2026/10/18較早main的0%預覽、同版BGE／Claude與隔離交易證據見[2026-10-18驗收](../docs/SAM_MAIN_PREVIEW_2026-10-18.md)，Key設定見[Claude版本1](CLAUDE_SECRET_SETUP.md)。該時點正式100%為`vibecart-web-00019-phf`；本次06:55正式發布見頁首，下方01:58狀態亦為歷史。

目前部署方式分開閱讀：[Firebase Hosting／Cloud Run 判定與操作](FIREBASE_CLOUD_RUN_DEPLOYMENT.md)、[Render 準備與驗收](RENDER_DEPLOYMENT.md)。

截至 2026-10-18 01:58，正式 `vibecart-web-00015-nlk` 已承接 100% 流量，Hosting rewrite 指向 `vibecart-web`。[部署讀回](../docs/SAM_RELEASE_2026-10-18.md)記錄來源 `1d2abf2`、映像 digest、Cloud Build、同映像 D4 隔離探針、Hosting 與公開路由；[D4 匯入](../docs/D4_IMPORT_ACCEPTANCE_2026-10-18.md)已完成指定批次。下列唯讀預覽步驟是新版本切換前的操作流程，不能代表目前正式服務仍在唯讀模式。

主責 SAM。正式修訂已開放結帳；同版登入／交易、真模型、D5 與最終畫面簽收仍依工作清單逐項驗收。這份部署設定不匯入資料、不建立會員、不跑 migration；新 consumer 或新映像上線後，須重新驗證 D4 synthetic 排除條件。

## 配置與目前邊界

- 專案 `vibecart-llmai`，Cloud Run `vibecart-web`，區域 `asia-east1`，Hosting site `vibecart-llmai`。
- 使用 Cloud Build／Artifact Registry；執行帳號 `vibecart-web@vibecart-llmai.iam.gserviceaccount.com` 只獲本服務兩個 secrets 的讀取權限。
- `MONGO_URI` 與穩定 `SECRET_KEY` 由 Secret Manager 注入，不寫入程式、映像或公開報告。資料庫連線沿用既有授權 URI；「唯讀」指應用層路由限制，本輪未修改 Atlas DB user 權限。
- `CLOUD_PREVIEW_READ_ONLY=true`：清除會員身分，禁止會員／後台／購物路由與所有寫入方法；介面僅提供商品瀏覽。`ENABLE_CHECKOUT`、模型推論均關閉。不要把此模式標成會員／AI／交易驗收完成。
- Flask 使用 `__session` cookie 與 Secure／HttpOnly／SameSite=Lax；動態頁面 `private, no-store`，避免 CDN 儲存會員頁面。
- `/health/live` 僅驗程序存活；`/health/ready` 才驗資料庫 ping 與現有 active v4 商品。錯誤回應不含連線 URI。兩者均不是全站验收。
- 最少 0／最多 1 instance、1 CPU、512Mi、concurrency 20。服務 startup 不 seed、不調庫存。公開瀏覽將對既有資料庫進行商品查詢。

## 可重現的建置與部署

前置：具權限的 Google Cloud／Firebase 帳號，Python 依賴、gcloud 與 Firebase CLI。10/12 本機缺 gcloud，實際建置／部署使用 REST API；下面是具 gcloud 的操作環境可用的等價步驟。不要把秘密當作 shell 參數傳入。

1. 在 repo 根目錄執行 `python scripts/prepare_cloud_source.py --output <repo外的暫存目錄>/vibecart-source.tar.gz`。這是白名單：網站 app、cloud_runtime、Dockerfile、雲端依賴，以及共用的 cart_service／sku_cart_service；不包含 MongoDB `.env`、匯出資料與測試帳號。
2. 把該 archive 解到獨立暫存目錄；以該目錄為 build context，不能直接把完整工作目錄送到 Cloud Build。
3. 用 `deploy/cloudbuild.yaml` 建置。呼叫者設定 `_IMAGE=asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web:<新的版本>`、build service account 與私有 logsBucket。本輪 build account 為 `278483818008-compute@developer.gserviceaccount.com`，只新增本專用 repository writer／build bucket objectAdmin。bucket `vibecart-llmai-sam-build-278483818008` 使用 uniform access 與 7 天物件 lifecycle，沒有 public ACL。
4. 建置包含容器內 `create_cloud_app()`＋`/health/live` smoke test，假 URI／假 session key 僅供 boot，不連 Atlas；這會攔截漏打包的共享模組。build SUCCESS 後取得 immutable image digest。
5. 在 Cloud Run 部署 digest，沿用 secret 的明確版本與 runtime account；使用 read-only=true、max-instances=1、min-instances=0。成功讀回 ready revision 後，才配置公開商品瀏覽的 invoker。
6. 驗 `/health/live`、`/health/ready`、首頁、商品明細、空搜尋；會員／後台／cart 及 POST 均須拒絕。記錄實際狀態碼與畫面。
7. 在 `deploy/firebase` 執行：

   ```powershell
   firebase deploy --only hosting --project vibecart-llmai --config firebase.json --non-interactive
   ```

   public 目錄只有 404 頁面；其他路徑 rewrite 至 Cloud Run。此命令應在後端可用且已驗後執行，不能用静態首頁掩蓋未可用後端。
8. 使用 Hosting URL 再驗相同路徑與手機／鍵盤操作；保存 release／revision／digest／PR 與測試證據。

本機故障注入：`python scripts/run_frontend_qa.py --env-file <私有.env路徑> --port 5093 --break-images`。它只在 HTML 回應替換 img src，不修改 Atlas 的商品圖片或文件。

## 後續功能開放

JEFF 先確認全部評分／歸因／推薦／排程 consumer 及 AI 契約；REN 先交登入／撤權／購物／事件接口。SAM 整合、建立少量私有測試帳號、驗角色與舊 session，再以新的已測 revision 開放功能；不要直接關掉 preview flag 冒充功能交付。

遠端 consumer 的 synthetic 排除、D4 apply／verify／重送、真模型與交易驗收各自列證據。沒有執行的 Scheduler 不可標為排程已驗。首次展示不等於最終簽收。

## 官方來源

- [Hosting 與 Cloud Run rewrite／區域](https://firebase.google.com/docs/hosting/cloud-run)
- [Hosting cookie 與 cache 行為](https://firebase.google.com/docs/hosting/manage-cache)
- [Cloud Run Secret Manager 配置](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
- [Cloud Run 保留路徑：避開 z 結尾](https://docs.cloud.google.com/run/docs/known-issues)
