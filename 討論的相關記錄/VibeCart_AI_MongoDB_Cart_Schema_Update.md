# VibeCart AI｜MongoDB 未結單購物車資料結構更新規格

**文件用途：** 提供 Codex 作為 MongoDB Schema 更新與程式實作依據\
**專案：** VibeCart AI｜懂你想買、更懂怎麼賣！\
**版本：** v1.0\
**日期：** 2026-09-16

------------------------------------------------------------------------

## 1. 本次資料庫設計決議

VibeCart AI
的「未結單購物車」屬於高頻率增減、數量修改、短生命週期且具有狀態性的資料，不適合以傳統固定表單概念處理，也不應直接寫入
`orders`。

本次決議採用 MongoDB 的雙層資料模型：

1.  `carts`：保存購物車目前狀態（Current State）。
2.  `cart_events`：保存購物車歷史行為事件（Event Log）。

核心原則：

> **Current State + Event Log**

`carts` 回答「使用者現在購物車裡有什麼？」；`cart_events`
回答「使用者曾經對購物車做過什麼？」。

這兩類資料後續同時提供 VibeCart AI 個人化推薦、棄單分析、轉換分析及
VibeInsight 營運分析使用。

------------------------------------------------------------------------

## 2. 為何不使用傳統 Form / Order 儲存

未結單購物車具有以下特性：

-   商品會頻繁加入與移除。
-   商品數量會頻繁修改。
-   使用者可能離開網站後再次回來。
-   購物車可能長時間未結帳。
-   購物車中的商品不代表正式交易成立。
-   商品被移除後，其歷史行為仍具有 AI 推薦與營運分析價值。

因此：

-   **Cart ≠ Order**
-   未結帳前，不建立正式訂單。
-   商品增減應更新 Active Cart，而非反覆建立表單。
-   歷史行為不可因購物車目前為空而消失。

------------------------------------------------------------------------

## 3. MongoDB Collection 架構

本次新增／確認以下 Collection：

``` text
MongoDB
│
├── users
├── products
├── carts              # 未結單購物車目前狀態
├── cart_events        # 購物車歷史事件
└── orders             # 已成立正式訂單
```

### Collection 職責

  Collection      用途                   資料異動模式
  --------------- ---------------------- ------------------------
  `users`         使用者資料             一般 CRUD
  `products`      商品主檔               一般 CRUD
  `carts`         未結單購物車目前狀態   高頻 Update
  `cart_events`   購物車行為歷史         Append-only 為原則
  `orders`        已成立訂單             低頻異動、保留交易歷史

------------------------------------------------------------------------

## 4. `carts` Collection

### 4.1 設計原則

原則上：

> **一個使用者同時間只允許一份 `active` Cart。**

商品項目直接存放於 `items[]` 陣列中。

### 4.2 建議 Schema

``` json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "status": "active",
  "items": [
    {
      "product_id": "ObjectId/String",
      "quantity": 2,
      "price_snapshot": 590.0,
      "added_at": "ISODate",
      "updated_at": "ISODate"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.3 欄位定義

  ----------------------------------------------------------------------------------------------------
  欄位                     型別                              必填 說明
  ------------------------ ---------------- --------------------- ------------------------------------
  `_id`                    ObjectId                            是 Cart ID

  `user_id`                ObjectId /                          是 使用者識別碼
                           String                                 

  `status`                 String                              是 `active`、`converted`、`abandoned`

  `items`                  Array                               是 購物車商品清單

  `items.product_id`       ObjectId /                          是 商品識別碼
                           String                                 

  `items.quantity`         Integer                             是 數量，必須 \> 0

  `items.price_snapshot`   Decimal/Double                      是 加入／最後確認時的價格快照

  `items.added_at`         Date                                是 首次加入時間

  `items.updated_at`       Date                                是 此商品最後修改時間

  `created_at`             Date                                是 Cart 建立時間

  `updated_at`             Date                                是 Cart 最後異動時間
  ----------------------------------------------------------------------------------------------------

### 4.4 `price_snapshot` 用途

`price_snapshot` 不取代 `products` 的即時售價。

它用來保存使用者將商品放入購物車時所看到的價格，後續可用於：

-   價格變動提示。
-   結帳前重新驗價。
-   棄單原因分析。
-   AI 分析價格敏感度。

正式成立 Order 時，仍應依專案定義的結帳規則重新確認成交價格。

------------------------------------------------------------------------

## 5. `cart_events` Collection

### 5.1 設計目的

`cart_events` 不保存「目前狀態」，而是保存每一次購物車行為。

原則：

> **Append-only：事件建立後原則上不修改、不覆蓋、不刪除。**

### 5.2 建議 Schema

``` json
{
  "_id": "ObjectId",
  "cart_id": "ObjectId",
  "user_id": "ObjectId/String",
  "event_type": "ADD",
  "product_id": "ObjectId/String",
  "quantity_before": 0,
  "quantity_after": 1,
  "price_snapshot": 590.0,
  "event_at": "ISODate",
  "metadata": {}
}
```

### 5.3 Event Type

Codex 第一階段至少實作：

``` text
ADD
REMOVE
QTY_CHANGE
CHECKOUT
ABANDON
```

定義：

-   `ADD`：商品加入購物車。
-   `REMOVE`：商品由購物車移除。
-   `QTY_CHANGE`：商品數量改變。
-   `CHECKOUT`：購物車進入成功結帳轉換。
-   `ABANDON`：依系統規則判定為棄單。

### 5.4 建議欄位

  ------------------------------------------------------------------------------------
  欄位                    型別                    說明
  ----------------------- ----------------------- ------------------------------------
  `_id`                   ObjectId                Event ID

  `cart_id`               ObjectId                對應 Cart

  `user_id`               ObjectId / String       使用者

  `event_type`            String                  事件類型

  `product_id`            ObjectId / String /     商品；CHECKOUT 等事件可視需要為 Null
                          Null                    

  `quantity_before`       Integer / Null          異動前數量

  `quantity_after`        Integer / Null          異動後數量

  `price_snapshot`        Decimal/Double / Null   事件發生時價格

  `event_at`              Date                    事件時間

  `metadata`              Object                  未來擴充來源、推薦模組、裝置等資訊
  ------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 6. 購物車生命週期

``` text
瀏覽商品
   ↓
