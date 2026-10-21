# SAM 分頁圖示 404 修正｜2026-10-22

## 問題及修改

10/22 本輪重新讀回公開 `web.app` 與 `firebaseapp.com` 的 `/favicon.ico`，兩者均404；正式修訂為 `vibecart-web-perf-8741400-1021`。前次發布紀錄已列此缺檔，但未修復。既有首頁、推薦、登入與健康入口均200。

新增本站黃綠購物車SVG、前後台的`rel=icon`，以及明確的`GET /favicon.ico`。回應為`image/svg+xml`並支援ETag／304，不需登入；匿名圖示讀取不存取資料庫。其他不存在的靜態路徑仍回404；不以整站404攔截器掩蓋缺檔。一般Flask factory的max_age為86400秒，但Cloud factory維持既有`private, no-store`；本輪不放寬雲端回應政策，也不宣稱正式圖示可快取一天。

## 本機驗證

用Flask client分別在legacy／v4模式驗證：GET 200、正確SVG MIME、一天快取、If-None-Match 304；未知靜態路徑404。過程將MongoClient設為立即拋錯以確認圖示沒有資料庫依賴，兩模式均通過。來源白名單／交付稽核7項passed。網站本機離線回歸399 passed／35 skipped（69.69秒）；跳過案例需額外真交易或模型前置，不能稱為全部真交易測試通過。GitHub CI另跑一次性MongoDB交易檢查，以其實際結果為準。

## 發布界線與重現

[本次映像配方](../deploy/Dockerfile.favicon-20261022)固定沿用已驗正式完整映像digest `b62b7ff2…`，只覆蓋四個圖示／模板／路由檔，保留既有套件、離線BGE及啟動命令。打包前必須將本次Git runtime白名單與來源`8741400`比對，差異只能是配方列出的四檔且無刪除，否則停止並另行審查。由固定Git提交製作flat來源包，再以同提交的此配方取代包內Dockerfile，記錄原來源清冊、配方hash與成品包hash；不讀未追蹤檔或本機憑證。

先做斷網容器啟動、BGE／非root／圖示／健康檢查，再建立正式服務0%候選；核對來源、digest、原設定指紋／IAM、Hosting及候選公開端點後，才提升流量。以下為實際完成結果，不由本機測試推定上線。

## GitHub、容器及正式發布

時間為台北2026/10/22；[完整去敏證據](inventory/SAM_FAVICON_RELEASE_2026-10-22.json)。

| 階段 | 實際結果 |
| --- | --- |
| GitHub | [PR #168](https://github.com/SamWang61/LLM_PJ/pull/168) HEAD `0256312`兩個offline CI成功後，合併main `5e38cfeee3d51580dc230039b2903ef2715ccea6`。保留同時完成的#167效能發布證據；清冊衝突以工具重建。 |
| 固定來源 | build來源`1af3959`，與合併後main的76個白名單來源逐檔相等；相對原正式來源`8741400`僅四檔變更、無刪除。封裝中的Dockerfile明列改用本次Git配方，不冒稱與網站原Dockerfile相同。 |
| 建置 | Cloud Build `77099734-2919-4f53-802c-e9e89421d224`於00:12:10 SUCCESS；新映像`sha256:d40711d619f20001357977c4cfdf96ebe63a96abf976c95cca0636e4d42e09aa`。斷網容器核對74個執行檔hash、UID 10001、離線BGE 512維、圖示200／304及health/live通過。Dockerfile與.dockerignore是建置輸入，不列執行檔hash。 |
| 候選 | `vibecart-web-icon-1af3959-1022`先0%；00:16讀回Ready／Active／ContainerHealthy及7條路由符合預期，圖示MIME與Git bytes相同、條件GET 304。原效能版仍100%；執行設定指紋、IAM及Hosting release不變。 |
| 正式切換 | 00:17:37提出流量更新；00:18:34讀回新修訂唯一100%，原`vibecart-web-perf-8741400-1021`保留0%及既有tag。不是重新發布Hosting。 |
| 公開入口 | 00:19:56兩個Firebase網域各六條GET均200，含/favicon.ico，圖示bytes與Git相同、登入頁宣告icon。一般Flask與直連Cloud Run的條件請求304；Firebase條件請求另觀察到200或304，200時仍核對相同完整SVG，不宣稱所有邊緣入口必回304。 |
| 日誌 | 精確以00:17:37.131～00:20:37.477查新修訂，39筆／1頁完整、無剩餘token；5xx／MongoDB／其他ERROR與404均0。HTTP 405為刻意GET登出安全探針。這是短觀察窗，不保證未來零錯誤。 |

首輪公開探針把所有條件GET都硬性要求304而停止，沒有從該次宣稱整批完成；修正驗證範圍後重新跑完上述12條公開GET及兩個條件請求。首次日誌查詢經PowerShell日期字串轉換，錯用較早起點；已保留該次範圍差異並改由Node直接傳原ISO時間重跑，斷言period_start相等，以上只採正確窗口。這兩項是本輪驗證器修正，不列為網站缺陷修復。

若需回退，先重新讀回原效能修訂、既有設定／VPC及資料契約，再將`vibecart-web-perf-8741400-1021`改回100%並核公開入口；本輪未執行回退。沒有刪除歷史修訂或其他人的tag。

不變更Atlas schema、D1～D4、會員或交易資料，也不替本人簽收。每日固定Drive備份的可逆ACL缺口仍獨立待辦，V5保持3/14。

English: Serve the missing favicon with an explicit public SVG route and declare it in both layouts. Verify cache validation without MongoDB access. The scoped image overlay preserves the pinned production runtime; build, deployment and human acceptance remain separate evidence.
