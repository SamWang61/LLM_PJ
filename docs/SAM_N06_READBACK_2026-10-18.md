# N06 回滾關聯資料讀回補強｜2026-10-18

SAM 在 [PR #61](https://github.com/SamWang61/LLM_PJ/pull/61) 的 `2e30880054b02c00872f11bfffe97873ca8f95d5` 基礎上補強探針，並於 **04:06～04:11（Asia/Taipei）** 重跑同映像私有驗收。補強由 [PR #69](https://github.com/SamWang61/LLM_PJ/pull/69) 審查，base 為 #61 分支，沒有直接合併 main。[無憑證結果與獨立讀回](inventory/sam-n06-readback-20261018.json)保留實際數字。

## 查詢契約與更正

現行 `sku_cart_service.checkout_cart` **會在 order_items 寫入 user_id**，所以原探針以 user_id 查正常結帳明細是有效的；先前把它解讀成「不存在的欄位」不正確，本輪不因該解讀將原 PR #61 的案例判失敗。

此次把明細查詢改為已確認屬於本輪的 `sku_id`，額外涵蓋缺少 user_id 或父訂單的異常殘留；同時補查原計數未涵蓋的 `cart_events`。四集合分別依本輪 user_id、sku_id、cart_id 查核，報告公開 before／after，避免只有布林結果。新增反向回歸以沒有 user_id／有效父訂單的異常明細和 cart event 證明差異可被看見；外部 SKU／cart 不被納入。

## 同映像遠端結果

- 正式 `vibecart-web-00015-nlk`／私有 `vibecart-acceptance-pr21-00005-5j5`，來源均為 `1d2abf2cfa7465636e49474062e11f6aca571dda`，映像 digest 均為 `1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b`；執行前後 serving revision／流量相同。沒有部署。
- 唯一批次 `ren-txn-e845fb610a46030c` 僅在 `vibecart_acceptance_pr21` 建立臨時會員／admin／商品／SKU；實際連線角色只有該庫 readWrite，私有 invoker 僅專用 SA。
- 最後庫存兩請求並行 HTTP **[400, 200]**，只成功一次，庫存 0；包含原成功案例總訂單 2。
- 失敗案例明確讓第二個 SKU 缺貨，HTTP 400；第一個 SKU 庫存維持 1、cart revision 不變。讀回如下：

| 集合 | 查詢範圍 | 失敗前 | 失敗後 |
|---|---|---:|---:|
| orders | 本輪兩個 customer user_id | 2 | 2 |
| order_items | 本輪兩個 sku_id，涵蓋異常孤兒明細 | 2 | 2 |
| behavior_events | 本輪兩個 customer user_id | 6 | 6 |
| cart_events | 本輪 customer 的 cart_id | 6 | 6 |

finally 的九範圍讀回均為 0；獨立 Atlas 連接器再查 users、products、SKU 的 marker 及 orders checkout 前綴均 0。依賴集合九範圍是 runner 的精確 ID 讀回，**沒有宣稱獨立連接器重查了全部九範圍**。獨立 IAM 查本輪 token creator condition 剩餘 0，私有匿名 `/health/live` 403；已簽發 token 仍依原到期失效，沒有落盤或分享。

這輪亦通過同映像角色、雙 session、重登入／舊 cookie、維運全 session 撤除、停用、demo checkout 重送／409 及單裝置登出。停用／撤 session 由受控操作端直接處理隔離夾具，仍不是 D5 管理 API／畫面已交付。[PR #67](https://github.com/SamWang61/LLM_PJ/pull/67)另保留兩角色停用後重啟、必須新登入的獨立流程與撤權計畫。

## 來源與離線回歸

實際執行探針提交為 `f09ff0c5634690b3c90dcb21629a73239a28714a`，三個執行器／探針 Git blob SHA-256 已列入 JSON；後續提交只補正註解、CI 與證據文件。CI 現會執行 `scripts/test_remote_member_transaction_checks.py`。

- 本輪 Python 安全回歸 **10 passed／0 skipped**，Node 執行器回歸 **3 passed／0 skipped**。
- 新推送 #61 的最終 head `2e30880054b02c00872f11bfffe97873ca8f95d5`：PR CI `39064958041`、push CI `39064954466` success；本輪另外重跑其原四個安全案例，4 passed。
- 獨立核對 #61 的 47 個部署來源 Git 物件與已部署來源全部相同；新增 D5 schema 沒有進執行封裝。D5 仍屬下一階段的本機演練，沒有正式 apply。
- 原 #61 報告的兩個 Python 探針 SHA 與其執行提交相同；Node 原始檔 hash 為 Windows CRLF，恰好等於同一 Git blob 轉 CRLF 的 bytes，不把它寫成 Git blob byte equality。本輪 Node 執行前已對齊提交的 LF bytes。

## 尚缺與下一步

N06 的同映像最後庫存競爭、受控缺貨回滾與關聯資料讀回已補齊；**任意 DB fault、checkout 中撤權的遠端注入及最終具名驗收仍缺**，不把整列 N06 改為完成。後續先整合 #61／#67／#69 證據，按 N11～N18 收斂 v1；不重做本輪已通過案例，也不把 D5、本機真模型或 demo checkout 當線上寫入／真付款。

N02 具名交接、實際展演窗口帳號、N12 實機、備援／排練與全站簽收仍待完成。REN 暫代不自動延長。原工作樹保留，沒有正式業務庫寫入、D1～D4 重匯或向他人發訊息。
