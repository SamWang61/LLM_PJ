# JEFF｜管理後台 設計與版面規格 v1.3

> 建立：2026-10-03；定案：2026-10-05；v1.1 修訂：2026-10-09；v1.2 契約補充：2026-10-16；v1.3 同步實作與視覺：2026-10-21（Asia/Taipei）
> 負責人：JEFF（AI／管理後台，見 [TEAM_OWNERSHIP.md](TEAM_OWNERSHIP.md)）
> 狀態：**版面已定案**（決策見第 10 節）；第 7 節資料來源對照、第 12 節 D5／AI 契約回覆供 SAM 對接 v4 資料庫。
> v1.1 依 SAM 審查（PR #11 `docs/JEFF_PUSH_REVIEW_2026-10-07.md`）與契約提案（`docs/SAM_DATA_CONTRACT_2026-10-07.md`）修訂。
> 配套文件：[AI_DASHBOARD.md](AI_DASHBOARD.md)（既有後台實作與驗證）。
> v1.2 由專案負責人接續確認啟用與驗收門檻、保存期限及批量重送語義。第 7.5 節的數量是 10/09 歷史讀回；即時狀態先看 [CURRENT_CONTEXT.md](CURRENT_CONTEXT.md)。本文件是設計契約，不代表 D5 寫入、自由提問、真模型或 D4 已部署驗收。
> **v1.3（2026-10-21，JEFF）**：依 main `c66f731` 同步 10/12～10/20 已合併的實作（T5 真模型調整、線上 AI 開關與 AI 映像、v4 權重、個人推薦範圍、SAM 的 6＋4 與 #5 快照），更新第 2、5、7、11、12.4 節並新增第 13 節；第 8 節改為 10/21 定案的淺色數據看板 token（`admin.css` 尚未改版）。

---

## 0. 文件用途

- **開發**：依第 3～6 節版面、第 8 節視覺規範與第 11 節檔案對應實作。
- **資料庫對接（SAM）**：第 7 節列出每個畫面元素對應的 v4 集合與欄位，以及目前缺少的資料。
- 文件中的線框圖**不含任何示範數字**；`{欄位}` 表示由資料庫或執行結果帶入的值。
- 實作一律讀取 v4 真實資料；資料為空時顯示空狀態，不以假資料填充。

