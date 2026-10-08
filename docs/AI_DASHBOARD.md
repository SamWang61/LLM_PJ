# 營運後台與 v4 測試交接 / Dashboard handoff

> 最新責任：AI／後台由 JEFF 負責；SAM 負責資料庫與測試。下文保留先前交付的技術與合併紀錄，不再代表現行分工。見 [現行分工](TEAM_OWNERSHIP.md)。Current ownership supersedes historical delivery attribution.

## 分支與負責人 / Branch ownership

先前交付紀錄：SAM 曾完成 AI 後台與 Atlas v4 連線交接。`feature/ai-dashboard` 建在 `feature/flask-sku-ai-integration` 之上；[PR #3](https://github.com/SamWang61/LLM_PJ/pull/3) 與 [PR #2](https://github.com/SamWang61/LLM_PJ/pull/2) 已依序合併，功能已進入 main；詳見 [合併與連線管理紀錄](MERGE_RECORD_2026-10-02.md)。現行責任以 TEAM_OWNERSHIP.md 為準。

合併方向：`feature/ai-dashboard` → `feature/flask-sku-ai-integration` → `main`。本次起點為整合提交 `bbb8e9c`；不用重建分支、強制推送或覆蓋同學工作。父分支進展時先 fetch，再 merge 父分支並重跑測試。

SAM previously delivered this stacked feature; current AI/admin ownership belongs to JEFF. Both dependent PRs have been merged in order; the delivery is now on main.

## 目錄責任 / File ownership

| 路徑 | 用途 / Purpose |
|---|---|
| `MuscleCore分析資料/website/app/admin.py` | 後台權限與篩選路由 / Admin routes |
| `MuscleCore分析資料/website/app/services/dashboard.py` | 日期、營收、庫存與行為監測 / Dashboard queries |
| `MuscleCore分析資料/website/app/services/ai_workflows.py` | AI 彙總範圍、快取與退回 / Summary workflow |
| `MuscleCore分析資料/website/app/templates/admin/` | 後台頁面；`layout.html` 為共用版型 / Admin views and shared layout |
| `MuscleCore分析資料/website/app/static/css/admin.css`、`static/js/admin.js` | 後台專用樣式與互動（不改前台 `main.css`／`base.html`） / Admin-only assets |
| `MuscleCore分析資料/website/tests/test_dashboard.py` | 範圍、權限與金額測試 / Offline tests |
| `MuscleCore分析資料/website/tests/test_admin_layout.py` | 共用版型、KPI 口徑、篩選同步與推薦政策測試 / Layout tests |
| `scripts/verify_v4_test.py` | 真實 Atlas 讀回及可清理測試 / Live verification |

保留原始架構、歷史報告與 migration；不改動已執行 migration 的 checksum。舊全量清冊保留為歷史快照；本次交付清冊另存 `docs/inventory/ai-dashboard.csv`，不把缺少本機大型附件的 worktree 當成全量來源。

Existing module paths and migration history are preserved. The scoped manifest supplements the historical full inventory.

## 已實作行為 / Implemented behavior

- 後台需有效管理員權限；每次請求讀回角色，寫入請求驗證 CSRF。
- 預設最近 100 筆；可指定台北日期，含結束日，最多 366 天／5,000 筆。超額顯示錯誤，不提供截斷後的區間統計。
- v4 可包含、排除或只看示範訂單；有效營收只計 paid 且未取消的訂單，金額保留 Decimal 精度。
- 每日營收、平均客單、區間熱銷與最近訂單共用篩選；每日表只列有有效訂單的日期。低庫存為目前狀態，不是歷史庫存；顯示總數及最多 100 個 SKU。
- 摘要只在按鈕提交時產生；快取區分日期與示範篩選，失敗或未啟用模型時顯示規則摘要。
- 推薦監測顯示最近 1,000 筆事件的前 20 組統計；不冒充點擊率／轉換歸因。資料庫推薦政策與現行執行權重分開呈現。
- legacy 保留既有未取消訂單與商品累計排行口徑，不稱為付款確認報表。

### 2026-10-09 後台共用版型（JEFF，T1／R05）

- 依設計規格 v1.1（PR #8 `docs/JEFF_ADMIN_UI_DESIGN.md`）第 4 節：獨立後台頁首（管理員、回商城、登出，不顯示購物車）、左側導覽（目前頁 `aria-current`）、系統狀態燈（資料庫／BGE／雲端 LLM，燈號旁有文字）。尚未實作的頁面在導覽中標示「尚未開放」，不連到不存在的路由。
- 狀態燈只反映設定層級：綠＝已設定／已載入、黃＝未安裝或未設定而退回規則、灰＝未啟用；不代表模型呼叫已成功。
- RWD：≥ 900px 側欄；620–899px 頂部可橫向捲動分頁列、狀態移至頁尾；< 620px 漢堡選單、KPI 一欄、按鈕全寬、表格橫向捲動。
- 懸浮提示由 Flask `flash` 驅動：成功 3.5 秒、錯誤 6 秒，滑鼠移上暫停。
- 營運總覽：KPI 改為「有效／全部訂單」（分母只套日期與示範篩選）；零有效訂單時平均客單顯示「—」，送給摘要模型的 `average_order_value` 為 `null`。每日有效營收加純 CSS 長條圖（高度相對同一篩選結果的最高日），表格保留於下方。範圍內含示範訂單時頁首標示「示範資料 n 筆」。
- 推薦監控：權重表改讀 v4 `recommendation_policy`，依權重排序並附中文名稱；明示前台規則基線尚未改用此政策（待 T7）。
- `POST /admin/summary` 與既有測試不變；新增 11 項離線測試，共 66 項通過。瀏覽器以本機 mongomock 預覽檢查桌機／平板／手機版面，未連線或寫入 Atlas；以私有 admin 帳號登入真實資料的畫面驗收待 D6 帳號（R04）。

Taipei date filters and demo exclusions apply consistently to v4 revenue, daily totals, ranking and summaries. Inventory is current; recommendation events are bounded counts, not attribution metrics.

## 私有連線與啟動 / Private connection and launch

SAM 的本機 `MuscleCore分析資料/website/.env.v4-test` 已備妥有效 URI，且受 Git 忽略與 Windows 檔案權限保護。不要貼到 PR、文件、聊天或共用雲端。此設定使用既有 `vibecart_ai` v4 資料庫，**不是新建的隔離測試資料庫**。Atlas connector 需重新登入，但本機 PyMongo 連線可獨立驗證。

使用應用程式 readWrite 帳號；不使用 schema 管理帳號啟動網站。預設 checkout、BGE、Claude 皆關閉。既有環境變數優先於設定檔；切換環境時使用新的終端並重新登入網站。

```powershell
cd MuscleCore分析資料\website
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-test.txt
# 確認 SAM 私下配置的 .env.v4-test 已在本機，再啟動
.\run_v4_test.ps1
```

`run_v4_test.ps1` 透過 `APP_ENV_FILE` 選擇設定，不覆蓋原 `.env`。沒有設定檔就停止。不要執行 legacy seed 寫入 v4。測試帳號與資料會清理，因此驗證後不留下共用管理員帳密。

The ignored local profile contains the existing v4 connection. It is not a newly isolated database. Keep it private; default checkout and model flags remain disabled.

## 驗證與剩餘界線 / Validation and limits

2026-10-02：38 項離線測試通過；真實 Atlas 的 27 集合、86 索引與五組整合檢查通過，測試資料筆數已恢復。離線測試涵蓋日期邊界、退款與取消排除、Decimal、空資料、超額查詢、CSRF、角色撤銷、摘要快取及輸出跳脫。真實 Atlas 結果以 [讀回報告](V4_TEST_VERIFICATION.json) 為準。

從倉庫根目錄執行讀回；`--smoke` 會寫入唯一識別的測試資料並清理，只可用於 SAM 已授權的 v4 測試環境：

```powershell
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/verify_v4_test.py --env-file 'MuscleCore分析資料/website/.env.v4-test' --smoke --report docs/V4_TEST_VERIFICATION.json
```

流程驗證註冊登入、購物車增刪改、結帳重送、管理員撤權、真實交易 rollback 與最後庫存併發。清理只使用本次產生的 ID，並比較執行前後集合筆數。報告不含 URI 或密碼，不執行歷史 migration。

完整 6+4 推薦、排程衰減／計分與批次統計仍屬後續工作；本次完成的是 SAM 的後台、連線與既有整合驗收。BGE 真實推論、Claude API 及手機全站 UAT 尚未驗收，不能把規則退回稱為模型成功。未提供模型憑證時不呼叫付費 API。

Live checks exercise real transactions with temporary owned fixtures. Real BGE/Claude providers and full scheduled recommendation processing remain outside the verified delivery. No migration or production deployment is performed.
