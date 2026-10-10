# 客戶與跨年訂單測試資料 / Synthetic customers and cross-year orders

規範與生成順序見 [TEST_DATA_SPEC](../../../docs/TEST_DATA_SPEC.md)。本批使用既有超市商品，指定資料庫為 vibecart_ai。

- `schema_test_profile.py`：v4 可選人口／批次欄位 overlay，歷史 migration 保留。
- `workflow.py`：生成、增補結構、交易試寫回滾、正式匯入、讀回驗證。
- `test_workflow.py`：可重複性、人口覆蓋、跨年、金額／關聯／時間／demo 破壞測試。
- `generated/manifest.json`：數量及完整資料雜湊。
- `generated/expected_metrics.json`：依台北日期計算的測試標準答案。
- `generated/apply_report.json`／`verify_report.json`：實際匯入與後續讀回證據；以文件比對、結構及聚合驗證結果判定完成。

All generated orders are demo; test accounts cannot log in. No existing catalog or stock is changed. Generation and import success do not establish frontend or real AI acceptance.

## D4 行為事件（2026-10-11）

`behavior_fixture.py` 提供離線 `build(data, catalog)`、`validate`、`expected`；新批次 `sam-behavior-20261011-v1`。`test_behavior_fixture.py` 驗證重現性與參照、時序、隔離、数量、重複等拒絕案例。無資料庫連線／匯入功能；正式入庫前需 JEFF 完成所有事件消費者的 synthetic 隔離。合併清單見 [JEFF 回覆與 SAM 工作](../../../docs/JEFF_REPLY_SAM_PLAN_2026-10-11.md)。

`behavior_import.py` 新增 live-reference preflight／transaction dry-run／gated apply／verify，僅寫 `behavior_events`。preflight唯讀，dry-run試寫後回滾；apply需實際部署隔離證據。報告僅數量／雜湊，不含會員資料或憑證。操作及本輪證據見 [SAM驗收矩陣](../../../docs/SAM_ACCEPTANCE_2026-10-11.md)。
