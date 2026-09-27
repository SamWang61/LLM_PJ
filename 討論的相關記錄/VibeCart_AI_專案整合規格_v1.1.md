# VibeCart AI｜懂你想買、更懂怎麼賣！

## 專案整合規格與表單欄位審查 v1.1

|版本資訊|內容|
|-|-|
|文件版本|v1.1，2026-09-13|
|承接文件|《LLM購物網站專題\_2026-09-09\_今日總結與下一步規劃\_v1.0.md》|
|技術基線|《VibeCart\_AI\_Firebase\_部署說明\_v1.1.md》，2026-09-11|
|本次來源|同組 CONVENTIONS.md、CONVENTIONS.pdf，以及已確認的專題決策|
|適用範圍|四人、四週專題；2026-09-05～2026-10-02|
|完成狀態|文件審查與新版規格完成；未在本次修改程式、遷移資料庫或部署|
|版本區別|專案整合文件 v1.1 與部署手冊 v1.1 為各自版本；本版目標資料規格標示 schema\_version=2，不表示現有資料已升級|

## 1\. 審查結論與修正清單

**附件需修正後整合。** 命名、UTC、金額精度、內嵌訂單快照、分層存取及版本化遷移原則可採用；框架、登入機制及 AI 建模不能直接覆蓋既有程式。兩份附件的核心欄位內容一致；PDF 的可空型別列有直線符號造成的欄位錯位，以 Markdown 的型別語意判讀。本文件是修正後的專案規格，原附件作為審查來源保留。

|編號|原附件／既有差異|本版決定|原因及影響|
|-|-|-|-|
|R01|附件採 FastAPI，已交付程式採 Flask|本期維持 Flask；Pydantic 可作資料驗證|不因欄位文件而重寫路由、模板與部署|
|R02|附件強制 Firebase Auth、禁止 password\_hash|保留 Flask 雜湊密碼登入；Firebase Auth 列後續遷移|現有帳號需要 password\_hash，直接移除會使登入失效|
|R03|Provider 與 api/local 執行模式混用|Provider 記 anthropic／huggingface／rules；執行模式另記|能辨識實際模型來源及備援|
|R04|BGE 被視作可替換的本地 LLM|明確為 Embedding，與 Claude 任務分工|BGE 不直接生成營運摘要或聊天回答|
|R05|缺商品向量與推薦結果|補 product\_embeddings、recommendations|支援模型版本、向量失效及點擊追蹤|
|R06|附件只有 7 集合，舊藍圖 14、部署版 8|以本版 13 個目標集合整合，保留配額與限流|集合數量由聚合邊界決定，不要求湊滿舊數量|
|R07|缺會員偏好；只有事件不足以表達主動需求|補偏好類別、標籤、預算|支援個人化推薦與冷啟動|
|R08|商品未定義規格、特價上限與貨幣|一個可售 SKU 一筆商品；補 brand、size、color、currency|避免衣服不同尺寸共用一份庫存|
|R09|訂單缺重複提交識別及 Demo 標記|補 checkout\_id、request\_hash、is\_demo、currency、paid\_at|保留既有重複結帳防護，Demo 不混入真實營收|
|R10|ai\_requests 假設每次都有文字、Prompt、成功結果|增補狀態、父子請求、快取、分項 Token；允許不適用值 null|向量任務、上游失敗與混合流程也能正確紀錄|
|R11|索引表遺漏分類名稱唯一性|補 categories.name 唯一索引；列查詢用複合索引|欄位字典與實際建索引規格一致|
|R12|已有環境變數與新名稱不同|保留部署版名稱，提供映射規則|文件改名不等於程式已支援新變數|
|R13|orders.status=demo\_paid 不在附件 Enum|明確遷移為 confirmed＋paid＋is\_demo=true|不把示範付款誤認為真實金流|
|R14|使用者用詞禁止 customer，但角色又用 customer|禁止混用只限實體命名，角色值保留 customer|消除文件內部矛盾|

## 2\. 專案定位、範圍與目前進度

正式名稱採 **VibeCart AI｜懂你想買、更懂怎麼賣！**。MuscleCore 是舊運動商品網站的流程與畫面參考；VibeInsight 是管理端模組名稱。Python 重構商品、會員與訂單流程，前台展示個人化商品推薦，後台展示 Local AI 推薦分析及 Claude 營運洞察。