加入商品
   ↓
建立 / 取得 Active Cart
   ↓
ADD / REMOVE / QTY_CHANGE
   ↓
持續更新 carts
   +
持續新增 cart_events
   │
   ├── 離開網站 → Active Cart 保留
   │
   ├── 超過棄單規則 → ABANDON
   │
   └── 成功結帳
          ↓
       建立 Order
          ↓
       CHECKOUT Event
          ↓
       Cart → converted
```

------------------------------------------------------------------------

## 7. Cart → Order 轉換規則

結帳成功時，Codex 應實作以下邏輯：

1.  取得該使用者目前 `active` Cart。
2.  驗證商品是否仍存在及可銷售。
3.  驗證庫存。
4.  重新確認商品成交價格。
5.  建立 `orders` Document。
6.  寫入 `CHECKOUT` cart event。
7.  將原 Cart `status` 改為 `converted`。
8.  保存原 Cart，不應直接刪除。
9.  使用者下一次加入商品時，再建立新的 Active Cart。

必須避免：

``` text
直接把 carts Document 改造成 orders Document
```

Cart 與 Order 必須維持不同 Collection 與不同生命週期。

------------------------------------------------------------------------

## 8. MongoDB Index 建議

Codex 建立／檢查以下索引：

### `carts`

-   `user_id`
-   `status`
-   `updated_at`
-   `user_id + status`

其中應確保同一 `user_id` 不會產生多份有效的 `active` Cart。實作時可評估
MongoDB partial unique index。

概念：

``` text
Unique:
user_id

Condition:
status == "active"
```

### `cart_events`

建議：

-   `cart_id + event_at`
-   `user_id + event_at`
-   `event_type + event_at`
-   `product_id + event_at`

用途包括購物歷程、AI 特徵、商品分析及棄單分析。

------------------------------------------------------------------------

## 9. AI / VibeInsight 資料應用

這兩個 Collection 不只是購物網站功能資料，也屬於 VibeCart AI 的 AI
行為資料來源。

### `carts`

提供：

-   目前購買意圖。
-   購物車商品組合。
-   即時推薦上下文。
-   購物車金額／品類特徵。

### `cart_events`

提供：

-   加入後移除行為。
-   商品反覆加入行為。
-   數量變動。
-   高意圖未購買商品。
-   棄單分析。
-   商品轉換分析。
-   使用者價格敏感度分析。
-   推薦模型／LLM 的行為上下文。

資料流概念：

``` text
carts + cart_events
        ↓
Behavior Features
        ↓
Recommendation / Analytics
        │
        ├── 猜你喜歡
        ├── 商品推薦
        ├── 棄單分析
        ├── 商品轉換分析
        └── VibeInsight
