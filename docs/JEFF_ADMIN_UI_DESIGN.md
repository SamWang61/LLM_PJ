# JEFF｜管理後台 設計與版面規格 v1.0

> 建立：2026-10-03；定案：2026-10-05（Asia/Taipei）
> 負責人：JEFF（AI／管理後台，見 [TEAM_OWNERSHIP.md](TEAM_OWNERSHIP.md)）
> 狀態：**版面已定案**（決策見第 10 節）；第 7 節資料來源對照供 SAM 對接 v4 資料庫。
> 配套文件：[AI_DASHBOARD.md](AI_DASHBOARD.md)（既有後台實作與驗證）。

---

## 0. 文件用途

- **開發**：依第 3～6 節版面、第 8 節視覺規範與第 11 節檔案對應實作。
- **資料庫對接（SAM）**：第 7 節列出每個畫面元素對應的 v4 集合與欄位，以及目前缺少的資料。
- 文件中的線框圖**不含任何示範數字**；`{欄位}` 表示由資料庫或執行結果帶入的值。
- 實作一律讀取 v4 真實資料；資料為空時顯示空狀態，不以假資料填充。

---

## 1. 設計目標

1. **Demo 一眼看懂兩條 AI 路線**：Local AI「找得準」、Cloud LLM「說得懂、看得深」，兩個板塊在導覽上獨立、視覺上可區分。
2. **數據可信**：每個數字標示資料範圍；AI 輸出標示來源（模型／規則退回）、耗時與「請人工核對」。
3. **沿用現有風格**：深色底、萊姆綠強調（`main.css`），不引入新框架。
4. **RWD**：桌機完整、平板可用、手機可讀（Demo 以桌機為主）。

---

## 2. 現況（main，2026-10-05）

| 頁面 | 路由 | 內容 |
|---|---|---|
| 營運決策中心 | `GET /admin/` | 日期／示範訂單篩選、4 張 KPI、營運摘要＋AI 摘要按鈕、熱銷排行、每日營收表、低庫存表、最近訂單表 |
| AI 摘要結果 | `POST /admin/summary` | 同上頁面，摘要區換成 Claude 輸出 |
| 推薦行為監控 | `GET /admin/recommendations` | 策略說明、旗標狀態、v4 權重政策、最近 1,000 筆事件前 20 組 |
| 篩選錯誤 | — | 錯誤訊息＋返回 |

**待改善**：沒有後台導覽；首頁區塊過多、AI 摘要不突出；共用前台頁首；推薦監控說明仍為舊權重 1/3/4/8。

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
- 商品／訂單／會員管理**顯示於導覽**。版面由本文件定義；寫入功能涉及資料契約，實作分工與範圍待 SAM 確認（見第 10 節 3-2）。

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
│ 有效營收   │ 有效訂單   │ 平均客單   │ 低庫存品項 │
│ {revenue} │ {orders}  │ {avg}     │ {count}   │
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

- 下拉選單列出可推薦商品；相似度以數值＋水平條顯示（條長＝分數）。
- 商品圖片取 `products.image_urls[0]`；無圖片時以商品名稱縮寫佔位。
- 狀態：模型未安裝 → 黃色提示＋安裝指令；無商品 → 空狀態「資料庫尚無可推薦商品」；不顯示假結果。

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