|層級|本期方案|狀態／界線|
|-|-|-|
|網站|Flask Application Factory＋Blueprint、Jinja2＋CSS|承接既有程式；FastAPI 未採用|
|部署|Firebase Hosting＋Cloud Run|已有部署文件；本次未驗證實站|
|資料庫|MongoDB Atlas；新環境建議 vibecart\_ai|既有 musclecore 不可只改連線名稱而當作遷移|
|登入|Flask Session＋密碼雜湊，customer/admin|Firebase Authentication 為後續替換方案|
|Local AI|BAAI/bge-small-zh-v1.5，本機 CPU 預計算商品向量|Cloud Run 讀 Atlas 向量做相似度，不在頁面請求下載模型|
|Cloud AI|Claude API，管理員觸發彙總洞察|實際模型 ID、額度由健維帳戶確認；過去 USD 4.5 不是目前餘額證明|
|GitHub|分工後決定正式專題 Repo|不把 Firebase\_Flask\_API 練習倉庫視為已定案的專題倉庫|

依既有交付文件，v1.0 有前台、登入、Session 購物車、Demo 結帳與規則推薦骨架；部署版 v1.1 已補 BGE 建置、Claude、快取、配額及部署流程，但仍有未執行的依賴測試與雲端驗收。本次僅完成文件，不能把既有「待驗證」改為「已通過」。

本期必要：商品搜尋／分類／詳情、會員登入、購物車、Demo 結帳、歷史訂單、偏好、推薦、後台商品維護、KPI、雙 AI 紀錄。真實金流、完整退款物流、多輪客服、評論情緒分析、微調、大型本機生成模型列後續；自由文字語意搜尋需即時查詢向量，目前預計算商品向量路線只能直接支援商品對商品推薦，關鍵字搜尋先保留獨立功能。

## 3\. 資料模型總覽

附件使用 MongoDB 集合與文件，不是 SQL 表單；畫面表單對應見第 7 節。以下為目標規格，程式仍須依第 9 節遷移。

|目標集合|用途|舊版對應與處置|
|-|-|-|
|users|帳號、角色、偏好|保留 users，name 映射 display\_name|
|categories|分類|從 products.category 正規化產生|
|products|可售 SKU、金額、庫存、描述|保留 products，stock 映射 stock\_quantity|
|carts|登入會員購物車|原 Session 購物車轉存；訪客仍可用 Session|
|orders|訂單及內嵌明細快照|保留 orders；不另建 order\_items|
|user\_events|瀏覽、搜尋、加購、購買、推薦曝光點擊|behavior\_events 遷移，保留原識別與時間|
|ai\_requests|AI 任務與執行紀錄|新增；不取代成本配額集合|
|product\_embeddings|BGE 向量|延續部署版，新增明確版本規範|
|recommendations|推薦清單及理由|從舊藍圖保留，支援成效追蹤|
|ai\_insights|彙總輸入與營運洞察快取|保留既有快取用途，補來源範圍|
|ai\_usage|每日／總呼叫配額|保留，禁止用 TTL 清除累計配額|
|request\_limits|登入／端點限流|保留 expires\_at TTL|
|schema\_migrations|遷移版本與執行結果|新增技術集合，用於重跑與查驗|

舊 14 集合藍圖中的 product\_tags 併入 products.tags；cart\_items 併入 carts.items；order\_items 併入 orders.items；ai\_conversations 多輪對話延後，單次執行改記 ai\_requests；daily\_product\_metrics 延後，MVP 由訂單與事件即時計算。已存在的舊集合需驗證資料遷移後才能退役，不可直接刪除。

## 4\. 欄位共同規則

識別碼在資料庫以 ObjectId 儲存、API 用 24 位十六進位字串傳輸並驗證。一般業務集合 \_id 採 ObjectId；既有 ai\_insights、ai\_usage、request\_limits 的字串 \_id 為明確例外，保留以避免破壞快取與配額。

金額使用 Decimal／Decimal128，API 以十進位字串輸入輸出，例如 "1290.00"；本期商品及訂單貨幣固定 TWD、最多兩位小數。時間存 UTC，報表日界及畫面使用 Asia/Taipei。可選欄位在新文件統一明確存 null；PATCH 未提供表示不改，提供 null 表示清空可空欄位。陣列預設 \[]、有界物件依指定結構驗證。

每個業務集合新文件加入 schema\_version: Integer=2；created\_at 由伺服器建立。可修改集合具有 updated\_at；事件、請求、推薦結果採追加紀錄或受控狀態更新。下列欄位上限為本版設計限制，不是服務商限制。

## 5\. 核心集合欄位字典

表內「是」表示新文件必要；「條件」由業務規則決定；共用 \_id、schema\_version 除例外集合外均必填。

