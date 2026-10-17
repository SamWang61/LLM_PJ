# VibeCart Cloud Run／Firebase 展示部署

目前部署方式分開閱讀：[Firebase Hosting／Cloud Run 判定與操作](FIREBASE_CLOUD_RUN_DEPLOYMENT.md)、[Render 準備與驗收](RENDER_DEPLOYMENT.md)。

2026-10-16 已在 [PR #21 整合來源](../docs/SAM_PR21_ACCEPTANCE_2026-10-16.md) 完成本機白名單 Docker build／boot、隔離交易測試與零流量 Cloud Run 唯讀預覽；Hosting 尚未發布此版。下方 10/12 配置與唯讀部署敘述保留歷史版本界線。

主責 SAM。先交付匿名商品瀏覽，再依 JEFF／REN 功能及 SAM 驗收接線完整流程。這份設定不匯入資料、不建立會員、不跑 migration；D4 仍須所有 consumer 的遠端隔離驗證通過才可 apply。

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
