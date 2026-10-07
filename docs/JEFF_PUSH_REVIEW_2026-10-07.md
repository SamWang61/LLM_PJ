# JEFF 推送審查與 SAM 缺口 / Push review and SAM gaps

核對日期：2026-10-07（Asia/Taipei）。本次只讀 GitHub／Atlas，未修改分支、合併 PR 或變更資料庫。

## 核實的推送 / Verified push

- [PR #8](https://github.com/SamWang61/LLM_PJ/pull/8)，`docs/jeff-admin-ui-design`，head `e7df81549b1ac13eb1c2b54256df117c54c29fa2`。
- JEFF 於 10/5 提交設計規格（25c28ce）及英文摘要（e7df815）。4 個 Markdown 檔、367 行新增；沒有 Python、HTML、CSS 或 migration 變更。
- 文件位於 docs/JEFF_ADMIN_UI_DESIGN.md，README、索引與 CHANGELOG 已同步，放置位置正確。
- GitHub 回讀：open、非草稿、未合併；mergeable=true、clean；兩筆 offline checks 為 success。這是文件分支的檢查，不是新後台功能驗收。
- 指定 mcp 服務離線，改用 Git fetch、已授權 GitHub REST 及既有 PyMongo 私有連線完成核對。

## 需要修正／補充 / Findings

1. **P1：AI 問答輸入契約不足。** 設計第 5.3 節（約 149–172 行）要問補貨、促銷、營收變化，且兩入口共用既有摘要邏輯。main 的 `summary_metrics` 只有範圍、營收、筆數、客單、低庫存數量，沒有商品級補貨表、庫存／銷量、比較期每日統計，也沒有問題輸入。須明訂新版白名單與缺資料退回，否則無法可靠支援這四種問題。自由文字可能含個資，「不含個資」須由伺服器端資料契約及處理機制落實，不能只靠畫面文字。此為跨 SAM／JEFF 契約缺口，不代表本 PR 已提交錯誤的運行程式。
2. **P2：分母口徑有歧義。** 第 247 行「有效訂單／範圍內訂單」都寫「同上」，容易讓分母也套用 paid／未取消。分子才是有效訂單；分母應含相同日期／demo 範圍內的全部付款及訂單狀態。平均客單除以有效訂單數，零筆時不得除零。
3. **P2：SKU 候選及價格條件不完整。** 第 258–261 行應補 `product_skus.status='active'`，並只用有效、可售 SKU 決定可購買候選／顯示最低價格。否則僅有下架 SKU 的商品可能進入推薦，或顯示不可購買的最低價。
4. **P2：D1～D3 狀態已過時。** 第 284 行仍寫業務集合為空。本次 Atlas 實際已有 336 商品／SKU、600 客戶、3,000 訂單、8,969 明細；D1／D2 已具資料，D3 已完成。應連結匯入報告與批次，提醒全部訂單為 demo、合成會員停用。
5. **P2：離線範圍需明確。** 第 186 行 Local 網路依賴「不需要」只適用模型已下載且輸入資料在本機的推論；網站讀取 Atlas／遠端圖片仍需網路。避免將本機推論不需 API 誤解成整站可離線。

其餘方向合理：沿用 Flask/Jinja、獨立後台 CSS、管理員與 CSRF、金額 Decimal128、範圍標示、模型失敗退回、不顯示未量測數字、Email 遮罩／不回傳 password_hash。規格已有改善先前 Claude 假資料原型的方向，但沒有程式推送可證明原型問題已修好。

English: Documentation placement and scope are correct; CI passed. Clarify AI payloads, KPI denominator, active/sellable SKU eligibility, current dataset readiness, and the boundary of offline inference before treating the design as an implementation contract.

## Atlas 本次只讀核對 / Live read-only evidence

| 集合／項目 | 2026-10-07 結果 |
|---|---|
| products／product_skus | 各 336 |
| users | 600 |
| orders／order_items | 3,000／8,969 |
| 本批 is_demo=true 訂單 | 3,000 |
| 本批啟用會員 | 0 |
| behavior_events | 0 |
| product_embeddings／ai_requests／recommendation_logs | 各 0；不排除其他程序記憶體快取，不能僅此宣稱模型從未運行 |
| migration | 5 筆全部 succeeded，含 20261005_05_synthetic_profile_v4 |
| users demographics | validator 已包含 |
| 推薦政策 | PURCHASE=4、ADD_TO_CART=3、SEARCH=2、PRODUCT_VIEW=1；2 分是搜尋，不是收藏 |

本次沒有重跑全量交易／完整 validator 測試；這是狀態與契約核對。

## SAM 尚未完成 / SAM outstanding work

| 優先 | 缺口 | 完成條件 |
|---|---|---|
| P1 | 本機成果尚未交付 GitHub | 將 test_data overlay／生成器／測試、TEST_DATA_SPEC、匯入證據、SAM 工作紀錄與超市讀取修改整理為可審查 PR；不要把其他人的未提交工作一起提交。main 目前沒有這些新增工具與規範 |
| P1 | GitHub 檢查器仍是舊 schema | main/scripts/check_v4_database.py 仍只接受原 v4 validator、四個 migration；Atlas 已是五個 migration 及 optional demographics／batch 欄位。應新增現行契約入口與回歸案例，不能改歷史 migration checksum |
| P1 | D5 後台寫入資料契約 | 定義商品／SKU 更新、訂單合法狀態轉移、會員停用、授權、CSRF、稽核、衝突及 rollback，與 JEFF/HEN 明確分工 |
| P1 | AI 問答白名單 | 提供分商品補貨、期間比較與必要的資料品質標示；JEFF 實作模型呼叫與畫面。不要發送會員資料 |
| P2 | D4 行為事件 | 生成有批次、參照、時間與標準答案的測試事件；不把模擬事件當真實轉換成效 |
| P2 | 可登入的測試帳號 | 現有 600 人全部停用，需另配置少量 customer/admin 私有憑證與撤權案例 |
| P2 | 與 JEFF 完成畫面对帳 | 對日期、demo、退款／取消、零筆、366 天／5,000 筆界線測試；資料匯入不是 UI／API 接線完成 |
| 待處理 | 其他協作事項 | PR #9 查詢手冊已合併；PR #10 Network Access 文件尚未合併；PR #5 計分候選仍是草稿，由 JEFF 決定，非 SAM 正式交付 |
| 待確認 | HEN／最終驗收／備份 | 此聊天尚未收到 HEN 晚上確認結果；整合驗收負責人與 Drive 私有／加密決策仍待確認，不因這次審查自動完成 |

建議順序：SAM 先交付現行 schema 與資料文件並補 D5／AI 契約，JEFF 更新設計文件並開始／提交功能實作，再以同批資料對帳。此文件是本機審查結果，沒有自動向 JEFF 發送評論或更改其 PR。
