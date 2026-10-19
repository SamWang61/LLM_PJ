# Render 部署準備與驗收｜2026-10-16

本文件規劃把現有 Flask／Gunicorn 容器部署為 Render Web Service；**尚未建立 Render 服務、憑證、Atlas 存取規則或網域切換**。主責：SAM，資料庫與功能主責依[同版驗收紀錄](../docs/SAM_PR21_ACCEPTANCE_2026-10-16.md)配合。Render 是 Cloud Run 的另一個執行入口，不會自動更新 Firebase Hosting。

## 建議路徑：使用已驗證的不可變映像

PR #21 的 47 檔白名單來源已建置為 `linux/amd64` 映像。Render 支援從 Google Artifact Registry 拉取 private image，並可指定 digest。這條路徑能沿用已核對的容器內容，避免 Render 直接以整個含文件／本機資料的 repository 作 Docker build context。10/16 預覽映像為：

```text
asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web@sha256:ae3dbfbd9863e1264dfb840714101f8d80be0d8a0b44bf8119ef9c91c0f18783
```

這是 OCI index digest；其中 linux/amd64 manifest 為 `sha256:f1c437e7e3dda072de508631edf350ca6baeb586925df5cbc1d21ad11e7c0d53`。正式操作前須重新確認 registry 仍保留該 digest。Render image-backed 服務每次部署／重排程都需要能重新拉取映像，且不會因 tag 更新自動部署。[Render 官方映像部署要求](https://render.com/docs/deploying-an-image)。

## 建立服務前的準備

| 項目 | 應完成的準備與驗收點 |
|---|---|
| 帳戶與成本 | 決定 Render workspace、服務名稱、地區、實際方案與預算；先查該方案的資源與預覽限制，不以 Cloud Run 的 512 MiB／1 CPU 當作 Render 已配置。 |
| 映像讀取 | 為 Render 建立**專用、最小權限**的 Google Artifact Registry reader 身分（`roles/artifactregistry.reader`，只限所需儲存庫）；在 Render 的 private registry credential 設定，核對能拉取指定 digest。不要把 registry 憑證、service account key 或 deploy hook 寫進 Git／文件。憑證型態及輪替方式先由管理員確認。 |
| Atlas 網路 | 先從**該 Render 服務**取得實際 outbound CIDR／專用 IP，與 Atlas 專案的 IP access list 比對後以最小範圍配置；不要為了測試直接開放 `0.0.0.0/0`。再以 `/health/ready` 與資料讀回驗證連通。Render 與 Cloud Run 出口不同，Cloud Run 成功不代表 Render 可連。 |
| 資料庫身分 | 為預覽建立範圍受限的 Atlas 帳號與獨立連線字串；現有 `cloud_runtime.py` 只接受 `vibecart-ai-free.odqe25w.mongodb.net`，若更換 cluster 必須先審查程式。正式交易所需權限、資料隔離與備份另核對，避免預覽服務寫入正式資料。 |
| 執行期環境 | 在 Render Environment 設 `MONGO_URI`、穩定且長度至少 32 的 `SECRET_KEY`，預覽設 `CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`。此 Dockerfile 的 Gunicorn 已監聽 `0.0.0.0:${PORT:-8080}`；保留 Render 注入的 `PORT`。不要把 `.env` 上傳到 Git，也不要在 Docker build 使用秘密 `ARG`。 |
| 安全與入口 | Web Service 會取得可公開存取的 `onrender.com` 網址；預覽路由的讀取／寫入限制要在上線前測。既有 Firebase Hosting rewrite 只指向 Cloud Run，不會自動指向 Render；展示網域、TLS、DNS 與回退須另定案。 |
| 版本與自動發布 | 首次先以固定 digest 手動部署，保存 Git SHA、OCI digest、Render deploy ID、設定版本與時間。Image-backed 服務沒有 Git push 自動發布；若改用 Git-backed，先解決下述 build context 與自動部署閘門。 |

[Render Web Service 與 PORT](https://render.com/docs/web-services)；[環境變數與秘密](https://render.com/docs/configure-environment-variables)；[Render outbound IP](https://render.com/docs/outbound-ip-addresses)；[Atlas IP access list](https://www.mongodb.com/docs/atlas/security/ip-access-list/)。

## Render Dashboard 操作順序

1. 選擇 **New → Web Service → Existing Image**，輸入上方完整 digest；新增只讀 registry credential，等 Render 確認可拉取後再 Connect。確認實際可用的方案、地區與費用。
2. 設定執行期環境變數與秘密。這些值由有權限的人在 Render 私有設定中填入，不從 Cloud Run 讀出秘密明文，也不隨 PR 提交。預覽維持唯讀；不要先啟用 checkout、會員與後台。
3. 設 HTTP health check path 為 `/health/ready`，因它會檢查 Atlas ping 與 active v4 商品。只有 `live` 通過而 `ready` 失敗時，先檢查 Atlas 網路／資料身分，不把它當作部署成功。[Render health check 規則](https://render.com/docs/health-checks)。
4. 手動部署後讀回 deploy 狀態、image digest、日誌與設定。測 `GET /health/live`、`/health/ready`、首頁、商品明細／搜尋，以及登入、後台、cart、checkout、POST 寫入在唯讀模式均被拒絕；檢查 `private, no-store` 與瀏覽器手機／鍵盤流程。
5. 對照 Atlas 商品／SKU 價格庫存及事件／訂單副作用，再由 REN／JEFF／SAM 完成各自主責的角色、交易、AI 與所有 consumer 驗收。D4 不得在未證明遠端 synthetic 隔離前匯入；D1～D3 不重匯。
6. 只有在 Render 版本、權限、資料與回退都驗收後才討論正式網域切換。保留 Cloud Run／Hosting 原入口及映像 digest，先制定 DNS 回退和 session cookie／domain 變更測試。

## 若要改用 GitHub 自動建置

10/20更新：[根目錄Dockerfile與嚴格context](ROOT_DOCKERFILE_2026-10-20.md)已補；下段是原flat封裝限制。Render尚未因此完成連線、秘密配置或部署驗收，不沿用Cloud Build私有候選結果宣稱Render成功。

目前 Dockerfile 位於 `MuscleCore分析資料/website/Dockerfile`，它的 `COPY app` 與 `COPY VibeCart_AI/services` 以**白名單解壓目錄**為 build context；共享服務的來源實際位於 repo 根目錄 `VibeCart_AI/services`。因此直接把網站子目錄設為 Render root directory 會漏掉共享模組，直接把整個 repo 當 Docker context 則可能納入不應上傳的資料。切換 Git-backed 之前，先另交 Render 專用 Dockerfile／嚴格 `.dockerignore` 或經 CI 建立白名單建置來源，驗 47 檔一致、secret 排除、容器 boot 與 CI；再連接指定 Git branch，將 auto-deploy 設為 Off 或 After CI Checks Pass 並確認 preview 不沿用正式 DB 秘密。[Render Docker](https://render.com/docs/docker)；[Render 部署與 CI](https://render.com/docs/deploys)；[預覽服務環境變數](https://render.com/docs/service-previews)。

本文件是可執行的準備與驗收清單，並不宣稱 Render 已部署或已取得 Atlas 新出口授權。