```

------------------------------------------------------------------------

## 10. Codex 實作任務

Codex 請依現有專案程式碼與 MongoDB 架構檢查後執行，不要破壞既有
Collection 或既有資料。

### Task 1：檢查現有 Schema

確認是否已存在：

-   `carts`
-   `cart_events`
-   `orders`
-   `users`
-   `products`

若已有同用途 Collection，優先評估相容與
migration，不要直接建立重複資料結構。

### Task 2：建立／更新 `carts`

完成：

-   Active Cart Schema
-   items array
-   timestamps
-   status
-   price_snapshot
-   validation
-   indexes

### Task 3：建立 `cart_events`

完成 Event Log Schema 與 indexes。

### Task 4：建立 Cart Service

至少提供：

``` text
get_active_cart(user_id)
add_item(user_id, product_id, quantity)
remove_item(user_id, product_id)
update_quantity(user_id, product_id, quantity)
checkout_cart(user_id)
```

每次 Cart 異動必須同步產生對應 `cart_events`。

### Task 5：處理併發與資料一致性

避免：

-   同一會員建立兩個 Active Cart。
-   快速連點造成重複 ADD。
-   quantity \<= 0。
-   商品不存在仍加入購物車。
-   結帳成功但 Cart 未 converted。
-   Order 建立失敗卻已清空 Cart。

若目前 MongoDB 部署環境支援 transaction，結帳流程優先評估
transaction；否則必須建立明確的錯誤回復與一致性機制。

### Task 6：保留 AI 擴充能力

不要把 `cart_events` 寫死成只能支援目前五種事件。

Schema 應允許未來擴充，例如：

``` text
VIEW
RECOMMEND_CLICK
SAVE_FOR_LATER
COUPON_APPLY
PRICE_CHANGE
RESTORE
```

但本版不要求全部實作。

------------------------------------------------------------------------

## 11. API 建議

若專案目前採 Flask / Python API，可依既有 API 命名規範整合：

``` text
GET    /api/cart
POST   /api/cart/items
PATCH  /api/cart/items/{product_id}
DELETE /api/cart/items/{product_id}
POST   /api/cart/checkout
```

實際 Route 名稱應優先遵循目前專案既有
conventions，不應為符合本文件而破壞既有 API。

------------------------------------------------------------------------

## 12. 驗收條件（Definition of Done）

Codex 完成更新後，至少確認：

-   [ ] 同一使用者只能取得一份 Active Cart。
-   [ ] 加入商品可正確建立或更新 Cart。
-   [ ] 相同商品再次加入可依規則更新 quantity。
-   [ ] 可修改 quantity。
-   [ ] quantity 不得小於 1；若 UI 採 0=刪除，後端必須明確轉為 REMOVE。
-   [ ] 可移除商品。
-   [ ] 每次 ADD 都建立 Event。
-   [ ] 每次 REMOVE 都建立 Event。
-   [ ] 每次 QTY_CHANGE 都建立 Event。
-   [ ] Cart 目前內容與 Event History 可分別查詢。
-   [ ] 使用者離站後 Active Cart 不會自動消失。
-   [ ] 結帳成功後建立 Order。
-   [ ] 結帳成功後 Cart 狀態改為 `converted`。
-   [ ] 結帳產生 CHECKOUT Event。
-   [ ] 原 Cart 歷史資料不因結帳被刪除。
-   [ ] `price_snapshot` 正確保存。
-   [ ] 必要 indexes 已建立。
-   [ ] 不破壞目前 `users`、`products`、`orders` 等既有資料。
-   [ ] 提供測試資料或 automated tests 驗證主要流程。

------------------------------------------------------------------------

## 13. Codex 執行原則

> **先檢查現有程式與 MongoDB
> Schema，再修改；禁止直接覆寫未知的既有結構。**

Codex 應：

1.  讀取目前專案 MongoDB model/schema、database initialization、API
    routes 與 service。
2.  比對本規格。
3.  列出需要新增、修改及 migration 的項目。
4.  以最小破壞原則更新。
5.  補充必要 indexes。
6.  補充測試。
7.  更新專案 MongoDB／API 文件。
8.  回報實際修改檔案、Schema 差異、migration 需求與測試結果。

------------------------------------------------------------------------

## 14. 最終架構結論

VibeCart AI 未結單購物車正式採用：

> **MongoDB Active Cart Document + Cart Event Log**

也就是：

``` text
Current State
    +
Event History
    ↓
Transactional Cart
    +
Behavior Data
    ↓
VibeCart Recommendation
    +
VibeInsight Analytics
```

這項設計同時滿足一般電商購物車操作與 VibeCart AI 後續
LLM／推薦／營運分析所需要的行為資料基礎。