### 5.1 users

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|display\_name|String|是|1～100 字|
|email|String|是|去前後空白、小寫、唯一；本期帳密註冊必要|
|auth\_provider|String|是／local|local；firebase 保留未啟用|
|password\_hash|String/null|條件|local 必填，僅伺服器雜湊；永不回傳 API|
|firebase\_uid|String/null|null|Firebase 遷移後才填；字串值部分唯一索引|
|role|String|customer|customer、admin；公開註冊不得自行指定 admin|
|is\_active|Boolean|true|停用帳號不得登入或呼叫受保護 API|
|preferences|Object|是|下列偏好物件|
|preferences.category\_ids|Array\[ObjectId]|\[]|上限 10，去重、參照有效分類|
|preferences.tags|Array\[String]|\[]|上限 20，每項 30 字|
|preferences.budget\_min / budget\_max|Decimal128/null|null|非負；兩者都有值時 min ≤ max|
|preferences.updated\_at|Date/null|null|尚未填偏好時為 null|
|created\_at / updated\_at|Date|是|UTC|

禁止明碼 password 入庫。附件「不存 Firebase 密碼」原則保留；本期 local 的 password\_hash 不在禁止範圍。未實作 Firebase 登入前，不得刪除舊 hash 或把 firebase\_uid 改必填。

### 5.2 categories

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|name|String|是|1～100 字、唯一|
|slug|String|是|1～100 字、小寫英文數字與連字號、唯一|
|description|String/null|null|最多 1000 字|
|sort\_order|Integer|0|非負、控制選單次序|
|is\_active|Boolean|true|停用後不接受新商品指派|
|created\_at / updated\_at|Date|是|UTC|

### 5.3 products

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|category\_id|ObjectId|是|參照 categories.\_id|
|name|String|是|1～200 字|
|description|String|是|1～5000 字；輸出做安全跳脫|
|sku|String|是|1～64 字、去空白、統一大寫、唯一|
|brand / size / color|String/null|null|各最多 100 字；無尺寸商品可空|
|price|Decimal128|是|非負、最多兩位小數|
|sale\_price|Decimal128/null|null|0 ≤ sale\_price ≤ price；零元不是無特價|
|currency|String|TWD|本期僅 TWD|
|stock\_quantity / safety\_stock|Integer|是／0|非負；扣庫存只能經交易服務|
|tags|Array\[String]|\[]|上限 20，每項 30 字、去重|
|image\_urls|Array\[String]|\[]|上限 10，經核准的 HTTPS 或站內資產路徑|
|is\_active|Boolean|true|下架排除搜尋、推薦與新結帳|
|created\_at / updated\_at|Date|是|UTC|

一個尺碼／顏色組合即一筆獨立 SKU。修改名稱、分類、描述、標籤、品牌或規格後，相關向量內容 hash 必須重新計算。舊 rating、sales\_count 暫留相容讀取，不把缺少評論來源的 rating 當真實評分；銷售 KPI 以 orders 計算，不信任前端傳入或未維護的 sales\_count。

### 5.4 carts 與 carts.items\[]

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|user\_id|ObjectId|是|唯一，一會員一份目前購物車|
|items|Array\[Object]|\[]|最多 20 個不同 product\_id|
|items\[].product\_id|ObjectId|是|商品必須存在|
|items\[].quantity|Integer|是|1～99；結帳再驗證庫存|
|items\[].added\_at|Date|是|UTC|
|created\_at / updated\_at|Date|是|UTC|

金額由伺服器按商品重新計算，不信任購物車快照價格。登入合併訪客購物車時同 SKU 合併、限制數量；移轉成功後清掉對應 Session 項目，重複登入不可再累加同一批。歷史購物車不混入此集合；訂單保留歷史內容。

### 5.5 orders 與 orders.items\[]

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|order\_number|String|是|對外訂單編號、唯一|
|user\_id|ObjectId|是|由登入身分決定|
|checkout\_id|String|是|一次結帳識別，與 user\_id 複合唯一|
|request\_hash|String|是|規範化結帳商品與數量摘要；同 key 不同內容回 409|
|status|String|pending|pending、confirmed、shipping、completed、cancelled|
|payment\_status|String|unpaid|unpaid、paid、failed、refunded|
|is\_demo|Boolean|true|本期示範結帳固定 true，僅伺服器可改|
|currency|String|TWD|本期固定 TWD|
|items|Array\[Object]|是|1～20 筆，不同 SKU|
|items\[].product\_id|ObjectId/null|條件|新結帳必須有值；舊歷史商品缺失才可 null|
|items\[].product\_name / sku|String|是|名稱與 SKU 下單快照|
|items\[].size / color|String/null|null|規格快照|
|items\[].unit\_price|Decimal128|是|成交價，sale\_price 非 null 時優先|
|items\[].quantity|Integer|是|1～99|
|items\[].subtotal\_amount|Decimal128|是|unit\_price × quantity|
|subtotal\_amount|Decimal128|是|明細小計加總|
|discount\_amount|Decimal128|0|0 ≤ discount\_amount ≤ subtotal\_amount|
|shipping\_fee|Decimal128|0|本期示範免運|
|total\_amount|Decimal128|是|subtotal\_amount − discount\_amount ＋ shipping\_fee|
|shipping\_address|Object/null|null|本期不收集；若未來實體配送再啟用收件人／電話／郵遞區號／地址驗證|
|paid\_at|Date/null|null|paid 時必要；Demo 時間不代表金流確認|
|created\_at / updated\_at|Date|是|UTC|

