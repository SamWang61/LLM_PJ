# REN R02：會員、購物與事件接口交接

日期：2026-10-17（Asia/Taipei）。核對來源為 PR #21 的 `1d60914d95eca924c8a1c5f4edfecf22ef443283`。本頁記錄該版程式目前的接口與剩餘決策；舊版 `HEN_R02_CONTRACT_2026-10-14.md` 的單一登入草稿已被多裝置實作取代。PR #21 仍是草稿，尚未合併 `main`。

## 1. 現行接口

| 範圍與位置 | 現行行為 | 呼叫者與驗證重點 |
|---|---|---|
| `GET/POST /auth/register`、`/auth/login`；`app/auth.py` | 註冊只建立 `customer`；email 正規化，重複回 409、欄位不合法回 400。登入要求 active 的 v4 user 與正確密碼；成功建立 30 日的裝置 session。 | 前台會員。資料庫只存 session token 的 SHA-256 digest；新裝置登入保留舊裝置。測重複 email、錯密碼、停用與兩裝置並存。 |
| `GET/POST /auth/logout`；`app/auth.py`、`app/services/member_sessions.py` | GET 為確認頁，POST 受共用 CSRF 保護；v4 登出刪除目前裝置的 `auth_sessions`，並清除瀏覽器 session。 | 前台會員。重播已登出裝置的舊 cookie 應拒絕，其他裝置繼續有效。 |
| `current_member()`、`login_required`、`admin_required`；`app/auth.py` | 每次請求重讀 user 的 active/status/schema/role，並核對裝置 session 存在、未過期及密碼 fingerprint。 | 所有受保護路由。停用、降權、密碼更新後的舊 session 須拒絕或失去管理權。legacy 模式不宣稱具相同的伺服器撤權。 |
| `revoke_user_sessions(db, user_id, mongo_session=...)`；`app/services/member_sessions.py` | 可信服務函式，刪除指定會員全部裝置的 session，可加入呼叫者的 MongoDB transaction。不是公開 HTTP API。 | JEFF 的後台停用／降權服務接入；需在同一交易提交狀態與撤權。SAM 驗撤權 rollback。 |
| `POST /cart/add/<product_id>`、`/cart/update/<sku_id>`、`/cart/remove/<sku_id>`、`GET /cart`；`app/store_v4.py` | 會員 ID 取已驗證 session；SKU 與商品狀態、數量、可售庫存由服務查核。mutation 用 `operation_id` 去重，可帶 `expected_revision`；相同鍵不同內容或版本衝突回 409。 | 前台會員。舊 API 的 revision 暫可省略；新表單應傳版本。後端重新取 SKU 價格，不採前端金額或 user ID。 |
| `POST /checkout`；`app/store_v4.py` → `app/services/sku_gateway.py` → `VibeCart_AI/services/sku_cart_service.py` | 需要 `checkout_id`、`cart_id`、`expected_revision`，且 `ENABLE_CHECKOUT=true`。相同鍵同內容回原訂單，不再扣庫存；不同內容／舊版本回 409。訂單、明細、庫存、購物車及事件由交易服務處理。 | 目前只建立 `is_demo=true` 示範訂單；`payment_status=paid` 是示範狀態，沒有付款商回執或退款。SAM 的隔離 replica set 已驗 rollback／並發；正式 Atlas 與遠端同版仍待驗。 |
| `GET /?q=...`、`GET /product/<id>`；`app/store_v4.py`、`app/services/member_events.py` | 已登入會員觸發 SEARCH／PRODUCT_VIEW；每次 GET 是新事件，沒有跨網路重播去重。 | 搜尋／瀏覽錯誤與事件寫入失敗須依路由回應驗證；匿名瀏覽不寫會員事件。 |
| SKU 加購／checkout；`VibeCart_AI/services/sku_cart_service.py` | ADD_TO_CART／PURCHASE 與購物 mutation 同交易，operation／checkout 識別碼去重；`BEHAVIOR_SYNTHETIC_BATCH` 由伺服器設定 synthetic metadata。所有現行 PURCHASE 均來自 demo checkout，標記 `demo_checkout` 與 `exclude_from_attribution`。 | JEFF 核對每個推薦、評分、歸因及排程 consumer；SAM 須驗同版遠端在 sort／limit 前排除 synthetic。正式付款若日後加入，PURCHASE 標記政策需重新定案。 |

## 2. 已有證據與界線

- PR #18 `5053993` 已推送；其 R02/R08、四事件與多裝置實作已包含在 PR #21。PR #18 的舊 HEN 名稱與原 base 是歷史資訊，不代表另一份待重做程式。
- 10/15 REN 版本在獨立、無憑證 localhost MongoDB replica set：網站測試 166 passed、0 skipped，含真 rollback、最後庫存並發、checkout 重送與撤權回滾；見 `docs/SAM_CI_TRANSACTION_ACCEPTANCE_2026-10-15.md`。
- PR #21 在 T5 合併前的隔離 replica set 為 171 passed、0 skipped；T5 合併後未帶該測試服務的本機網站回歸為 172 passed、3 skipped。不能把不同提交的結果合併寫成同版真交易通過。
- Cloud Run 的 PR #21 零流量預覽是唯讀模式，登入、購物及後台寫入被擋；舊正式 revision 的會員 QA 不能當作 PR #21 同版遠端交易驗收。D4 指定批次尚不可 apply，D1～D3 不重匯。

## 3. 依序交接與未決決策

1. **R02／REN → SAM、JEFF**：以本頁作實際函式／路由交接。JEFF 須確認後台停用、降權、最後管理員與自停用規則，並在受權、CSRF、稽核及交易完善的寫入流程接 `revoke_user_sessions()`；目前沒有可驗收的後台全裝置撤權頁面。
2. **R08／REN → SAM**：會員與購物程式已交；SAM 以 PR #21 同版、獨立測試環境重驗跨裝置、角色、舊 cookie、購物版本衝突、checkout 重送、庫存／明細與 rollback，並補人工瀏覽器及手機證據。測後停用私有帳號並撤權，不啟用 600 位合成會員。
3. **事件／JEFF、SAM**：REN 的四種觸發已交。JEFF 明列實際部署的 consumer／排程及正式購買歸因政策；SAM 遠端逐一讀回 synthetic 排除後，才考慮 D4 正式匯入。
4. **付款／取消**：目前只有 demo checkout。真正付款、退款、取消後的庫存補回及稽核由 JEFF／SAM 定案後另實作；不能依現有 `paid` 欄位推定已付款。
