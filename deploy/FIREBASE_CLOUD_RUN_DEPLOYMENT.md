# Firebase Hosting／Cloud Run 部署判定與操作｜2026-10-16

本文件只說明 `vibecart-llmai` 的現行部署方式；[PR #21 同版驗證](../docs/SAM_PR21_ACCEPTANCE_2026-10-16.md)記錄實測證據。主責：SAM。部署、資料讀回與最終簽收分開判定。

## 現況與「需要重新部署 Firebase 嗎？」

- `deploy/firebase/firebase.json` 的 `**` rewrite 指向 `asia-east1` 的 Cloud Run 服務 `vibecart-web`，沒有 `pinTag`。Hosting 不是此 Flask 程式的建置平台。
- PR #21 的不可變映像已在 Cloud Run 建立 `vibecart-web-00008-5bw`，標記 `pr21-preview`，一般流量 **0%**；`vibecart-web-00007-m9k` 仍為 **100%**。預覽網址：<https://pr21-preview---vibecart-web-m44ncgz5ta-de.a.run.app>。這是 10/16 的讀回快照，操作前重新核對。
- **現在無須重發 Firebase Hosting。** 只重發目前的 Hosting 設定，仍會轉送至 Cloud Run 服務的正式流量分配，不會把零流量預覽變成正式驗收。
- 若日後要由 `vibecart-llmai.web.app` 提供 PR #21，須先完成審查、角色／交易、資料與畫面驗收，再有意識地調整 Cloud Run 正式流量並讀回；若 Hosting 的靜態檔、rewrite、header、網域或 `pinTag` 配置也改變，才另部署 Hosting 並核對 release。不要以 Hosting HTTP 200 代替同版 backend 驗收。
- 若選 Render 做獨立入口，Firebase Hosting 不需要跟著重發；是否切換展示網域應在 Render 驗收後另決定，見 [Render 準備文件](RENDER_DEPLOYMENT.md)。

[Firebase 官方 rewrite 說明](https://firebase.google.com/docs/hosting/cloud-run)；[Hosting `pinTag` 行為](https://firebase.google.com/docs/hosting/full-config#how_pintag_works_within_the_run_block)。

## 可重現的 Cloud Run 發布流程

1. 從待審查的完整 Git SHA 建立乾淨工作樹，核對 `docs/CURRENT_CONTEXT.md`、PR、CI 與現有 Cloud Run ready revision／流量。原 `C:\LLM\LLM_PJ` 有未提交內容，不用它直接建置。
2. 在 repo 根目錄執行 `python scripts/prepare_cloud_source.py --output <repo 外暫存目錄>/source.tar.gz`；確認白名單檔案（10/18 為 52 個，含 AI 映像用的 `requirements-cloud-ai.txt`）、沒有 `.env`／資料匯出／測試帳號，逐檔比對 Git 提交位元組並保存 SHA-256。解壓至隔離 build context。
3. 使用 `MuscleCore分析資料/website/Dockerfile` 建置 `linux/amd64` 映像並以假 URI／假 session key 做本機 boot、`/health/live` 與唯讀拒絕測試。Dockerfile 已用 Gunicorn 監聽 `${PORT:-8080}`，不在啟動時匯入資料或執行 migration。
4. 推送至專案 Artifact Registry，讀回不可變 OCI digest 及 amd64 子 manifest；修訂版本若顯示子 manifest digest，應與 index 內對應項目一致。秘密僅用 Secret Manager 引用，不進入映像、命令參數或 Git。
5. 建立預覽修訂時指定映像 digest、`CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`，保留既有 secret 引用；關閉「立即提供這個修訂版本」。讀回舊 revision 100%／新 revision 0%，需要遠端 HTTP 驗證時才加零流量 tag。
6. 對標記網址驗 `/health/live`、`/health/ready`、商品列表與明細、搜尋、`Cache-Control`、匿名會員／後台／cart／checkout 拒絕及 POST 寫入拒絕。再以瀏覽器驗桌面、手機及鍵盤；若要宣稱資料與角色正確，另做授權的 Atlas 讀回、交易／撤權與具名驗收。
7. 只有當正式流量切換獲得完整驗收，才調整 Cloud Run traffic，讀回 revision／image／比例與正常服務網址。變更 Hosting 配置時，在 `deploy/firebase` 執行 `firebase deploy --only hosting --project vibecart-llmai --config firebase.json --non-interactive`，並讀回 release、rewrite 與 Hosting 網址。部署前後都保留回退所需的舊 revision／release 識別。

`/health/live` 只證明程序存活；`/health/ready` 證明當下資料庫 ping 與 active 商品可讀，仍不等於交易、AI 或全部 consumer 驗收。D4 正式匯入須先證明每個遠端 consumer 的 synthetic 隔離；D1～D3 不重匯。

## 相關來源

- [專案既有 Cloud Run／Hosting 細節與歷史配置](README.md)
- [Firebase Hosting 部署與預覽頻道](https://firebase.google.com/docs/hosting/deploying)
- [Cloud Run 修訂流量與標記](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)
