# REN R08：SAM 代理驗證紀錄｜2026-10-17

本紀錄由 **SAM 代理 REN（24 小時）**執行，依據 [REN 工作異常報告 PR #27](https://github.com/SamWang61/LLM_PJ/pull/27) 的 2026-10-17 11:10～2026-10-18 11:10（Asia/Taipei）期間。Git／GitHub 實際操作者為 `SamWang61`；REN 保留原模組責任。本頁的檢查對象是 [REN R08 PR #25](https://github.com/SamWang61/LLM_PJ/pull/25) 程式提交 `ac74b4f49853c6a92e1dd26bfe5bf430fba1154d`，文件提交不改變受測程式。

## 本次同版結果

2026-10-17，在乾淨的 PR #25 工作樹，以一次性、無正式憑證的 localhost MongoDB 8 replica set `rsREN20261017` 執行完整網站測試：**179 passed、0 skipped（31.57s）**。其中包含三項需要真 MongoDB transaction 的測試；本結果取代此 PR 先前的 176 passed／3 skipped 本機紀錄。這只證明此程式版的隔離本機測試，尚非雲端、Atlas、跨角色人工或付款驗收。

可重現命令（於 `MuscleCore分析資料/website` 執行；Python 使用已安裝專案依賴的虛擬環境）：

```powershell
docker run --rm -d --name ren-r08-rs-20261017 -p 127.0.0.1:27017:27017 mongo:8 --replSet rsREN20261017 --bind_ip_all
docker exec ren-r08-rs-20261017 mongosh --quiet --eval 'rs.initiate({_id:"rsREN20261017",members:[{_id:0,host:"127.0.0.1:27017"}]})'
$env:REN_TEST_MONGO_URI = 'mongodb://127.0.0.1:27017/?replicaSet=rsREN20261017'
python -m pytest tests -q -p no:cacheprovider
Remove-Item Env:REN_TEST_MONGO_URI
docker stop ren-r08-rs-20261017
```

本次測後 `db.getMongo().getDBNames()` 僅有 `admin`、`config`、`local`；已停止 `--rm` 容器。命令中的測試 URI 只指向本機，不含 Atlas 或專案私人設定。重跑時須另用空閒本機埠，並在測後清理。

## REN 範圍後續驗收順序

| 清單項目 | 同版待做事項 | 前置與可保存證據 |
|---|---|---|
| #07 會員／多裝置／撤權 | 在獲授權的同版遠端環境，用少量私有測試帳號重現註冊、錯密碼、兩裝置並存、同瀏覽器重新登入後舊 cookie 失效、單裝置登出、停用與降權。 | SAM 提供測試環境及帳號；JEFF 接入後台停用／降權的全裝置撤權交易。保存 revision／digest、請求結果、資料讀回及桌面／手機畫面；測後撤權。 |
| #08 SKU cart／demo checkout | 驗商品／SKU／庫存、cart revision 409、同 `operation_id` 去重、checkout 重送不重扣、訂單明細與庫存讀回、rollback 及最後庫存並發。 | 先將 PR #25 修正納入整合最終版，並確認有可寫的隔離環境。記錄 request／response 識別碼、前後庫存與交易結果。現行 checkout 是 demo，不代表付款商扣款。 |
| #10 四事件觸發 | 核對 SEARCH、PRODUCT_VIEW、ADD_TO_CART、PURCHASE 的事件欄位及 demo／synthetic 標記。 | REN 觸發端由 SAM 代驗；JEFF 提供所有實際推薦、評分、歸因及排程 consumer 清單。SAM 逐一核對部署版在 sort／limit 前的排除及正常事件對照，未完成前 D4 不 apply。 |
| S03～S05 素材 | 以最終同版桌面與手機流程擷取商品／搜尋、會員登入、購物車與 demo checkout 畫面，標明示範資料及未實現付款。 | 每張保留檔名、時間、最終 SHA、URL、revision／digest、測試帳號類型與驗收人。不能用較舊唯讀預覽或單張 HTTP 200 代替流程證據。 |

PR #25 以草稿 PR #21 為 base；上述本機測試當時沒有合併 `main`、部署、寫入 Atlas 或重匯 D1～D3；後續唯讀預覽部署另記於下節。正式遠端驗收須先定最終整合 SHA，再以同版環境逐項取證。到 2026-10-18 11:10 代理期滿，SAM 應列出已交／未交 SHA、遠端證據及阻礙交回 REN；沒有恢復資料時，REN 軟體異常仍標為待確認。

## Firebase／Cloud Run 唯讀預覽（2026-10-17 11:32 Asia/Taipei）

- PR #25 的來源提交 `5f73fe6bd6f5d0496e61a593a31831bd38f0c378` 以 Git 提交物件原始位元組建立 47 檔 Docker context，推送到 Artifact Registry。映像 index digest 為 `sha256:1fc2a3e01380cdb67a9117ed1db2e04d315e369533ba86e28f409749376dca47`。
- Cloud Run `vibecart-web` 新 revision `vibecart-web-00010-q8l` 已 Ready，標籤 `pr25-5f73fe6`，流量 **0%**；正式流量仍由 `vibecart-web-00007-m9k` 承接 100%。預覽網址：<https://pr25-5f73fe6---vibecart-web-m44ncgz5ta-de.a.run.app/>。預覽環境設定 `CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`。
- 預覽版 `/health/live`、`/health/ready`、首頁、無結果搜尋與商品詳情均回應 200；瀏覽器實測商品頁與共用頁尾三位成員的 `mailto:` 連結。登入、管理、購物車與 checkout 請求回應 403，符合唯讀預覽設定。這些結果不代表會員／訂單、Atlas 寫入、行動版或付款驗收。
- Firebase Hosting 預覽 channel：<https://vibecart-llmai--pr25-5f73fe6-g2aj380d.web.app/>（到期時間 2026-10-18 03:31 UTC）。其未固定版號的 rewrite 目前指向正式流量版本；首頁及登入頁回應 200，未顯示此 PR 的新頁尾。Firebase 拒絕先在 channel 固定新版，原因是 live rewrite 尚未固定；為避免將唯讀版固定到正式入口，本次未變更 live Hosting 或正式 Cloud Run 流量。
- 上述為預覽部署與匿名瀏覽驗證；PR #21／#25 仍是草稿。正式上線須先完成整合、可寫環境的交易／權限驗收，並重新核對 Cloud Run revision、映像 digest 及 Hosting rewrite。

## 10/17 晚間接續：S03 與登入返回路徑

- 上節 11:32 的 PR 與正式流量資訊為當時快照；[PR #38 正式部署紀錄](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)已記載 PR #21 合併及 `vibecart-web-00012-85f` 在 16:04 承接正式 100% 流量，且私有同版服務完成隔離交易讀回。此處不把該紀錄延伸成真付款或全站簽收。
- SAM 暫代 REN 於正式 Hosting 實拍商品頁並唯讀對帳一件 active 商品／SKU：`CF-1210303000104`／`CF-SKU-1210303000104`，畫面與 Atlas 都是 NT$79.00、庫存 95。原始 JPEG、PNG 和取證限制見 [S03 證據](../簡報文件/screenshots/S03-product-evidence.md)；[PR #43](https://github.com/SamWang61/LLM_PJ/pull/43) 已通過文件與離線測試 CI 並合併。這是單件商品的 S03 部分證據，仍待最終 revision 再確認、手機畫面及簽認。
- 同一正式網站的匿名 `/cart` 正確導至 `/auth/login?next=/cart`，但登入頁標題顯示舊品牌 `MuscleCore`，而既有登入函式成功後固定返回首頁，使原購物車導向失效。本次修正 v4 登入／註冊標題及註冊眉標，保留 legacy 文字；成功登入時僅接受安全的站內 `next` 路徑，阻擋站外返回網址。定向離線測試 `test_ren_auth_order.py`、`test_v4_routes.py` 為 **53 passed**，含購物車返回與站外導向拒絕。這只是本機修正，合併、重新部署及正式登入流程尚須另行讀回；沒有在正式站建立測試帳號或訂單。
