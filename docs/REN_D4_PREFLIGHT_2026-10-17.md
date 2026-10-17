# D4 正式庫唯讀 preflight｜2026-10-17 16:05（台灣時間）

SAM 暫代 REN 執行 D4 資料層前置核對。程式來自 GitHub `main` `57ea59b42c59a4f984e16ead42159b2b2a60cf56`；`VibeCart_AI/MongoDB/test_data/behavior_import.py` 的本機與該提交 Git blob 均為 `69b93a17492433d210abcd196f9111c8ad912c3f`。僅在程序記憶體取得 Cloud Run 正式服務原有 Secret Manager Mongo URI，先核對 scheme、主機、資料庫與帳號，再以 `run(db, action="preflight", max_orders=100)` 執行。未列印、保存 URI 或密碼，未執行 `dry-run`、`apply` 或任何資料庫寫入。

## 程式讀回

| 項目 | 結果 |
|---|---|
| 目標 | Atlas `vibecart_ai`，指定 D4 batch `sam-behavior-20261011-v1` |
| `check_schema` | `behavior_events` validator 與 Git 定義相同，`validationLevel=strict`、`validationAction=error`；6 個索引（含 `_id_`）及鍵／唯一性檢查通過。Atlas 連接器另唯讀列出這 6 個索引。 |
| D1～D3 來源 | `sam-synthetic-20261005-v1` 的訂單、明細、會員、商品參照可供 fixture 建置與驗證。 |
| 規劃事件 | **1,240**：ADD_TO_CART／PRODUCT_VIEW／PURCHASE／SEARCH 各 **310**。此為最多 100 筆來源訂單所規劃的合成練習事件，非正式績效或轉換率。 |
| dataset SHA-256 | `da6998425bc80746902b407336489f43bfcc77bc7f092d9ece5e3b02d1d0edea` |
| preflight 報告 | `status=passed`、`existing=0`、`missing=1240`、`committed=false`、`inserted=0`、`database_writes=0`。 |

執行後另以 Atlas 連接器唯讀計數：指定 D4 batch **0**；原 D1～D3 batch 訂單 **3,000**、明細 **8,969**。這證明本次沒有把 D4 寫入正式庫，也沒有重匯 D1～D3。

## 尚未解除的匯入閘門

資料層 preflight 成功**不等於 D4 可 apply**。正式流量仍由舊 `vibecart-web-00007-m9k` 承接；已部署的後台監控與前台推薦尚缺同版遠端合成／正常事件對照、排序／limit 前排除、輸出讀回與測後清理證據。計分排程及正式歸因的未部署判定也須以匯入當時的完整雲端資產清單重查。待這些證據經核對後，才按 [D4 閘門與程序](D4_REMOTE_GATE_2026-10-17.md)執行交易 rollback dry-run，再考慮 apply、讀回及冪等重送。**目前不得 apply。**
