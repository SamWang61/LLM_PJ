# v4 離線偏好快照操作 / Offline preference snapshots

更新：2026-10-20（Asia/Taipei）。[黃健維（JEFF）](mailto:jeff841117@gmail.com)負責推薦／計分契約，[汪文彥（SAM）](mailto:cashsam@gmail.com)負責資料庫、測試與整合，沿用[現行分工](TEAM_OWNERSHIP.md)。程式位於 `VibeCart_AI/services/preference_service.py`，批次入口為 `scripts/rebuild_preference_scores.py`。

PR #5 的前台推薦部分已由現行請求時計分接續；**明確指定會員的離線持久快照工具尚未被取代**。此工具須主動執行，預設dry-run，未接入前台請求或啟用排程。本輪修復與交付不連線或寫入Atlas，也不代表正式環境已採用快照。

## 與現行6＋4的計分界線

現行 `app/services/storefront_ranking.py` 每次請求讀取最近最多1000筆合格行為並計算6＋4推薦；分類累計也做時間衰減，沒有明確分類的SEARCH可依文字找商品／分類。[10/18對話決議](../討論的相關記錄/商品評價與猜你喜歡6加4推薦_對話決議_2026-10-18.md)記錄其實作與正式驗收範圍。

本工具保留快照 `score_version=1` 原語義：分類以**原始權重累計**後封頂70／30，只有商品分數逐事件衰減；SEARCH只使用明確ObjectId參照。兩者的事件窗口與分類算法不同，數值不保證相等。離線快照不替換現行首頁排序，也不推算新的跨類關聯規則。

## 計分契約 / Scoring contract

| 行為 | 現行預設權重 | 商品分數半衰期 |
|---|---:|---:|
| PURCHASE | 4 | 365 天 |
| ADD_TO_CART | 3 | 180 天 |
| SEARCH | 2 | 90 天 |
| PRODUCT_VIEW | 1 | 30 天 |

執行時讀取資料庫有效政策，不使用前台 legacy 的 1／3／4／8 基線。僅支援版本 1；未支援版本或政策不合法時停止。事件按時間與 event_id 排序，每個事件只計一次，不乘以購買數量；相同 event_id 卻內容不同時報錯。

大、小類別分數為原始事件權重總和，分別封頂 70、30。商品分數逐事件計算 `weight × 0.5 ** (age_days / half_life_days)` 再加總，避免把新事件的日期套用到整段歷史；raw_score 保留未衰減總和。

只計指定有效v4會員在計算時間以前的事件，匿名事件不歸入會員。**先排除synthetic與synthetic_batch_id，再排序及套用事件上限**，避免合成批次擠掉真人事件。SEARCH只使用明確分類／商品ObjectId，不從文字推測參照。

PURCHASE須連到同一會員、v4、已付款且未取消的有效訂單；失效、退款或找不到訂單不計。依現行personalization契約，真人會員的有效示範已付款購買可影響本人快照，但仍不計入正式成效歸因。合成事件即使連到有效訂單也排除；快照工具不改變監控／歸因的production篩選規則。瀏覽、搜尋、加購不做付款判定。

Categories retain capped raw totals; products decay per event. Personalization excludes synthetic batches before limiting and permits a real member's valid demo purchase. This is distinct from production attribution and request-time ranking.

## 預覽與寫入 / Preview and apply

在倉庫根目錄使用已安裝網站測試依賴的Python環境。私有設定檔須明確提供v4連線、MONGO_DB及有效會員ObjectId；URI與密碼不要放進命令列、Git或報告。以下僅示範語法，本輪沒有執行Atlas操作。

```powershell
# 預設只讀取及計算，stdout 僅輸出彙總筆數
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/rebuild_preference_scores.py --env-file '<私有設定檔>' --user-id '<會員ObjectId>'

# 需另有該資料庫寫入授權；名稱必須精確符合設定檔的 MONGO_DB
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/rebuild_preference_scores.py --env-file '<私有設定檔>' --user-id '<會員ObjectId>' --apply --database-confirm '<該設定檔的MONGO_DB>'
```

每次限明確指定1～100位會員，可重複 `--user-id`，重複ID只執行一次。`--max-events` 預設10000，合法範圍1～100000；任一會員超過上限即停止，不寫入截斷快照，也不提供無界全庫掃描。`--apply`與精確的 `--database-confirm` 是CLI寫入必要條件；服務層apply仍獨立檢查user_id單欄唯一索引，不能繞過CLI向不符合條件的集合寫入。

每位會員替換一份完整快照，不累加舊分數，因此可重跑。已有快照時以**完整前像**作compare-and-swap，若其他worker先更新則拒絕覆蓋；較舊as_of不能取代較新快照，首次建立由唯一user_id索引防重。批次以單一會員為提交單位；後面會員失敗時，前面已提交快照仍保留。輸出只給進度／彙總與去敏錯誤，不將失敗批次稱為整批成功或整批rollback。

衰減每次重算，無新事件仍會更新商品分數。不修改 `behavior_events.processed_at`，保留既有 `cross_category_scores`，本服務不推算關聯規則。

寫入前重新讀取會員與政策；會員失效、政策改變或快照並行更新時停止該會員。這仍不是跨集合的時間點交易，檢查後仍可能有新事件、訂單退款、會員或政策異動。請在單一政策的維護時段執行，並在下一輪完整重建收斂，不宣稱已消除所有跨集合競爭窗口。排程建置、正式部署與正式資料apply均須另有實際版本及驗收證據。

The default is read-only. Apply commits per member, uses optimistic concurrency and preserves cross-category scores. A failed batch can have earlier completed members. Subsequent rebuilds converge event/order changes; this is not a multi-collection transactional snapshot.

## 驗證與上線狀態 / Verification and rollout

本輪測試入口為 `MuscleCore分析資料/website/tests/test_preference_scores.py`、`test_preference_score_persistence.py`與`scripts/test_preference_cli.py`；[新交付報告](PR5_SCORING_DELIVERY_2026-10-20.md)記錄74項唯一測試、真localhost MongoDB與清理。CI及合併SHA以本輪PR最新HEAD為準，不把工具合併當Atlas上線或排程啟用。

[SAM_SCORING_VERIFICATION.json](SAM_SCORING_VERIFICATION.json)、[sam-scoring.csv](inventory/sam-scoring.csv)及[SAM_WORK_PLAN.md](SAM_WORK_PLAN.md)保留**2026-10-02歷史**。其中50項離線測試與Atlas預覽／寫入／重跑記錄只證明當時來源與舊語義；原先排除示範購買的結果不適用於本輪personalization更新，不能冒充今日重跑。

The current delivery is an opt-in offline snapshot tool. It does not enable a scheduler, alter storefront ranking, or write to Atlas during this repair. Historical October2 verification remains dated; new results belong to the current PR record.
