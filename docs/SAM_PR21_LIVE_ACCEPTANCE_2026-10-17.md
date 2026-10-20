# PR #21 正式部署與隔離交易驗收｜2026-10-17

核對時間：2026-10-17 16:06（Asia/Taipei）。本頁記錄程式已正式承接流量、隔離 Atlas 交易，以及尚未完成的全站簽收；不把示範訂單當付款或正式購買歸因。

## 版本與正式流量

- [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21) 已合併，merge SHA `2fd43557bac0148e02fa427163a9657a13c7ae23`；該版本 [main CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39006863627) success。核對時最新 main 為 `57ea59b42c59a4f984e16ead42159b2b2a60cf56`，其後只新增文件，沒有改動 Cloud Run 封裝程式；[最新 main CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39015711794) success。
- `asia-east1/vibecart-web` 的 `vibecart-web-00012-85f` 於 16:03 建立、Ready，來源標籤為上述 merge SHA，實際 amd64 映像 `sha256:d933a5d8bf3f9264beac3bc9738e2bb84d11cf92e1b8ce097b0cd3000be40b91`。環境讀回 `CLOUD_PREVIEW_READ_ONLY=false`、`ENABLE_CHECKOUT=true`，正式 Mongo URI 與 session key 仍引用 Secret Manager。先在零流量標籤驗 `/health/live`、`/health/ready`、首頁及登入頁 200，匿名後台轉登入，然後於 16:04 將此修訂切至 **100% 正式流量**；舊 `00007-m9k` 保留 `rollback-00007` 零流量標籤。
- 切換後 [Cloud Run](https://vibecart-web-m44ncgz5ta-de.a.run.app/) 與 [Firebase Hosting](https://vibecart-llmai.web.app/) 的首頁和 `/health/ready` 都回 200；Cloud Run 登入頁回 200。16:05 對正式服務查詢切換後 ERROR 日誌為 0。這是當時的部署與基本可用性證據，並非所有業務流程或真模型的正式簽收。

## Atlas 權限與私有服務

- Atlas 專案 `6aa9bd20af3f21039447a5c0` 的 `sam_pr21_acceptance_20261017` 最終唯讀讀回僅有 `readWrite@vibecart_acceptance_pr21`，scope 僅 `vibecart-ai-free`；舊 `atlasAdmin`、`readWriteAnyDatabase` 角色已移除，Collection 限制為空。Secret Manager `vibecart-pr21-acceptance-mongo-uri` 版本 1 為 ENABLED；密鑰只在程序記憶體解析，沒有輸出 URI 或密碼。以此憑證對獨立庫 `ping=1`、初始集合為空；對正式 `vibecart_ai` 讀集合回 `Unauthorized (8000)`。
- 私有 `vibecart-acceptance-pr21-00003-8hr` 使用相同 amd64 映像，只引用獨立 Mongo URI 與 session secret，並設定 `CLOUD_ACCEPTANCE_MODE=true`、`CLOUD_ACCEPTANCE_DB=vibecart_acceptance_pr21`、可寫與 demo checkout。服務 IAM 的 invoker 只列驗收服務身分、沒有 `allUsers`；匿名請求拒絕。建立一件明確標為 `PR21-ACCEPTANCE-ONLY` 的商品、SKU 與兩個分類後，授權 `/health/live`、`/health/ready` 均為 200，商城與商品頁亦為 200。

## 遠端交易讀回

- 在私有 Cloud Run 修訂透過兩個獨立 HTTP cookie session 驗證：匿名購物車 302 轉登入；會員註冊 302、兩裝置登入後各自購物車 200，資料庫同時有 2 筆該會員 session；會員後台 302 拒絕、隔離測試管理員登入後後台 200；搜尋與商品頁 200。
- 遠端 JSON 加購 200；結帳 200 並在隔離 Atlas 讀回同一筆訂單／明細、庫存減 1 與 PURCHASE 事件。相同 checkout ID 與內容重送 200 且回同一訂單；以相同 ID 改動 revision 重送 409，訂單／明細各維持 1 筆、庫存沒有再次扣減。該會員事件種類讀回 `SEARCH`、`PRODUCT_VIEW`、`ADD_TO_CART`、`PURCHASE`；訂單為 `is_demo=true`，不是付款或正式歸因。
- 以同版 `CartService` 直接連獨立 Atlas 的真交易測試，故意在庫存／訂單寫入後拋錯，讀回訂單／明細 0、庫存回復；再次正常 checkout 與相同 ID 重送只得一筆。另一組最後一件庫存的雙執行緒 checkout 為成功 1、拒絕 1，訂單 1、庫存 0。這是遠端 Atlas 交易證據；故障注入與併發不是由 Cloud Run HTTP 入口觸發。
- 真瀏覽器經受控 localhost 代理連到同一私有 Cloud Run 服務，完成註冊、選規格、加購與示範結帳，頁面顯示 `VC6AD32B4DE3316C160715C21C` 已建立且未串接付款，商品庫存由 1 顯示為 0。瀏覽器 DOM 與代理請求狀態在本次聊天核對；沒有保存可獨立交付的畫面截圖，因此簡報 S01～S12 截圖簽收仍需另做。
- 直接 Atlas 交易夾具暫時包含不完整的 active 商品，曾使私有驗收首頁回 500；已停用這兩件夾具商品及 SKU，重新讀回私有首頁 200。此失誤未觸及正式資料庫或正式服務。所有 8 個隔離測試帳號現為 inactive，`auth_sessions=0`，臨時 `serviceAccountTokenCreator` 已撤銷，本機代理已停止。
- 驗收庫目前保留可供核對的示範資料：`users=8`、`orders=5`、`order_items=5`、`behavior_events=18`、`carts=6`、`cart_events=11`、`products=3`（只有原一件為 active）、`product_skus=3`、`categories=2`、`auth_sessions=0`。資料只在 `vibecart_acceptance_pr21`；需由 SAM 在證據核對後訂定清理日期並執行隔離庫清理，不能把留存資料混入正式業務。

## 正式資料對照與未完成門檻

正式 `vibecart_ai` 以 Atlas 連接器唯讀讀回：原 D1～D3 批次訂單 **3,000**，批次外額外 demo 訂單 **2**，指定 D4 批次事件 **0**；沒有重匯 D1～D3 或執行 D4 apply。正式服務切換後尚無真會員交易、付款或全站人工簽收證據；線上 Claude／BGE／自由提問仍關閉，D4 全部實際部署 consumer 的遠端 synthetic／正常事件隔離仍需完成，最終 PPTX、離線備援、S01～S12 素材與排練另行核對。`/health/ready` 200 與本次隔離交易不代表這些項目已完成。
