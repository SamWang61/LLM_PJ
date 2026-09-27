# LLM 購物網站專題｜四週進度跟蹤表 v2.0

> 文件版本：v2.0  
> 原始版本：v1.0（2026-09-03）  
> 本次修訂：2026-09-08  
> 專案期間：2026-09-05～2026-10-02（四週）  
> 專案人數：4 人  
> 專題基底：2025 亮點士林第 3 組 **MuscleCore 運動用品電商網站**  
> 本次主要修訂依據：舊站 36 頁報告、13～16 頁展示影片、9/4 課堂「API／雲端模型 vs Local／本機模型」要求，以及前次 VibeCart AI／InsightCart AI 討論結果。  
> 建議主技術：**Python Flask＋Jinja2＋Bootstrap 5＋MongoDB Atlas＋Hugging Face 模型＋LLM API**

---

## 0. 本次修訂摘要（v1.0 → v2.0）

本版不再只把舊站視為「參考網站」，而是將它正式定義為 **功能與操作流程基底**，重新以 Python 架構改寫；同時依老師 9/4 課堂要求，將 AI 架構調整為可清楚展示兩種模式差異的 **Hybrid AI 雙路線**。

### 本版六項核心修正

1. **購物網站本體沿用 MuscleCore 運動商品電商的操作邏輯與畫面流程**，但後端、路由、登入與資料存取改以 Python Flask 重寫。
2. **登入角色明確分為 Customer／Admin**：一般會員登入後進入購物網站與會員中心；管理者登入後進入後台。
3. **後台新增兩大 AI 板塊**，讓成果展示不只是「網站加一個聊天機器人」。
4. **AI 同時呈現兩種技術路線**：
   - Local／本機模型：以 Hugging Face 輕量模型做商品語意向量與推薦。
   - API／雲端 LLM：做推薦理由、營運摘要與決策建議。
5. **不購置 GPU／AI 主機**：Local 路線限定為可在一般電腦 CPU 執行的小型模型與預先計算；大型生成式模型以 API 為主。
6. 原舊站的金流、LINE BOT、複雜 Email 驗證等功能移至 Could／Future，避免四週專題被功能數量拖垮。

> **專題展示主句：**  
> **同一個電商後台，用 Local AI 做「找得準」，用 Cloud LLM 做「說得懂、看得深」。**

---

# 一、專案目標與定位

## 1.1 專題正式定位

本專題以陳仁千先前參與完成的 **MuscleCore 運動用品電商網站**為功能框架，重新以 Python Flask、CSS 套件與 MongoDB Atlas 建置，保留原本成熟的運動商品網購流程，再加入兩種 AI 架構的實際應用比較。

系統分成三個層次：

```text
使用者帳戶
│
├─ Customer／一般會員
│   └─ 運動用品購物網站
│      ├─ 商品瀏覽／分類／搜尋
│      ├─ 商品詳情
│      ├─ 購物車／結帳（MVP 可簡化）
│      ├─ 會員中心／訂單紀錄
│      └─ 接收 AI 推薦結果
│
└─ Admin／管理者
    └─ 管理後台
       ├─ 商品管理
       ├─ 訂單管理
       ├─ 會員管理
       ├─ AI 板塊 A：Local Recommendation Engine
       └─ AI 板塊 B：Cloud LLM Business Insight
```

## 1.2 專題價值

本專題不是重新發明一個購物車，而是把已知可行的電商流程改造成一個 **Python＋MongoDB＋Hybrid AI 的完整資訊系統**。

- **前台價值**：使用者能正常購物，並看到由 AI 產生的推薦結果。
- **後台價值**：管理者不只 CRUD，而能直接看到「商品關聯」與「營運洞察」。
- **技術價值**：同一專題內明確比較 **Local Model 與 API LLM** 的角色、限制與成本差異。
- **展示價值**：老師可以直接從畫面看出兩種 AI 不是換名字，而是解決不同問題。

---

# 二、舊 MuscleCore 網站可利用的完整細節盤點

