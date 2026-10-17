# D4 行為事件匯入閘門與遠端驗收｜2026-10-17

**2026-10-18 00:23（Asia/Taipei）更新：**[PR #47 的同版私有探針](REN_D4_PRIVATE_PROBE_2026-10-17.md)已通過前台推薦／管理監控的正常與 1,001 synthetic 對照，五集合探針殘留 0、臨時 IAM role 已撤。正式與私有同為 main `80513a951d0dff67fd47a153a45918522b5ffbb5` 映像；43 區盤點有 42 區可讀、1 區明確地區政策拒絕，完整範圍見[盤點更新](D4_DEPLOYED_CONSUMER_INVENTORY_2026-10-17.md)。正式 D4 的 1,240 筆規劃事件已通過 preflight 與 abort dry-run，batch 仍 0；D1～D3 與額外 2 demo 訂單保留。

目前下一步是把已發布的不可變證據填入 `consumer_checks`，覆核部署／地區範圍後才進行 apply、verify 與冪等重送。**本次尚未 apply，不能標 D4 已匯入或全站最終簽收。以下為較早歷史快照，舊版 revision 與「缺正常／synthetic 對照」須依本次更新校正。**

同日後續 [PR #21 同版遠端預覽](SAM_PR21_REMOTE_PREVIEW_2026-10-17.md)已建立零流量唯讀修訂 `vibecart-web-00009-xfq`，再次唯讀讀回 D4 0、原 D1～D3 訂單 3,000、額外示範訂單 2。Cloud Run 全區服務清單只有一項；Job 43 區中 42 區無項目、1 區 403，Functions／Scheduler API 未啟用，資產總清單仍不完整。新修訂拒絕登入、後台、購物與寫入，因此**沒有**對前台／後台 consumer 執行 synthetic 與正常對照。D4 閘門不變。

本頁記錄 PR #21 的程式缺口、已修範圍及正式匯入前的遠端證據。**目前不得執行 D4 apply**。D1～D3 的 600 位停用合成會員、3,000 筆示範訂單與 8,969 筆明細保留，不重匯；額外兩筆示範訂單也保留。

**11:40 更新**：SAM 已代盤點 [實際部署 consumer 與排程](D4_DEPLOYED_CONSUMER_INVENTORY_2026-10-17.md)：正式流量仍由較舊 `vibecart-web-00007-m9k` 承接；Cloud Run Jobs、Pub/Sub 訂閱為空，Scheduler／Functions 等 API 未啟用。計分排程與正式歸因目前未部署；本輪調整匯入證據格式，允許這兩項以有範圍和檔案雜湊的 `not_deployed` 雲端盤點記錄，但管理員監控與前台推薦仍須同版遠端合成／正常事件對照。正式 revision 來源與此對照仍缺，**閘門維持未通過**。

2026-10-17 10:49（Asia/Taipei）以 MongoDB Atlas 連接器唯讀聚合讀回：指定 D4 batch 的 `behavior_events` 為 **0**；原 D1～D3 batch 的 `orders` 為 **3,000**；不屬原 batch 且 `is_demo=true` 的 `orders` 為 **2**。此查詢未寫入資料，也沒有證明 consumer 隔離。

## 程式原因與本輪修正

1. legacy `app/store.py` 的瀏覽、加購、結帳事件原先都沒有 `metadata`。本輪讓三個寫入點使用伺服器端的 synthetic metadata；有 `BEHAVIOR_SYNTHETIC_BATCH` 時使用指定批次，沒有設定時使用 `legacy-demo`，一律排除正式歸因。legacy 路徑不在現行 Cloud Run `DATA_MODE=v4` 的服務流量上，但本機或舊版部署不得再漏標。
2. v4 `sku_cart_service.py` 原先按 `event_type=PURCHASE` 一律排除歸因。本輪改成按結帳產生的 `order.is_demo` 決定。**現行 checkout 仍固定建立 `is_demo=true` 訂單**，所以所有由此路徑產生的購買事件仍排除歸因；不得把這次改動寫成正式購買歸因已啟用。未來若要正式訂單，須另定付款、庫存、退款、稽核及權限契約並驗收。
3. `behavior_import.py` 原本接受四個 consumer 的純 `passed` 字串。本輪要求每項留下來源完整 SHA、映像 digest、revision、遠端證據網址、檢查時間、合成輸入數、合成可見數 0 與正常事件可見數。格式檢查只防止空泛的完成聲明，**不能取代實際遠端讀回或人工核對**。

## 實際 consumer 盤點與缺口

| 類別 | 本版程式 | 遠端同版證據 |
|---|---|---|
| 管理員推薦監控 | `app/services/dashboard.py` 在排序及 1000 筆上限前套用 `production_behavior_query()` | 缺管理員可授權環境、同版 revision/digest 與合成／正常事件對照讀回。現有零流量預覽禁止 `/admin`。 |
| 前台推薦 | `app/store_v4.py` 在排序及 50 筆上限前過濾，`ai_workflows` 再做記憶體過濾 | 缺同版登入會員的遠端對照讀回；現有零流量預覽只允許匿名讀取。 |
| 計分排程 | PR #21 未查到正式 `user_preference_scores` 寫入 worker／job；PR #5 候選不在本版 | 缺雲端服務／排程實際部署清單及「未部署」核對；不得用本機原始碼推定遠端不存在。 |
| 正式歸因 | PR #21 未查到正式 `recommendation_logs` 歸因 consumer | 同上；示範 PURCHASE 排除歸因不等於正式歸因驗收。 |
| legacy 事件寫入 | 本輪補伺服器端 synthetic metadata | 需核對是否有任何 legacy revision 承接流量；本輪沒有遠端路由／版本證據。 |

## 可執行的驗收順序

1. 從雲端管理端讀回 Cloud Run 各 revision、流量比例、Job／Scheduler、Hosting rewrite 及其他實際 consumer，逐項對應完整來源 SHA 與映像 digest；保留讀回時間和不可變證據。不能只檢查 PR、HTTP 200 或單一服務。
2. 在隔離且可撤回的資料與帳號範圍，使用明確標記的 synthetic 與正常對照事件，對每個實際部署 consumer 驗證 synthetic 在排序／limit 前被排除、正常事件可見，並核對寫入目的地未被 synthetic 污染。留下查詢、預期、實際及清理讀回。不可拿 D4 正式批次作探針。
3. 對未部署的計分／歸因工作，保存 Cloud Run Job、Scheduler 與相關服務清單的管理端讀回，並在正式啟用時重新驗收。任何新 consumer 都要納入盤點。
4. 將每項通過的證據填入 `behavior_import.py` 所需的 `consumer_checks`，由 SAM 核對網址內容、revision、digest、source SHA、時間及部署清單後，才可考慮 D4 preflight、交易 dry-run、apply 與正式讀回。只改 JSON 不能視為驗收。

本輪本機測試：最初未啟動 replica set 時網站 `175 passed, 3 skipped`；啟動無憑證、一次性 localhost MongoDB replica set 後，同版完整網站測試為 **`178 passed, 0 skipped`**，含交易回滾、最後庫存並發及撤權回滾；D4 匯入／fixture 完整測試 `26 passed`。測試命令與環境見 [PR #21 同版驗證紀錄](SAM_PR21_ACCEPTANCE_2026-10-16.md)。目前只完成程式修正、本機驗證及上述 Atlas 唯讀計數；**未部署新修訂、未建立示範帳號、未向 Atlas 寫入 D4、未驗真 Claude/BGE、未啟用自由提問**。D5 繼續標為規格，PR #21 保持草稿。
