# VibeCart AI｜MongoDB 完整資料結構規格

**專案：** VibeCart AI｜懂你想買、更懂怎麼賣！  
**版本：** v1.0  
**日期：** 2026-09-18

---

## 1. 系統範圍

本文件整合以下需求：

- 商品主檔與商品分類。
- SKU、庫存與物流。
- 客戶5星評價。
- 新商品預設4.0星，第一筆實際評價建立後移除預設評分。
- 平均評分小數點第一位顯示，第二位無條件進位。
- 購買、加入購物車、搜尋、點擊行為權重。
- 大類別上限70，小類別上限30。
- 猜你喜歡推薦6項。
- 破圈與邏輯關聯推薦4項。
- 新會員每個大類別亂數推薦1項4.5星以上商品。
- 消耗品重複購買率與補貨週期。
- MongoDB 購物車目前狀態與事件歷史分離。

---

## 2. Collection 總覽

```text
MongoDB
│
├── users
├── products
├── product_skus
├── product_reviews
├── product_repurchase_stats
├── categories
├── brands
├── orders
├── order_items
├── carts
├── cart_events
├── behavior_events
├── user_preference_scores
├── cross_category_rules
├── product_purchase_sequences
├── recommendation_pools
├── first_member_recommendations
├── recommendation_logs
└── system_configs
```

---

## 3. `users`