> 來源：`[第3組]運動用品電商網站_報告(亮點士林2025 JS全端開發).pdf` 與 13～16 頁展示影片。

## 2.1 舊站可直接承接的使用流程

### A. 前台購物網站

依報告第 13～15 頁與展示影片可確認舊站已有以下操作概念：

- MuscleCore 品牌首頁與 Hero Banner。
- 上方導覽列／商品分類入口。
- 運動商品卡片式列表。
- 商品名稱、價格、圖片、加入購物車。
- 商品詳情頁。
- 商品數量調整。
- 會員註冊、登入。
- 會員中心。
- 個人資料管理。
- 密碼修改。
- 訂單紀錄與訂單狀態。
- 購物車品項增減／刪除。
- 購物車總額計算。
- 結帳頁、收件資料、付款方式。

### B. 管理後台

依報告第 16～18 頁與後台展示影片，可確認舊站已有：

- 管理者登入頁。
- Dashboard 首頁。
- 商品管理。
- 商品新增／修改／刪除。
- 訂單管理。
- 訂單清單與狀態。
- 會員資料管理。
- 後台側邊導覽列。
- 管理介面採卡片／表格型資訊呈現。

### C. 舊資料庫概念

報告第 18、24、29～33 頁呈現 MongoDB Atlas 的使用方式，舊站主要資料集合概念為：

```text
shopping_mall
├─ admin
├─ members
├─ products
└─ orders
```

本專題可以承接這四類資料概念，但建議 Python 重構時改成更容易維護的 Schema。

## 2.2 舊技術架構與本專題重寫對照

| 層級 | 舊 MuscleCore | 本專題建議 | 處理方式 |
|---|---|---|---|
| 前端框架 | React、JS／TS | Flask Jinja2 | **重寫** |
| CSS | Tailwind／既有模板 | Bootstrap 5 為主 | **重寫，保留視覺概念** |
| 後端 | Node.js＋Express | Python Flask | **完整重寫** |
| API | REST API | Flask Blueprint／JSON API | **重寫** |
| DB | MongoDB Atlas | MongoDB Atlas | **延用平台與資料概念** |
| Admin UI | TailAdmin 類後台模板 | Bootstrap Admin Dashboard | **保留資訊架構，換模板** |
| AI 工具 | ChatGPT／Claude／Lovable 曾作開發輔助 | Hugging Face Local Model＋LLM API | **改為系統正式功能** |
| 測試工具 | Postman | Postman＋pytest（可選） | **延用** |
| 版控 | 舊案列為未來改善 | GitHub PR／Milestone | **本專題正式導入** |

## 2.3 舊站功能的「保留／簡化／延後」決策

| 舊站功能 | 本專題處理 | 原因 |
|---|---|---|
| 首頁／商品列表／詳情 | **Must 保留** | 購物網站主流程 |
| 商品分類／搜尋 | **Must 保留** | AI 推薦前的基本比較基準 |
| 會員註冊／登入 | **Must 保留** | 必須展示不同角色帳戶 |
| 會員中心 | **Should 保留** | 可累積個人偏好與訂單資料 |
| 購物車 | **Should 保留** | 舊站已有完整展示，開發價值高 |
| 簡化結帳 | **Should 保留** | 只需建立訂單，不強求真金流 |
| 管理者登入 | **Must 保留** | AI 板塊入口 |
| 商品 CRUD | **Must 保留** | 後台必要功能 |
| 訂單／會員清單 | **Must／Should** | AI 營運洞察資料來源 |
| 綠界／第三方金流 | **Could／Future** | 四週風險高、不是本專題 AI 核心 |
| LINE BOT | **Future** | 展示價值低於 AI 雙路線 |
| Email 雙重驗證 | **Future** | 舊組已遇到驗證困難，本期不重踩雷區 |
| 完整 JWT Token 架構 | **Future／選配** | Flask Session＋權限檢查足以支撐課堂 Demo |

> 舊站報告第 34～35 頁提到的未來改善與困難，已直接轉成這次的範圍控制依據：**不要讓模板、驗證與第三方服務，把 AI 專題做成除錯專題。**

