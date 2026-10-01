# v4 行為計分操作 / Preference scoring

SAM 負責。本服務依現行 v4 Schema 的 `recommendation_policy` 計算會員偏好，補上先前只有欄位與政策、沒有工作程序的缺口。程式位於 `VibeCart_AI/services/preference_service.py`，批次入口為 `scripts/rebuild_preference_scores.py`。

## 計分契約 / Scoring contract

| 行為 | 現行預設權重 | 商品分數半衰期 |
|---|---:|---:|
| PURCHASE | 4 | 365 天 |
| ADD_TO_CART | 3 | 180 天 |
| SEARCH | 2 | 90 天 |
| PRODUCT_VIEW | 1 | 30 天 |

執行時讀取資料庫有效政策，不使用前台 legacy 的 1／3／4／8 基線。僅支援版本 1；未支援版本或政策不合法時停止。事件按時間與 event_id 排序，每個事件只計一次，不乘以購買數量；相同 event_id 卻內容不同時報錯。

大、小類別分數為原始事件權重總和，分別封頂 70、30。商品分數逐事件計算 `weight × 0.5 ** (age_days / half_life_days)` 再加總，避免把新事件的日期套用到整段歷史；raw_score 保留未衰減總和。

只計指定會員在計算時間以前的事件。SEARCH 只使用事件已明確記錄的分類／商品 ObjectId，不從文字猜測；匿名事件不歸給會員。PURCHASE 需能連到同一會員的 v4 已付款、未取消且 `is_demo=false` 訂單；失效、退款、缺少訂單及示範購買皆不計分。瀏覽、搜尋、加購不做付款判定。

Categories use capped raw totals. Product scores decay each unique event independently. Quantity does not multiply an event's weight. Only valid non-demo paid purchase events contribute; unmapped search text is never guessed.

## 預覽與寫入 / Preview and apply

在完整倉庫根目錄，使用已安裝網站測試依賴的 Python 環境。將 `<會員ObjectId>` 換成已授權測試的有效 v4 會員；不要把 URI 寫入命令列。

```powershell
# 預設只讀取及計算，stdout 僅輸出彙總筆數
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/rebuild_preference_scores.py --env-file 'MuscleCore分析資料/website/.env.v4-test' --user-id '<會員ObjectId>'

# 明確指定寫入，database-confirm 必須符合設定檔的 MONGO_DB
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/rebuild_preference_scores.py --env-file 'MuscleCore分析資料/website/.env.v4-test' --user-id '<會員ObjectId>' --apply --database-confirm vibecart_ai
```

可重複 `--user-id`，每次最多 100 位明確指定的會員；重複 ID 只執行一次。每人預設最多 10,000 事件，`--max-events` 可調整至 100,000。超過限制停止該會員，不寫入不完整統計；不提供無界全庫掃描。寫入前要求 user_id 唯一索引。

每位會員獨立提交完整分數快照，不做累加，因此失敗後可重跑。使用原快照比對防止覆蓋另一個 worker 的更新；較舊計算時間不能覆蓋新快照。若批次中途失敗，前面會員已完成的提交保留，stdout 有進度，不能稱為整批成功或整批 rollback。

衰減每次重算，無新事件仍會更新商品分數。不修改 `behavior_events.processed_at`，避免干擾其他消費者；保留既有 `cross_category_scores`，本服務不推算關聯規則。一次執行期間新增事件或訂單狀態異動，由下一次重算收斂；這不是跨集合的時間點交易快照。應以單一政策維護時段更新政策並重新計算。

The default is read-only. Apply commits per member, uses optimistic concurrency and preserves cross-category scores. A failed batch can have earlier completed members. Subsequent rebuilds converge event/order changes; this is not a multi-collection transactional snapshot.

## 驗證與上線狀態 / Verification and rollout

離線測試：`MuscleCore分析資料/website/tests/test_preference_scores.py`；真實驗證已加入 `scripts/verify_v4_test.py --smoke`，以臨時會員實測預覽、寫入、重跑、嚴格 validator 與示範購買排除，最後清理分數文件。證據：[SAM 計分驗證](SAM_SCORING_VERIFICATION.json)。

此階段未替真實會員建立永久分數，未啟用排程，也未替換前台推薦流程。完成的內容是計分服務、可執行工具與驗證；6＋4 推薦、首次推薦池、模型與關聯統計仍見 [SAM 清單](SAM_WORK_PLAN.md)。

No permanent real-member scores or scheduler were enabled by this delivery. Frontend ranking remains unchanged; the new scoring service is ready for controlled use and later integration.