特價已體現在 unit\_price，不得在 discount\_amount 再扣一次。Demo 結帳可由 pending/unpaid 轉 confirmed/paid；介面需顯示「模擬付款」。本期不開放真實退款、物流狀態修改。confirmed→shipping→completed 為後續流程；未付款 pending 才可取消並原子返還已扣庫存，重複取消不得重複補庫存。已付款取消須未來退款流程，MVP 拒絕此操作。

### 5.6 user\_events

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|event\_id|String|是|唯一，去除重送事件|
|user\_id|ObjectId/null|null|登入者由伺服器指定|
|session\_id|String|是|最多 128 字，不存登入 Cookie 或 Token|
|event\_type|String|是|見下方事件值|
|product\_id|ObjectId/null|條件|商品事件必要|
|order\_id|ObjectId/null|條件|purchase 必要|
|recommendation\_id|ObjectId/null|條件|推薦曝光／點擊必要|
|search\_query|String/null|null|product\_search 必填，1～200 字|
|event\_metadata|Object|{}|白名單輔助資訊，序列化最多 2 KB，不放個資或核心指標|
|created\_at|Date|是|伺服器收到事件 UTC 時間|

事件值：product\_view、product\_search、add\_to\_cart、remove\_from\_cart、purchase、recommendation\_impression、recommendation\_click。purchase 僅在伺服器訂單提交後產生，一訂單一筆；推薦曝光於清單成功呈現才產生，點擊需驗證商品存在於該次推薦清單。

### 5.7 ai\_requests

|欄位|BSON 型別|必填／預設|驗證及用途|
|-|-|-|-|
|user\_id / parent\_request\_id|ObjectId/null|null|使用者及父流程追蹤|
|task\_type|String|是|product\_embedding、product\_recommendation、sales\_summary；其他任務列後續|
|execution\_mode|String|是|local、api、hybrid、baseline|
|requested\_provider|String|是|huggingface、anthropic、rules、pipeline|
|actual\_provider|String/null|null|同上；未真正執行或尚待處理為 null|
|model\_name / model\_revision|String/null|null|模型任務需記錄實際識別；rules 可空|
|prompt\_name / prompt\_version|String/null|null|生成任務必要，Embedding 不適用|
|status|String|queued|queued、running、succeeded、failed、timeout|
|is\_success|Boolean/null|null|未完成為 null；終態與 status 一致|
|input\_text / output\_text|String/null|null|去識別化、各最多 8000 字；向量不可塞入 output\_text|
|input\_summary|Object|{}|白名單商品 IDs／聚合範圍／數值，最多 8 KB|
|parameters|Object|{}|白名單 top\_k、temperature、max\_tokens 等；由後端限制|
|latency\_ms|Integer/null|null|終態必填且非負|
|input\_tokens / output\_tokens / token\_count|Integer/null|null|供應商未回用量時保留 null；不臆測零成本|
|estimated\_cost|Decimal128/null|null|非負，估計值並非帳單|
|cost\_currency|String/null|null|有估計成本時為 USD|
|is\_cache\_hit|Boolean|false|快取命中不重計 API 呼叫成本|
|fallback\_reason / error\_code|String/null|null|結構化原因，不存金鑰或上游完整敏感訊息|
|created\_at / started\_at / completed\_at|Date/null|條件|created\_at 必填，開始／結束時補時間|

混合流程以一筆 parent 記總耗時，每個模型／備援各一筆 child；成本只加總 leaf，避免重複計算。Claude timeout 記 failed/timeout child；規則備援另記 rules child，不能把 BGE 標成 Claude 替代摘要模型。舊資料不能推知的 Token 與耗時保留 null 並在遷移報告標記，不偽造數據。

## 6\. AI 與技術集合欄位補充

### 6.1 product\_embeddings

|欄位|BSON 型別|必填／規則|
|-|-|-|
|product\_id|ObjectId|必填，參照商品|
|model|String|必填，沿用部署版名稱；本期 BAAI/bge-small-zh-v1.5|
|revision|String|必填，實際模型 revision；舊 main-unpinned 要標示待重建|
|vector|Array\[Double]|必填，本期驗證 512 個有限數值，禁止 NaN／Infinity、零向量|
|dimension|Integer|必填，本期 512|
|content\_hash|String|必填，商品標準化輸入內容 SHA-256|
|preprocessing\_version|String|必填，文字拼接與正規化版本|
|is\_normalized|Boolean|必填，標示向量是否已 L2 正規化|
|created\_at / updated\_at|Date|必填，UTC|