- 單次問答，不保留歷史；不提供模型切換選單。
- 「營收為什麼下滑？」：資料不足以判斷因果時，模型須回答資料不足，不得捏造原因。
- 來源標籤：`Claude`（綠）／`規則退回`（黃）；失敗只顯示原因類型（未設定 Key／逾時／服務錯誤）。

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
│ 網路依賴        │ 不需要                  │ 需要                  │
│ 擅長           │ 找相似、分類、排序        │ 摘要、解讀、自然語言問答  │
│ 限制           │ 不會生成文字              │ 費用、延遲、可能幻覺     │
└────────────────┴──────────────────────┴──────────────────────┘
```

- 實測值來自 A、B 的實際呼叫紀錄；尚未量測時顯示「尚未量測，請先到 A／B 執行一次」。

### 5.5 推薦監控 `/admin/recommendations`

- 沿用現有內容，套用新版型；權重說明改為讀取 v4 `recommendation_policy`（4/3/2/1）。
- 預留：推薦曝光、點擊、加購、購買數（依 `recommendation_logs`）。

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
| 有效營收 | `orders.total_amount`（Decimal128） | `payment_status='paid'` 且 `status!='cancelled'`；依 `ordered_at` 台北日期篩選；`is_demo` 依篩選 |
| 有效訂單／範圍內訂單 | `orders` 筆數 | 同上 |
| 平均客單 | 有效營收 ÷ 有效訂單 | — |
| 低庫存品項 | `product_skus` | `status='active'` 且 `available_quantity <= safety_stock` |
| 熱銷排行 | `order_items` 依 `product_id` 加總 `quantity`，名稱取 `product_name_snapshot` | 只計有效訂單 |
| 每日營收 | 有效訂單依 `ordered_at` 台北日期分組 | — |
| 最近訂單 | `orders.order_number`、`status`、`payment_status`、`is_demo`、`total_amount` | — |

### 7.2 AI 板塊 A

| 畫面元素 | 來源 | 規則 |
|---|---|---|
| 商品下拉選單／候選 | `products` | `status='active'`、`is_ai_recommendable=true`，且至少一個 `product_skus.available_quantity > 0` |
| 模型輸入文字 | `products.product_name`、`category_path`、`summary`、`description`、`product_tags` | 由程式組合 |
| 商品圖片 | `products.image_urls[0]` | 選填；空陣列以縮寫佔位 |
| 價格 | `product_skus.price` 最低值 | Decimal128 |
| 分類名稱 | `categories.name`（`major_category_id`、`minor_category_id`） | — |

### 7.3 推薦監控

| 畫面元素 | 來源 |
|---|---|
| 權重政策 | `system_configs`（`config_key='recommendation_policy'`、`status='active'`）的 `settings.weights` |
| 事件統計 | `behavior_events.event_type`、`product_id`、`event_at` |
| 曝光／點擊／加購／購買（預留） | `recommendation_logs.items`、`clicked_product_ids`、`added_to_cart_product_ids`、`purchased_product_ids` |

### 7.4 管理頁面

| 頁面 | 集合 | 主要欄位 |
|---|---|---|
| 商品管理 | `products`、`product_skus`、`categories`、`brands` | `product_code`、`product_name`、`status`、`is_ai_recommendable`、`average_rating_display`、`rating_count`、`image_urls`；SKU：`sku_code`、`variant_attributes`、`price`、`stock_quantity`、`available_quantity`、`safety_stock`、`stock_status` |
| 訂單管理 | `orders`、`order_items` | `order_number`、`ordered_at`、`status`、`payment_status`、`shipping_status`、`is_demo`、`subtotal`、`discount_amount`、`shipping_fee`、`total_amount`；明細：`product_name_snapshot`、`unit_price`、`quantity`、`line_total` |
| 會員管理 | `users` | `display_name`、`email`、`role`、`member_level`、`status`、`registered_at`、`last_login_at` |

### 7.5 需要資料庫提供的內容

| # | 需求 | 原因 |
|---|---|---|
| D1 | v4 示範資料：`categories`、`brands`、`products`、`product_skus`（建議 30 筆以上商品、跨多個大類別） | 目前業務集合為空，AI 板塊 A 無法計算、KPI 全為 0 |
| D2 | 部分商品填入 `image_urls` | 推薦結果顯示圖片 |
| D3 | 示範訂單 `orders`／`order_items`（`is_demo=true`，跨多個日期） | 營運總覽、每日營收、AI 板塊 B 需要資料 |
| D4 | 示範 `behavior_events` | 推薦監控與後續個人化推薦 |
| D5 | 確認後台寫入（商品、訂單狀態、會員狀態）的資料契約與權限 | 管理頁面的新增／編輯 |

---

## 8. 視覺規範（沿用 `app/static/css/main.css`）

| Token | 值 | 用途 |
|---|---|---|
| `--bg` | `#0c0e0d` | 頁面底色 |
| `--panel` | `#151816` | 卡片 |
| `--ink` | `#f4f6f1` | 主要文字 |
| `--muted` | `#a8b0a7` | 次要文字 |
| `--lime` | `#b7ff2a` | 強調、主要按鈕、目前頁、Local AI |
| `--line` | `#293028` | 邊框 |
| `--danger` | `#ff6b6b` | 錯誤 |
| `--radius` | `18px` | 卡片圓角 |
| `--cloud`（新） | `#7cc4ff` | Cloud LLM 標籤 |
| `--warn`（新） | `#ffc857` | 規則退回、模型未載入 |
| 字型 | `Inter, "Noto Sans TC", system-ui` | — |
| 斷點 | 900px、620px | — |

- 後台樣式寫在 **`static/css/admin.css`**，由 `admin/layout.html` 載入，不修改前台 `main.css`。
- 元件沿用：`.panel`、`.metrics`、`.button`、`.button.secondary`、`.table-wrap`、`.rank`、`.insight`、`.eyebrow`。
- 新元件：`.admin-layout`、`.admin-nav`、`.status-dot`、`.score-bar`、`.source-badge`、`.ai-answer`、`.toast`。

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
| 2026-10-04 | 3-2 | 商品／訂單／會員管理顯示於導覽，版面見第 6 節 | **待 SAM 確認**：寫入功能的實作分工與資料契約（D5） |
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

---

## 11. 實作檔案對應（相對 `MuscleCore分析資料/website/app/`）

| 頁面 | 檔案 |
|---|---|
| 共用版型 | `templates/admin/layout.html`（新）、`static/css/admin.css`（新） |
| 營運總覽 | `templates/admin/dashboard.html`（改版型） |
| AI 板塊 A | `admin.py` 新路由、`services/local_ai.py`（新）、`templates/admin/ai_recommendation.html`（新） |
| AI 板塊 B | `admin.py` 新路由、`services/ai_workflows.py`（擴充問答）、`templates/admin/ai_insight.html`（新） |
| AI 比較 | `admin.py` 新路由、`templates/admin/ai_compare.html`（新） |
| 推薦監控 | `templates/admin/recommendations.html`（改版型與文字） |
| 商品管理 | `admin.py` 新路由、`services/admin_catalog.py`（新）、`templates/admin/products.html`、`product_form.html`（新） |
| 訂單管理 | `admin.py` 新路由、`templates/admin/orders.html`、`order_detail.html`（新） |
| 會員管理 | `admin.py` 新路由、`templates/admin/members.html`（新） |
