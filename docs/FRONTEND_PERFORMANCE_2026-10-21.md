# #152 前台效能與操作改善

本輪依使用者要求接續 #152，優先改善登入及頁面回應，再補商品瀏覽與購物操作。原始回報、截圖與前一次七個 PR 發布歷史保留於 [JEFF 回報](JEFF_FRONTEND_ISSUES_2026-10-21.md) 與 [優化系統](優化系統.md)。本文件將本機測試、GitHub、部署與正式操作證據分開記錄。

**正式交付（2026-10-21）**：[PR #166](https://github.com/SamWang61/LLM_PJ/pull/166) 經固定 HEAD CI 成功合併 `8741400`，21:59 新版承接正式 **100%**。本機 **449 passed／0 skipped**、候選 26 項檢查及公開站 18 組瀏覽器操作通過。會員登入 POST 暖機中位數 **1.374 → 0.583 秒**、匿名首頁 **1.961 → 0.715 秒**、商品頁 **1.980 → 0.597 秒**。測試資料清除後由獨立 Job 讀回 0；詳細時間、原始量測、來源 hash 與截圖見[去敏證據](inventory/frontend_performance_20261021/release-evidence.json)。

## 修改內容

| 回報 | 本輪處理 |
| --- | --- |
| F11／F04 | 每個 Flask app／工作程序共用延遲建立的 MongoClient；請求結束只釋放請求參照。Linux fork 後重設連線與鎖。移除每次請求多餘 ping，保留 `/health/ready` 的明確探測及 2.5 秒網路／連線池等待上限。 |
| F01 | 沿用上一輪重送身分驗證、防連點與一次點擊登出；失效 HTML 表單改用網站版型並提供回首頁／重新登入。錯誤 token 仍回 400。 |
| F09 | 商品頁以同小類最多 4 件的有界查詢取代整目錄上一項／下一項。標示「同分類商品」，為一般商品瀏覽，不改個人 6＋4 推薦規則。列表返回連結保留原頁碼／搜尋／分類。 |
| F02 | 無候選的推薦區塊收起；保留即時刷新容器，有新合格評價仍會顯示。沒有熱門退回、假星等或推薦門檻修改。 |
| F03 | 精簡首頁介紹，搜尋與分類集中在同一表單；下拉取代全部標籤攤開，保留清除篩選。 |
| F05／F10 | 一般商品、推薦與同分類共用商品卡，整張單一連結可用鍵盤操作；價格／操作位置一致，描述限制行數。 |
| F06／F08 | 規格隱去 SKU 代碼；選規格即顯示相應價格／庫存。數量支援加減與手動輸入，依可售量及原有 99 件上限限制。售完時停用選單／數量／加入購物車並明示補貨中，後端交易仍重查庫存。 |
| F07 | 商品標題縮至 24～28px，介紹保留換行並可收合，來源連結保留。 |
| F12 | 購物車加入商品圖片／規格／單價／小計／數量調整與摘要；空車提供繼續購物。商品與 SKU 以批次查詢讀取，保留原 revision／operation ID 與示範結帳。 |

連線池只共用資料庫傳輸，不快取會員、權限、Session、庫存、評價或推薦結果；每次請求仍讀取當前資料。首頁仍為目前小型目錄讀取完整候選來計算既定 6＋4，未加入會讓庫存過期的 60 秒快取。推薦設定的權重沿用同次已讀設定，省去一次重複查詢。

實作依 [MongoDB 官方多執行緒與 fork 說明](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/mongoclient/#concurrent-execution)：工作程序間建立獨立 client，程序內使用原生連線池。密碼雜湊成本、CSRF、目前裝置撤銷、交易提交前權限檢查及部署安全設定保留。

## 正式站新舊量測

2026-10-21 21:42 起，從同一 Windows 工作站對公開 Firebase 網址做循序 Requests Session 量測。每項 8 次，第一筆另列、後 7 筆取中位數及最大值；登入 POST 不跟隨跳轉，登入後頁面另量。這是短期暖機樣本，不是冷啟動保證、負載測試或 p95 SLO。舊正式 revision `vibecart-web-jeff-f616-1021`，digest `35998718…`。

| 路徑／動作 | 舊版暖機中位數（ms） | 新版暖機中位數（ms） | 縮短 |
| --- | ---: | ---: | ---: |
| 健康頁 | 123.5 | 131.5 | 無改善（+8.0ms） |
| 登入頁 | 138.1 | 143.3 | 無改善（+5.2ms） |
| 匿名首頁 | 1961.0 | 714.6 | 63.6% |
| 乳品與蛋品篩選 | 1960.0 | 701.7 | 64.2% |
| 商品頁 | 1980.3 | 596.7 | 69.9% |
| 會員登入 POST | 1374.4 | 583.3 | 57.6% |
| 會員登入後首頁 | 2284.8 | 1057.9 | 53.7% |
| 管理員登入 POST | 1363.9 | 564.6 | 58.6% |
| 管理員後台首頁 | 1642.2 | 662.5 | 59.7% |

新版於 22:00 起以相同公開入口、工作站及腳本量測，表中為 response-header TTFB；不含瀏覽器圖片載入／渲染。首頁預讀取得商品連結，首筆亦不視為冷啟動。使用本輪專屬、三小時到期的兩個受控身分；不同時點的個人行為資料可能不同，不把整頁差額全歸因於單一改動。健康頁與登入 GET 沒有資料庫工作，維持約 0.13～0.14 秒。

另在同一 Cloud Run Job、同一 Atlas 對相同「ping＋投影商品讀取」做 8 次對照，去首筆後每次新建 MongoClient 為 **912.1ms**，重用 client 為 **145.7ms**。這是連線生命週期的隔離證據，並非整頁時間。Cloud Run `minScale=0` 保留；冷啟動、長期尖峰與多使用者負載未在本輪量測。

## 交付狀態

本機完整網站＋稽核 migration 回歸 **449 passed／0 skipped**（99.10 秒），包含真 localhost replica set 交易。連線池併發、fork 後隔離、初始化失敗重試／原 client 恢復、庫存即時讀取、相關商品界線、失效表單拒絕，以及評價後推薦重新出現均通過。本機瀏覽器已驗缺貨停用、單一規格預選及數量上限；隨機測試庫獨立確認已移除，自有 MongoDB 與預覽程序已停止。

| 階段 | 實際結果 |
| --- | --- |
| GitHub 程式 | PR #166 HEAD `d12333343ed178d60ffd669500f0db77e1937055`，[PR CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39611688463) 與 push CI 成功；21:55 合併 `87414002009524913413ae2af9b4ec6a76c72979`，[main CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39612225731) 成功。 |
| 建置 | Cloud Build `56cce79c-2271-4acc-8b09-cd87d56b4f2d` SUCCESS；75 runtime＋17 稽核來源逐檔比對固定 Git 提交。UID 10001、離線 BGE 512 維、AI import 及 health/live 均通過。 |
| 映像／正式修訂 | `sha256:b62b7ff27f7e31b2fcdc10a35b5c921457842847b3ebe5a80282165255c1160f`；`vibecart-web-perf-8741400-1021`，Ready／Active／Healthy。 |
| 候選 | 先建 0% 候選，26 項會員／管理員登入、重送身分檢查、角色邊界、CSRF、登出與舊 Session 拒絕、商品及後台頁、active schema 檢查通過。 |
| 切換 | **21:59:23** 發布，21:59:29 控制平面確認新修訂唯一 100%；後續讀回仍相同。原 `vibecart-web-jeff-f616-1021` 保留 0% 作回退。 |
| 設定與 Hosting | VPC／ALL_TRAFFIC、服務身分、資源、縮放、AI 旗標及秘密引用設定指紋不變；IAM binding hash 相同。Firebase release `1792363722745000`／version `a33b77d8155885b8` 與既有 Cloud Run rewrite 沿用。 |
| 公開路由 | `web.app`、`firebaseapp.com` 各五個正常路由 200、GET logout 405；與瀏覽器互動證據分開列。 |

## 正式瀏覽器驗證

2026-10-21 **22:00～22:06**，由 Codex 在同一 Windows 工作站 IAB 對公開 Firebase 正式網址實際操作，18 組檢查通過。以下為原始 JPEG，未編修影像；精確時間、尺寸及 SHA-256 見去敏清冊。

| 操作 | 畫面結果與原圖 |
| --- | --- |
| 商城／篩選／完整商品卡 | 空推薦收起；下拉大類／小類、搜尋與分頁可用；第 2 頁進商品後返回仍保留分類與頁碼。[商城](inventory/frontend_performance_20261021/01-catalog.jpg)、[分類](inventory/frontend_performance_20261021/03-category.jpg) |
| 商品／庫存／規格 | 唯一可售規格自動選取、價格庫存一致；加減上限正確。既有缺貨品 0 庫存時所有購買控制停用；同小類最多 4 件。[商品](inventory/frontend_performance_20261021/04-product.jpg)、[缺貨](inventory/frontend_performance_20261021/02-sold-out.jpg) |
| 會員登入／推薦 | 正常登入，搜尋受控商品只得 1 件；已有行為時顯示 6 件個人推薦且保留預設星等標示，未建立假評價。 |
| 購物車／示範訂單 | 1 件單價 145，增至 2 件後小計與摘要均 290；移除後有空車入口。重加 1 件建立示範訂單，前台成功、後台讀到 145。既有示範流程的 paid 狀態不代表實際收款。[購物車](inventory/frontend_performance_20261021/05-cart.jpg)、[建立成功](inventory/frontend_performance_20261021/06-checkout.jpg) |
| 前後台一次登出 | 兩種版型均點一次即安全登出，無確認頁或 JS 對話框；重開 `/cart`／`/admin/` 均要求登入。[會員](inventory/frontend_performance_20261021/07-customer-logout.jpg)、[管理員](inventory/frontend_performance_20261021/10-admin-logout.jpg) |
| 失效表單 | 跨分頁留存登入表單，登出後送出仍被 CSRF 拒絕，顯示網站版型與回首頁／重新登入。[錯誤恢復](inventory/frontend_performance_20261021/08-expired-form.jpg) |
| 後台 | 管理員登入、營運總覽、商品管理與訂單列表可讀；既有唯讀限制保留。[後台](inventory/frontend_performance_20261021/09-admin.jpg) |

## 清理、日誌與範圍

22:06 同交易清除僅本輪擁有的 2 個使用者、34 個 Session、1 件商品／1 個 SKU、1 張示範訂單／1 筆明細、1 個購物車、5 筆 cart event、7 筆行為與1筆推薦紀錄。22:07 獨立唯讀 Job 確認 10 類範圍全部 **0**，目錄恢復 **336 商品／336 SKU**；active contract **30 集合／96 索引／8 migrations**、12 組關聯 0 orphan，既有 migration checksum 相同。本輪沒有新 migration、D1～D4 匯入或變更其他商品庫存。5 個自有臨時 Job 刪除後逐一讀回 404。

發布後日誌按固定起訖完整分頁讀回，5xx、資料庫與其他 ERROR 均 0。出現的 400 為刻意送出舊登入表單；405 為 GET logout 安全探針；404 為既有 `/favicon.ico` 缺檔。各次查詢的完整頁數、時間窗及 HTTP 分類保留於清冊，不把 HTTP 200 代替功能驗收。憑證僅由私有 DPAPI 檔在記憶體解密，沒有寫進 Git、截圖或公開日誌。

本輪完成 #152 的 12 項技術改善及上述正式操作驗證；JEFF／SAM／REN 本人簽收、真手機、第二台設備與整體 V5 關卡仍分列，V5 維持 **3／14**。未做長期壓力／冷啟動測試，首頁完整候選讀取仍可在目錄擴大時另作效能工作。若需回退，先核對舊修訂與資料相容性，將 `vibecart-web-jeff-f616-1021` 切回 100% 再驗登入與公開路由；本輪未回退。

## v5 簡報 GitHub 交付

使用者另要求推送的 [v5 簡報](../簡報文件/超市AI版_2026-10-18/VibeCart_AI_超市網購與AI系統_2026-10-18_v5.pptx) 已經 [PR #165](https://github.com/SamWang61/LLM_PJ/pull/165) 推送並於 **22:00:14** 合併 main `f76a3b4`；[main CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39612959409) 成功。14 張投影片、3,262,322 bytes，ZIP CRC 與 XML 解析通過；本機來源、遠端固定提交下載與 main Git blob 的 SHA-256 均為 `4aa9b13286fe98574d3dd648889545ad196d92cea9aebb9a143c794ad392d193`。內容原樣保留，非本輪重新製作或變更本人驗收狀態。

English summary: Reuse a lazy, fork-safe per-worker MongoClient; preserve live authorization/stock/review reads. Bound product-detail catalog work, batch cart reads, simplify storefront controls, and keep rating/recommendation eligibility unchanged. Warm public response samples are reported separately from cold starts and browser acceptance.
