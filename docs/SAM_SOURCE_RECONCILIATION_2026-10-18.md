# 正式映像與主線來源核對｜2026-10-18

2026-10-18（Asia/Taipei）核對 `main` `7a94f07a25630699ce4834d03c508f9f323dc92e` 與 00:12 正式發布的來源 `80513a951d0dff67fd47a153a45918522b5ffbb5`。後者的 Cloud Run revision 為 `vibecart-web-00013-ds5`，映像 digest、Cloud Build 與當時的 100% 流量讀回見 [發布紀錄](SAM_RELEASE_2026-10-18.md)。

以 [47 檔部署封裝 manifest](inventory/sam-release-archive-20261018.json) 的 `sourcePath` 逐一執行 `git show HEAD:<path>`，對 Git blob 位元組計算 SHA-256，再與 manifest 記錄比較：**47/47 相同、0 差異**。這只證明主線目前的部署白名單檔案與已發布映像的來源相同；`main` SHA 本身較新，沒有據此重新建置、部署或變更流量。PR #52 的 REN 命名變更主要涉及文件與測試名稱；該分支完整網站測試在隔離 localhost replica set 為 186 passed／0 skipped，PR CI 已成功，合併 SHA 即上列 `7a94f07`。

另外從此乾淨工作樹執行 `python scripts/prepare_cloud_source.py --output <倉庫外暫存檔>`，得到 47 檔；解開後以 Docker 29.6.1 從獨立 context 建置，使用假 URI／假 session key 執行容器內 `create_cloud_app()` 及 `/health/live`，回傳 `container-boot-ok`。本機映像 digest 為 `sha256:17626ad81d61b95aa5c7d5771ffe163e4e44d78d80d166bf1fa0dcebc6db5e65`。這是本機 build／boot，不是 Cloud Build 或正式修訂；tar.gz 的位元雜湊會受封裝時間中繼資料影響，檔案內容以逐檔 manifest 比對為準。

本次公開 Hosting 即時 GET `/`、`/health/live`、`/health/ready` 均回 200。HTTP 200 不顯示 Cloud Run 管理端 revision／digest；本次沒有重讀 Cloud Run 控制平面，也沒有登入、下單、模型、D5 或 Atlas 寫入測試。新修訂一旦部署，須重新核對部署白名單、revision、digest、角色與交易，並重跑 D4 consumer 隔離條件。
