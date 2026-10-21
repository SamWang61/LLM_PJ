# 營運後台與 v4 測試交接 / Dashboard handoff

**2026/10/20 PR #5接續**：[離線持久快照操作](PREFERENCE_SCORING.md)是前台請求時計分之外的opt-in工具，JEFF主責、SAM整合。現行6＋4分類會衰減並支援文字搜尋；快照version1分類維持raw權重上限70／30、商品逐事件衰減、SEARCH僅明確ObjectId，數值不保證相等。新工具不接前台或啟排程，本輪不連Atlas；10/2的50項與Atlas驗證只作歷史。下方較早「完整6＋4仍屬後續」描述保留原交付日期，現況分別讀[6＋4對話決議](../討論的相關記錄/商品評價與猜你喜歡6加4推薦_對話決議_2026-10-18.md)與本輪快照PR結果。

<!-- SAM MAIN PREVIEW 20261018 BEGIN -->
**2026/10/18 17:34 SAM 最新main無流量預覽**：[部署與驗收](SAM_MAIN_PREVIEW_2026-10-18.md)。來源`20ee040`、52檔封裝／GCS讀回一致、AI build三步SUCCESS；私有真BGE、Claude四固定問題／快取、角色／交易／1001 synthetic及停用退回已驗，fixture清理0。Key版本1 Enabled，只引用於私有預覽，自由提問false。**正式19／私有base11仍100%舊版，最新main只在0% tag；Hosting未重發，V5仍2/14完成。**
<!-- SAM MAIN PREVIEW 20261018 END -->

> 2026/10/18 16:30 最新：[SAM三PR整合與驗收](SAM_JEFF_PR82_84_ACCEPTANCE_2026-10-18.md)。#82～#84本輪已完成程式測試；舊段落保留交付時序，不代稱已部署或線上AI驗收。

> 最新責任：AI／後台由 JEFF 負責；SAM 負責資料庫與測試。下文保留先前交付的技術與合併紀錄，不再代表現行分工。見 [現行分工](TEAM_OWNERSHIP.md)。Current ownership supersedes historical delivery attribution.

## 分支與負責人 / Branch ownership

