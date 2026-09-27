# VibeCart AI｜MongoDB 行為權重計分實作規格

**專案：** VibeCart AI｜懂你想買、更懂怎麼賣！  
**版本：** v1.0  
**日期：** 2026-09-18

---

## 1. 文件目的

本文件定義如何使用 MongoDB 保存與計算使用者行為權重，支援：

- 個人化商品推薦。
- 大類別與小類別偏好分數。
- 商品直接興趣分數。
- 購買、加入購物車、搜尋、點擊等行為追蹤。
- 行為時間衰減。
- 大類別與小類別分數上限。
- 會員首次推薦與後續推薦的資料來源。

本文件與購物車規格採用相同原則：目前狀態與事件歷史分離。購物車目前狀態保存在 `carts`，購物車歷史保存在 `cart_events`；一般使用者行為則保存在 `behavior_events`。

---

## 2. 行為權重

| 行為 | `event_type` | 原始權重 |
|---|---|---:|
| 購買 | `PURCHASE` | 4 |
| 加入購物車／選購 | `ADD_TO_CART` | 3 |
| 搜尋 | `SEARCH` | 2 |
| 商品點擊／瀏覽 | `PRODUCT_VIEW` | 1 |

建議將權重放在設定集合，而不是寫死在程式碼：

```json
{
  "_id": "default_v1",
  "version": 1,
  "weights": {
    "PURCHASE": 4,
    "ADD_TO_CART": 3,
    "SEARCH": 2,
    "PRODUCT_VIEW": 1
  },
  "caps": {
    "major_category": 70,
    "minor_category": 30
  },
  "enabled": true,
  "created_at": "ISODate"
}
```

---

## 3. `behavior_events` Collection

### 3.1 建議文件結構

```json
{
  "_id": "ObjectId",
  "event_id": "String",
  "user_id": "ObjectId/String",
  "session_id": "String",
  "event_type": "PURCHASE",
  "product_id": "ObjectId/String",
  "major_category_id": "ObjectId/String",
  "minor_category_id": "ObjectId/String",
  "quantity": 1,
  "order_id": "ObjectId/String/null",
  "cart_id": "ObjectId/String/null",
  "search_query": null,
  "source": "organic",
  "recommendation_id": null,
  "event_at": "ISODate",
  "processed_at": null,
  "score_version": 1,
  "metadata": {},
  "created_at": "ISODate"
}
```

### 3.2 欄位規則

| 欄位 | 必填 | 說明 |
|---|---:|---|
| `event_id` | 是 | 前端或 API 產生的冪等鍵，避免重複計分。 |
| `user_id` | 是 | 已登入會員的識別碼。匿名使用者可先使用 `anonymous_id`。 |
| `session_id` | 是 | 瀏覽工作階段。 |
| `event_type` | 是 | `PURCHASE`、`ADD_TO_CART`、`SEARCH`、`PRODUCT_VIEW`。 |
| `product_id` | 視事件而定 | 搜尋事件可為 `null`，其他事件通常必填。 |
| `major_category_id` | 是 | 事件發生當下的商品大類別快照。 |
| `minor_category_id` | 是 | 事件發生當下的商品小類別快照。 |
| `quantity` | 否 | 購買或加入購物車數量，預設為 1。 |
| `order_id` | 購買必填 | 對應已成立且有效的訂單。 |
| `event_at` | 是 | 行為發生時間。 |
| `processed_at` | 否 | 分數處理完成時間。 |
| `score_version` | 是 | 當時使用的計分規則版本。 |

`behavior_events` 建議採 append-only。若事件錯誤，不直接修改原始事件，應建立更正事件或將原事件標記為無效。

---

## 4. `user_preference_scores` Collection

### 4.1 建議文件結構

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
  "cross_category_scores": {
    "baby_care|beverages": 8.0
  },
  "last_processed_event_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 4.2 分數計算

每個事件的原始權重如下：

```text
PURCHASE    = 4
ADD_TO_CART = 3
SEARCH      = 2
PRODUCT_VIEW = 1
```

大類別：

```python
new_major_score = min(old_major_score + weight, 70)
```

小類別：

```python
new_minor_score = min(old_minor_score + weight, 30)
```

商品：

```python
new_product_score = old_product_score + weight
```

如果購買數量要影響商品分數，建議只對 `PURCHASE` 使用受限數量係數，避免大量購買造成異常偏高：

```python
quantity_factor = min(quantity, 3)
product_increment = weight * quantity_factor
```

大類別與小類別通常以一次事件計分，不建議直接乘上購買數量。

---

## 5. 時間衰減

若只累加分數，舊行為會永久影響推薦。建議採用半衰期：

```text
decayed_score = raw_score * 0.5 ** (age_days / half_life_days)
```

建議半衰期：

