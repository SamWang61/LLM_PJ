# SAM D5 與 AI 資料契約提案

日期：2026-10-07；狀態：SAM 提案，JEFF／HEN 尚未接受。SAM 定義資料與測試；JEFF 實作管理後台／AI；HEN 實作會員／購物流程。本文不代表已有可用寫入 API。

## D5 寫入協定

所有變更由伺服器驗證登入且目前仍為 active 的管理員；拒絕客戶、停用會員及過期身分。Cookie 請求必須驗證 CSRF，不能僅隱藏按鈕。請求包含 request_id、expected_updated_at、明確資源 ID 與 allowlist patch；不接受任意 MongoDB operator、角色、password_hash 或 synthetic_batch_id 更新。

|操作|允許及驗證|交易／衝突規則|
|---|---|---|
|商品|name、description、status、is_ai_recommendable；分類必須存在，status 僅 active/inactive/draft|比對 updated_at；保留 ID、schema_version、評價與歷史快照|
|SKU|price、stock_quantity、status；TWD Decimal128 兩位，非負金額／整數庫存，合法 product_id|同交易重算 stock_status；庫存帳與補貨原因需 JEFF 確認，不能由歷史合成訂單重算庫存|
|訂單|pending→confirmed→shipping→completed；pending/confirmed→cancelled；completed 為終態|confirmed 必須 paid，shipping 必須 shipped，completed 必須 delivered；取消退款是獨立付款確認，不能直接把 paid 改為 refunded 假裝退款成功|
|會員停用|status=inactive、is_active=false；不刪除歷史訂單|撤銷 session／token；最後一位管理員與自己停用策略待 JEFF/HEN 確認|

不可修改已建訂單的 user_id、價格／分類快照、總額、checkout_id 或 is_demo。退款外部流程採有冪等键的待辦紀錄與回應確認，不能宣稱 MongoDB transaction 可回滾付款商。

同一 request_id 與相同內容重送回傳原結果；相同 ID 不同內容回 409。updated_at 比對失敗回 409；驗證錯誤 422、未登入 401、無權限／CSRF 403、不存在 404。上限每批 100 筆，逐筆結果或整批原子模式須呼叫者明選；原子模式任何失敗全部回滾。交易使用 snapshot/majority；業務更新與稽核同交易，稽核失敗不得留下成功更新。現有 schema 沒有完整稽核集合，須新增獨立 migration，不能修改既有五筆。稽核只記 actor ID、request ID、資源、白名單前後值、UTC 時間、理由與結果，不記密碼／token／URI。實作前須確認欄位與保留期限。

## AI 白名單 v1

伺服器重新聚合，禁止直接信任瀏覽器摘要。僅傳以下形狀；未知欄位拒絕，缺資料回 data_unavailable，不能補造數字。

- contract_version、timezone=Asia/Taipei、generated_at、來源批次／demo 標示、資料截止與品質警示。
- current_range、comparison_range：台北日期起訖轉 UTC 半開區間；各 1–366 日、結束大於開始。比較期預設緊接前期等長，閏日按實際天數；相同篩選口徑。
- totals：all_orders、valid_orders、revenue、average_order_value。all_orders 只套日期／demo；valid_orders 另套 paid 且非 cancelled；revenue 用 total_amount、Decimal 精算後字串兩位；零有效單客單為 null。比較基期為零時成長率 null。
- daily：date、all_orders、valid_orders、revenue，補零日期；最多 366 列／期。
- products：product_id、name、sku_id、price、stock_quantity、reorder_point、valid_sold_units、promotion_eligible。最多 100 列，排序與截斷必標示；補貨僅候選，不自動寫庫存。促銷資格若無可核實成本、效期、規則，傳 null，不推測毛利。
- 候選須 product.status=active、is_ai_recommendable=true、SKU.status=active 且 stock_quantity>0；最低價只算这些可售 SKU。沒有可售 SKU 即排除。

每期最大 5,000 訂單，超過回 range_too_large，不能靜默截斷營收；先計數再聚合。禁止 users、email、生日、婚姻、session、password_hash、原始訂單、付款／物流地址。自由問題改為 replenishment/promotion/revenue_change/period_compare 四個 intent 與受驗證參數；自由文字若日後啟用須另訂去識別化契約。

## D4／登入與驗收待辦

D1/D2：商品 336／SKU 336；D3：停用合成會員 600、demo 訂單 3,000、明細 8,969，既有批次不重匯。D4 使用新批次，metadata 記批次，event_id 唯一且能辨識 synthetic；四事件權重 PURCHASE=4、ADD_TO_CART=3、SEARCH=2、PRODUCT_VIEW=1。PURCHASE 參照真實存在的本批有效 demo 訂單／明細，時間不得早於下單；不得觸發正式推薦歸因或營收。未建立或匯入 D4。

私有登入測試需單獨少量 customer/admin、不可啟用既有 600 人；隨機密碼只存私有密碼管理器、hash 入庫，測完停用並撤銷 session。現有角色授權／session 接口由 HEN/JEFF 確認後實作；本次不造出無法驗證撤權的帳號。

待 API 接線後驗收：越權／CSRF、重送及不同 payload、雙人版本衝突、稽核失敗交易回滾、非法狀態跳躍、取消退款、停用後舊 session、100/101 批量、366/367 日、5000/5001 訂單、零資料／零基期、跨年／閏日、demo 排除為零、下架低價 SKU 不影響最低可售價。離線測試與 Atlas 結構檢查不等於此表已通過。