```json
{
  "_id": "ObjectId",
  "email": "String",
  "display_name": "String",
  "status": "active",
  "member_level": "normal",
  "registered_at": "ISODate",
  "first_recommendation_generated_at": null,
  "last_login_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

欄位規則：

- `registered_at` 用於判斷是否首次加入會員。
- `first_recommendation_generated_at` 設為非空後，不得再次產生首次會員推薦，除非管理員執行明確重置。
- 不建議把性別、家庭角色等敏感推論直接寫入推薦條件。

索引：

```javascript
db.users.createIndex({ email: 1 }, { unique: true })
db.users.createIndex({ registered_at: 1 })
```

---

## 4. `categories`

```json
{
  "_id": "ObjectId",
  "category_code": "FOOD",
  "name": "食品專區",
  "level": 1,
  "parent_id": null,
  "path": ["FOOD"],
  "status": "active",
  "sort_order": 10,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

小類別範例：

```json
{
  "category_code": "COFFEE",
  "name": "咖啡茶飲",
  "level": 2,
  "parent_id": "FOOD_OBJECT_ID",
  "path": ["FOOD", "COFFEE"],
  "status": "active"
}
```

商品必須保存分類快照，避免分類改名後歷史行為無法還原。

---

## 5. `products`

```json
{
  "_id": "ObjectId",
  "product_code": "GRO-BABY-DIA-001",
  "product_name": "嬰兒紙尿布",
  "product_aliases": ["尿布", "紙尿褲"],
  "brand_id": "ObjectId/String/null",
  "major_category_id": "baby_care",
  "minor_category_id": "diaper",
  "category_path": ["baby_care", "diaper"],
  "summary": "適合日常育兒使用的吸收型紙尿布。",
  "description": "完整商品說明",
  "usage_scenarios": ["育兒", "家庭補貨"],
  "target_segments": ["家庭", "父母"],
  "product_tags": ["消耗品", "補貨型商品"],
  "status": "active",
  "is_ai_recommendable": true,
  "image_urls": [],
  "shipping_profile_id": "ObjectId/String/null",
  "rating_status": "DEFAULT",
  "rating_default_value": 4.0,
  "rating_sum": 0,
  "rating_count": 0,
  "average_rating_raw": null,
  "average_rating_display": 4.0,
  "rating_distribution": {
    "star_1": 0,
    "star_2": 0,
    "star_3": 0,
    "star_4": 0,
    "star_5": 0
  },
  "product_lifecycle_type": "consumable",
  "replenishment_enabled": true,
  "expected_repurchase_interval_days": 45,
  "expected_purchase_frequency_year": 8.0,
  "minimum_repeat_frequency_year": 1.0,
  "replenishment_basis": "category_benchmark",
  "replenishment_confidence": 0.25,
  "repeat_purchase_rate_12m": null,
  "repeat_customer_count_12m": 0,
  "unique_buyer_count_12m": 0,
  "order_count_12m": 0,
  "avg_purchase_frequency_12m": null,
  "median_repurchase_interval_days": null,
  "last_repurchase_calculated_at": null,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 5.1 評價規則

新商品：

```text
rating_status = DEFAULT
rating_default_value = 4.0
rating_sum = 0
rating_count = 0
average_rating_display = 4.0
```

第一筆有效評價建立後：

```text
rating_status = ACTUAL
rating_default_value = null 或保留為歷史設定
rating_sum = 實際星數
rating_count = 1
average_rating_raw = 實際星數
average_rating_display = 實際星數
```

平均評分：

```text
average_rating_display
= ceil((rating_sum / rating_count) * 10) / 10
```

注意：這是小數點第二位無條件進位，不是一般四捨五入。

### 5.2 重複購買率規則

```text
repeat_purchase_rate_12m
= 12個月內購買兩次以上的不同客戶數
/ 12個月內不同購買客戶總數
```

```text
avg_purchase_frequency_12m
= 12個月有效訂單數
/ 12個月不同購買客戶數
```

新商品沒有歷史交易時：

```text
replenishment_basis = category_benchmark
replenishment_confidence = 低
```

有足夠歷史資料後：

```text
replenishment_basis = historical
replenishment_confidence = 依樣本量與穩定度計算
```

---

## 6. `product_skus`

```json
{
  "_id": "ObjectId",
  "product_id": "ObjectId/String",
  "sku_code": "GRO-BABY-DIA-001-M-XL",
  "variant_attributes": {
    "size": "M",
    "pack": "XL"
  },
  "price": 399.0,
  "cost_price": null,
  "stock_quantity": 100,
  "reserved_quantity": 0,
  "available_quantity": 100,
  "safety_stock": 10,
  "stock_status": "in_stock",
  "barcode": null,
  "weight_grams": 1200,
  "status": "active",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

索引：

```javascript
db.product_skus.createIndex({ sku_code: 1 }, { unique: true })
db.product_skus.createIndex({ product_id: 1, status: 1 })
```

---

## 7. `product_reviews`

```json
{
  "_id": "ObjectId",
  "product_id": "ObjectId/String",
  "user_id": "ObjectId/String",
  "order_id": "ObjectId/String",
  "order_item_id": "ObjectId/String",
  "rating": 5,
  "review_title": "很實用",
  "review_content": "商品符合描述。",
  "verified_purchase": true,
  "status": "published",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

限制：

- `rating` 必須介於1～5。
- 必須對應已完成或已送達訂單。
- 同一使用者對同一訂單明細只能評價一次。
- 只有 `published` 評價可計入商品平均評分。

索引：

```javascript
db.product_reviews.createIndex(
  { user_id: 1, order_item_id: 1 },
  { unique: true }
)
db.product_reviews.createIndex({ product_id: 1, status: 1 })
```

---

## 8. `orders` 與 `order_items`

### `orders`

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "order_number": "VC202609180001",
  "status": "completed",
  "payment_status": "paid",
  "shipping_status": "delivered",
  "subtotal": 1000.0,
  "shipping_fee": 60.0,
  "total_amount": 1060.0,
  "ordered_at": "ISODate",
  "completed_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### `order_items`

```json
{
  "_id": "ObjectId",
  "order_id": "ObjectId/String",
  "user_id": "ObjectId/String",
  "product_id": "ObjectId/String",
  "sku_id": "ObjectId/String",
  "product_code_snapshot": "GRO-BABY-DIA-001",
  "product_name_snapshot": "嬰兒紙尿布",
  "major_category_id_snapshot": "baby_care",
  "minor_category_id_snapshot": "diaper",
  "quantity": 2,
  "unit_price": 399.0,
  "line_total": 798.0,
  "created_at": "ISODate"
}
```

`order_items` 是計算商品購買頻率、商品關聯及前後購買順序的必要資料。

---

## 9. `carts` 與 `cart_events`

附件規格採用：

```text
carts = Current State
cart_events = Event History
```

### `carts`

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "status": "active",
  "items": [
    {
      "product_id": "ObjectId/String",
      "sku_id": "ObjectId/String",
      "quantity": 2,
      "price_snapshot": 399.0,
      "added_at": "ISODate",
      "updated_at": "ISODate"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### `cart_events`

```json
{
  "_id": "ObjectId",
  "event_id": "String",
  "cart_id": "ObjectId",
  "user_id": "ObjectId/String",
  "event_type": "ADD",
  "product_id": "ObjectId/String",
  "sku_id": "ObjectId/String/null",
  "quantity_before": 0,
  "quantity_after": 1,
  "price_snapshot": 399.0,
  "event_at": "ISODate",
  "metadata": {},
  "created_at": "ISODate"
}
```

事件類型至少包含：

```text
ADD
REMOVE
QTY_CHANGE
CHECKOUT
ABANDON
```

索引：

```javascript
db.carts.createIndex({ user_id: 1, status: 1 })
db.carts.createIndex(
  { user_id: 1 },
  { unique: true, partialFilterExpression: { status: "active" } }
)
db.cart_events.createIndex({ event_id: 1 }, { unique: true })
db.cart_events.createIndex({ user_id: 1, event_at: -1 })
db.cart_events.createIndex({ product_id: 1, event_at: -1 })
```

結帳流程必須：

1. 驗證 active cart。
2. 驗證商品、庫存與價格。
3. 建立 order 與 order_items。
4. 建立 `CHECKOUT` event。
5. 將 cart 改為 `converted`。
6. 保留原 cart，不直接刪除。

---

## 10. `behavior_events`

```json
{
  "_id": "ObjectId",
  "event_id": "String",
  "user_id": "ObjectId/String",
  "anonymous_id": "String/null",
  "session_id": "String",
  "event_type": "PURCHASE",
  "product_id": "ObjectId/String/null",
  "major_category_id": "ObjectId/String/null",
  "minor_category_id": "ObjectId/String/null",
  "quantity": 1,
  "order_id": "ObjectId/String/null",
  "cart_id": "ObjectId/String/null",
  "search_query": null,
  "source": "organic",
  "recommendation_id": null,
  "event_at": "ISODate",
  "score_version": 1,
  "processed_at": null,
  "metadata": {},
  "created_at": "ISODate"
}
```

行為權重：

```text
PURCHASE = 4
ADD_TO_CART = 3
SEARCH = 2
PRODUCT_VIEW = 1
```

索引：

```javascript
db.behavior_events.createIndex({ event_id: 1 }, { unique: true })
db.behavior_events.createIndex({ user_id: 1, event_at: -1 })
db.behavior_events.createIndex({ user_id: 1, event_type: 1, event_at: -1 })
db.behavior_events.createIndex({ product_id: 1, event_at: -1 })
db.behavior_events.createIndex({ processed_at: 1, event_at: 1 })
```

---

## 11. `user_preference_scores`

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "score_version": 1,
  "major_categories": {
    "food": {
      "raw_score": 42.0,
      "score": 42.0,
      "last_event_at": "ISODate"
    }
  },
  "minor_categories": {
    "coffee": {
      "raw_score": 22.0,
      "score": 22.0,
      "last_event_at": "ISODate"
    }
  },
  "products": {
    "PROD-001": {
      "raw_score": 9.0,
      "score": 8.4,
      "last_event_at": "ISODate"
    }
  },
  "cross_category_scores": {},
  "last_processed_event_at": "ISODate",
  "updated_at": "ISODate"
}
```

規則：

```text
major_categories score <= 70
minor_categories score <= 30
product score 使用時間衰減
```

時間衰減：

```text
decayed_score = raw_score × 0.5 ** (age_days / half_life_days)
```

建議半衰期：

```text
PURCHASE: 365天
ADD_TO_CART: 180天
SEARCH: 90天
PRODUCT_VIEW: 30天
```

索引：

```javascript
db.user_preference_scores.createIndex({ user_id: 1 }, { unique: true })
```

---

## 12. `product_repurchase_stats`

```json
{
  "_id": "ObjectId",
  "product_id": "ObjectId/String",
  "major_category_id": "ObjectId/String",
  "minor_category_id": "ObjectId/String",
  "period_type": "12m",
  "period_start": "ISODate",
  "period_end": "ISODate",
  "unique_buyer_count": 1000,
  "repeat_customer_count": 650,
  "order_count": 2200,
  "repeat_purchase_rate": 0.65,
  "avg_purchase_frequency": 2.2,
  "median_repurchase_interval_days": 91,
  "p25_repurchase_interval_days": 45,
  "p75_repurchase_interval_days": 150,
  "sample_size_status": "adequate",
  "calculated_at": "ISODate"
}
```

建議以每日或每週批次更新，不要在每一筆訂單寫入時同步重算完整12個月統計。

---

## 13. `cross_category_rules`

```json
{
  "_id": "ObjectId",
  "antecedent": {
    "major_category_id": "baby_care",
    "minor_category_id": "diaper"
  },
  "consequent": {
    "major_category_id": "beverages",
    "minor_category_id": "beer"
  },
  "window_days": 30,
  "support": 0.018,
  "confidence": 0.143,
  "lift": 2.31,
  "co_purchase_count": 320,
  "antecedent_customer_count": 2240,
  "rule_score": 0.0,
  "minimum_sample_size": 500,
  "source": "historical_transactions",
  "status": "active",
  "calculated_at": "ISODate"
}
```

啟用門檻建議：

```text
antecedent_customer_count >= 500
co_purchase_count >= 50
confidence >= 0.05
lift >= 1.20
```

---

## 14. `product_purchase_sequences`

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "first_product_id": "ObjectId/String",
  "next_product_id": "ObjectId/String",
  "first_order_id": "ObjectId/String",
  "next_order_id": "ObjectId/String",
  "days_between": 21,
  "window_days": 30,
  "first_major_category_id": "baby_care",
  "next_major_category_id": "beverages",
  "created_at": "ISODate"
}
```

用途：

- A 商品購買後30天內是否購買B。
- A 商品是否提高B的購買機率。
- 補貨與交叉銷售時間預測。

---

## 15. `recommendation_pools`

首次會員推薦池：

```json
{
  "_id": "ObjectId",
  "pool_type": "FIRST_MEMBER",
  "major_category_id": "food",
  "product_ids": ["ObjectId/String"],
  "filters": {
    "rating_status": "ACTUAL",
    "average_rating_display_gte": 4.5,
    "status": "active",
    "is_ai_recommendable": true
  },
  "generated_at": "ISODate",
  "expires_at": "ISODate"
}
```

首次會員推薦規則：

```text
每一個啟用大類別隨機1項
實際評價平均 >= 4.5
不可使用新商品預設4.0星
保存random_seed與推薦快照
```

---

## 16. `first_member_recommendations`

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "recommendation_session_id": "String",
  "recommendation_type": "FIRST_MEMBER",
  "items": [
    {
      "major_category_id": "food",
      "product_id": "ObjectId/String",
      "average_rating_display": 4.8,
      "rating_count": 22,
      "position": 1
    }
  ],
  "rule_version": 1,
  "random_seed": "String",
  "created_at": "ISODate"
}
```

`users.first_recommendation_generated_at` 與本 Collection 的 `user_id` 應共同保證首次推薦不重複產生。

---

## 17. `recommendation_logs`

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "recommendation_id": "String",
  "recommendation_type": "PERSONALIZED",
  "algorithm_version": "v1.0",
  "items": [
    {
      "product_id": "ObjectId/String",
      "position": 1,
      "score": 72.4,
      "reason_code": "HIGH_CATEGORY_AFFINITY"
    }
  ],
  "shown_at": "ISODate",
  "clicked_product_ids": [],
  "added_to_cart_product_ids": [],
  "purchased_product_ids": [],
  "created_at": "ISODate"
}
```

---

## 18. 推薦流程

### 18.1 首次會員

```text
會員註冊完成
  ↓