| 行為 | 建議半衰期 |
|---|---:|
| `PURCHASE` | 365 天 |
| `ADD_TO_CART` | 180 天 |
| `SEARCH` | 90 天 |
| `PRODUCT_VIEW` | 30 天 |

如果要簡化第一版，可採固定每 30 天乘以 0.8 的方式，但半衰期模型較容易針對不同商品生命週期調整。

---

## 6. MongoDB Update 範例

### 6.1 商品行為計分

```python
from datetime import datetime, timezone

WEIGHTS = {
    "PURCHASE": 4,
    "ADD_TO_CART": 3,
    "SEARCH": 2,
    "PRODUCT_VIEW": 1,
}

MAJOR_CAP = 70
MINOR_CAP = 30


def build_score_update(event):
    weight = WEIGHTS[event["event_type"]]
    major_key = f"major_categories.{event['major_category_id']}"
    minor_key = f"minor_categories.{event['minor_category_id']}"
    product_key = f"products.{event['product_id']}"
    now = datetime.now(timezone.utc)

    return {
        "$inc": {
            f"{major_key}.raw_score": weight,
            f"{minor_key}.raw_score": weight,
            f"{product_key}.raw_score": weight,
        },
        "$set": {
            "user_id": event["user_id"],
            f"{major_key}.last_event_at": event["event_at"],
            f"{minor_key}.last_event_at": event["event_at"],
            f"{product_key}.last_event_at": event["event_at"],
            "last_processed_event_at": event["event_at"],
            "updated_at": now,
        },
    }
```

實務上，大類別與小類別上限需要使用 aggregation pipeline update，或先讀取目前分數再以 transaction 更新，避免超過上限。

### 6.2 建議使用 aggregation pipeline 保護上限

```javascript
db.user_preference_scores.updateOne(
  { user_id: userId },
  [
    {
      $set: {
        [`major_categories.${majorId}.score`]: {
          $min: [
            {
              $add: [
                { $ifNull: [`$major_categories.${majorId}.score`, 0] },
                weight
              ]
            },
            70
          ]
        },
        [`minor_categories.${minorId}.score`]: {
          $min: [
            {
              $add: [
                { $ifNull: [`$minor_categories.${minorId}.score`, 0] },
                weight
              ]
            },
            30
          ]
        },
        updated_at: new Date()
      }
    }
  ],
  { upsert: true }
)
```

若使用動態欄位名稱，應由後端安全地組合欄位路徑，並拒絕包含 `.`、`$` 或非法字元的識別碼。

---

## 7. 事件去重與處理器

建議建立 `behavior_event_processing` 或直接在 `behavior_events` 使用 `processed_at`，但最安全的方式是建立唯一索引：

```javascript
db.behavior_events.createIndex(
  { event_id: 1 },
  { unique: true }
)
```

計分流程：

```text
接收事件
  ↓
以 event_id 寫入 behavior_events
  ↓
若 duplicate key：忽略，不重複計分
  ↓
讀取事件規則與權重
  ↓
更新 user_preference_scores
  ↓
標記 processed_at
  ↓
寫入 score_update_logs
```

若要支援可靠重試，建議使用 Outbox／Queue 或 MongoDB Change Streams，不要在 HTTP 請求中只完成一半流程。

---

## 8. 索引

```javascript
db.behavior_events.createIndex({ event_id: 1 }, { unique: true })
db.behavior_events.createIndex({ user_id: 1, event_at: -1 })
db.behavior_events.createIndex({ user_id: 1, event_type: 1, event_at: -1 })
db.behavior_events.createIndex({ product_id: 1, event_at: -1 })
db.behavior_events.createIndex({ processed_at: 1, event_at: 1 })
db.user_preference_scores.createIndex({ user_id: 1 }, { unique: true })
```

---

## 9. 推薦候選分數

對商品 `p`：

```text
behavior_score(p)
= major_category_score(p)
+ minor_category_score(p)
+ product_score(p) × product_factor
```

如果完全依照第一版規則：

```text
behavior_score(p)
= major_category_score(p) + minor_category_score(p)
```

建議候選排序後再套用：

- 上架狀態。
- 庫存狀態。
- AI 推薦開關。
- 評價門檻。
- 最近已購買與補貨週期。
- 品牌與小類別去重。
- 推薦曝光頻率限制。

---

## 10. 驗收條件

- [ ] 事件有唯一 `event_id`。
- [ ] 重送相同事件不會重複加分。
- [ ] 購買權重為 4。
- [ ] 加入購物車權重為 3。
- [ ] 搜尋權重為 2。
- [ ] 商品點擊權重為 1。
- [ ] 大類別分數最高為 70。
- [ ] 小類別分數最高為 30。
- [ ] 商品分數可單獨累積。
- [ ] 可依時間衰減。
- [ ] 原始事件可追查。
- [ ] 分數版本可追查。
- [ ] 重新計算結果可與即時累計結果比對。
