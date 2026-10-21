# #152 前台效能與操作改善

本輪依使用者要求接續 #152，優先改善登入及頁面回應，再補商品瀏覽與購物操作。原始回報、截圖與前一次七個 PR 發布歷史保留於 [JEFF 回報](JEFF_FRONTEND_ISSUES_2026-10-21.md) 與 [優化系統](優化系統.md)。本文件將本機測試、GitHub、部署與正式操作證據分開記錄。

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

## 正式舊版量測基準

2026-10-21 21:42 起，從同一 Windows 工作站對公開 Firebase 網址做循序 Requests Session 量測。每項 8 次，第一筆另列、後 7 筆取中位數及最大值；登入 POST 不跟隨跳轉，登入後頁面另量。這是短期暖機樣本，不是冷啟動保證、負載測試或 p95 SLO。舊正式 revision `vibecart-web-jeff-f616-1021`，digest `35998718…`。

| 路徑／動作 | 舊版暖機 TTFB 中位數（ms） |
| --- | ---: |
| 健康頁 | 123.5 |
| 登入頁 | 138.1 |
| 匿名首頁 | 1961.0 |
| 乳品與蛋品篩選 | 1960.0 |
| 商品頁 | 1980.3 |
| 會員登入 POST | 1374.4 |
| 會員登入後首頁 | 2284.8 |
| 管理員登入 POST | 1363.9 |
| 管理員後台首頁 | 1642.2 |

使用本輪專屬、三小時到期的兩個受控測試身分。憑證只存使用者私有 DPAPI 加密檔，不寫入 Git、日誌或報告。正式資料清理與獨立讀回在驗證後記錄。

## 交付狀態

本機完整網站＋稽核 migration 回歸 **449 passed／0 skipped**（99.10 秒），包含真 localhost replica set 交易。連線池併發、fork 後隔離、初始化失敗重試／原 client 恢復、庫存即時讀取、相關商品界線、失效表單拒絕，以及評價後推薦重新出現均通過。本機瀏覽器已驗缺貨停用、單一規格預選及數量上限。GitHub CI、正式部署、新舊比較及公開站操作將於完成後填入；此段不代表已部署。

English summary: Reuse a lazy, fork-safe per-worker MongoClient; preserve live authorization/stock/review reads. Bound product-detail catalog work, batch cart reads, simplify storefront controls, and keep rating/recommendation eligibility unchanged. Warm public response samples are reported separately from cold starts and browser acceptance.
