# HEN R02／R08 接口契約與順序

日期：2026-10-14（Asia/Taipei）。基底 origin/main `066e9da`，HEN 遠端 `e66e06c` 已為 main 祖先；原目錄異動保留。依使用者要求完成 HEN 工作，文件內提示詞是參考，並非額外發布授權。以下「本輪方案」仍待 SAM／JEFF 接受，不將 SAM 提案視為團隊定案。

## 依序交付

1. R02：本契約與現況盤點。
2. R08 會員：既有註冊／登入、即時 active／role、POST 登出與伺服器撤權。
3. R08 購物：沿用 store_v4 → sku_gateway → sku_cart_service → cart_service 的交易層，補版本與邊界測試。
4. 事件：搜尋／瀏覽／加購／購買，demo／測試事件排除正式歸因。
5. 隔離測試、操作文件、審查與交付；合併／部署／正式帳號／D4 由 SAM 接續。

## 現有接口及本輪方案

所有 Cookie 狀態變更沿用 security.py 的 CSRF（缺失／不符 400）。會員身分只取 signed session，金額從 SKU 重新取得；不取請求的 user_id／price。資料庫錯誤 503，不回傳 URI／例外內容。

|接口／呼叫者|輸入／結果與資料變更|身分、錯誤、重送及測試|
|---|---|---|
|GET/POST /auth/register，會員表單|name/email/password；email 正規化、customer 固定；新增既有 v4 users，成功 302|重複 email 409，輸入不合法 400；需既有 email unique index；重送不新增第二會員|
|GET/POST /auth/login，會員表單|email/password；成功 302、登入 cookie|v4 active/status/schema/role 即時確認；錯誤密碼／停用不建立登入|
|GET/POST /auth/logout，導覽|GET 顯示確認，POST 執行登出|POST CSRF；本輪 v4 方案撤銷該會員所有舊 cookie；不只清瀏覽器|
|login_required/admin_required，路由|每請求重讀 users；更新 session 顯示角色|未登入／停用／世代不符轉登入；customer 管理頁拒絕；資料庫錯誤 503|
|revoke_user_sessions(db,user_id)，JEFF 可信服務|更新既有 users.last_login_at 登入世代|函式不是公開 API；由 JEFF 的已授權停用／角色變更服務呼叫，禁止客戶任意撤權|
|POST /cart/add/<product_id>|sku_id、quantity 1..99、operation_id；回 cart ID/revision/status 或 303|僅目前會員；SKU 歸屬與商品狀態／庫存驗證；錯誤 400/404，重送相同內容不再加購／寫事件，改內容 409|
|POST /cart/update/<sku_id>、/cart/remove/<sku_id>|quantity（update）、operation_id、expected_revision；回 cart 或 303|頁面傳 revision；相同鍵同內容重送成功、不同內容或版本衝突 409；既有無 revision API 暫相容，見限制|
|GET /cart|目前會員 cart／SKU 快照估價、checkout revision|會員不能讀別人的 cart；無前端 owner 欄位|
|POST /checkout|checkout_id、cart_id、expected_revision；回 order 或 303|預設關閉 403；啟用為 demo，server 重新計價；相同鍵不同 cart/revision 409，原結果重送庫存只扣一次；庫存／訂單／明細／事件同 snapshot/majority transaction|
|GET /?q=、/product/<product_id>|SEARCH／PRODUCT_VIEW；登入會員才寫事件|伺服器判定登入；GET 每次代表一次新瀏覽／搜尋，不承諾網路重播去重；事件失敗 503|
|CartService 加購／checkout|ADD_TO_CART／PURCHASE|與操作同交易，operation_id 去重；demo PURCHASE 必排除正式歸因；來源權重既有 4/3/2/1|

## 撤權方案與待確認

本輪 v4 建議採單一有效登入，使用既有 nullable BSON date `last_login_at` 作為世代，cookie 持有對應毫秒值。登入與撤權以 CAS 推進且至少增加 1ms；新登入／登出讓舊 cookie 失效。停用與角色變動每請求重讀，JEFF 在持久停用／降權時應呼叫撤權，避免停用後重新啟用使舊 cookie 復活。不新增 token 或集合、不改歷史 migration。legacy 保留登入 cookie 行為，僅登出改 POST／CSRF，legacy 不宣稱具伺服器撤權。

SAM／HEN：確認單一登入政策及 last_login_at 作為世代兼容其他寫入者；若要多裝置獨立登出，需另訂 session schema／新 migration，本輪不可部署成該政策。JEFF：停用／降權與撤權須同一交易時，以函式 session 參數銜接；最後管理員、自停用策略與後台路由由 JEFF 定案。

付款：既有 demo 訂單仍為 confirmed/paid/is_demo=true，只是示範狀態，不是付款商回執；取消／退款接口未定，不自行新增。SAM／JEFF 確認 demo 庫存與後台取消補回責任，正式付款另案。

## 測試與驗收界線

本機 mongomock 測 auth/CSRF/重送/版本/事件；它不驗 MongoDB validators、交易 rollback 或並發。另附需獨立 replica set 的 opt-in 測試：隨機獨立資料庫、真交易 rollback、最後庫存並發、重送，禁止指向正式 Atlas。SAM 負責隔離 MongoDB 環境與 validator 驗收，JEFF 核對所有評分／歸因消費者；D4 必須在遠端隔離完成後才 apply。

整合 PR #17 仍是 SAM／JEFF 未合併工作；本輪不合入整個分支。SAM 整合時保留其前台／隔離變更並使用本輪接口與測試。少量私有帳號、遠端瀏覽器、部署與整合簽收待 SAM；既有 600 位合成會員不啟用。