---

# 三、帳戶、登入與權限設計

## 3.1 角色

本專題採最少兩種帳戶角色：

| Role | 登入後位置 | 權限 |
|---|---|---|
| `customer` | 購物網站／會員中心 | 商品瀏覽、搜尋、購物車、訂單、推薦 |
| `admin` | 管理後台 | 商品／訂單／會員管理＋兩大 AI 板塊 |

## 3.2 建議資料結構

舊站的 `admin` 與 `members` 可以保留，但為降低 Python 程式複雜度，**建議合併成 `users` Collection，增加 `role` 欄位**：

```json
{
  "_id": "...",
  "email": "user@example.com",
  "password_hash": "...",
  "name": "Sam",
  "role": "customer",
  "created_at": "..."
}
```

後台登入成功後檢查 `role == admin`；Customer 不得直接進入 `/admin/*`。

## 3.3 安全最低要求

- 密碼不得明碼存放，使用 Werkzeug password hash。
- `.env` 保存 MongoDB URI 與 API Key。
- `.env` 必須列入 `.gitignore`。
- 管理者路由要做 role-based access control。
- Demo 帳戶使用假資料，不放真實個資。

---

# 四、兩大 AI 板塊：本專題的真正亮點

## 4.1 AI 板塊 A｜Local Recommendation Engine

### 定位

> **Local AI：負責「找得準」。**

使用 Hugging Face 輕量模型在本機執行商品文字向量化，計算商品之間的語意相似度，建立「猜你喜歡／相似商品」推薦。

### 建議模型

`BAAI/bge-small-zh-v1.5`

### 為什麼適合本專題

- 模型相對小，可在一般電腦 CPU 執行。
- 不需要每次推薦都呼叫付費 API。
- 商品資料量不大時，可先離線產生向量，Demo 時速度穩定。
- 可以清楚展示「模型在本機」與「雲端 API」的技術差異。

### 建議輸入

```text
商品名稱 + 商品分類 + 商品描述 + 標籤
```

### 建議輸出

```text
目前商品：Adidas Running Shoes

Top 5 語意相似商品：
1. Nike Air Zoom       similarity=0.89
2. ASICS Gel Runner    similarity=0.86
3. New Balance 1080    similarity=0.82
...
```

### 後台畫面建議

- 選擇商品。
- 顯示 Top 5 推薦商品。
- 顯示 similarity score。
- 顯示 Local Model 名稱。
- 顯示處理時間。
- 可按「更新商品向量」。

### 前台如何使用

後台 Local AI 算出的推薦，可直接在商品詳情頁或首頁顯示：

> **猜你喜歡／相似商品**

因此 AI 雖然管理入口在後台，結果仍能回饋購物網站。

---

## 4.2 AI 板塊 B｜Cloud LLM Business Insight

### 定位

> **Cloud LLM：負責「說得懂、看得深」。**

Python 後端先從 MongoDB 聚合商品、訂單與會員行為數據，再把「整理後的摘要資料」送到 LLM API，讓模型產生營運解讀與可執行建議。

### 可展示問題

- 本週賣得最好的商品是什麼？
- 哪個商品類別銷售下降？
- 哪些商品需要注意庫存？
- 哪些商品適合一起促銷？
- 近期顧客偏好有什麼變化？
- 請替本週營運狀況產生 5 行主管摘要。

### 建議輸出

```text
營運摘要：
1. 跑鞋類本週營收占比最高，較上週增加 18%。
2. 健身器材瀏覽量高但轉換率偏低。
3. 商品 A 庫存低於近期平均銷售量，建議優先補貨。
4. 商品 B 與 C 經常出現在同類瀏覽行為，可測試組合促銷。
```

### 後台畫面建議

- KPI 卡片：營收、訂單數、平均客單價、熱門分類。
- 「AI 產生本週摘要」按鈕。
- 自然語言問題輸入框。
- AI 回覆區。
- 顯示 API 模型名稱／呼叫時間。

---

