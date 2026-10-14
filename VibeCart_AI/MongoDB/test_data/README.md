# 客戶與跨年訂單測試資料 / Synthetic customers and cross-year orders

規範與生成順序見 [TEST_DATA_SPEC](../../../docs/TEST_DATA_SPEC.md)。本批使用既有超市商品，指定資料庫為 vibecart_ai。

- `schema_test_profile.py`：v4 可選人口／批次欄位 overlay，歷史 migration 保留。
- `workflow.py`：生成、增補結構、交易試寫回滾、正式匯入、讀回驗證。
- `test_workflow.py`：可重複性、人口覆蓋、跨年、金額／關聯／時間／demo 破壞測試。
- `generated/manifest.json`：數量及完整資料雜湊。
- `generated/expected_metrics.json`：依台北日期計算的測試標準答案。
- `generated/apply_report.json`／`verify_report.json`：實際匯入與後續讀回證據；以文件比對、結構及聚合驗證結果判定完成。

All generated orders are demo; test accounts cannot log in. No existing catalog or stock is changed. Generation and import success do not establish frontend or real AI acceptance.
