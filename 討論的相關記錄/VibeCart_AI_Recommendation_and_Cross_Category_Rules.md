# VibeCart AI｜購買行為、補貨頻率與破圈推薦規格

**專案：** VibeCart AI｜懂你想買、更懂怎麼賣！  
**版本：** v1.0  
**日期：** 2026-09-18

---

## 1. 文件目的

本文件定義以下推薦規則：

1. 使用者購買、加入購物車、搜尋與點擊行為的權重。
2. 依大類別與小類別分數產生「猜你喜歡」6 項商品。
3. 依市場籃子分析與前後購買序列產生破圈推薦4項商品。
4. 首次加入會員時，每個大類別隨機推薦1項商品。
5. 首次推薦商品必須為實際評價4.5星以上。
6. 消耗品的補貨週期與重複購買率。
7. 推薦結果的去重、排序、庫存與安全規則。

---

## 2. 行為權重

| 行為 | 事件 | 權重 |
|---|---|---:|
| 購買 | `PURCHASE` | 4 |
| 選購／加入購物車 | `ADD_TO_CART` | 3 |
| 搜尋 | `SEARCH` | 2 |
| 商品點擊／瀏覽 | `PRODUCT_VIEW` | 1 |

大類別上限為70，小類別上限為30。商品直接分數建議不設固定上限，但必須使用時間衰減。

---

## 3. 會員首次推薦

### 3.1 觸發時機

「第一次加入會員的首次推薦」應在會員完成註冊並建立 `user_id` 後觸發，而不是在尚未取得會員識別碼時觸發。

### 3.2 推薦規則

對每一個啟用中的大類別：

1. 搜尋該大類別中符合條件的商品。
2. 只允許 `rating_status = ACTUAL` 的商品。
3. `average_rating_display >= 4.5`。
4. 商品必須上架。
5. 商品必須可銷售或有可接受的預購狀態。
6. 依商品大類別分組。
7. 每個大類別亂數選1項。
8. 建立首次推薦快照，避免同一次頁面刷新得到不同商品。

### 3.3 評價條件的解釋

新商品預設4.0星不符合首次推薦的4.5星門檻。首次推薦只使用已產生至少一筆真實評價且實際平均值達到4.5星的商品。

建議額外設定最小評價數：

```text
minimum_rating_count = 3 或 5
```

若嚴格照需求，只檢查4.5星以上即可；但若沒有最小評價數，單一筆5星評價就可能被選入首次推薦池。建議在設定中保留可調整欄位。

### 3.4 首次推薦文件

建立 `first_member_recommendations`：

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
      "random_seed": "String",
      "position": 1
    }
  ],
  "rule_version": 1,
  "created_at": "ISODate",
  "expires_at": "ISODate"
}
```

### 3.5 隨機選取方式

不建議使用完全不可追蹤的 `Math.random()`。應保存：

- `random_seed`。
- `rule_version`。
- 候選池數量。
- 選取時間。
- 最終選中的商品。

MongoDB 可使用 aggregation 的 `$sample`，但正式推薦服務仍應保存結果快照：

```javascript
db.products.aggregate([
  {
    $match: {
      status: "active",
      is_ai_recommendable: true,
      rating_status: "ACTUAL",
      average_rating_display: { $gte: 4.5 },
      major_category_id: { $in: activeMajorCategoryIds }
    }
  },
  { $group: { _id: "$major_category_id", candidates: { $push: "$$ROOT" } } },
  { $project: {
      major_category_id: "$_id",
      product: { $arrayElemAt: ["$candidates", { $floor: { $multiply: [{ $rand: {} }, { $size: "$candidates" }] } }] }
  } }
])
```

若資料量很大，可先建立符合條件的推薦池，不要每次註冊都掃描整個 `products`。

### 3.6 首次推薦池

可使用 `recommendation_pools`：

```json
{
  "_id": "ObjectId",
  "pool_type": "FIRST_MEMBER",
  "major_category_id": "food",
  "product_ids": ["ObjectId/String"],
  "filters": {
    "rating_gte": 4.5,
    "rating_status": "ACTUAL",
    "status": "active"
  },
  "generated_at": "ISODate",
  "expires_at": "ISODate"
}
```

---

## 4. 「猜你喜歡」6項推薦

### 4.1 個人偏好分數

```text
personal_score(product)
= major_category_score
+ minor_category_score
+ product_direct_score × product_factor
```

第一版可完全依照指定規則：

```text
personal_score(product)
= major_category_score + minor_category_score
```

### 4.2 候選流程

```text
讀取 user_preference_scores
  ↓
找出大類別分數與小類別分數
  ↓
建立商品候選池
  ↓
排除缺貨、下架、不可推薦商品
  ↓
依分數排序
  ↓
套用商品補貨週期與最近購買排除
  ↓
品牌、小類別與SKU去重
  ↓
取前6項
```

### 4.3 建議排序公式

```text
final_personal_score
= behavior_score
+ rating_factor
+ stock_factor
+ replenishment_factor
- exposure_penalty
```

但行為分數仍應是主要因素，不要讓評價或庫存因素完全取代使用者興趣。

---

## 5. 破圈推薦4項

### 5.1 破圈推薦定義

破圈推薦是跨越使用者目前主要興趣類別，依據：

- 同籃購買關係。
- 前後購買順序。
- 商品用途與生活情境。
- 會員群體的統計關聯。

例如：

```text
嬰兒用品 → 飲料
個人香氛 → 女性護理
咖啡豆 → 濾紙
電鑽 → 鑽頭與螺絲
```

這些是待驗證假設，不是固定因果關係。

### 5.2 `cross_category_rules`

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

### 5.3 市場籃子指標

```text
support(A,B)
= 同時購買A與B的交易數 / 全部交易數
```

```text
confidence(A→B)
= 同時購買A與B的交易數 / 購買A的交易數
```

```text
lift(A→B)
= confidence(A→B) / P(B)
```

建議第一版最低門檻：

```text
antecedent_customer_count >= 500
co_purchase_count >= 50
confidence >= 0.05
lift >= 1.20
```

### 5.4 前後購買分析

同籃購買不能代表前後購買關係。建議建立 `product_purchase_sequences`：

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
  "created_at": "ISODate"
}
```