# 五、老師要求的兩種 AI 模式：如何同時呈現而不增加硬體投資

## 5.1 最終策略：不是二選一，而是「分工」

本專題採：

```text
Local Model
    ↓
語意向量／相似度推薦
    ↓
速度穩定、資料留在本機、低單次成本

Cloud LLM API
    ↓
自然語言生成／營運推論／推薦理由
    ↓
能力較強、不需 GPU、開發速度快
```

這比只在報告中理論比較更有說服力，因為兩種模式都真的出現在 Demo。

## 5.2 API 與 Local 的比較表

| 比較項目 | Local／本機模型 | Cloud／API LLM |
|---|---|---|
| 本專題用途 | 語意推薦、Embedding | 營運摘要、推薦理由、問答 |
| 硬體需求 | 輕量模型可 CPU | 本機幾乎無 GPU 需求 |
| 初始建置 | 較高 | 較低 |
| 單次使用成本 | 低 | 依 API 計費／額度 |
| 網路依賴 | 低 | 高 |
| 隱私 | 資料可不離機 | 資料需送往服務端 |
| 模型能力 | 受本機模型規模限制 | 可使用大型模型 |
| 速度 | 小模型穩定 | 受網路與 API 服務影響 |
| 維護 | 模型檔、套件、版本自行管理 | 供應商管理模型 |
| 四週專題適合度 | **適合小型 PoC** | **適合作主線功能** |

## 5.3 不買 GPU 的實作邊界

本專題**不下載 7B／14B 等大型生成式 LLM 當正式主線**，避免把四週開發時間變成顯卡規格研究會。

Local 僅執行：

- 小型 Hugging Face Embedding 模型。
- 商品向量預先計算。
- 小資料量相似度檢索。

Cloud API 執行：

- 自然語言摘要。
- 推薦原因生成。
- Business Insight。

### 最低可行展示

若現有電腦效能有限：

- Demo 商品先控制 20～100 筆。
- 向量預先產生並快取。
- Demo 時只做 similarity search。
- API 回覆可做 30～60 秒快取，避免反覆付費或超時。

---

# 六、更新後的 MVP 範圍

## 6.1 Must｜四週內一定要完成

| 功能 | 驗收標準 |
|---|---|
| Python Flask 專案骨架 | 可啟動、Blueprint 正常 |
| Bootstrap 5 共用版型 | 前台／後台可辨識且 RWD 基本正常 |
| MongoDB Atlas | 商品、使用者、訂單至少三類資料可讀寫 |
| Customer／Admin 登入分流 | 不同 role 登入後導向不同介面 |
| 商品首頁／列表／詳情 | MongoDB 正確顯示 |
| 商品搜尋／分類 | 可依關鍵字與分類查詢 |
| 管理者商品 CRUD | 新增、修改、查詢、下架正常 |
| AI A：Local 語意推薦 | 可選商品並回傳 Top-N 相似商品＋分數 |
| AI B：Cloud LLM 營運摘要 | 可用 MongoDB 聚合資料產生至少一份 AI 摘要 |
| GitHub 協作 | 分支＋PR＋Review 正常 |
| 公開 Demo URL | 外部瀏覽器可完整走主要流程 |

## 6.2 Should｜Must 穩定後完成

- 購物車。
- 簡化結帳並建立訂單。
- 會員中心／歷史訂單。
- LLM 推薦理由。
- 瀏覽／點擊行為紀錄。
- 後台 KPI 卡片。
- AI 使用紀錄與 latency 顯示。

## 6.3 Could／Future｜本期不作為驗收條件

- 真實金流。
- LINE Pay／信用卡。
- LINE BOT。
- Email 雙重驗證。
- 7B 以上本機生成式 LLM。
- 複雜 Fine-tuning。
- 完整 Recommendation System 線上學習。
- 企業級 JWT／OAuth SSO。

---

# 七、MongoDB Schema 建議

## 7.1 Collections

