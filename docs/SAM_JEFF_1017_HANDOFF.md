# 10/17 JEFF 交付核對與 SAM 決定

本紀錄依 JEFF 的 10/17 本機交付說明，核對 [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21)、[PR #23](https://github.com/SamWang61/LLM_PJ/pull/23) 和同版程式。專案負責人已授權在本對話處理決策。此處將程式、離線驗證、遠端部署與最終簽收分開記錄；沒有將 JEFF 的本機模型敘述當成 SAM 的遠端驗收。

## 1. 分支與驗證

- 10/17 將 JEFF PR #23 的 `caa88d9bac9bb71baa58dd5d1cd7b70cc4136704` 合併至 PR #21 分支；合併提交 `6e401ef459b4ca5e002c22ee225cb4c63375ec3a`。`main` 未合併。T5 相對原 #21 只有六個檔案：`ai_payload.py`、`ai_workflows.py`、`ai_insight.html`、`test_ai_insight.py`、`AI_DASHBOARD.md`、`CHANGELOG.md`。
- 合併前乾淨工作樹執行網站測試 **172 passed、3 skipped**；另有合成資料測試 **26 passed**、備份契約 **3 passed**、`prepare_cloud_source.py` **47 個白名單檔案**、文件政策 **284 files／266 UTF-8 texts／0 errors**、`git diff --check` 與 `git lfs fsck` 通過。3 個 skipped 不能當成通過的交易驗收；先前 PR #21 在隔離 replica set 的 **171 passed、0 skipped** 屬 T5 合併前程式。
- 合併提交的 [push CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38991253680) 與 [PR CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38991257679) 均成功。這些 CI 不呼叫真 Claude／BGE，也不測 Atlas 正式交易或部署。

## 2. behavior_events consumer 與 D4 閘門

以合併提交的追蹤程式搜尋 `behavior_events`、`recommendation_logs`、`user_preference_scores` 並檢查呼叫路徑：

| 路徑 | 核對結果 |
|---|---|
| `app/services/dashboard.py` 推薦監控 | `production_behavior_query()` 在排序及 1000 筆上限前送入 MongoDB 查詢。 |
| `app/store_v4.py` 前台推薦 | 同一查詢在排序及 50 筆上限前排除 synthetic；`ai_workflows.storefront_recommendations()` 再用 `production_events()` 過濾。 |
| `app/store.py` legacy 首頁 | 讀取端有相同過濾；legacy 商品瀏覽／購物事件寫入**未**加 synthetic metadata。此路徑非現行 `DATA_MODE=v4`，但不能照 JEFF 說明宣稱 legacy 寫入已標記。 |
| `app/services/member_events.py` | 只有配置 `BEHAVIOR_SYNTHETIC_BATCH` 時才將讀取事件加上 synthetic、batch ID 與 attribution 排除。 |
| `VibeCart_AI/services/sku_cart_service.py` | 沿用設定的 batch metadata；所有 `PURCHASE` 都加 `exclude_from_attribution=true`，不只示範結帳。這意味現行正式購買事件也不會進歸因，仍需另訂正式歸因政策。 |
| `scripts/verify_v4_test.py` | 驗證工具只清理它建立的測試資料；不是正式推薦 consumer。 |

已追蹤的網站與共用服務中，尚無 `recommendation_logs`、`user_preference_scores` 的正式處理器或排程作業。PR #5 的 `preference_service.py` 不在 #21，且未過濾 synthetic；**不納入本版**。T5 六個變更檔沒有新增 behavior event 讀寫。

離線 `test_behavior_scope.py` 與 HEN 測試涵蓋 synthetic 在 sort／limit 前排除；但 Cloud Run 的 PR #21 預覽是唯讀並封鎖 `/admin`，正式流量仍為較舊的 revision。尚未取得**每一個實際部署 consumer／排程**同版隔離的遠端讀回，故 **D4 不可正式匯入**，D1～D3 也不重匯。JEFF 的「可以匯入」只作程式審查意見，不能取代此閘門。

## 3. 展示與功能邊界

- **已實作，限離線或所述範圍驗證**：後台版型、營運總覽、推薦監控、四個固定雲端洞察問題、Local 相似商品、AI 比較、白名單 v1 與模型失敗規則退回。自由提問有伺服器旗標與防護，但預設關閉。
- **JEFF 本機 T5 紀錄**：BGE 對 324 個可售商品量測；Claude 三回九次呼叫。`docs/AI_DASHBOARD.md` 留有數值和限制，但原始腳本未提交，本輪未重做付費呼叫，也沒有同版線上管理員／真模型驗收。簡報須標「JEFF 本機 Atlas 唯讀實測」及來源 SHA；不可寫成公開網站已啟用 AI。
- **只有規格，未實作**：D5 商品／SKU／訂單／會員寫入、180 天稽核及重送紀錄、批量 request_id、6+4 推薦、計分衰減、排程、回購／跨類及「猜你喜歡」。取消／退款與刪除不列入 v1。

## 4. 由專案負責人接手的決定

1. **線上 Claude 暫不開啟。** 現行 `cloud_runtime.py` 明確關閉 AI；PR #21 預覽禁止後台，且未做同版管理員、真模型和費用／密鑰遠端驗收。先以本機 T5 示範或截圖；若未來要開，另交雲端依賴、Secret Manager、明確旗標、預覽／正式版與回退測試，不能只填環境變數就宣稱已上線。
2. **BGE 僅本機展示**，線上維持關閉；自由提問保持關閉，只展示四個固定問題；PR #5 截止前不採用。
3. **D5 與後台全裝置撤權**：簡報標示 D5 為規格。HEN 已提供可信的 `revoke_user_sessions()` 函式，但沒有已驗收的管理員寫入頁面；本輪不單獨開未具完整權限、CSRF、交易與稽核的撤權入口。
4. **S06～S08 截圖放簡報 PR #19** 的素材流程；應以本機同版管理員登入拍攝、記錄 commit SHA、執行環境、日期和使用的展示資料，不能把零流量唯讀預覽標成後台線上畫面。本輪沒有合格截圖可交，不補空白占位圖。
5. **10/14 額外兩筆示範訂單保留**，不刪除、不重匯 D1～D3。展示雲端洞察手動選 `2026-09-29`～`2026-10-05` 並顯示比較區間／示範資料提示；不把預設近七日的 2 筆當作整體營運。共用弱密碼不得寫入文件或截圖；展示後以受控流程更換並撤銷舊 session。
6. #12～#15 的內容雖在 PR #21，只有 #21 經審查合併 `main` 後才處理重複 PR。PR #21 仍維持草稿，待 [最終驗收缺口](SAM_PR21_ACCEPTANCE_2026-10-16.md) 補齊。

## 下一個可驗收步驟

以 #21 合併後程式建置**新**的零流量、不可變預覽映像，讀回 revision／digest；在可授權且不污染正式資料的環境實測匿名、會員、管理員、交易、撤權及各 consumer 的 synthetic 排除，保存預期與實際結果。完成前保留現行正式流量與 D4 閘門；部署、HTTP 200、CI 綠燈均非最終簽收。
