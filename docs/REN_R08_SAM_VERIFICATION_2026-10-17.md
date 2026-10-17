# REN R08：SAM 代理驗證紀錄｜2026-10-17

本紀錄由 **SAM 代理 REN（24 小時）**執行，依據 [REN 工作異常報告 PR #27](https://github.com/SamWang61/LLM_PJ/pull/27) 的 2026-10-17 11:10～2026-10-18 11:10（Asia/Taipei）期間。Git／GitHub 實際操作者為 `SamWang61`；REN 保留原模組責任。本頁的檢查對象是 [REN R08 PR #25](https://github.com/SamWang61/LLM_PJ/pull/25) 程式提交 `ac74b4f49853c6a92e1dd26bfe5bf430fba1154d`，文件提交不改變受測程式。

## 本次同版結果

2026-10-17，在乾淨的 PR #25 工作樹，以一次性、無正式憑證的 localhost MongoDB 8 replica set `rsREN20261017` 執行完整網站測試：**179 passed、0 skipped（31.57s）**。其中包含三項需要真 MongoDB transaction 的測試；本結果取代此 PR 先前的 176 passed／3 skipped 本機紀錄。這只證明此程式版的隔離本機測試，尚非雲端、Atlas、跨角色人工或付款驗收。

可重現命令（於 `MuscleCore分析資料/website` 執行；Python 使用已安裝專案依賴的虛擬環境）：

```powershell
docker run --rm -d --name ren-r08-rs-20261017 -p 127.0.0.1:27017:27017 mongo:8 --replSet rsREN20261017 --bind_ip_all
docker exec ren-r08-rs-20261017 mongosh --quiet --eval 'rs.initiate({_id:"rsREN20261017",members:[{_id:0,host:"127.0.0.1:27017"}]})'
$env:HEN_TEST_MONGO_URI = 'mongodb://127.0.0.1:27017/?replicaSet=rsREN20261017'
python -m pytest tests -q -p no:cacheprovider
Remove-Item Env:HEN_TEST_MONGO_URI
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

PR #25 以草稿 PR #21 為 base；本次測試沒有合併 `main`、部署、寫入 Atlas 或重匯 D1～D3。正式遠端驗收須先定最終整合 SHA，再以同版環境逐項取證。到 2026-10-18 11:10 代理期滿，SAM 應列出已交／未交 SHA、遠端證據及阻礙交回 REN；沒有恢復資料時，REN 軟體異常仍標為待確認。