```text
vibecart_ai  或  insightcart_ai
├─ users
├─ products
├─ orders
├─ events             # Should：瀏覽／點擊／收藏等行為
├─ product_embeddings # Local AI 向量／模型版本
└─ ai_logs            # AI 呼叫紀錄／Latency／用途
```

## 7.2 products 最低欄位

```json
{
  "sku": "SHOE-001",
  "name": "運動跑鞋",
  "category": "鞋類",
  "brand": "...",
  "price": 1980,
  "stock": 15,
  "description": "...",
  "tags": ["跑步", "透氣", "輕量"],
  "image_url": "...",
  "active": true
}
```

## 7.3 orders 最低欄位

```json
{
  "order_no": "ORD20260908001",
  "user_id": "...",
  "items": [
    {"product_id": "...", "qty": 1, "price": 1980}
  ],
  "total_amount": 1980,
  "status": "paid",
  "created_at": "..."
}
```

---

# 八、Python 專案架構建議

```text
project/
├─ app.py
├─ config.py
├─ requirements.txt
├─ .env.example
├─ .gitignore
│
├─ routes/
│  ├─ auth.py
│  ├─ store.py
│  ├─ member.py
│  ├─ admin.py
│  └─ ai.py
│
├─ services/
│  ├─ mongo_service.py
│  ├─ local_recommender.py
│  └─ llm_api_service.py
│
├─ templates/
│  ├─ base.html
│  ├─ store/
│  ├─ member/
│  └─ admin/
│
├─ static/
│  ├─ css/
│  ├─ js/
│  └─ images/
│
├─ scripts/
│  ├─ seed_products.py
│  └─ build_embeddings.py
│
└─ tests/
   ├─ test_auth.py
   ├─ test_products.py
   └─ test_ai.py
```

### AI 路由建議

```text
/admin/ai/recommendation   → Local Model
/admin/ai/insight          → Cloud LLM API
```

---

# 九、總進度跟蹤表 v2.0

狀態代碼：⬜ 未開始｜🟨 進行中｜🟦 待確認｜🟩 已完成｜🟥 阻塞

| ID | 工作項目 | 預定完成日 | 負責人 | 交付物／驗收條件 | 狀態 | 本次修訂備註 |
|---|---|---:|---|---|:---:|---|
| P01 | 名稱／口號提案 | 09/03 | Sam | VibeCart／InsightCart 方案 | 🟩 | 已完成 |
| P02 | 名稱與側重表決 | 09/05 | 全組 | LINE 決議 | 🟦 | 尚未取得本對話最終表決紀錄 |
| P03 | 舊站展示資料取得 | 09/05 | 陳仁千／全組 | PDF＋展示影片 | 🟩 | 本版已納入 36 頁報告與 4 段影片 |
| P04 | 舊站功能盤點 | 09/06 | Sam＋全組 | 可沿用／重寫／延後表 | 🟩 | 本文件第二節已完成 |
| P05 | GitHub 專題倉庫 | 09/08 | 待確認 | Repo＋README＋Issues＋Milestones | ⬜ | 正式名稱確認後立即建立 |
| P06 | 四人派工 | 09/08 | 全組 | 每人主責＋複核 | ⬜ | 依新 AI 雙路線重分工 |
| P07 | 分支與權限 | 09/08 | GitHub 管理者 | main 保護＋develop＋feature | ⬜ | 同 P05 |
| P08 | Flask＋Bootstrap 骨架 | 09/10 | 前端＋後端 | 首頁、導覽、Blueprint | ⬜ | 新增 Customer／Admin 路由 |
| P09 | MongoDB Schema／種子資料 | 09/10 | DB 負責人 | users/products/orders | ⬜ | 可從舊 MuscleCore 資料欄位轉換 |
| P10 | Role-based Login | 09/11 | 後端 | customer/admin 分流 | ⬜ | 本版新增 Must |
| P11 | 前台商品瀏覽／搜尋／詳情 | 09/16 | 前端＋後端 | 主購物流程 | ⬜ | 參考舊站 UI 流程 |
| P12 | AI A：Local Recommendation | 09/18 | AI 負責人 | Top-N 推薦＋similarity | ⬜ | 建議 BGE Small |
| P13 | 管理者商品 CRUD | 09/21 | 後端＋DB | 新增／修改／下架 | ⬜ | 舊站已具完整操作參考 |
| P14 | 管理者訂單／會員資料 | 09/23 | 後端＋DB | 列表／查詢 | ⬜ | AI B 的資料來源 |
| P15 | AI B：Cloud LLM Insight | 09/25 | AI＋後端 | 營運摘要＋問答 | ⬜ | API 主線 |
| P16 | API vs Local 比較實測 | 09/25 | AI＋PM | 延遲／成本／隱私／限制表 | ⬜ | 老師要求的差異展示 |
| P17 | 測試站部署 | 09/25 | DevOps | 外網 URL | ⬜ | Render／Azure 擇一 |
| P18 | 整合測試／文件 | 09/29 | 全組 | README＋測試紀錄 | ⬜ | 停止新增 Could |
| P19 | 正式部署／Demo 彩排 | 10/01 | 全組 | 展示腳本＋備援影片 | ⬜ | 至少 1 次完整彩排 |
| P20 | v1.0.0 封版 | 10/02 | PM | Release／Tag | ⬜ | 僅修 Blocker |