English summary (v1.3): Syncs the spec with merged work through main `c66f731` (real-model adjustments, online AI flags and image, v4 weights, the personalization scope, SAM's 6+4 ranking) and adopts the light dashboard tokens decided on 10/21, not yet applied to `admin.css`. Earlier summary: Admin layout and v4 field mapping with explicit KPI and sellable-SKU rules. Section 12 defines a separate release gate for administrator free-text questions, 180-day audit and idempotency-record retention, batch request IDs, and no admin-to-admin deactivation. D5 writes, live model inference, and D4 import remain separate acceptance items.

---

## 1. 設計目標

1. **Demo 一眼看懂兩條 AI 路線**：Local AI「找得準」、Cloud LLM「說得懂、看得深」，兩個板塊在導覽上獨立、視覺上可區分。
2. **數據可信**：每個數字標示資料範圍；AI 輸出標示來源（模型／規則退回）、耗時與「請人工核對」。
3. **沿用現有風格**：深色底、萊姆綠強調（`main.css`），不引入新框架。
4. **RWD**：桌機完整、平板可用、手機可讀（Demo 以桌機為主）。

---

## 2. 現況（main `c66f731`，2026-10-21）

| 頁面 | 路由 | 狀態 |
|---|---|---|
| 營運總覽 | `GET /admin/`、`POST /admin/summary` | ✅ 已實作（T1）：共用版型、有效／全部訂單 KPI、每日營收長條圖＋表、熱銷、規則／AI 摘要、低庫存、最近訂單 |
| AI 板塊 A｜Local 推薦 | `GET /admin/ai/recommendation`、`POST /admin/ai/recommendation/refresh` | ✅ 已實作（T3）；T5 本機真 BGE 實測 |
| AI 板塊 B｜雲端洞察 | `GET`／`POST /admin/ai/insight` | ✅ 已實作（T2）；4 個預設 intent；自由提問有旗標且預設關閉；T5 真 Claude 實測後調整（第 5.3 節） |
| AI 比較 | `GET /admin/ai/compare` | ✅ 已實作（T4）：只用實際呼叫的量測 |
| 推薦監控 | `GET /admin/recommendations` | ✅ 權重讀 v4 政策；曝光／點擊／加購／購買**未實作**（需 `recommendation_logs`） |
| 商品／訂單／會員管理 | `/admin/products`、`/admin/orders`、`/admin/members` | ❌ 未實作；導覽顯示「尚未開放」 |
| D5 後台寫入 | — | ❌ 未實作；SAM 的 `schema_d5_v1.py`（migration `20261018_07_admin_audit_receipts_v4`）為未啟用草案 |
| 線上 AI | Cloud Run | 🟨 程式與 AI 映像選項已合併（第 13 節）；Claude Key 版本 1 已建立，私有 0% 預覽已驗 BGE＋Claude。正式站是否開啟以 [CURRENT_CONTEXT.md](CURRENT_CONTEXT.md) 為準 |
| 視覺改版 | `static/css/admin.css` | 📝 10/21 定案淺色數據看板（第 8 節），**尚未實作** |

10/05 的舊版現況（無後台導覽、共用前台頁首、舊權重 1/3/4/8）已由 T1～T4 與 B1 解決，保留於 git 歷史。

---

## 3. 資訊架構

```
後台導覽（左側欄）
├─ 營運總覽            /admin/                      KPI、每日營收（圖＋表）、熱銷、規則摘要＋AI 摘要、低庫存、最近訂單
├─ AI
│  ├─ ◆ Local 推薦     /admin/ai/recommendation     AI 板塊 A：相似商品 Top 5、更新向量
│  ├─ ☁ 雲端洞察       /admin/ai/insight            AI 板塊 B：KPI 快照、快速提問、自然語言問答
│  └─ ⇄ AI 比較        /admin/ai/compare            Local vs Cloud 實測比較
├─ 監控
│  └─ 推薦監控         /admin/recommendations       權重政策、事件統計（之後加曝光／轉換）
└─ 管理
   ├─ 商品管理         /admin/products              列表、新增／編輯
   ├─ 訂單管理         /admin/orders                列表、明細、狀態
   └─ 會員管理         /admin/members               列表、狀態
```

- AI 摘要**兩處都保留**：營運總覽的「產生此範圍的 AI 摘要」沿用 `POST /admin/summary`；AI 板塊 B 使用自己的路由。兩者共用 `services/ai_workflows.py` 的摘要邏輯。
- 商品／訂單／會員管理**顯示於導覽**；路由未交付時須顯示「尚未開放」，不得連到 404。版面由本文件定義；JEFF 負責後台寫入功能，SAM 負責資料契約、migration 與驗收，REN 提供登入撤權及訂單／庫存接口（見第 12.3 節）。

---

## 4. 共用版型

### 4.1 桌機（≥ 900px）

```
┌──────────────────────────────────────────────────────────────────┐
│ [M] VibeInsight 後台                 管理員：{display_name} │ 回商城 │ 登出 │
├──────────────┬───────────────────────────────────────────────────┤
│ 營運總覽      │  EYEBROW                                          │
│ ─ AI ─────── │  頁面標題                          [主要動作按鈕]  │
│ ◆ Local 推薦  │  {資料範圍} · 模式 {DATA_MODE} · 讀取時間 {now}     │
│ ☁ 雲端洞察    │ ┌───────────────────────────────────────────────┐ │
│ ⇄ AI 比較     │ │ 內容區（panel 卡片）                           │ │
│ ─ 監控 ────── │ └───────────────────────────────────────────────┘ │
│ 推薦監控      │                                                   │
│ ─ 管理 ────── │                                                   │
│ 商品管理      │                                                   │
│ 訂單管理      │                                                   │
│ 會員管理      │                                                   │
│ 系統狀態      │                                                   │
│ ● 資料庫 {狀態} │                                                  │
│ ● BGE {狀態}   │                                                   │
│ ● 雲端 LLM {狀態}│                                                 │
└──────────────┴───────────────────────────────────────────────────┘
   側欄 220px                       內容最大寬 1180px
```

- 新增 `templates/admin/layout.html`，所有後台頁繼承；**後台使用獨立頁首**（管理員、回商城、登出），不顯示前台購物車。
- 系統狀態燈：綠＝可用、黃＝退回規則、灰＝未啟用；燈號旁必有文字。
- 目前頁面以萊姆綠左邊框標示（`aria-current="page"`）。

### 4.2 平板（620–899px）
側欄收合為頂部水平分頁列（可橫向捲動），系統狀態移到頁尾。

### 4.3 手機（< 620px）
頂部漢堡選單；KPI 一欄；表格保持 `.table-wrap` 橫向捲動；按鈕全寬。

### 4.4 操作提示
- 右上角懸浮提示：成功（綠）3.5 秒、錯誤（紅）6 秒，滑鼠移上暫停；以 Flask `flash` 訊息驅動。
- 表單欄位驗證錯誤顯示在欄位下方，並以 `role="alert"` 宣告。

---

## 5. AI 與營運頁面版面

### 5.1 營運總覽 `/admin/`

```
EYEBROW: VIBEINSIGHT AI
營運決策中心                                         [AI 洞察 →]
{資料範圍} · {示範訂單篩選}
┌ 篩選列：開始日期 │ 結束日期 │ 示範訂單 ▼ │ [套用] 重設 ─────────┐
┌──────────┬──────────┬──────────┬──────────┐
│ 有效營收   │ 有效／全部訂單 │ 平均客單 │ 低庫存品項 │
│ {revenue} │ {valid}/{all} │ {avg}   │ {count}   │
└──────────┴──────────┴──────────┴──────────┘
┌ 每日有效營收：長條圖＋表格 ─────────┬ 熱銷排行 Top 10 ─────┐
└──────────────────────────────────┴─────────────────────┘
┌ 營運摘要：規則摘要 ／ [產生此範圍的 AI 摘要]（POST /admin/summary）┐
┌ 低庫存明細 ──────────────────┬ 最近訂單 ───────────────────┐
```

- 查詢邏輯沿用 `services/dashboard.py`，只重新排版。
- 長條圖以純 CSS／inline SVG 繪製，不加套件；表格保留供精確數值與無障礙。

### 5.2 AI 板塊 A｜Local 推薦 `/admin/ai/recommendation`

```
EYEBROW: LOCAL AI · 本機模型
相似商品推薦                                   [更新商品向量]
模型 {BGE_MODEL} · CPU · 資料不離開本機 · 向量 {已快取筆數} 筆／最後更新 {時間}
┌ 選擇商品：[ 下拉選單 ▼ ]  [計算相似商品] ─────────────────────────┐
┌ 目前商品 ───────────────┐ ┌ Top 5 相似商品 ────────────────────┐
│ [圖] {product_name}     │ │ 1 [圖] {名稱} {分類} ▇▇▇▇ {score} │
│ {分類} · {價格} · {標籤} │ │ …（最多 5 筆）                      │
│ 模型輸入文字預覽          │ │ 處理時間 {ms}（快取命中 {n}/{total}） │
└────────────────────────┘ └───────────────────────────────────┘
┌ 說明：為什麼是本機模型 ─────────────────────────────────────────┐
```

- 下拉選單與 Top 5 只含**可推薦且可購買**商品：`products.status='active'`、`is_ai_recommendable=true`，且至少一個 `product_skus.status='active'` 並 `available_quantity>0`；基準商品本身排除。顯示價格為可售 SKU 的最低價。
- 相似度以數值＋水平條顯示（條長＝分數）。
- 商品圖片取 `products.image_urls[0]`；無圖片時以商品名稱縮寫佔位。
- 狀態：模型未安裝 → 黃色提示＋安裝指令；無商品 → 空狀態「資料庫尚無可推薦商品」；不顯示假結果。
- **實作備註（v1.3）**：模型輸入使用 `categories.name` 的大／小類名稱（`category_path` 存的是分類代碼，見第 7.2 節）。「更新商品向量」清除快取後全部重算。T5 本機實測（CPU、324 筆可售商品）：模型載入 5.0 秒、全量向量化 7.6 秒、查詢中位數 26.5 ms；同一商品不同包裝（單入／箱購）相似度最高，前台推薦需合併。

### 5.3 AI 板塊 B｜雲端洞察 `/admin/ai/insight`

```
EYEBROW: CLOUD LLM · 雲端 API
AI 營運洞察
模型 {CLAUDE_MODEL} · 只傳送彙總數字，不含個資
┌ 資料範圍：日期 ▼ │ 示範訂單 ▼ ─────────────────────────────────┐
┌ KPI 快照（與營運總覽相同來源）────────────────────────────────────┐
┌ 快速提問 ──────────────────────────────────────────────────────┐
│ [產生本週主管摘要] [哪些商品該補貨？] [哪些商品適合促銷？] [營收為什麼下滑？] │
│ ┌──────────────────────────────────────────────┐ [送出]        │
│ │ 輸入你的問題（最多 300 字）                    │               │
│ └──────────────────────────────────────────────┘               │
└────────────────────────────────────────────────────────────────┘
┌ AI 回覆 ───────────────────────────────────────────────────────┐
│ Q：{問題}                                                       │
│ A：{回覆}                                                       │
│ ── {模型} · {耗時} · 輸入 {in}／輸出 {out} tokens · 請人工核對     │
└────────────────────────────────────────────────────────────────┘
┌ ▸ 送給模型的資料（<details>）：實際傳送的彙總 JSON ─────────────────┐
```

- 提問方式：四個預設 intent 可獨立交付；自由輸入須通過第 12.2 節的獨立啟用門檻與驗收，未通過時介面隱藏且伺服器拒絕，不因預設問題可用而自動開放。
- 不論哪種提問，送給模型的資料都由伺服器依第 12.2 節白名單重新聚合，不信任瀏覽器送來的數字；「送給模型的資料」預覽必須與該次請求為同一物件。
- 數值由程式計算，模型只解讀；資料未提供的項目（例如來客數、流量、毛利）須回答無法判定，不得推論。
- 單次問答，不保留歷史；不提供模型切換選單。
- 「營收為什麼下滑？」：資料不足以判斷因果時，模型須回答資料不足，不得捏造原因。
- 來源標籤：`Claude`（綠）／`規則退回`（黃）；失敗只顯示原因類型（未設定 Key／逾時／服務錯誤）。
- **T5 真模型實測後的規則（v1.3，已實作）**：
  - 回覆上限 `max_tokens` 1200、逾時 45 秒（營運總覽摘要維持 600）；`stop_reason=max_tokens` 時標示「內容可能不完整」。
  - 送給模型的商品依 intent 限量：`period_compare`／`revenue_change` 20 筆、`replenishment`／`promotion` 50 筆、自由提問 100 筆（白名單上限仍為 100）；JSON 縮排 1。實測輸入由約 18,000 降到 5,000～10,000 tokens。
  - `replenishment` 候選由程式先篩選 `available_quantity <= safety_stock`，模型只排序與說明。
  - System prompt 要求日期照抄範圍欄位、不得自行加減乘除產生新數字、不使用 Markdown 標題。
  - 「營收為什麼下滑？」改為列出兩期各自營收最高／最低的日期，不由模型判斷「差異最大」。
  - 未指定日期時，本期為最近有訂單日往前 7 天；展示時建議手動指定完整區間。

### 5.4 AI 比較 `/admin/ai/compare`

```
EYEBROW: HYBRID AI
Local AI vs Cloud LLM
┌────────────────┬──────────────────────┬──────────────────────┐
│ 比較項目        │ ◆ Local（BGE）         │ ☁ Cloud（Claude）     │
├────────────────┼──────────────────────┼──────────────────────┤
│ 實測延遲        │ {最近 N 次中位數}        │ {最近 N 次中位數}       │
│ 每次成本        │ 本機 CPU，無 API 費用    │ 依 token 計費 {估算}    │
│ 資料是否離開本機 │ 否                     │ 是（僅彙總數字）        │
│ 推論是否需網路   │ 否（模型已下載至本機）     │ 是                    │
│ 擅長           │ 找相似、分類、排序        │ 摘要、解讀、自然語言問答  │
│ 限制           │ 不會生成文字              │ 費用、延遲、可能幻覺     │
└────────────────┴──────────────────────┴──────────────────────┘
```

- 實測值來自 A、B 的實際呼叫紀錄；尚未量測時顯示「尚未量測，請先到 A／B 執行一次」。
- 「推論不需網路」僅指 BGE 模型已下載後的本機推論；網站讀取 Atlas 資料與遠端商品圖片仍需網路，整站並非可離線運作。
- **實作備註（v1.3）**：N＝最近 10 次成功呼叫；Local 只計相似商品計算，Cloud 計洞察與總覽摘要的實際 API 呼叫（快取命中與失敗不計）。成本只在設定 `CLAUDE_INPUT_USD_PER_MTOK`／`CLAUDE_OUTPUT_USD_PER_MTOK` 時估算，未設定則只顯示 token。另列最近 20 筆呼叫紀錄（不含問題內容）；量測存在程序記憶體，重新啟動即清空。

### 5.5 推薦監控 `/admin/recommendations`

- 沿用現有內容，套用新版型；權重說明改為讀取 v4 `recommendation_policy`（4/3/2/1）。**已實作（B1，#83）**：規則推薦讀 active 政策，缺少、負數、非數字、NaN／Infinity 的權重以預設值補上；SEARCH 事件以 `search_query` 比對商品名稱與分類計分。
- **事件範圍（B2，#84）**：推薦監控與成效／歸因統計使用 `production_*`（排除 synthetic 與 `exclude_from_attribution`）；會員自己的前台推薦使用 `personalization_*`（只排除 synthetic），真實會員的示範結帳會影響本人推薦但不計入成效。
- 預留（**未實作**）：推薦曝光、點擊、加購、購買數（依 `recommendation_logs`；目前沒有程式寫入）。

---

## 6. 管理頁面版面

### 6.1 商品管理 `/admin/products`

```
商品管理                                              [新增商品]
┌ 篩選：關鍵字 │ 大類別 ▼ │ 狀態 ▼ │ 可推薦 ▼ ───────────────────────┐
┌ 列表 ─────────────────────────────────────────────────────────┐
│ 圖 │ 商品代碼 │ 名稱 │ 分類 │ SKU 數 │ 可售量合計 │ 評價 │ 狀態 │ 可推薦 │ 操作 │
└──────────────────────────────────────────────────────────────┘
新增／編輯表單：基本資料（代碼、名稱、品牌、分類、摘要、描述、標籤、圖片網址）
               AI 設定（可推薦、生命週期、補貨週期）
               SKU 子表（SKU 代碼、規格、售價、庫存、安全庫存、狀態）
```

### 6.2 訂單管理 `/admin/orders`

```
訂單管理
┌ 篩選：日期 │ 訂單狀態 ▼ │ 付款狀態 ▼ │ 示範訂單 ▼ │ 訂單編號 ─────────┐
┌ 列表：訂單編號 │ 下單時間 │ 狀態 │ 付款 │ 出貨 │ 示範 │ 金額 │ 操作 ─────┐
明細頁：訂單資訊、品項（快照名稱、單價、數量、小計）、金額組成、狀態時間軸
```

### 6.3 會員管理 `/admin/members`

```
會員管理
┌ 篩選：關鍵字 │ 角色 ▼ │ 狀態 ▼ ──────────────────────────────────┐
┌ 列表：顯示名稱 │ Email（遮罩）│ 角色 │ 等級 │ 狀態 │ 註冊時間 │ 最後登入 ─┐
```

- Email 預設遮罩顯示；後台不顯示、不回傳 `password_hash`。
- 會員個資不送入任何 LLM。

---

## 7. 資料來源對照（供 SAM 對接）

v4 集合與欄位依 `VibeCart_AI/MongoDB/schema_complete_v4.py`。

### 7.1 營運總覽／AI 板塊 B 的 KPI

| 畫面元素 | 來源 | 規則 |
|---|---|---|
| 範圍（共同條件） | `orders.ordered_at`、`is_demo` | 台北日期起訖轉 UTC 半開區間；`is_demo` 依篩選。以下所有訂單指標都先套用此條件 |
| 全部訂單（分母） | `orders` 筆數 | **只套範圍條件**，包含所有付款與訂單狀態 |
| 有效訂單（分子） | `orders` 筆數 | 範圍條件＋`payment_status='paid'` 且 `status!='cancelled'` |
| 有效營收 | 有效訂單的 `total_amount`（Decimal128） | Decimal 精算，顯示兩位 |
| 平均客單 | 有效營收 ÷ 有效訂單 | 有效訂單為 0 時顯示「—」（null），不除以零 |
| 低庫存品項 | `product_skus` | `status='active'` 且 `available_quantity <= safety_stock` |
| 熱銷排行 | `order_items` 依 `product_id` 加總 `quantity`，名稱取 `product_name_snapshot` | 只計有效訂單 |
| 每日營收 | 有效訂單依 `ordered_at` 台北日期分組 | — |
| 最近訂單 | `orders.order_number`、`status`、`payment_status`、`is_demo`、`total_amount` | — |

### 7.2 AI 板塊 A

| 畫面元素 | 來源 | 規則 |
|---|---|---|
| 商品下拉選單／候選 | `products`＋`product_skus` | `products.status='active'`、`is_ai_recommendable=true`，且至少一個 SKU `status='active'` 並 `available_quantity > 0`；沒有可售 SKU 的商品排除 |
| 模型輸入文字 | `products.product_name`、`categories.name`（大／小類）、`summary`、`description`、`product_tags` | 由程式組合；`category_path` 為分類代碼（例如 `SM-DAIRY`），不送入模型（v1.3） |
| 商品圖片 | `products.image_urls[0]` | 選填；空陣列以縮寫佔位 |
| 價格 | 可售 SKU（`status='active'` 且 `available_quantity>0`）的 `price` 最低值 | Decimal128；下架或無庫存 SKU 的低價不得影響顯示 |
| 分類名稱 | `categories.name`（`major_category_id`、`minor_category_id`） | — |

### 7.3 推薦監控

| 畫面元素 | 來源 |
|---|---|
| 權重政策 | `system_configs`（`config_key='recommendation_policy'`、`status='active'`）的 `settings.weights` |
| 事件統計 | `behavior_events.event_type`、`product_id`、`event_at`；以 `production_behavior_query()` 排除 synthetic 與 `exclude_from_attribution` |
| 曝光／點擊／加購／購買（預留） | `recommendation_logs.items`、`clicked_product_ids`、`added_to_cart_product_ids`、`purchased_product_ids` |

### 7.4 管理頁面

| 頁面 | 集合 | 主要欄位 |
|---|---|---|
| 商品管理 | `products`、`product_skus`、`categories`、`brands` | `product_code`、`product_name`、`status`、`is_ai_recommendable`、`average_rating_display`、`rating_count`、`image_urls`；SKU：`sku_code`、`variant_attributes`、`price`、`stock_quantity`、`available_quantity`、`safety_stock`、`stock_status` |
| 訂單管理 | `orders`、`order_items` | `order_number`、`ordered_at`、`status`、`payment_status`、`shipping_status`、`is_demo`、`subtotal`、`discount_amount`、`shipping_fee`、`total_amount`；明細：`product_name_snapshot`、`unit_price`、`quantity`、`line_total` |
| 會員管理 | `users` | `display_name`、`email`、`role`、`member_level`、`status`、`registered_at`、`last_login_at` |

### 7.5 資料準備狀態（v1.3：2026-10-21 依 main 文件核對；即時數字以 [CURRENT_CONTEXT.md](CURRENT_CONTEXT.md) 為準）

| # | 需求 | 狀態 |
|---|---|---|
| D1 | 分類、品牌、商品、SKU | ✅ 10/09 讀回：`categories` 32、`brands` 128、`products` 336、`product_skus` 336 |
| D2 | 商品圖片 `image_urls` | ✅ 10/09 讀回 336／336 有圖片 |
| — | 可推薦／可售 | 10/09：336 商品 active 且可推薦、324 個 SKU 可售；10/12～10/17 T5 實測時可售候選 324 筆 |
| D3 | 示範訂單與明細 | ✅ 3,000 筆 demo 訂單（10/17 讀回為 3,002，多 2 筆 10/14 示範結帳）、`order_items` 8,969；600 位合成會員全部停用 |
| D4 | 行為事件 `behavior_events` | ✅ 10/18 SAM 正式匯入 1,240 筆 synthetic 事件並完成 verify（[D4 驗收](D4_IMPORT_ACCEPTANCE_2026-10-18.md)）；推薦與監控依第 5.5 節範圍排除 |
| D5 | 後台寫入契約與稽核 Schema | 📝 契約見第 12.3 節；SAM `schema_d5_v1.py`（`20261018_07_admin_audit_receipts_v4`）已於隔離本機 MongoDB 演練，**尚未啟用**；寫入功能未實作 |
| D6 | 可登入的私有 customer／admin 測試帳號 | 依 SAM 私有驗收環境紀錄（見 CURRENT_CONTEXT）；帳密不入 Git |

所有營運數字皆來自示範訂單，展示時須標示「示範資料」。10/09 的原始讀回與匯入證據見 git 歷史與 `VibeCart_AI/MongoDB/test_data/`。

---

## 8. 視覺規範（v1.3：淺色數據看板，2026-10-21 定案）

> 依第 10 節 2026-10-21 的四筆視覺決策更新；設計參考 Demo：https://claude.ai/artifact/Cqw1YCeAXzjThabF534WfU 。**現行 `admin.css` 仍為 v1.2 深色 token，改版尚未實作。**前台 `main.css` 不變。

| Token | 值 | 用途 |
|---|---|---|
| `--bg` | `#f3f5f8` | 頁面底色 |
| `--panel` | `#ffffff` | 卡片（細邊框＋淡陰影） |
| `--panel-2` | `#f6f8fa` | 次底（表頭、篩選列、程式碼區） |
| `--line` | `#e2e6eb` | 邊框 |
| `--ink` | `#111827` | 主要文字 |
| `--ink-2` | `#374151` | 次要內文 |
| `--muted` | `#6b7280` | 說明文字 |
| `--brand` | `#b7ff2a` | **只用於色塊**：主要按鈕、Logo、選取狀態（白底上不可當文字或細線） |
| `--lime` | `#5a960e` | 文字、連結、目前頁、Local AI、長條圖與走勢圖 |
| `--cloud` | `#2b7bc4` | Cloud LLM 標籤（淺色底）；`#7cc4ff` 只用於深色底 |
| `--ok` | `#1f9d55` | 可用、成功 |
| `--warn` | `#b7791f` | 規則退回、模型未載入 |
| `--danger` | `#d64545` | 錯誤 |
| `--radius` | `10px` | 卡片圓角 |
| 字型 | `"IBM Plex Sans", "Noto Sans TC"`；數字用等寬 `"JetBrains Mono"` | 字型檔的載入方式於實作時確認 |
| 斷點 | 900px、620px | 不變 |

- 標籤與提示改為淺色底＋深色字；狀態燈旁仍必有文字（第 9 節）。
- 營運總覽改為 12 欄看板格線：KPI 卡附 14 天走勢小圖與「近 7 天 vs 前 7 天」變化；每日營收為 inline SVG 長條圖（刻度、日均線、滑鼠提示），資料表收進「查看資料表」；熱銷 Top 10 改橫條；低庫存加水位條。仍符合 5.1-1（長條圖＋保留表格）。
- **待決定**：Demo 的「分類營收占比」區塊在第 7 節尚無對應欄位，採用前須先定義資料來源（例如有效訂單明細依大類快照欄位加總）與範圍口徑。
- 後台樣式寫在 **`static/css/admin.css`**，由 `admin/layout.html` 載入，不修改前台 `main.css`。
- 元件沿用：`.panel`、`.metrics`、`.button`、`.button.secondary`、`.table-wrap`、`.rank`、`.insight`、`.eyebrow`；新元件：`.admin-layout`、`.admin-nav`、`.status-dot`、`.score-bar`、`.source-badge`、`.ai-answer`、`.toast`。
- v1.2 深色 token（`--bg #0c0e0d`、`--lime #b7ff2a` 等）保留於 git 歷史；改版完成前仍為現行樣式。

---

## 9. 互動、狀態與無障礙

- 伺服器端渲染（Flask + Jinja2），不引入前端框架；所有 POST 帶 `csrf_token`，所有後台路由 `@admin_required`。
- 每個 AI 結果附來源（模型／規則）、耗時、資料範圍。
- 空資料、模型未啟用、模型失敗、資料庫不可用各有明確文字；**不顯示空白卡片或假資料**。
- 數字格式：金額 `NT$ 1,234.00`；分數小數 2 位；耗時 < 1 秒用 ms，否則用秒（1 位小數）。
- 側欄 `<nav aria-label="後台導覽">`；狀態燈有文字；表格有 `<thead>`；分數條附數值；錯誤 `role="alert"`。

---

## 10. 決策紀錄

| 日期 | 編號 | 決定 | 備註 |
|---|---|---|---|
| 2026-10-04 | 3-1 | AI 摘要兩處都保留：營運總覽按鈕＋AI 板塊 B 完整問答 | 共用 `services/ai_workflows.py` |
| 2026-10-04 | 3-1（路由） | 保留 `POST /admin/summary` 給營運總覽；B 使用自己的路由 | 現有測試不需修改 |
| 2026-10-04 | 3-2 | 商品／訂單／會員管理顯示於導覽，版面見第 6 節 | 分工及 D5 契約於 10/16 補定，見第 12.3 節 |
| 2026-10-04 | 4-1 | 左側欄；平板頂部分頁列、手機漢堡選單 | — |
| 2026-10-04 | 4-2 | 後台獨立頁首，不顯示前台購物車 | — |
| 2026-10-04 | 5.1-1 | 每日營收加長條圖（純 CSS／inline SVG），保留表格 | — |
| 2026-10-04 | 5.2-1 | 商品選擇用下拉選單 | 商品變多後再考慮搜尋框 |
| 2026-10-04 | 5.2-2 | Top 5 顯示商品圖片 | v4 已有 `products.image_urls`；需資料（D2），無圖時縮寫佔位 |
| 2026-10-04 | 5.3-1 | 快速提問 4 顆：本週主管摘要、該補貨、適合促銷、營收為什麼下滑 | — |
| 2026-10-04 | 5.3-2 | 不保留問答歷史 | — |
| 2026-10-04 | 5.3-3 | 不提供雲端模型切換 | — |
| 2026-10-04 | 6-1 | Cloud 識別色 `#7cc4ff` | — |
| 2026-10-04 | 6-2 | 後台樣式拆成 `static/css/admin.css` | 避免與前台 `main.css` 衝突 |
| 2026-10-04 | 4.4 | 懸浮提示：成功 3.5 秒、錯誤 6 秒、滑鼠移上暫停 | — |
| 2026-10-05 | — | 文件移除所有示範數字，改以欄位對照（第 7 節） | 便於以資料庫真實資料對接 |
| 2026-10-09 | 審查 P2 | KPI 分子＝有效訂單、分母＝範圍內全部訂單；零有效單客單為 null | 第 7.1 節 |
| 2026-10-09 | 審查 P2 | 推薦候選與最低價只計 active 且可售 SKU | 第 5.2、7.2 節 |
| 2026-10-09 | 審查 P2 | 「不需網路」限定為本機模型推論 | 第 5.4 節 |
| 2026-10-09 | 審查 P2 | D1～D3 已有資料，更新準備狀態 | 第 7.5 節 |
| 2026-10-09 | A | 雲端洞察：預設問題＋管理員自由輸入；自由輸入另設啟用及驗收門檻 | 10/16 補定，見第 12.2 節 |
| 2026-10-09 | B | 稽核欄位採 SAM 提案，保留 180 天 | 第 12.3 節 |
| 2026-10-09 | C | 後台**不能停用任何管理員帳號**；管理員停用只能由資料庫維護人員直接操作資料庫 | 第 12.3 節 |
| 2026-10-09 | D | 第一版寫入範圍採 SAM 提案欄位；退款不做 | 第 12.3 節 |
| 2026-10-16 | A 補充 | 四個固定 intent 與自由提問分開啟用；自由提問通過權限、資料、濫用及真模型驗收才開放 | 第 12.2 節 |
| 2026-10-16 | B 補充 | 稽核及獨立重送紀錄各保留 180 天；批量模式與 request_id 規則定案 | 第 12.3 節 |
| 2026-10-17 | T5-1 | 雲端洞察 `max_tokens` 1200、逾時 45 秒，截斷時標示；商品依 intent 限量 20／50／100；補貨候選由程式篩選；prompt 禁止自行計算並要求日期照抄 | 真 Claude 3 回 9 次實測（第 5.3 節、[AI_DASHBOARD.md](AI_DASHBOARD.md) T5） |
| 2026-10-18 | A1 | 雲端 runtime 的三個 AI 開關改讀環境變數，預設關閉、只接受 true／false；不放寬 preview／acceptance 檢查 | #82，第 13 節 |
| 2026-10-18 | A2 | AI 映像為建置選項 `INSTALL_AI`（預設不變）：CPU 版 PyTorch、建置時內建 BGE 模型、執行期離線載入 | #82，第 13 節 |
| 2026-10-18 | B1 | 規則推薦改用 v4 政策權重 4/3/2/1，讀 active 政策並驗證數值；SEARCH 依搜尋字計分 | #83（SAM 補 NaN／Infinity 防護），第 5.5 節 |
| 2026-10-18 | B2 | 個人推薦只排除 synthetic；示範結帳影響本人推薦但不計入成效／歸因 | #84，第 5.5、7.3 節 |
| 2026-10-18 | 6+4 | 前台首頁「猜你喜歡」改為 6＋4 兩區（請求時計分、高星優先、分類上限、去重） | SAM #81 `storefront_ranking.py`；6＋4 由 SAM 主責 |
| 2026-10-20 | PR #5 | 偏好分數持久快照以 opt-in CLI 交付（預設 dry-run），**未啟用排程** | SAM 整合，見 `docs/PR5_SCORING_DELIVERY_2026-10-20.md` |
| 2026-10-21 | 視覺 | 後台改採**淺色數據看板風格**（取代第 8 節的深色 token）：底色 `--bg #f3f5f8`、卡片 `--panel #ffffff`（細邊框＋淡陰影）、次底 `--panel-2 #f6f8fa`、邊框 `--line #e2e6eb`、文字 `--ink #111827`／`--ink-2 #374151`／`--muted #6b7280`；圓角 `--radius 10px`；字型 `"IBM Plex Sans", "Noto Sans TC"`，數字用等寬 `"JetBrains Mono"` | Demo：https://claude.ai/artifact/Cqw1YCeAXzjThabF534WfU 。v1.3 已更新第 8 節 token 表與字型；新樣式仍只寫在 `admin.css`（6-2），前台 `main.css` 不變；`admin.css` 改版尚未實作 |
| 2026-10-21 | 視覺（品牌色） | 萊姆綠分兩種用途：`--brand #b7ff2a` 只用於色塊（主要按鈕、Logo、選取狀態）；文字、連結、目前頁、Local AI、長條圖與走勢圖改用 `--lime #5a960e` | `#b7ff2a` 在白底上對比不足，不能當文字或細線 |
| 2026-10-21 | 6-1 補充 | 淺色底的 Cloud 色改用 `#2b7bc4`（同色系加深）；`#7cc4ff` 只用於深色底 | 狀態色同步調整：`--ok #1f9d55`、`--warn #b7791f`、`--danger #d64545`；標籤與提示改為淺色底＋深色字 |
| 2026-10-21 | 視覺（總覽） | 營運總覽改為 12 欄看板格線：KPI 卡附 14 天走勢小圖與「近 7 天 vs 前 7 天」變化；每日營收為 inline SVG 長條圖（刻度、日均線、滑鼠提示），資料表收進「查看資料表」；熱銷 Top 10 改橫條；低庫存加水位條 | 仍符合 5.1-1（長條圖＋保留表格）。Demo 另有「分類營收占比」區塊，第 7 節尚無對應欄位，**是否採用及資料來源待主 session 決定** |

---

## 11. 實作檔案對應（相對 `MuscleCore分析資料/website/app/`）

| 頁面 | 檔案 | 狀態 |
|---|---|---|
| 共用版型 | `templates/admin/layout.html`、`static/css/admin.css`、`static/js/admin.js` | ✅（視覺改版待做，第 8 節） |
| 營運總覽 | `templates/admin/dashboard.html`、`services/dashboard.py` | ✅ |
| AI 板塊 A | `admin.py`、`services/local_ai.py`、`templates/admin/ai_recommendation.html` | ✅ |
| AI 板塊 B | `admin.py`、`services/ai_payload.py`（白名單 v1）、`services/ai_workflows.py`（`run_claude`、intent、防護）、`templates/admin/ai_insight.html` | ✅ |
| AI 比較 | `admin.py`、`services/ai_compare.py`、`templates/admin/ai_compare.html` | ✅ |
| 推薦監控 | `templates/admin/recommendations.html`、`services/dashboard.py` | ✅（曝光／轉換未做） |
| 推薦權重與範圍 | `services/recommendation.py`（`policy_weights`）、`services/behavior_scope.py`（`production_*`／`personalization_*`） | ✅ |
| 前台 6＋4 | `services/storefront_ranking.py`、`store_v4.py`（SAM 主責） | ✅ |
| 線上 AI | 網站根目錄 `cloud_runtime.py`、`Dockerfile`、`requirements-cloud-ai.txt`；倉庫 `deploy/cloudbuild.yaml` | ✅ 程式；部署見第 13 節 |
| 商品管理 | `admin.py` 新路由、`services/admin_catalog.py`、`templates/admin/products.html`、`product_form.html` | ❌ 未實作 |
| 訂單管理 | `admin.py` 新路由、`templates/admin/orders.html`、`order_detail.html` | ❌ 未實作 |
| 會員管理 | `admin.py` 新路由、`templates/admin/members.html` | ❌ 未實作 |

---

## 12. D5／AI 資料契約回覆（JEFF 2026-10-09；專案負責人 2026-10-16 補定）

回覆對象：PR #11 `docs/SAM_DATA_CONTRACT_2026-10-07.md`（SAM 提案）。

### 12.1 總結

| 項目 | 回覆 |
|---|---|
| D5 寫入協定 | **接受**，並補充第 12.3 節決定 |
| AI 白名單 v1 | **接受**資料形狀與上限；**修訂**提問方式（第 12.2 節） |
| D4 事件 | 接受四權重 PURCHASE=4、ADD_TO_CART=3、SEARCH=2、PRODUCT_VIEW=1；synthetic 事件以 `metadata` 批次辨識，**不計入正式推薦歸因與成效**。所有 consumer／排程先完成遠端隔離驗證，SAM 才能匯入；後台監控須明確排除或標示測試批次 |
| 測試帳號 | 後台授權路徑：`@admin_required`，每次請求重新讀取使用者 `role='admin'` 與有效狀態（現行 `app/auth.py`） |

### 12.2 AI 提問方式（決策 A）

- **預設問題**：四個 intent，參數由伺服器驗證。

  | 按鈕 | intent |
  |---|---|
  | 產生本週主管摘要 | `period_compare`（本期 vs 緊接前期） |
  | 哪些商品該補貨？ | `replenishment` |
  | 哪些商品適合促銷？ | `promotion` |
  | 營收為什麼下滑？ | `revenue_change` |

- **自由輸入啟用條件（10/16 定案）**：與四個固定 intent 分開設旗標 `AI_FREE_QUESTION_ENABLED`，預設為 false。只有 `AI_SUMMARY_ENABLED=true`、`DATA_MODE=v4`、有效管理員登入與 session 撤權檢查、CSRF、白名單 v1 伺服器端重新聚合及以下驗收全部通過，才可在指定展示 revision 顯式啟用。旗標關閉時介面不顯示輸入框，伺服器亦拒絕 `free_question`；僅隱藏按鈕不算停用。PR #21 `7798bc5` 已加入預設關閉的本機旗標與伺服器拒絕，遠端真模型及完整啟用驗收仍未完成。
- **必備防護**：問題至多 300 字並移除控制字元；明顯 Email、電話、身分證格式輸入在模型呼叫前拒絕；問題置於獨立的 `untrusted_question` 欄位，不得改變 system prompt、工具、資料範圍或伺服器計算值。只送白名單 v1 彙總，禁止會員個資、原始訂單及瀏覽器提供的數字；非本店營運問題固定拒答，缺資料明說「資料未提供」。模型輸出由模板 escape；持久化日誌只記 intent、問題長度、耗時、token、結果類型，不記問題全文。若有短期記憶體快取，須限制留存與存取，並於驗收紀錄揭露。每位管理員每分鐘最多 6 次；超過回 429。單實例可用程序內限流，若增加實例須改用共用限流儲存並重新驗收。
- **啟用驗收**：在同一來源 SHA／部署 revision，逐項保存預期與實際結果：匿名、customer、停用 admin、已撤權舊 session、缺 CSRF 均不得提問；300／301 字、控制字元、個資與 prompt injection；第 6／7 次請求限流；伺服器白名單 payload 與畫面「送給模型的資料」相同且無個資；真模型與規則退回各自標示來源、耗時、錯誤及資料截止；持久化日誌不含問題全文。驗收前維持旗標關閉；離線測試或設定成功不替代遠端真模型驗收。

### 12.3 後台寫入決策（決策 B、C、D）

**B｜稽核**
- 欄位：`actor_id`、`request_id`、`resource_type`、`resource_id`、白名單欄位 `before`／`after`、`reason`、`result`、`created_at`（UTC）。不記密碼、token、URI。
- **稽核保存 180 天**（`created_at` TTL）；TTL 為背景清除，查詢仍須用時間條件。稽核資料不能兼作重送去重紀錄。
- 業務更新與稽核同一交易；稽核失敗則整筆回滾。
- **重送紀錄保存 180 天**：另設 `admin_write_requests`，以 `(actor_id, request_id)` 唯一，保存規範化請求雜湊、模式、最小結果、`created_at`／`expires_at`；不保存密碼、token、URI 或完整會員資料。TTL 清除以 `expires_at` 為準，伺服器判定到期不得只依賴 TTL 背景執行。180 天內同 ID、同內容回原結果，同 ID、不同內容回 409；超過 180 天不承諾重送原結果，客戶端必須以新 ID 和新 `expected_updated_at` 發起新操作，不得重用舊 ID。
- **單筆與批量 ID**：單筆 `request_id` 為每次操作新產生的 UUIDv4。批量最多 100 筆，必須提交 UUIDv4 `batch_request_id`、明選 `atomic` 或 `per_item`、以及有固定順序的項目。整批雜湊包含模式與按順序排列的資源、版本及白名單 patch；同 batch ID 改順序、模式或內容均回 409。`atomic` 全部業務更新、稽核及批量結果在同一交易提交，任一失敗全部回滾。`per_item` 為每項獨立交易，項目 ID 固定由 `batch_request_id` 與零起算位置組成；每項業務更新、稽核與成功結果同交易提交，驗證或版本衝突的終局失敗亦記錄最小結果但不寫業務資料。重送相同批量時，已完成項目回原結果，只有中斷前未開始的項目才繼續；要修正失敗項目須另開新 batch ID。批量總結果可由固定項目結果重建，不得因回應遺失而重複寫入。
- **驗收**：單筆／批量相同 ID 同內容重送、同 ID 改內容或順序 409、部分成功後中斷重送、`atomic` 失敗全回滾、稽核失敗回滾、100／101 筆、180 天邊界及過期資料查詢。先在隔離 MongoDB transaction 環境驗證，再以最終版本核對遠端；未建好獨立重送紀錄前不得宣稱 D5 寫入可驗收。

**C｜會員停用**
- 後台**只能停用 customer**，不能停用任何 `role='admin'` 帳號（包含自己）。介面上對管理員列不顯示停用操作，伺服器端亦拒絕（403）。
- 管理員帳號的停用只能由資料庫維護人員直接操作資料庫完成。
- 停用同時撤銷該會員的 session（依 REN 的撤權機制）。

**D｜第一版寫入範圍**

| 資源 | 可修改 | 不做 |
|---|---|---|
| 商品 | `product_name`、`description`、`status`（active／inactive／draft）、`is_ai_recommendable` | 分類搬移、評價欄位 |
| SKU | `price`、`stock_quantity`（不得小於 `reserved_quantity`）、`status`；同交易重算 `available_quantity`、`stock_status` | 成本價 |
| 訂單 | 狀態依合法順序：pending→confirmed→shipping→completed；pending／confirmed→cancelled | **退款**（列為後續）、修改金額／快照／`is_demo` |
| 會員 | customer 停用 | 管理員停用、角色變更 |

- 版本衝突、錯誤碼依 SAM 提案（`expected_updated_at`、409／422／401／403／404）；重送保存及批量 ID 依 12.3-B。付款／退款與取消庫存語義仍需在實作前依 REN 接口核對，本文不宣稱已交付 D5 寫入 API。

### 12.4 交給 SAM 的後續

1. 依 12.3-B 設計稽核與獨立重送紀錄的新 migration；目前第六筆為會員 device sessions，不能沿用舊稽核草案的 `_06_` 名稱，且不改歷史 migration checksum。**v1.3 狀態**：SAM 已提出 `schema_d5_v1.py`（`20261018_07_admin_audit_receipts_v4`）並在隔離本機 MongoDB 演練，尚未啟用。
2. JEFF 提供全部 consumer／排程清單並完成遠端 synthetic 隔離驗證後，SAM 才可匯入 D4 行為事件（依 12.1）。**v1.3 狀態**：10/18 已匯入 1,240 筆並 verify。
3. 配置私有 admin／customer 測試帳號。
4. JEFF 實作 12.2 獨立旗標與防護；SAM 依同一來源 SHA／部署 revision 驗收後才開放自由提問。**v1.3 狀態**：旗標與六點防護已實作，雲端 runtime 可由環境變數設定（預設 false）；啟用驗收未完成，展示維持關閉。

---

## 13. 線上 AI 部署設定（v1.3 新增）

詳細設定、建議值與驗收紀錄見 [AI_DASHBOARD.md 的「線上 AI 設定」](AI_DASHBOARD.md) 與 `deploy/CLAUDE_SECRET_SETUP.md`。設計約束如下：

- 三個 AI 開關（`AI_SUMMARY_ENABLED`、`AI_RECOMMENDATIONS_ENABLED`、`AI_FREE_QUESTION_ENABLED`）由 Cloud Run 環境變數決定，**預設 false**，非 true／false 的值拒絕啟動；開啟 AI 不得放寬 `CLOUD_PREVIEW_READ_ONLY`、驗收模式、資料庫網址與 `SECRET_KEY` 檢查。
- `ANTHROPIC_API_KEY` 只放 Secret Manager，Key 內容由金鑰擁有人（JEFF）在 Console 新增版本；部署引用明確版本號，不經由對話、命令參數、檔案或 Git。
- BGE 必須在建置時內建於 AI 映像（`INSTALL_AI=true`，`HF_HOME=/srv/models`、執行期 `HF_HUB_OFFLINE=1`）；Cloud Build 須通過離線載入檢查。
- 發布流程：建置 → 零流量修訂驗證（BGE、Claude 4 個預設問題、退回）→ JEFF 與 SAM 都同意後才切流量；保留舊修訂以便退回。費用（Cloud Build、Artifact Registry、Cloud Run 記憶體）屬專案帳單，由 SAM 決定；Claude API 費用由 JEFF 的 Key 負擔。
- 備案：BGE 記憶體或冷啟動不符時只開 Claude（`AI_RECOMMENDATIONS_ENABLED=false`）。長期方案：商品向量離線預先計算存入 Atlas（`product_embeddings`），網站只做 cosine。
