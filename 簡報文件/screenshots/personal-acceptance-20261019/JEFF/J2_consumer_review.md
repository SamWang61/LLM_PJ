# JEFF J2｜behavior_events consumer 與 synthetic 排除覆核

- 本人姓名／代號：黃健維 JEFF（已確認，見第 6 節）
- 覆核方式：原始碼唯讀比對（由 Claude Code 依 JEFF 指示整理，JEFF 覆核）；未連線正式資料庫、未寫入、未部署
- 比對時間（Asia/Taipei）：2026-10-20
- GitHub main：`c66f731`（PR #5 合併後）
- 正式部署來源：`fc4e7c071c34a43594a50f6d0407952e8f20113b`（依 `docs/SAM_FIVE_N11_2026-10-20.md`、`docs/inventory/SAM_FIVE_N15_FINAL_2026-10-20.json`：正式 `vibecart-web-five-fc4e` 100%，digest `5efdd89f…`）
- 判定基準：`docs/JEFF_ADMIN_UI_DESIGN.md` v1.2 第 12.1 節「D4 synthetic 事件不計入正式推薦歸因」，以及 B2 決定「真實會員的示範購買計入個人推薦、不計入歸因」

## 1. 兩種過濾範圍（`app/services/behavior_scope.py`）

| 函式 | 排除條件 | 用途 |
|---|---|---|
| `production_behavior_query()`／`production_events()` | `metadata.synthetic=true`、`metadata.synthetic_batch_id` 非空、`metadata.exclude_from_attribution=true` | 監控、歸因、推薦成效 |
| `personalization_behavior_query()`／`personalization_events()` | 只排除 synthetic（`synthetic=true` 或有 `synthetic_batch_id`） | 會員自己的個人推薦（示範結帳仍會影響） |

## 2. 讀取端 consumer（正式部署來源與 main 逐檔 blob 相同）

| # | 程式 | 讀取方式 | 使用範圍 | 判定 |
|---|---|---|---|---|
| R1 | `app/services/dashboard.py:99` 推薦監控 | `behavior_events.find(production_behavior_query())` | production | ✅ synthetic 與示範購買都排除 |
| R2 | `app/store_v4.py:26` `recommendation_blocks()`（前台 6+4） | `find(personalization_behavior_query({'user_id': 會員}))`，limit 1000，**在 limit 之前排除 synthetic** | personalization | ✅ synthetic 排除；示範購買保留（B2） |
| R3 | `app/services/storefront_ranking.py:57` `recommendations_6_4()` | 再以 `personalization_events()` 過濾 | personalization | ✅ 雙重排除 |
| R4 | `app/services/ai_workflows.py:158、200` `storefront_recommendations()`（規則／BGE） | `personalization_events()` | personalization | ✅ |
| R5 | `app/services/recommendation.py` 規則推薦 | 由 R4 傳入已過濾事件 | personalization | ✅ |
| R6 | `app/store.py:25`（legacy 首頁） | `personalization_behavior_query()` | personalization | ✅；正式為 `DATA_MODE=v4`，此藍圖不註冊 |
| R7 | `VibeCart_AI/services/preference_service.py:172`（PR #5 持久快照 CLI，**main 有、正式部署來源沒有**） | 查詢內排除 `synthetic`／`synthetic_batch_id`，在排序／limit 之前；示範購買保留給個人化 | personalization | ✅；屬手動批次工具，不是線上服務 |

後台 AI 頁（雲端洞察、Local 相似商品、AI 比較）不讀 `behavior_events`。

## 3. 寫入端標記

| # | 程式 | 寫入事件 | 標記 |
|---|---|---|---|
| W1 | `app/services/member_events.py` `record_read_event()` | PRODUCT_VIEW、SEARCH | 只有設定 `BEHAVIOR_SYNTHETIC_BATCH` 時才標 synthetic；正式環境變數名稱清單**沒有**此變數（`SAM_FIVE_N15_FINAL` 讀回），真實會員事件不會被誤濾 |
| W2 | `VibeCart_AI/services/sku_cart_service.py:123` | ADD_TO_CART | 無特別標記（真實行為） |
| W3 | `VibeCart_AI/services/sku_cart_service.py:177` | PURCHASE | 示範訂單標 `demo_checkout`、`exclude_from_attribution`（不計歸因，但計入個人化） |
| W4 | `app/store.py:41、56、98`（legacy） | view／cart／purchase | `legacy_default=True` → 標 synthetic；正式 v4 不使用 |

## 4. 正式部署一致性

`behavior_scope.py`、`dashboard.py`、`recommendation.py`、`storefront_ranking.py`、`ai_workflows.py`、`store_v4.py`、`member_events.py`、`sku_cart_service.py`、`cart_service.py` 共 9 檔，正式部署來源 `fc4e7c0` 與 main `c66f731` 的 Git blob **完全相同**。main 比部署多出的只有 `VibeCart_AI/services/preference_service.py` 與 `scripts/rebuild_preference_scores.py`（PR #5，離線批次工具）。

## 5. D1～D4 不重匯

依 SAM 文件：D4 synthetic 維持 1,240 筆、未重匯（`docs/SAM_MAIN_PRODUCTION_ACCEPTANCE_2026-10-19.md`）；同映像私有探針「正常事件 13→14、加入 1,001 筆 synthetic 後仍 14」（`docs/inventory/SAM_PROXY_N11_SAME_IMAGE_2026-10-20.json`、`SAM_FIVE_N06_NORMAL_2026-10-20.json`）。本覆核未重新連線驗證資料筆數。

## 6. 結論與界線

- **原始碼層級**：所有讀取 `behavior_events` 的程式都套用了正確範圍；synthetic 不會回流正式歸因或個人推薦；示範購買只影響個人推薦。✅
- **本覆核不包含**：正式資料庫實際筆數的重新讀回、0% 流量舊修訂與其他 GCP 位置的資源（見 SAM N11 文件的界線）。
- JEFF 本人確認：上述結論**同意**；簽名：黃健維 JEFF；時間：2026-10-20 23:07（Asia/Taipei）。