---

# 十、四週專案時程 v2.0

| 週次 | 日期 | 本週目標 | 主要工作 | Milestone |
|---|---|---|---|---|
| Week 1 | 09/05～09/11 | 舊站盤點＋Python 技術地基 | 舊站功能拆解、Repo、Flask、Bootstrap、MongoDB、角色登入 | **M1：Customer／Admin 可登入，網站可讀取商品** |
| Week 2 | 09/12～09/18 | 購物前台＋Local AI | 商品列表、詳情、搜尋、Local Embedding、Top-N 推薦 | **M2：完成「瀏覽→查看→Local AI 推薦」** |
| Week 3 | 09/19～09/25 | 後台＋Cloud LLM | 商品 CRUD、訂單／會員、KPI、LLM Insight、測試部署 | **M3：後台兩個 AI 板塊都可 Demo** |
| Week 4 | 09/26～10/02 | 整合、比較、部署、成果呈現 | 測試、API vs Local 比較、簡報、正式站、封版 | **M4：10 分鐘內完整展示前台＋後台＋雙 AI** |

### 關鍵路徑

```text
舊站盤點
→ Python Flask 骨架
→ MongoDB＋角色登入
→ 購物網站 MVP
→ Local AI 推薦
→ 後台 CRUD／營運資料
→ Cloud LLM Insight
→ API vs Local 實測比較
→ 雲端部署
→ Demo／封版
```

---

# 十一、四人派工建議 v2.0

| 角色 | 建議人選 | 主責 | 複核 |
|---|---|---|---|
| A. PM／整合 | Sam（待全組確認） | Scope、Issues、Milestone、架構整合、AI 比較表、簡報 | Admin＋Demo |
| B. 舊站／前端 | 陳仁千（待本人確認） | 舊站流程、Bootstrap 前台、商品／會員畫面 | Store UX |
| C. Flask／MongoDB | 組員 3 | Auth、Role、Blueprint、CRUD、Orders | AI 資料輸入正確性 |
| D. AI／部署 | 組員 4 | Local Embedding、LLM API、測試、部署 | README／效能比較 |

### 開發原則

- 每個核心功能 1 人主責、1 人複核。
- 單一 Issue 控制在 0.5～2 天。
- 卡關超過 4 小時立即回報。
- Week 3 後不再隨意增加功能。
- AI 功能優先保證 **可重現與可解釋**，不要追求「模型越大越像神諭」。

---

# 十二、GitHub 倉庫與分支規劃

## 12.1 Repo

候選：

```text
vibecart-ai
insightcart-ai
```

## 12.2 Branch

```text
main
└─ develop
   ├─ feature/frontend-store
   ├─ feature/backend-db
   ├─ feature/auth-role
   ├─ feature/ai-local
   ├─ feature/ai-api
   └─ feature/docs-demo
```