保留 product\_id＋model 唯一鍵：MVP 每個商品／模型一份目前向量，更新 revision 時替換；不同 revision 或 preprocessing\_version 不可混算。Double 禁用僅限金額，向量與相似度可以使用。BGE 提供文字向量供檢索與相似度；相似度不是購買機率。[模型官方說明](https://huggingface.co/BAAI/bge-small-zh-v1.5)

### 6.2 recommendations

|欄位|BSON 型別|必填／規則|
|-|-|-|
|user\_id|ObjectId/null|登入者填值，訪客為 null|
|session\_id|String|必填，最多 128 字|
|source\_product\_id|ObjectId/null|相似商品模式必填|
|ai\_request\_id|ObjectId|必填，連到產生清單的請求|
|strategy|String|baseline、bge\_similar、bge\_personalized|
|model / revision|String/null|BGE 策略必填|
|items|Array\[Object]|最多 10 筆，允許 \[] 表示無結果|
|items\[].product\_id|ObjectId|必填，不重複|
|items\[].rank|Integer|1 起算、連續|
|items\[].score|Double|有限值；BGE cosine 在 -1～1，規則分數另行解釋|
|items\[].reason|String|必填，最多 500 字，MVP 可用模板理由|
|created\_at|Date|必填|

個人化最低規格：登入者最近 30 天最多 100 筆商品瀏覽／加購／購買事件，權重暫定 1／3／5，建立有效商品向量加權平均，再套偏好預算、有效分類、上架與庫存篩選；無有效行為時使用偏好＋規則推薦。bge\_similar 是商品相似，不能單憑此功能宣稱已完成使用者個人化。權重屬本版設計值，需以測試案例調整並記版本。

### 6.3 ai\_insights

|欄位|BSON 型別|必填／規則|
|-|-|-|
|\_id|String|快取 hash；由彙總、日期範圍、Demo 篩選、模型、Prompt 版本產生|
|ai\_request\_id|ObjectId/null|新資料必填；舊無法關聯才 null|
|task\_type|String|sales\_summary|
|period\_start / period\_end|Date|新資料必填，UTC 半開區間 \[start,end)|
|report\_timezone|String|Asia/Taipei|
|is\_demo|Boolean|本期 true，與輸入篩選一致|
|input\_summary|Object|有界白名單數據，最多 8 KB，不含 email／地址|
|text / model / prompt\_version|String|新資料必填，文字最多 8000 字|
|usage|Object|僅已回傳的 Token 用量；無則 {}|
|elapsed\_ms|Integer/null|非負，舊未知可空|
|created\_at / expires\_at|Date|必填，快取到期，expires\_at TTL|

快取可過期，執行稽核由 ai\_requests 留存；讀取時仍檢查 expires\_at，不能等 TTL 刪除才判過期。舊以最近 100 筆算摘要的結果需標示樣本，不得稱全期間總營收；目標報表按時間範圍聚合全數符合訂單後再傳送摘要。

### 6.4 ai\_usage、request\_limits、schema\_migrations

|集合|欄位與型別|規則|
|-|-|-|
|ai\_usage|\_id:String、count:Integer、updated\_at:Date|沿用 total／UTC 日期識別，count 非負；先原子預扣再呼叫，禁止清空重設預算|
|request\_limits|\_id:String、count:Integer、expires\_at:Date|沿用時間窗＋帳號 hash；count 非負，TTL 清理；限流由後端執行|
|schema\_migrations|\_id:String、checksum:String、status:String、started\_at:Date、completed\_at:Date/null、counts:Object、error\_code:String/null|ID 為腳本版本；status=running/succeeded/failed；counts 只存來源／目標／錯誤筆數|

三者新建記 schema\_version=2；既有配額與限流的 \_id 格式不因統一命名而改寫。遷移紀錄 checksum 不匹配時停止，成功版本不再執行；失敗重跑須先確認部分寫入，不能把有紀錄等同已成功。

## 7\. 網站表單、角色及資料歸屬

|表單／頁面|使用者可填欄位|伺服器負責|角色|
|-|-|-|-|
|註冊|display\_name、email、password、確認密碼|雜湊、role=customer、識別碼、時間|訪客|
|登入|email、password|Session、頻率限制、帳號狀態|訪客|
|會員偏好|category\_ids、tags、budget\_min/max|驗證分類、user\_id、更新時間|本人|
|商品查詢|關鍵字、category\_id、價格上下限|上架篩選、排序、分頁|全部|
|購物車|product\_id、quantity|最新價格、所有權、上限|本人／訪客 Session|
|Demo 結帳|結帳確認、checkout\_id|價格、總額、庫存、request\_hash、is\_demo、狀態|登入本人|
|訂單查詢|訂單編號、日期範圍|本人訂單範圍；金額唯讀|本人；admin 可跨會員|
|商品維護|分類、name、sku、描述、價格、庫存、規格、圖片、上架狀態|權限、向量失效、完整驗證|admin|
|分類維護|name、slug、description、sort\_order、is\_active|唯一性及引用檢查|admin|
|推薦展示|商品／偏好條件|候選清單、score、rank、曝光紀錄|全部，依身分範圍|
|AI 營運洞察|日期範圍、Demo 篩選|彙總、Prompt、模型、成本、配額|admin|
|AI 執行紀錄|任務、狀態、時間篩選|去識別紀錄、分項耗時|admin 唯讀|

隱藏按鈕不是授權控制；Service 每次核對登入者、role、is\_active 與資源 owner。一般使用者不得寫 role、user\_id、成交價、total\_amount 或付款狀態；敏感欄位不在 Response。Cookie 表單沿用 CSRF 驗證，URL 或 JSON 帶其他會員 ID 不得繞過檢查。

## 8\. 索引、統計與一致性

|集合|索引鍵|要求|
|-|-|-|
|users|email|Unique|
|users|firebase\_uid|Unique，僅欄位為 String 的 partial filter，允許多筆 null|
|categories|name；slug|各自 Unique|
|products|sku|Unique|
|products|category\_id:1、is\_active:1|Compound|
|products|name:text、description:text|一個複合 text 索引；中文搜尋效果須驗證，不等於 BGE 向量搜尋|
|carts|user\_id|Unique|
|orders|order\_number|Unique|
|orders|user\_id:1、checkout\_id:1|Unique|
|orders|user\_id:1、created\_at:-1|Compound|
|orders|is\_demo:1、payment\_status:1、created\_at:-1|報表查詢|
|orders|status:1、created\_at:-1|後台狀態查詢|
|user\_events|event\_id|Unique|
|user\_events|order\_id|purchase 且 order\_id 為 ObjectId 的部分唯一索引|
|user\_events|user\_id:1、event\_type:1、created\_at:-1|行為推薦|
|user\_events|recommendation\_id:1、event\_type:1|推薦成效|
|product\_embeddings|product\_id:1、model:1|Unique，承接既有索引|
|recommendations|user\_id:1、created\_at:-1|查推薦歷史|
|ai\_requests|task\_type:1、actual\_provider:1、created\_at:-1|任務統計|
|ai\_requests|parent\_request\_id:1|混合流程追蹤|
|ai\_insights；request\_limits|expires\_at:1|各設 TTL expireAfterSeconds=0|

名稱採 uq\_{collection}*{fields}、idx*{collection}*{fields}、ttl*{collection}\_{field}。新建索引前列出既有鍵與選項，避免同鍵重複索引或唯一約束撞舊資料。本期 user\_events、ai\_requests 不自動設 TTL，保留至專題驗收後再決定保留期。

KPI：訂單數為符合期間及 Demo 篩選的非 cancelled 訂單；營收為 paid 且非 cancelled 訂單 total\_amount 加總；客單價以同一筆集合的 paid 訂單數為分母，無訂單顯示 0 並標示無資料；熱銷按同集合 items.quantity 加總；低庫存為上架商品 stock\_quantity ≤ safety\_stock。本期未處理部分退款，不宣稱能計算退款後淨營收。推薦 CTR 以期間內去重的推薦曝光清單為 cohort，分子是該 cohort 中有點擊的清單數，分母是曝光清單數，零分母顯示無資料。

結帳在同一 transaction 中驗證商品、用 stock\_quantity ≥ quantity 條件原子扣庫存、建立訂單與 purchase 事件、清除已結帳購物車。不同商品任一失敗全筆回滾；同 checkout\_id 查既有訂單，不能重扣。commit 結果不明先按唯一鍵查回，禁止盲目重送。MongoDB 多文件交易需支援的 replica set／sharded cluster；standalone 不能作此驗收環境。[MongoDB 交易文件](https://www.mongodb.com/docs/manual/core/transactions/)

## 9\. v1.1 程式到目標 Schema 的遷移對照

|來源|目標|回填與相容方式|
|-|-|-|
|users.name|users.display\_name|複製原值，空值人工補正；保留原 \_id 與 password\_hash|
|users.preferences|新 preferences 結構|可識別欄位映射；未知鍵留備份，不整份覆寫|
|products.category|category\_id＋categories|整理名稱去重後建分類，建立舊名稱→ID 對照|
|products.stock|stock\_quantity|驗證非負整數；異常隔離，不能自動歸零|
|既有數值 price／total|Decimal128 金額|以原始十進位文字轉換、確認精度；逐單比對，不直接 Decimal(float)|
|orders.order\_no|order\_number|保留值與唯一性；同步修改查詢、畫面與重試路徑|
|orders.total|total\_amount|比對明細重算；差異列表人工查核|
|orders.status=demo\_paid|confirmed、paid、is\_demo=true|paid\_at 無確切資料時以 created\_at 回填並在遷移報告標註推定|
|舊訂單缺 checkout\_id|checkout\_id|historical:{原訂單\_id}，僅作歷史識別，不能視為原始客戶 key|
|舊訂單缺 request\_hash|request\_hash|由既有快照重建，標記為歷史重建|
|behavior\_events|user\_events|保留 \_id，event\_id=legacy:{\_id}；補缺 session\_id=legacy:{\_id} 並標示合成值，不作真實 session 分析|
|舊事件值／無法確認 user\_id|定義內事件／關聯|列出值域與關聯例外，不猜測使用者；不合法資料隔離|
|product\_embeddings|同集合|保留 model／revision／vector，新增 dimension；前處理版本未知則列待重建|
|ai\_insights|同集合|不捏造缺少的日期或 Prompt；舊快取自然失效，新鍵涵蓋 Prompt 版本與範圍|
|ai\_usage／request\_limits|同集合|保留 ID、count、到期規則，新增欄位不得清空配額|

其他回填：既有商品的 sale\_price=null、tags/image\_urls 缺失時 \[]、currency=TWD 僅在確認原幣別後填；safety\_stock 缺失可用設計預設 0。訂單 discount\_amount/shipping\_fee 不能無條件填零，須確認原總額與明細；未知 status 不強行設 paid，應隔離查核。新增必填的 AI 欄位只對新紀錄強制，舊紀錄先維持舊 schema\_version，後續可重建者才升級。

遷移順序：備份並記筆數／金額 → 列出 validator/index 與不合規資料 → dry-run 對照報告 → 在測試副本新增欄位及集合 → 回填／保留舊欄位 → 程式雙讀相容、以新欄位寫入 → 比對主外鍵及金額 → 建唯一索引 → validator 由相容過渡至嚴格 → 完成驗收後才移除舊欄位。需要切換寫入時使用短暫維護窗，避免新舊版本同時寫出不一致資料。

預計腳本：20260913\_01\_expand\_schema.py、20260913\_02\_backfill.py、20260913\_03\_indexes.py、20260913\_04\_validate.py；這是實作工作清單，本次未交付或執行這些腳本。不得宣稱已完成一鍵初始化。回滾先停寫，恢復匹配的程式與資料備份；網站版本回退不等於資料庫回退。

## 10\. 部署與命名規範整合

Hosting 承接網站入口及靜態檔，Python Flask 在 Cloud Run 執行，MongoDB 在 Atlas；保留部署手冊的 rewrite、健康檢查與容器設定。[Firebase 官方整合說明](https://firebase.google.com/docs/hosting/cloud-run)

|附件名稱／設定|本期使用方式|
|-|-|
|MONGODB\_URI|現有程式 MONGO\_URI；未加相容讀取前使用舊名稱|
|MONGODB\_DATABASE|現有程式 MONGO\_DB；新 DB 建議 vibecart\_ai|
|API\_LLM\_KEY|現有 ANTHROPIC\_API\_KEY，存 Secret Manager|
|API\_LLM\_MODEL|現有 CLAUDE\_MODEL，依帳戶可用模型填入|
|LLM\_MODE|不直接取代 ENABLE\_CLAUDE；execution\_mode 為任務紀錄|
|LOCAL\_LLM\_BASE\_URL|本期不需要，本機批次 BGE 無 HTTP 模型服務|
|BGE\_REVISION|固定實際模型版本，記錄入向量文件|
|SECRET\_KEY|保留跨實例一致的 Session 金鑰|
|ENABLE\_CHECKOUT|保留預設關閉；交易驗收後啟用|
|AI\_DAILY\_CALL\_LIMIT／AI\_TOTAL\_CALL\_LIMIT|保留既有配額控制，不能只用 log 估算取代|
|Firebase Storage|需要上傳才開通；現有站內示範圖片可以繼續使用|

若未來接受新別名，同時設定舊新名稱且值不同時啟動直接報錯；不能靜默選錯 DB。`.env.example` 僅放範例，金鑰、URI 密碼與憑證不進 Git。

沿用命名：Python 函式／變數 snake\_case，類別 PascalCase，常數 UPPER\_SNAKE\_CASE，集合複數 snake\_case，JSON key snake\_case，業務關聯 {entity}\_id。Pydantic 類別保留 Document/Create/Update/Response/Filter/Summary/Result；Repository 存取 DB、Service 負責授權與商業一致性。AIService 統一調度 EmbeddingService、ClaudeService、RulesService；既有 LLMRouter 可供生成任務使用，不能強制 Embedding 假裝成聊天模型。

新 API 路徑可採 /api/products、/api/orders；訂單明細是內嵌快照，讀取採 /api/orders/{order\_id}/items，不提供直接改歷史明細的獨立 CRUD。既有 /ai/similar/{product\_id} 不因本文件直接失效，改路由須有相容及測試。

## 11\. 驗收清單、分工與時程

|驗收項目|通過條件|
|-|-|
|環境重建|至少兩台電腦可依 README 啟動；紀錄依賴版本|
|Schema|13 集合目標與既有資料有對照；初始化重跑不重複建 Seed|
|登入|原帳號可登入；不回傳 hash；customer 無法越權|
|金額|0.10＋0.20=0.30；特價不重扣；前端篡改價格無效|
|庫存|庫存 1、兩人同時結帳最多一張成立；多商品失敗全回滾|
|冪等|同 checkout\_id 不重扣；不同內容同 key 回 409；未知提交結果可查回|
|推薦|下架／缺貨不推薦；同向量版本；更新商品後舊向量排除|
|個人化|兩位不同偏好／行為會員結果可解釋；新會員有冷啟動結果|
|AI|模型／Prompt／耗時／模式可追溯；超時與備援不報假成功|
|快取與配額|快取不呼叫上游；失敗後配額不任意回補；遷移不重設 count|
|報表|Demo 與真實資料分開；日期日界一致；沒有全期間數據就標示樣本|
|部署|web.app 登入持續、商品／API 可讀；healthz/readyz 通過；斷線回可診斷訊息|

|時段|執行重點|驗收產物|
|-|-|-|
|09/13～09/18，Week 2|欄位映射、分類／商品 CRUD、偏好與 BGE、補 M1 缺口|Schema 遷移測試、M2 搜尋→商品→推薦|
|09/19～09/25，Week 3|兩個後台 AI 板塊、KPI、紀錄、部署測試|M3 外網展示、模型效能／成本紀錄|
|09/26～10/02，Week 4|凍結新增功能、整合驗收、簡報、彩排|M4 10 分鐘 Demo、阻斷問題清零、Release|

分工建議：Sam 負責 PM／文件／整合，陳仁千負責舊站與前端，邱伊平 負責 Flask／MongoDB，黃健維 負責 AI／測試／部署； GitHub 帳號與分支項目 9/16確認。feature/\* 經 PR 至 develop，由非作者複核，main 保存可展示版；Model、Validator、Index、Migration 與關鍵測試在同一功能 PR 對齊。

Demo：會員登入→調偏好／查商品→看 BGE 推薦→加入購物車→Demo 結帳；管理員登入→看 KPI→Local 推薦分析→Claude 彙總洞察→展示 latency／Token／備援。相似度任務與文字生成任務分開評估；比較 Baseline/BGE 的推薦命中與耗時，另評 Claude 摘要數字正確性與成本，不把不同任務分數硬排成模型優劣。使用 Atlas 的網站仍依賴網路，本機 Embedding 沒有 API 費不等於整站零成本。

仍需組內補齊的部署輸入：專題 Firebase Project ID、Atlas 目標 DB、費用負責人、Claude 可用模型與額度、正式 Repo 與分工。四個 API 練習專案不自動沿用為 VibeCart 部署目標。

## 12\. 版本變更紀錄與文件優先序

|版本|日期|主要內容|
|-|-|-|
|專案整合 v1.0|2026-09-09|MuscleCore 重構方向、4 集合 MVP、14 集合藍圖、四週計畫|
|部署手冊 v1.1（獨立文件）|2026-09-11|VibeCart 定名、Flask／Firebase／Atlas、8 集合、BGE／Claude 部署流程|
|專案整合 v1.1（本文件）|2026-09-13|審查 CONVENTIONS 雙附件、修正框架與登入衝突、完整欄位與畫面映射、13 集合目標、遷移及驗收規格|

優先序：使用者最新決策 → 本文件的目標設計 → 部署 v1.1 的現有程式操作事實 → 09/09 舊方案。本文更新專案規格，不宣稱部署手冊所描述的程式已具備新欄位。FastAPI、Firebase Auth、Render/Azure 選型、舊母品牌命名與強制 14 集合，不再作為本期必要決策。部署手冊保留作現有版本操作依據，待程式與資料遷移完成後再同步其下一版。

來源查核：CONVENTIONS.md 全文、CONVENTIONS.pdf 全文、09/09 專案文件全文、09/11 部署手冊全文。官方技術頁於 2026-09-13 查閱；本次無資料庫連線、雲端部署或付費模型執行，驗收表全部為待執行條件。

