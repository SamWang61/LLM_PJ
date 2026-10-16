# JEFF 後台原型檢視 / JEFF admin prototype review

檢查日期：2026-10-05。來源：https://claude.ai/artifact/4ZakrG9VZB98hmfdXsxdzz

結論：畫面架構部分符合規範，可作為後台互動原型；尚不能認定功能整合或上線驗收通過。頁面明示 Demo／假資料，管理頁明示不寫入資料庫。本次僅操作瀏覽器原型，沒有查閱其原始碼、驗證 Atlas 或實際模型 API，也沒有修改 JEFF 的程式。

English: The UI is a useful partial prototype, not evidence of production integration. This review covers observable browser behavior only, not its source code, database persistence, or real model execution.

## 對照依據 / References

- `docs/AI_DASHBOARD.md`：範圍一致性、付款統計、低庫存、摘要與推薦監測。
- `docs/FLASK_SKU_AI_INTEGRATION.md`：有效商品與庫存篩選、AI 白名單輸入、模型設定與安全界線。
- `討論的相關記錄/VibeCart_AI_專案整合規格_v1.1.md`：雙 AI 任務分工、執行紀錄與示範流程。此歷史規格不取代現行 v4 schema 或最新責任分工。

## 實測結果 / Observed results

| 項目 | 結果與界線 |
|---|---|
| 八個主要頁面 | 營運總覽、Local 推薦、雲端洞察、AI 比較、推薦監控、商品、訂單、會員管理均可開啟 |
| 商品搜尋 | 輸入「乳清」，列表縮小為 1 / 16 項，符合互動預期 |
| 商品相似推薦 | 選乳清蛋白並計算後，基準商品與 Top 5 更新；僅證明展示互動，不證明 BGE 推論 |
| 日期檢核 | 起日 2026-10-04、迄日 2026-10-03，提交紀錄顯示錯誤「開始日期不可晚於結束日期」 |
| 雲端退回 | 狀態預覽選逾時，再問補貨問題，顯示規則回覆、原因及非 AI 分析標示；僅驗證模擬情境 |
| 推薦監控 | 標明最近 1,000 筆事件，次數非轉換率；歸因指標留空、衰減排程標示尚未接線，界線表達合理 |
| 每日金額加總 | 展示的 14 天營收合計 486,320，與總 KPI 相符；不代表真實帳務資料正確 |
| 商品／訂單／會員管理 | 有管理列表與操作入口，未逐一驗收新增、修改、刪除或持久化；會員電話有遮蔽 |

## 必須修正 / Required corrections

### P1：篩選顯示成功，但資料未同步 / Filters do not update displayed data

重現：總覽起迄日期均設為 2026-10-03，示範訂單選「排除示範」，按套用。提交紀錄顯示成功，但 KPI 仍為 486,320、92 / 100；每日表仍列 9/20–10/3，最近訂單仍含示範訂單，頁首仍寫包含示範。已重現兩次。

修正：範圍說明、KPI、每日表、熱銷、最近訂單與摘要必須使用同一篩選資料；低庫存保持目前狀態。無資料時顯示空狀態，不能留下舊數字。即使使用假資料，也應實際篩選。

### P1：推薦包含下架商品 / Inactive product recommended

重現：乳清蛋白相似推薦第一名為 BCAA 胺基酸粉（0.87）；商品管理同一品項 MC-AA10 為「下架」。

修正：若結果代表可供前台使用的推薦，應先排除下架、不可推薦及無可售庫存的商品；若這只是後台全商品分析，需明確區分分析模式與正式推薦模式，並標示商品狀態。

### P1：AI 資料預覽與問題不同步 / AI payload preview is stale

重現：先提問「營收為什麼下滑？」，再切逾時模式提問「哪些商品該補貨？」。頁面顯示補貨回覆，但展開「送給模型的資料」後，JSON 的 question 仍為「哪些商品適合促銷？」。

修正：預覽須來自該次請求的相同資料物件，包含問題、範圍與示範篩選。未送出 API 時不得稱為「實際傳送」。預覽還含商品名稱；現行 Flask 白名單不包含商品自由文字，擴充前須明訂資料契約及防注入處理。

### P2：AI 解讀含無法由資料支持的推論 / Unsupported analytical claims

「營收為什麼下滑？」回覆將訂單數下降直接推論為來客數減少，預覽資料未提供流量或訪客數；所稱 14 天平均 34,312.86 也與展示每日表加總 486,320 / 14 = 34,737.14 不符。

修正：數值由程式計算，模型僅解讀；缺少流量資料就標示無法判定來客變化。原因推測需與已知事實分開。

### P2：模型與量測標示 / Model and measurement labeling

頁面顯示 claude-sonnet-5、最近十次中位數、Token、估算成本及模型載入／資料庫連線狀態。本次沒有對應執行證據，不判定模型 ID 可用性或真實量測。Demo 應在指標旁標示「示範值」，正式版應從實際模型設定與執行紀錄讀取。

## 整合驗收待辦 / Integration acceptance still required

1. JEFF 修正上述三項 P1 及分析數字問題，提供對應 GitHub 提交與啟動方式。
2. SAM 驗證 v4 欄位契約、已付款／退款／取消口徑、日期邊界、零資料、366 天及 5,000 筆界線、金額精度。
3. 驗證管理員登入、逐次角色檢查、撤權、CSRF、真實登出與資料持久化；目前原型的登出及回商城連結都指向 #overview。
4. 驗證真實 BGE、雲端 API、快取分範圍、逾時、使用紀錄與成本；不能用狀態預覽替代故障測試。
5. JEFF 的會員／訂單後台操作需與 HEN 的會員／購物流程共用資料契約；分工不因此重新指派。跨模組驗收責任仍依 TEAM_OWNERSHIP.md 待確認。

English: Fix filtering, inactive-product eligibility, and payload consistency first. Then verify numeric claims, real providers, authorization, persistence, data contracts, and failure behavior. No full integration acceptance is granted by this review.