### PR 規則

1. `main` 禁止直接 Push。
2. Feature → Pull Request → `develop`。
3. 至少 1 位非作者 Review。
4. 合併前檢查：程式可啟動、主要流程、`.env`、API Key、MongoDB URI。
5. Demo 版確認後再 `develop → main`。

---

# 十三、Milestone 與驗收標準 v2.0

| Milestone | 截止 | 驗收內容 | 通過條件 |
|---|---:|---|---|
| M0｜方向定案 | 09/08 | 舊站基底、Python 重寫、雙 AI 路線 | 4 人理解 Scope |
| M1｜技術地基 | 09/11 | Flask、MongoDB、Bootstrap、Customer/Admin Login | 另一台電腦可依 README 啟動 |
| M2｜Store＋Local AI | 09/18 | 商品列表／詳情／搜尋＋Top-N 推薦 | 至少 5 組商品測試正確，Demo 不超時 |
| M3｜Admin＋Cloud LLM | 09/25 | CRUD＋Order／Member＋AI Insight＋測試站 | 外網可登入後台並完成兩 AI 情境 |
| M4｜正式交付 | 10/02 | 正式站、API vs Local 比較、簡報、Demo、Release | 10 分鐘內完整展示，Blocker=0 |

---

# 十四、Demo 腳本建議（最能讓老師看出兩種 AI 差別）

## 情境 1｜一般會員

1. Customer 登入。
2. 瀏覽運動跑鞋。
3. 開啟其中一項商品詳情。
4. 畫面顯示「猜你喜歡」。
5. 說明：這些結果來自 **Local Hugging Face Embedding**，沒有呼叫大型雲端 LLM。

## 情境 2｜管理者：Local AI

1. Admin 登入。
2. 進入「AI 商品推薦」。
3. 選擇一個商品。
4. 顯示 Top 5 相似商品＋Similarity Score＋處理時間。
5. 強調：**資料留在本機、成本低、適合固定任務。**

## 情境 3｜管理者：Cloud LLM

1. 進入「AI 營運洞察」。
2. 系統先顯示 MongoDB 聚合 KPI。
3. 按「產生本週摘要」。
4. LLM API 產生營運解讀與建議。
5. 再問一題：「哪些商品適合做促銷？」
6. 強調：**大型模型推理與自然語言能力強，但依賴網路與 API。**

## 情境 4｜比較收尾

直接顯示比較表：

```text
Local AI  → 找得準、快、資料留本機
Cloud LLM → 說得懂、推理強、不需本地 GPU
```

老師若問「為什麼不用全 Local？」：

> 因本專題只有四週且團隊沒有 GPU 投資，因此採小模型 Local 化處理固定推薦任務；需要大型生成能力的部分以 API 實作。這不是逃避 Local，而是依任務特性做成本與效能分工。

---

# 十五、部署平台

| 平台 | 適合度 | 建議 |
|---|:---:|---|
| Render | ★★★★★ | 四週專題首選，GitHub 自動部署快 |
| Azure App Service | ★★★★☆ | 若沿用舊 MuscleCore Azure 經驗，可優先 |
| Google Cloud Run | ★★★★☆ | 若老師要求容器化再選 |
| Railway | ★★★★☆ | Render 備選 |

### 注意

Local Embedding 若部署到資源很小的免費 Web Service，啟動時間可能較長。可採：

- 開發機預先計算商品向量。
- 將 embedding 結果存 MongoDB。
- 正式網站只做 similarity calculation。

這樣仍保留「Local 模型建立向量」的實驗成果，同時降低雲端 Demo 風險。

---

# 十六、風險與管控 v2.0