確認沒有 first_recommendation_generated_at
  ↓
從每個大類別推薦池隨機選1項
  ↓
只允許實際評價4.5星以上
  ↓
建立 first_member_recommendations
  ↓
更新 users.first_recommendation_generated_at
```

### 18.2 一般猜你喜歡

```text
behavior_events / cart_events / orders
  ↓
user_preference_scores
  ↓
大類別分數 + 小類別分數
  ↓
候選商品排序
  ↓
補貨、庫存、評價與去重
  ↓
輸出6項
```

### 18.3 破圈推薦

```text
orders + order_items
  ↓
同籃分析與前後序列分析
  ↓
cross_category_rules
  ↓
依confidence、lift、sample size篩選
  ↓
排除已推薦商品
  ↓
輸出4項
```

---

## 19. 建議索引總表

```javascript
// 商品
db.products.createIndex({ product_code: 1 }, { unique: true })
db.products.createIndex({ major_category_id: 1, minor_category_id: 1, status: 1 })
db.products.createIndex({ status: 1, average_rating_display: -1 })
db.products.createIndex({ is_ai_recommendable: 1, status: 1, major_category_id: 1 })

// 訂單
db.orders.createIndex({ user_id: 1, ordered_at: -1 })
db.orders.createIndex({ status: 1, ordered_at: -1 })
db.order_items.createIndex({ product_id: 1, created_at: -1 })
db.order_items.createIndex({ user_id: 1, created_at: -1 })
db.order_items.createIndex({ order_id: 1 })

