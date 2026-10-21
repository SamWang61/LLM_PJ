# SAM 分頁圖示 404 修正｜2026-10-22

## 問題及修改

10/22 本輪重新讀回公開 `web.app` 與 `firebaseapp.com` 的 `/favicon.ico`，兩者均404；正式修訂為 `vibecart-web-perf-8741400-1021`。前次發布紀錄已列此缺檔，但未修復。既有首頁、推薦、登入與健康入口均200。

新增本站黃綠購物車SVG、前後台的`rel=icon`，以及明確的`GET /favicon.ico`。回應為`image/svg+xml`、一天快取並支援ETag／304，不需登入或讀資料庫。其他不存在的靜態路徑仍回404；不以整站404攔截器掩蓋缺檔。

## 本機驗證

用Flask client分別在legacy／v4模式驗證：GET 200、正確SVG MIME、一天快取、If-None-Match 304；未知靜態路徑404。過程將MongoClient設為立即拋錯以確認圖示沒有資料庫依賴，兩模式均通過。來源白名單／交付稽核7項passed。

## 發布界線與重現

[本次映像配方](../deploy/Dockerfile.favicon-20261022)固定沿用已驗正式完整映像digest `b62b7ff2…`，只覆蓋四個圖示／模板／路由檔，保留既有套件、離線BGE及啟動命令。打包前必須將本次Git runtime白名單與來源`8741400`比對，差異只能是配方列出的四檔且無刪除，否則停止並另行審查。由固定Git提交製作flat來源包，再以同提交的此配方取代包內Dockerfile，記錄原來源清冊、配方hash與成品包hash；不讀未追蹤檔或本機憑證。

先做斷網容器啟動、BGE／非root／圖示／健康檢查，再建立正式服務0%候選；核對來源、digest、原設定指紋／IAM、Hosting及候選公開端點後，才提升流量。實際建置、部署與線上驗證結果完成後補記；此版本文字不表示已部署。

不變更Atlas schema、D1～D4、會員或交易資料，也不替本人簽收。每日固定Drive備份的可逆ACL缺口仍獨立待辦，V5保持3/14。

English: Serve the missing favicon with an explicit public SVG route and declare it in both layouts. Verify cache validation without MongoDB access. The scoped image overlay preserves the pinned production runtime; build, deployment and human acceptance remain separate evidence.