| 風險 | 機率／衝擊 | 預防 | 觸發後處置 |
|---|---|---|---|
| 四週範圍過大 | 高／高 | Must／Should／Could 鎖定 | Week 3 停止加功能 |
| Local 模型電腦太慢 | 中／中 | 小模型＋預計算＋快取 | 只 Demo 20～100 商品 |
| LLM API 超時／額度 | 中／高 | 限制 Prompt、快取結果 | 備援一組已驗證測試資料 |
| 老師看不出 AI 差異 | 中／高 | 兩個獨立後台板塊＋比較表 | Demo 明確顯示模型路線與 latency |
| MongoDB／API Key 外洩 | 中／高 | `.env`＋GitHub Secret | 立即撤銷／輪替 |
| 舊站程式碼授權不清 | 中／中 | 只沿用流程／畫面概念／資料欄位 | 全部 Python 自行重寫 |
| 模擬營運資料太少 | 高／中 | 建立 seed orders／events | 清楚標示「Demo 模擬資料」 |
| 金流／Email 卡住 | 高／中 | 本期不列 Must | 直接移出範圍 |
| 分支衝突 | 中／中 | 模組化 Branch＋小 PR | PM 整合後作者複測 |
| 部署太晚 | 中／高 | Week 3 前測試站 | Render／Azure 二選一備援 |

---

# 十七、下一次全組必須確認的 10 件事

- [ ] 1. 正式名稱：VibeCart AI 或 InsightCart AI。
- [ ] 2. GitHub Repo 正式名稱與擁有者。
- [ ] 3. 舊 MuscleCore 程式碼是否可參考；本專題原則仍以 Python 自行重寫。
- [ ] 4. 四位組員 GitHub 帳號與角色。
- [ ] 5. 前端採 Bootstrap 5 是否全組同意。
- [ ] 6. Customer／Admin 採同一 `users` Collection＋role 是否同意。
- [ ] 7. Local AI 採 `BAAI/bge-small-zh-v1.5` 是否同意。
- [ ] 8. Cloud LLM API 使用哪一服務／模型與額度來源。
- [ ] 9. 購物車／簡化結帳是否列為 Should，而非阻塞 AI 開發。
- [ ] 10. 部署優先 Render 或 Azure。

---

# 十八、決策紀錄 v2.0

| 日期 | 決策項目 | 決策結果 | 影響／後續 |
|---:|---|---|---|
| 2026-09-03 | 建立四週 v1.0 | Flask＋Bootstrap＋MongoDB＋Hugging Face | 建立初版專案時程 |
| 2026-09-04 | 老師要求 | 希望同專題看出兩種 AI／模型應用差異 | 必須補 Local vs API 架構 |
| 2026-09-08 | 舊站附件完成盤點 | MuscleCore 作為購物網站功能與 UI 流程基底 | Python 重寫，不照搬 JS 架構 |
| 2026-09-08 | AI 架構修正 | **Local Recommendation＋Cloud LLM Insight** | 兩個後台 AI 板塊分工 |
| 待全組確認 | 正式名稱 | VibeCart AI／InsightCart AI | 決定 Repo 名稱與視覺品牌 |
| 待全組確認 | Cloud LLM API | 待選 | 確認 API Key／額度 |
| 待全組確認 | 部署平台 | Render／Azure | Week 3 建測試站 |

---

# 十九、每次更新規則

- 每週三課後及每週六更新本表。
- Issue／PR 完成後才改成 🟩。
- 延遲超過 1 天標記 🟥 並寫原因。
- Milestone 必須由非原作者複測。
- AI 功能驗收需記錄：**模型／模式、輸入、輸出、Latency、是否 API、是否本機**。
- 專題總進度以「已通過驗收的 Must」計算，不以程式碼行數或熬夜程度灌水。

---

# 二十、成果報告建議章節

1. 專題背景與舊 MuscleCore 網站分析。
2. 為何以 Python 重寫。
3. 系統角色與 Flask 架構。
4. MongoDB Schema。
5. Local AI 商品推薦設計。
6. Cloud LLM Business Insight 設計。
7. Local vs API 實測比較。
8. 前台／後台 Demo。
9. 專案管理與 GitHub 協作。
10. 限制與未來改善。

> **最後的評分重點不是「我們串了幾個 AI」，而是能否說清楚：為什麼這個任務選 Local、那個任務選 API，並用實際系統證明選擇是合理的。**