// 評價
db.product_reviews.createIndex({ product_id: 1, status: 1 })
db.product_reviews.createIndex({ user_id: 1, order_item_id: 1 }, { unique: true })

// 行為
db.behavior_events.createIndex({ event_id: 1 }, { unique: true })
db.behavior_events.createIndex({ user_id: 1, event_at: -1 })

// 購物車
db.carts.createIndex({ user_id: 1, status: 1 })
db.carts.createIndex({ user_id: 1 }, { unique: true, partialFilterExpression: { status: "active" } })
db.cart_events.createIndex({ event_id: 1 }, { unique: true })
db.cart_events.createIndex({ user_id: 1, event_at: -1 })

// 使用者分數
db.user_preference_scores.createIndex({ user_id: 1 }, { unique: true })

// 推薦規則
db.cross_category_rules.createIndex({ "antecedent.major_category_id": 1, status: 1 })
db.cross_category_rules.createIndex({ "antecedent.minor_category_id": 1, confidence: -1, lift: -1 })
```

---

## 20. 交易一致性

結帳時建議使用 MongoDB transaction：

```text
建立 orders
建立 order_items
建立 PURCHASE behavior_events
建立 CHECKOUT cart_event
更新 carts.status = converted
更新庫存
```

若部署環境不支援 transaction，必須使用明確的 outbox、重試與補償機制，避免：

- 訂單已成立但購買行為未記錄。
- 購買行為已記錄但付款失敗。
- Cart 已轉換但 Order 不存在。
- 庫存扣除但訂單建立失敗。

---

## 21. 批次計算任務

### 每次行為事件

- 寫入 `behavior_events`。
- 計算使用者偏好分數。
- 更新 `user_preference_scores`。

### 每日

- 更新商品評價彙總。
- 更新庫存與商品可推薦狀態。
- 產生或更新首次推薦池。
- 處理新增訂單事件。

### 每週

- 計算商品12個月重複購買率。
- 計算平均購買頻率與再購買間隔。
- 更新同籃購買規則。
- 更新前後購買序列規則。
- 檢查破圈規則樣本量與穩定度。

### 每月

- 評估權重版本效果。
- 評估推薦點擊率與購買轉換率。
- 比較不同推薦模型版本。
- 淘汰低信心或長期未觸發的破圈規則。

---

## 22. Definition of Done

- [ ] 商品主檔可保存大類別、小類別、摘要、說明與出貨設定。
- [ ] 商品新上架預設顯示4.0星，但評價數為0。
- [ ] 第一筆有效評價後，預設評分不再計入。
- [ ] 平均評分小數點第二位無條件進位。
- [ ] 客戶只能對有效訂單商品評價。
- [ ] 行為事件可保存購買、加入購物車、搜尋與點擊。
- [ ] 行為事件具備唯一鍵，重送不重複計分。
- [ ] 大類別上限70。
- [ ] 小類別上限30。
- [ ] 新會員每個大類別亂數推薦1項實際4.5星以上商品。
- [ ] 首次推薦結果有快照與規則版本。
- [ ] 一般猜你喜歡輸出6項。
- [ ] 破圈推薦輸出4項或可用數量。
- [ ] 破圈規則保存support、confidence、lift與樣本數。
- [ ] 商品具備重複購買率與補貨週期欄位。
- [ ] 可區分消耗品與耐用品。
- [ ] 購物車仍維持Current State與Event Log分離。
- [ ] 結帳流程可一致地建立Order、Order Items與Purchase Event。
- [ ] 推薦曝光、點擊、加購與購買可被追蹤。