先前交付紀錄：SAM 曾完成 AI 後台與 Atlas v4 連線交接。`feature/ai-dashboard` 建在 `feature/flask-sku-ai-integration` 之上；[PR #3](https://github.com/SamWang61/LLM_PJ/pull/3) 與 [PR #2](https://github.com/SamWang61/LLM_PJ/pull/2) 已依序合併，功能已進入 main；詳見 [合併與連線管理紀錄](MERGE_RECORD_2026-10-02.md)。現行責任以 TEAM_OWNERSHIP.md 為準。

合併方向：`feature/ai-dashboard` → `feature/flask-sku-ai-integration` → `main`。本次起點為整合提交 `bbb8e9c`；不用重建分支、強制推送或覆蓋同學工作。父分支進展時先 fetch，再 merge 父分支並重跑測試。

SAM previously delivered this stacked feature; current AI/admin ownership belongs to JEFF. Both dependent PRs have been merged in order; the delivery is now on main.

## 目錄責任 / File ownership

| 路徑 | 用途 / Purpose |
|---|---|
| `MuscleCore分析資料/website/app/admin.py` | 後台權限與篩選路由 / Admin routes |
| `MuscleCore分析資料/website/app/services/dashboard.py` | 日期、營收、庫存與行為監測 / Dashboard queries |
| `MuscleCore分析資料/website/app/services/ai_workflows.py` | AI 彙總範圍、快取與退回 / Summary workflow |
| `MuscleCore分析資料/website/app/templates/admin/` | 後台頁面；`layout.html` 為共用版型 / Admin views and shared layout |
| `MuscleCore分析資料/website/app/static/css/admin.css`、`static/js/admin.js` | 後台專用樣式與互動（不改前台 `main.css`／`base.html`） / Admin-only assets |
| `MuscleCore分析資料/website/tests/test_dashboard.py` | 範圍、權限與金額測試 / Offline tests |
| `MuscleCore分析資料/website/tests/test_admin_layout.py` | 共用版型、KPI 口徑、篩選同步與推薦政策測試 / Layout tests |
| `MuscleCore分析資料/website/app/services/ai_payload.py` | AI 白名單 v1 伺服器端彙總 / Whitelist v1 aggregation |
| `MuscleCore分析資料/website/tests/test_ai_insight.py` | 雲端洞察：白名單、intent、防護、退回與量測測試 / Insight tests |
| `MuscleCore分析資料/website/app/services/local_ai.py` | Local BGE 相似商品與向量更新 / Local similar products |
| `MuscleCore分析資料/website/tests/test_local_ai.py` | Local 推薦：排序、可售過濾、模型缺失、CSRF 測試 / Local AI tests |
| `MuscleCore分析資料/website/app/services/ai_compare.py` | Local vs Cloud 實測比較 / Measured comparison |
| `MuscleCore分析資料/website/tests/test_ai_compare.py` | AI 比較：中位數、未量測、成本設定測試 / Comparison tests |
| `scripts/verify_v4_test.py` | 真實 Atlas 讀回及可清理測試 / Live verification |

保留原始架構、歷史報告與 migration；不改動已執行 migration 的 checksum。舊全量清冊保留為歷史快照；本次交付清冊另存 `docs/inventory/ai-dashboard.csv`，不把缺少本機大型附件的 worktree 當成全量來源。

Existing module paths and migration history are preserved. The scoped manifest supplements the historical full inventory.

## 已實作行為 / Implemented behavior

- 後台需有效管理員權限；每次請求讀回角色，寫入請求驗證 CSRF。
- 預設最近 100 筆；可指定台北日期，含結束日，最多 366 天／5,000 筆。超額顯示錯誤，不提供截斷後的區間統計。
- v4 可包含、排除或只看示範訂單；有效營收只計 paid 且未取消的訂單，金額保留 Decimal 精度。
- 每日營收、平均客單、區間熱銷與最近訂單共用篩選；每日表只列有有效訂單的日期。低庫存為目前狀態，不是歷史庫存；顯示總數及最多 100 個 SKU。
- 摘要只在按鈕提交時產生；快取區分日期與示範篩選，失敗或未啟用模型時顯示規則摘要。
- 推薦監測顯示最近 1,000 筆事件的前 20 組統計；不冒充點擊率／轉換歸因。資料庫推薦政策與現行執行權重分開呈現。
- legacy 保留既有未取消訂單與商品累計排行口徑，不稱為付款確認報表。

### 2026-10-09 後台共用版型（JEFF，T1／R05）

- 依設計規格 v1.1（PR #8 `docs/JEFF_ADMIN_UI_DESIGN.md`）第 4 節：獨立後台頁首（管理員、回商城、登出，不顯示購物車）、左側導覽（目前頁 `aria-current`）、系統狀態燈（資料庫／BGE／雲端 LLM，燈號旁有文字）。尚未實作的頁面在導覽中標示「尚未開放」，不連到不存在的路由。
- 狀態燈只反映設定層級：綠＝已設定／已載入、黃＝未安裝或未設定而退回規則、灰＝未啟用；不代表模型呼叫已成功。
- RWD：≥ 900px 側欄；620–899px 頂部可橫向捲動分頁列、狀態移至頁尾；< 620px 漢堡選單、KPI 一欄、按鈕全寬、表格橫向捲動。
- 懸浮提示由 Flask `flash` 驅動：成功 3.5 秒、錯誤 6 秒，滑鼠移上暫停。
- 營運總覽：KPI 改為「有效／全部訂單」（分母只套日期與示範篩選）；零有效訂單時平均客單顯示「—」，送給摘要模型的 `average_order_value` 為 `null`。每日有效營收加純 CSS 長條圖（高度相對同一篩選結果的最高日），表格保留於下方。範圍內含示範訂單時頁首標示「示範資料 n 筆」。
- 推薦監控：權重表改讀 v4 `recommendation_policy`，依權重排序並附中文名稱；明示前台規則基線尚未改用此政策（待 T7）。
- `POST /admin/summary` 與既有測試不變；新增 11 項離線測試，共 66 項通過。瀏覽器以本機 mongomock 預覽檢查桌機／平板／手機版面，未連線或寫入 Atlas；以私有 admin 帳號登入真實資料的畫面驗收待 D6 帳號（R04）。

### 2026-10-09 AI 板塊 B：雲端洞察 `/admin/ai/insight`（JEFF，T2／R09）

- **資料**（`services/ai_payload.py`，依 SAM 白名單 v1）：伺服器重新彙總本期與緊接前期等長的比較期（各 1–366 台北日）。內容包含 totals（全部／有效訂單、有效營收、平均客單，零有效單為 `null`）、程式算好的變化率（基期為零時 `null`）、補零的 daily，以及 products（最多 100 筆，依 intent 排序並標示截斷）。products 每個商品一列，取最低價可售 SKU，欄位為白名單的 product_id、name、sku_id、price、stock_quantity、safety_stock、valid_sold_units、promotion_eligible（無成本資料一律 `null`），另加契約補充說明的 `available_quantity`。候選只計 active、可推薦，且 SKU active、`available_quantity>0` 的商品，被排除的數量寫入 warnings。每期先計數，超過 5,000 單回 `range_too_large`，不截斷統計。不含任何會員欄位或原始訂單。
- **提問**：4 個預設 intent（`period_compare`、`replenishment`、`promotion`、`revenue_change`）加自由輸入。按預設問題時不會帶出輸入框文字。自由輸入已實作的防護（設計規格 12.2 待與 SAM 確認的 6 點）：(1) 300 字上限並去除控制字元；(2) system prompt 限定只回答本店營運、只依資料，非營運問題固定拒答；(3) 問題放在 `untrusted_question` 欄位並標示為不可信輸入；(4) 偵測 Email、手機／市話、身分證格式就拒送（422）；(5) 呼叫紀錄只記 intent、耗時與 token，不記問題全文；(6) 每位管理員每分鐘上限 `AI_INSIGHT_RATE_LIMIT`（預設 6 次，超過回 429）。
- **輸出**：顯示模型、耗時、輸入／輸出 token、資料範圍與「請人工核對」，模型輸出一律 HTML escape。「送給模型的資料」`<details>` 顯示的就是送進 prompt 的同一個 JSON 字串，並依狀態標示：本次實際傳送、快取（原始請求內容）、已送出但呼叫失敗、未送出。相同請求 5 分鐘內走快取。
- **退回**：未啟用、未設定 Key／模型、逾時、服務錯誤時，改用同一份 payload 算出的規則答案，標示「規則退回 · 原因類型」，不顯示例外內容。「營收為什麼下滑」的規則答案只列數字變化，並寫明無法判定原因。
- **共用邏輯**：營運總覽的 AI 摘要與雲端洞察共用 `run_claude`（呼叫、量測 token／耗時、輸出驗證、失敗分類）。總覽摘要的資料仍是原本的 `summary_metrics`（支援「最近 100 筆」範圍）。程序內保留最近 100 次呼叫的量測，供 T4 比較頁使用。
- 驗證：新增 26 項離線測試（假模型，共 92 項通過），涵蓋 366／367 日（閏年）、5,000 單上限（以 monkeypatch 縮小上限測邊界）、零資料、零基期、demo 排除、白名單不含個資、escape、預覽與實際送出內容相同、防護拒送不呼叫模型、CSRF、未知 intent、快取、限流與失敗退回。瀏覽器以 mongomock 加假模型預覽，未呼叫真實 API、未連線 Atlas。**真實 Claude 對 4 個 intent 的正確性尚未實測（T5）**。

### 2026-10-09 AI 板塊 A：Local 相似商品 `/admin/ai/recommendation`（JEFF，T3／R09）

- **選商品**：下拉選單與 Top 5 只包含上架、可推薦，且至少一個 SKU 為 active、`available_quantity>0` 的商品，並依分類分組。基準商品本身排除。價格取可售 SKU 的最低價，下架或沒庫存的 SKU 價格不影響顯示。
- **模型輸入**：商品名稱、大／小類別名稱、摘要、描述與標籤，沿用 `product_text`，可在頁面「模型輸入文字預覽」展開查看。`category_path` 存的是分類代碼，對語意比對沒有幫助，所以改從 `categories` 讀取分類名稱。
- **相似度**：同一個 BGE 模型為每個商品產生向量，再算基準商品與其他商品的 cosine 相似度，顯示 Top 5 的數值與水平條（`role="meter"`）。另顯示處理時間與快取命中數（沿用 `CachedEmbeddings`，新增 `cached_count`、`clear`）。圖片取 `image_urls[0]`，沒有圖片時用商品名稱前兩字佔位。
- **「更新商品向量」**：POST 並驗證 CSRF，清除快取後全部重算，以懸浮提示回報筆數與耗時，再導回原本選的商品。
- **模型不可用**：套件未安裝或模型檔案未下載時，顯示黃色提示與安裝／下載指令，**不顯示假結果**，也不顯示例外內容。這個後台頁面不受前台開關 `AI_RECOMMENDATIONS_ENABLED` 限制；狀態燈的 BGE 文字會同時標示前台是否啟用。
- 每次相似計算與向量更新都記入程序內量測（provider `bge`），供 T4 比較頁使用。
- 驗證：新增 12 項離線測試（假 Embeddings，共 104 項通過），涵蓋排序、Top 5、排除自己、下架／不可推薦／缺貨／停用 SKU 排除、最低可售價、快取命中、模型缺失與載入失敗、CSRF、空資料、權限。瀏覽器以 mongomock 加假 Embeddings 預覽版面。**真實 BGE 的相關性與延遲尚未實測（T5，需先安裝 `requirements-ai.txt`）**。

### 2026-10-09 AI 比較 `/admin/ai/compare`（JEFF，T4／R09）

- 比較表依設計規格第 5.4 節，比較延遲、成本、資料是否離開本機、推論是否需網路、擅長與限制。
- **延遲**：每一側取最近 10 次成功呼叫的中位數。Local 只計「相似商品」計算，不計更新向量；Cloud 計雲端洞察與總覽 AI 摘要的實際 API 呼叫，快取命中與失敗都不計。
- **成本**：Cloud 顯示最近幾次的平均輸入／輸出 token。只有設定 `CLAUDE_INPUT_USD_PER_MTOK`、`CLAUDE_OUTPUT_USD_PER_MTOK`（每百萬 token 美元單價，預設空值）時才估算每次金額，不內建任何價格。
- **未量測**：顯示「尚未量測，請先到 A／B 執行一次」並附連結，不填示範數字。「推論不需網路」註明只指模型推論，網站讀 Atlas 與遠端圖片仍需網路。
- **呼叫紀錄**：列出最近 20 筆，含類型、intent、模型、耗時、token、快取命中，不含問題內容。紀錄在程序記憶體中，重新啟動會清空，多個 worker 時各自獨立。
- 新增共用 `duration` 篩選器（< 1 秒用 ms，否則用秒並取 1 位小數），取代 A、B 頁各自的 macro；手機寬度下頁首不換行，比較表改為橫向捲動。
- 驗證：新增 11 項離線測試（共 115 項通過），涵蓋未量測狀態、最近 10 次中位數、Local／Cloud 分開計算、只有設定單價才估算、紀錄不含問題文字、從 A 頁實際呼叫到比較頁、時間格式、權限。**真實延遲與 token 待 T5 實測後才會出現**。

### 2026-10-12 真實模型實測（JEFF，T5／R09）

**環境**：Windows 10、CPU；Python 3.13.3；`requirements-ai.txt`（torch 2.14.1+cpu、sentence-transformers 5.7.0）；資料讀自 Atlas `vibecart_ai`，**只做唯讀查詢**。實測腳本只放在本機，未提交；它直接呼叫 `services/local_ai.py`、`services/ai_payload.py` 與 `insight_answer`，和網站走同一段程式。比較頁的量測只保存在網站程序記憶體中，腳本是另一個程序，所以這些數字不會出現在 `/admin/ai/compare`。

**BGE（`BAAI/bge-small-zh-v1.5`，512 維）**

| 項目 | 實測 |
|---|---|
| 可售候選商品 | 324 |
| 模型載入（已下載後） | 5.0 秒 |
| 324 筆商品全部向量化（冷啟動、「更新商品向量」） | 7.6 秒 |
| 相似查詢（向量已快取 324/324） | 22～31 ms，8 次中位數 26.5 ms |

- **相關性**：從 8 個不同大類各取 1 個商品作基準，人工檢視 Top 5 共 40 筆。40 筆全部與基準同大類，37 筆同小類。跨小類的 3 筆仍屬合理鄰近：玉米粒罐頭對沙茶醬、純水對蘆筍汁、蠶豆對米豆。例如漱口水的 Top 5 是同品牌漱口水、牙膏、口腔噴劑等口腔清潔用品。
- **觀察**：同一商品的不同包裝（單入對箱購）分數最高（0.94～0.95）。後台「找相似」這樣是合理的，但之後做前台推薦（T8）時應考慮合併同商品的不同包裝。

**Claude（`claude-sonnet-5`，雲端洞察 4 個 intent，範圍 2026-09-29～10-05 對比 09-22～09-28，含示範訂單）**

| 回合 | 延遲 | 輸入 tokens | 輸出 tokens | 數字核對 |
|---|---|---|---|---|
| 第 1 回（原設定） | 8.8～10.6 秒 | 17,891～18,113 | 4 次都是 600，**全部被截斷** | 營收、訂單、變化率、每日、庫存範圍皆與送出資料一致；**1 處日期抄錯**（比較期寫成 09/22–10/28） |
| 第 2 回（修正後） | 7.5～8.6 秒 | 5,229～10,010 | 476～597，**皆未截斷** | 日期正確；每日最高／最低、促銷 50 筆銷量 0 與庫存 87～100 皆正確；**補貨回覆有 2 處問題**：誤稱 50 筆可售量皆為 3（實際含 40～43），並自行算出「缺口 7 件」 |

- **第 1 回後的修正**：
  - 雲端洞察的 `max_tokens` 改為 1200、逾時改為 45 秒（總覽摘要維持 600）。
  - 偵測 `stop_reason=max_tokens` 時，回覆下方標示「內容可能不完整」。
  - 送出的 JSON 縮排由 2 改為 1。
  - products 依 intent 限量：主管摘要與營收變化 20 筆、補貨與促銷 50 筆、自由提問 100 筆。
  - system prompt 要求日期照抄、不用 Markdown 標題；修正 prompt 中誤寫的「運動商品電商」。
  - 「營收為什麼下滑」改為列出兩期各自最高與最低的日期，不讓模型自己比較差異。
- **第 2 回後的修正**：
  - 補貨候選改由程式篩選，只送「可售量 ≤ 安全庫存」的商品。實際資料共 29 筆，可售量都是 3。
  - system prompt 明文禁止自行加減乘除產生新數字。
  - 2026-10-17 第 3 回以真實 Claude 驗證（只問補貨 1 次）：範圍自動移到 10/09～10/15，因 Atlas 新增 2 筆 10/14 的示範訂單，共 3,002 筆。延遲 20.6 秒，輸入 6,726、輸出 1,186 tokens，未截斷。回覆中的 29 筆候選、可售量 3、安全庫存 10、本期銷量皆為 0，以及點名的 9 個商品，全部與送出資料一致，**不再以偏概全，也不再自行計算差額**。仍有 1 處小瑕疵：說「其餘 23 項」，是 29−6 自行相減，數字正確但違反「不自行計算」。另外回覆長度超出 prompt 要求的 400 字，接近 1200 tokens 上限。
- **結論**：模型會正確引用程式算好的數字，但仍可能抄錯日期、以偏概全或自行計算，所以畫面上的「請人工核對」必須保留。請模型做「判斷或篩選」的部分，應盡量改由程式先做好。

### 2026-10-18 規則推薦改用 v4 權重（JEFF，B1）

- `services/recommendation.py` 原本使用舊權重（瀏覽 1、收藏 3、加購 4、購買 8），改為 v4 `recommendation_policy`：PURCHASE 4、ADD_TO_CART 3、SEARCH 2、PRODUCT_VIEW 1。
- v4 前台會讀取 active 的政策（`policy_weights`），缺少、負數、非數字、非有限數值或錯誤settings／weights結構均以預設值補上；legacy 用預設值，舊事件名稱（view／cart／purchase／favorite）對應到 v4 名稱。
- SEARCH 事件沒有商品 ID，改為以 `search_query` 比對商品名稱與分類，命中的商品加 2 分。
- `ai_workflows.py` 移除舊的事件名稱轉換；推薦監控頁的說明同步更新。
- B1原10項政策測試加SAM7項安全回歸，共17項。synthetic隔離保持；同輪B2已改個人推薦用personalization，監控／歸因仍用production，見下節。

### 2026-10-18 示範結帳計入個人推薦（JEFF，B2）

- **問題**：真實會員完成示範結帳後，PURCHASE 事件帶 `exclude_from_attribution`，原本前台推薦和推薦監控一樣把它排除，所以買完之後「猜你喜歡」沒有任何變化。
- **改法**：`behavior_scope.py` 新增 `personalization_behavior_query()`／`personalization_events()`，只排除 synthetic 批次（`synthetic`、`synthetic_batch_id`），保留示範結帳；前台推薦（v4、legacy、規則推薦、LangGraph 基線）改用它。
- **不變**：推薦監控與成效／歸因統計仍用 `production_*`，示範結帳**不計入**；synthetic 事件在兩種範圍都排除。
- 新增7項離線測試。16:22唯讀確認正式與私有服務均無BEHAVIOR_SYNTHETIC_BATCH；本輪未改雲端設定。

Taipei date filters and demo exclusions apply consistently to v4 revenue, daily totals, ranking and summaries. Inventory is current; recommendation events are bounded counts, not attribution metrics.

## 私有連線與啟動 / Private connection and launch

SAM 的本機 `MuscleCore分析資料/website/.env.v4-test` 已備妥有效 URI，且受 Git 忽略與 Windows 檔案權限保護。不要貼到 PR、文件、聊天或共用雲端。此設定使用既有 `vibecart_ai` v4 資料庫，**不是新建的隔離測試資料庫**。Atlas connector 需重新登入，但本機 PyMongo 連線可獨立驗證。

使用應用程式 readWrite 帳號；不使用 schema 管理帳號啟動網站。預設 checkout、BGE、Claude 皆關閉。既有環境變數優先於設定檔；切換環境時使用新的終端並重新登入網站。

```powershell
cd MuscleCore分析資料\website
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-test.txt
# 確認 SAM 私下配置的 .env.v4-test 已在本機，再啟動
.\run_v4_test.ps1
```

`run_v4_test.ps1` 透過 `APP_ENV_FILE` 選擇設定，不覆蓋原 `.env`。沒有設定檔就停止。不要執行 legacy seed 寫入 v4。測試帳號與資料會清理，因此驗證後不留下共用管理員帳密。

The ignored local profile contains the existing v4 connection. It is not a newly isolated database. Keep it private; default checkout and model flags remain disabled.

## 線上 AI 設定 / Online AI configuration（JEFF，2026-10-18，A1／A2）

**狀態：程式與建置設定已完成；SAM已實際建置精簡與AI映像、Gunicorn boot及真BGE斷網驗證。尚未執行Cloud Build／發布或部署；線上AI仍關閉。** 部署由 SAM 執行或授權，費用記在 `vibecart-llmai` 帳單；Claude API 費用由 JEFF 的 Key 負擔。

| 設定 | 位置 | 預設 | 線上建議值 |
|---|---|---|---|
| `AI_SUMMARY_ENABLED` | Cloud Run 環境變數（`cloud_runtime.py` 讀取） | `false` | `true` |
| `AI_RECOMMENDATIONS_ENABLED` | 同上 | `false` | `true`（只開 Claude 時 `false`） |
| `AI_FREE_QUESTION_ENABLED` | 同上 | `false` | `false`（展示只用 4 個預設問題） |
| `CLAUDE_MODEL` | 環境變數 | 空 | `claude-sonnet-5` |
| `ANTHROPIC_API_KEY` | Secret Manager 同名 secret，授權 `vibecart-web@` 讀取 | 無 | 由有權金鑰擁有人在Console新增版本 |
| `BGE_MODEL` | 環境變數 | `BAAI/bge-small-zh-v1.5` | 不變 |
| `INSTALL_AI` | Docker 建置參數（Cloud Build `_INSTALL_AI`） | `false`（映像與原本相同） | `true` |
| 記憶體／CPU | Cloud Run | 512Mi | 2Gi、CPU 2（只開 Claude 可先試 1Gi） |

- 三個 AI 開關只接受 `true`／`false`，其他值會拒絕啟動；開了 AI 之後，`CLOUD_PREVIEW_READ_ONLY=true` 仍擋 `/admin`。
- `INSTALL_AI=true` 會安裝 `requirements-cloud-ai.txt`（CPU 版 PyTorch，版本與 T5 實測相同），並在建置時把 BGE 模型下載到 `/srv/models`；執行期 `HF_HUB_OFFLINE=1`，搭配 `local_files_only=True` 載入。Cloud Build 會多跑一步離線載入檢查（日誌出現 `ai-image-ok`）。
- 建議流程：建置 → 建立空 secret 並授權 → JEFF 貼入 Key → 部署**零流量**修訂（tag `ai-preview`）→ 量測冷啟動、BGE、Claude 4 個預設問題 → JEFF 與 SAM 都同意後才切流量；舊修訂保留以便退回。
- **本機已驗／雲端待測**：本輪AI映像inspect大小505,795,251 bytes、快取build3.45秒、斷網2Gi／1CPU流程15.477秒；這些不是registry大小、Cloud Run冷啟動或整個容器peak。雲端實測仍待辦。
- **備案**：BGE 記憶體不足或冷啟動過慢時，部署 `AI_RECOMMENDATIONS_ENABLED=false`，只開 Claude（映像不需重建）；若今天不上線，簡報使用 T5 本機實測數字。
- **B3本輪已唯讀確認**：16:22正式19與私有11均未設定 `BEHAVIOR_SYNTHETIC_BATCH`；若日後誤設，真實會員事件將被標為synthetic並排除。
- **長期方案（B4，下一階段）**：商品向量離線批次計算存入 Atlas（schema 已有 `product_embeddings`，寫入需 SAM 同意），網站只做 cosine，降低記憶體與冷啟動。

English: The integrated source passed local builds, Gunicorn boot, and real offline BGE checks. Cloud Build, deployment, and real Claude acceptance remain pending; production AI stays off. Flags default to off and must be exactly true/false. The AI image (`INSTALL_AI=true`) bakes in CPU PyTorch and the BGE model. The Claude key lives in Secret Manager and is entered by JEFF. The recommended rollout is a zero-traffic revision with 2Gi memory, verified before any traffic switch, with Claude-only as the fallback.

## 推薦成效紀錄 / Recommendation attribution（JEFF，2026-10-21）

依設計規格第 5.5、7.3 節，把推薦監控預留的「曝光／點擊／加購／購買」接上 `recommendation_logs`（`services/recommendation_logs.py`）。

- **曝光**：登入會員在首頁或推薦片段看到 6＋4 時，每個非空區塊寫一筆紀錄（`PERSONALIZED`／`CROSS_CATEGORY`），內容為商品、位置、分數、理由代碼與 `algorithm_version`。30 分鐘內同一位會員看到完全相同的清單（例如切回分頁重新整理）只算一次。推薦卡片連結帶 `rec=<recommendation_id>`。
- **點擊**：從推薦卡片進入商品頁時，寫入 `clicked_product_ids`，同一筆 `PRODUCT_VIEW` 事件也帶 `recommendation_id`。只有紀錄屬於該會員、且清單裡確實有該商品才會記；偽造、格式錯誤或別人的編號一律忽略。
- **加購**：商品頁的加入購物車表單帶著同一個 `rec`，成功加入後寫入 `added_to_cart_product_ids`。
- **購買**：結帳後，對 30 天內曾加購該商品的紀錄寫入 `purchased_product_ids`；**示範訂單不計入**（與 B2 的歸因規則一致）。目前網站訂單都是示範訂單，所以購買數會是 0。
- **不記錄**：未登入訪客（schema 要求 `user_id`）、設定 `BEHAVIOR_SYNTHETIC_BATCH` 的測試環境（`recommendation_logs` 沒有可標示 synthetic 的欄位）、唯讀預覽。寫入失敗只記警告，不影響頁面、購物車或結帳。
- **推薦監控**：新增「推薦成效（最近 30 天）」，兩種推薦各列推薦清單、曝光、點擊、加購、購買、點擊率（點擊÷曝光）與點擊後加購率（加購÷點擊），分母為 0 時顯示「—」；沒有紀錄時顯示空狀態。
- **動到的前台檔案**：`store_v4.py`（首頁、推薦片段、商品頁、加入購物車、結帳）、`services/member_events.py`（`record_read_event` 新增可選的 `recommendation_id`）、`templates/store/recommendations_v4.html`、`templates/store/product.html`。前台排序與畫面不變，只多了連結參數與隱藏欄位。
- **驗證**：網站離線測試 323 passed／21 skipped（新增 `tests/test_recommendation_logs.py` 10 項：曝光與連結、30 分鐘不重複、點擊與加購、偽造編號、清單外商品、訪客與合成批次不記錄、購買只計非示範且需先加購、寫入失敗不影響頁面、監控漏斗與空狀態）。

## 驗證與剩餘界線 / Validation and limits

2026-10-02：38 項離線測試通過；真實 Atlas 的 27 集合、86 索引與五組整合檢查通過，測試資料筆數已恢復。離線測試涵蓋日期邊界、退款與取消排除、Decimal、空資料、超額查詢、CSRF、角色撤銷、摘要快取及輸出跳脫。真實 Atlas 結果以 [讀回報告](V4_TEST_VERIFICATION.json) 為準。

從倉庫根目錄執行讀回；`--smoke` 會寫入唯一識別的測試資料並清理，只可用於 SAM 已授權的 v4 測試環境：

```powershell
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/verify_v4_test.py --env-file 'MuscleCore分析資料/website/.env.v4-test' --smoke --report docs/V4_TEST_VERIFICATION.json
```

流程驗證註冊登入、購物車增刪改、結帳重送、管理員撤權、真實交易 rollback 與最後庫存併發。清理只使用本次產生的 ID，並比較執行前後集合筆數。報告不含 URI 或密碼，不執行歷史 migration。

完整 6+4 推薦、排程衰減／計分與批次統計仍屬後續工作；本次完成的是 SAM 的後台、連線與既有整合驗收。BGE 真實推論與 Claude API 已於 2026-10-12 實測（見上方 T5 小節）；手機全站 UAT 尚未驗收，不能把規則退回稱為模型成功。未提供模型憑證時不呼叫付費 API。

Earlier live checks exercised transactions with temporary owned fixtures. The T5 section above records JEFF's local real BGE and Claude calls against read-only Atlas data; same-revision Cloud Run administrator/model acceptance and scheduled recommendation processing remain unverified. No migration or production deployment was performed for T5.