```text
P(B within 30d | A)
= 購買A後30天內購買B的客戶數 / 購買A的客戶數
```

### 5.5 破圈排序

```text
cross_score
= confidence × log(1 + lift) × log(1 + co_purchase_count)
```

實際推薦時再加入：

- 使用者目前大類別偏好。
- 商品是否有貨。
- 商品評價。
- 商品價格可接受度。
- 是否已被個人推薦區推薦。
- 推薦曝光頻率。

### 5.6 4項輸出規則

```text
破圈候選依 cross_score 排序
  ↓
排除個人推薦區已有商品
  ↓
排除缺貨與不可推薦商品
  ↓
最多同一小類別2項
  ↓
取4項
```

若不足4項，不要用低可信度規則硬湊，應顯示實際可用數量。

---

## 6. 補貨與重複購買

### 6.1 兩個不同指標

```text
年重複購買率
= 12個月內購買兩次以上的不同客戶數
/ 12個月內購買該商品的不同客戶總數
```

```text
年平均購買頻率
= 12個月有效訂單數
/ 12個月不同購買客戶數
```

### 6.2 商品週期類型

| 類型 | 說明 |
|---|---|
| `consumable` | 會持續消耗，例如尿布、食品、洗衣精。 |
| `durable` | 不容易損壞，例如手工具、家具。 |
| `semi_durable` | 可使用一段時間後補購，例如濾芯、燈泡。 |
| `seasonal` | 有季節性，例如防曬、冬季用品。 |

### 6.3 商品欄位

```json
{
  "product_lifecycle_type": "consumable",
  "replenishment_enabled": true,
  "expected_repurchase_interval_days": 45,
  "expected_purchase_frequency_year": 8.0,
  "minimum_repeat_frequency_year": 1.0,
  "replenishment_basis": "category_benchmark",
  "replenishment_confidence": 0.25,
  "repeat_purchase_rate_12m": 0.0,
  "avg_purchase_frequency_12m": 0.0,
  "median_repurchase_interval_days": null
}
```

新商品沒有資料時，`replenishment_basis` 應為 `category_benchmark`；有足夠交易量後改為 `historical`。

### 6.4 補貨推薦

```text
若商品為消耗品
且距離上次購買 >= expected_repurchase_interval_days
且商品仍可銷售
則提高補貨推薦分數
```

耐用品則採用：

```text
若距離上次購買 < 預估使用壽命
則降低同一商品推薦權重
```

---

## 7. 推薦結果總配置

```text
第一次加入會員：每個大類別隨機1項，限定實際4.5星以上

一般會員首頁：
- 猜你喜歡：6項
- 你可能也需要／破圈推薦：4項
```

推薦去重：

- 同一商品不可出現在兩個區塊。
- 同一 SKU 不重複出現。
- 同一小類別最多3項，破圈區最多2項。
- 缺貨商品不可推薦。
- 近期已購買的耐用品降低權重。
- 消耗品進入補貨週期後才重新提高權重。

---

## 8. 推薦紀錄

建立 `recommendation_logs`：

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId/String",
  "recommendation_id": "String",
  "recommendation_type": "FIRST_MEMBER",
  "algorithm_version": "v1.0",
  "items": [
    {
      "product_id": "ObjectId/String",
      "position": 1,
      "score": 72.4,
      "reason_code": "CATEGORY_RANDOM_HIGH_RATING"
    }
  ],
  "shown_at": "ISODate",
  "clicked_product_ids": [],
  "purchased_product_ids": []
}
```

推薦效果至少要追蹤：

```text
曝光數
點擊數
加入購物車數
購買數
推薦轉換率
推薦商品平均客單價
推薦後30日回購率
```

---

## 9. 安全與公平性

破圈推薦不可把性別、年齡或家庭角色當成確定事實。例如：

```text
男性買尿布，所以一定會買啤酒
女性買香氛，所以一定需要衛生棉
```

這類關係只能在統計上達到樣本量、confidence 與 lift 門檻時啟用，且推薦文案應使用：

```text
「您可能也會需要」
「常與此商品一起購買」
「其他相似購物情境的會員也常選購」
```

不要使用：

```text
「因為您是男性，所以推薦啤酒」
「女性都會需要衛生棉」
```

酒類、藥品、保健品、兒童用品與個人衛生用品應另行套用年齡、法規、敏感類別與推薦限制。

---

## 10. 驗收條件

- [ ] 新會員每個啟用大類別最多取得1項首次推薦。
- [ ] 首次推薦商品為實際評價4.5星以上。
- [ ] 預設4.0星商品不得進入首次推薦池。
- [ ] 首次推薦結果可被保存與重現。
- [ ] 一般個人推薦輸出6項。
- [ ] 破圈推薦輸出4項或實際可用數量。
- [ ] 同一商品不出現在兩個推薦區。
- [ ] 破圈規則保存support、confidence、lift與樣本數。
- [ ] 消耗品具備補貨週期。
- [ ] 耐用品不會被錯誤地高頻推薦。
- [ ] 每次推薦都保存演算法版本與推薦理由。
- [ ] 可計算推薦曝光、點擊、加入購物車與購買轉換。
