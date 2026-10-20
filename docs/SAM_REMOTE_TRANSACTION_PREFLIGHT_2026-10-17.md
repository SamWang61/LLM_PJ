# SAM 遠端交易驗收前置｜2026-10-17

目前 [PR #21 零流量預覽](SAM_PR21_REMOTE_PREVIEW_2026-10-17.md)只讀取正式 `vibecart_ai`，登入與交易入口均回 403。Atlas 連通與資料對帳不等於已驗收會員、管理員、購物車或結帳。

## 已備妥的程式防護

`MuscleCore分析資料/website/cloud_runtime.py` 新增可選的 `CLOUD_ACCEPTANCE_DB`。只有 `K_SERVICE=vibecart-acceptance-pr21`、`CLOUD_ACCEPTANCE_MODE=true`、`CLOUD_PREVIEW_READ_ONLY=false`，且資料庫名稱符合 `vibecart_acceptance_[a-z0-9_]+`，才允許連至獨立驗收資料庫；否則啟動失敗。未設定時仍使用原來的 `vibecart_ai`。Claude、BGE 與自由提問仍保持關閉；是否啟用 checkout 另由 `ENABLE_CHECKOUT` 決定。本機環境契約測試 8 passed，未對 Atlas 寫入。

本次於一次性、無憑證的本機 Docker MongoDB replica set 重跑網站完整測試：**180 passed、0 skipped**，容器已停止。這是本機交易行為與回歸測試，不是遠端交易驗收。

合併 REN 交接 `main` 後的 PR #21 程式提交 `2251c88a250c1001942960230f691c2acea10803` 已重新封裝與建置：47/47 白名單檔案與 Git blob 完全相同，tar SHA-256 `c7851f2db0ed764c5f2230316d16d1890e9331c48924f4956a50db2f6efaafa1`，本機 Docker image build 通過。以假 MongoDB URI 啟動唯讀容器，`/health/live` 200、`/health/ready` 503（無資料庫的預期結果）、`/auth/login` 403；容器已停止。此映像尚未推送或部署到 Cloud Run。

此防護只避免服務誤選正式資料庫，**不是完整隔離的證明**。Atlas 唯讀讀回的 3 個資料庫使用者，權限分別是正式 `vibecart_ai` 的 readWrite/dbAdmin、正式庫的 readWrite，以及 admin 的 atlasAdmin；目前沒有已核實的獨立驗收 DB 專用帳號。私有服務的 IAM、網路入口、獨立 session secret、資料保留與清理權限也尚未讀回。不可直接把現有公開 `vibecart-web` 切成可寫入模式。

## 建立私有驗收服務前必備

1. 固定待驗 Git 完整 SHA 與容器 amd64 digest；使用獨立 `vibecart-acceptance-pr21` Cloud Run 服務，僅允許授權測試者呼叫，保持主站 `vibecart-web` 100% 舊版流量與 Hosting rewrite 不變。讀回 ingress、invoker IAM、服務帳號、revision 與 digest，再發任何測試請求。
2. 使用獨立資料庫 `vibecart_acceptance_pr21` 與最小權限資料庫帳號；新憑證由 Secret Manager 注入，不寫入 Git、文件或終端輸出。先讀回實際目標 DB 名稱及空集合狀態。若無法限制憑證只碰驗收 DB，停止寫入驗收。
3. 在該 DB 執行現行版本化 schema／索引，僅放最少量人工可辨識的測試商品、SKU、會員與管理員；不得複製 D1～D3、D4、真會員或正式訂單。記錄測試資料清單、批次 ID 與清理／保留期限；不能以已存在的額外兩筆示範訂單替代。
4. 以真瀏覽器及兩個獨立裝置 session 驗匿名、會員、管理員權限與停用撤權；驗 SKU 加入／更新、checkout 重送 409、不重扣、最後庫存併發、rollback、訂單與明細及 SEARCH／VIEW／ADD／PURCHASE metadata。每項保留請求狀態、服務 revision/digest、資料庫寫前／寫後讀回、畫面及時間。購買仍是 demo，不能稱為真付款或正式歸因。
5. 執行後停用測試帳號與 session，按事先清單核對集合筆數、事件／訂單批次與清理；保留必要匿名化驗收摘要。正式 Atlas `vibecart_ai` 的 D1～D3、兩筆額外示範訂單、D4 0 及主站流量再唯讀比對，證明未受影響。

本頁為可執行前置與驗收標準，**尚未建立、部署或驗收私有可寫入服務**。在 IAM、最小權限 MongoDB 憑證與獨立資料庫未齊之前，PR #21 保持草稿，D4 不得 apply，遠端角色與交易不得寫成已通過。
