# 2026-10-05 客戶與跨年訂單匯入結果 / Synthetic data import result

目的地：Atlas `vibecart-ai-free`／`vibecart_ai`；批次：`sam-synthetic-20261005-v1`。依 [測試資料規範](TEST_DATA_SPEC.md) 執行。本次不是新建隔離資料庫，也不是正式交易。

## 已完成 / Completed

| 項目 | 結果 |
|---|---|
| 合成客戶 | 600；男／女各 300，六年齡層各 100，五婚姻狀態各 120 |
| 跨年訂單 | 3,000；2024-01-01～2026-10-05，34 個年月 |
| 訂單明細 | 8,969；同 SKU 不在同單重複，單價／數量／合計一致 |
| 有效訂單 | 1,800（paid 且未取消）；均為示範，不是實際收款 |
| 無訂單會員 | 67，包含固定保留的 60 位 |
| Schema | 27 集合、86 索引；3 集合增補可選欄位，strict/error 保留；新遷移 succeeded |
| 離線測試 | 9 項通過：可重複、人口分布、月份／demo、故意破壞金額／關聯／時間／標記、增補結構與排序獨立性 |
| Atlas 試寫 | 全批交易插入後回滾，原筆數不變 |
| 正式匯入 | 12,569 筆文件單一交易提交，不覆寫既有文件 |
| 完整讀回 | 全部 BSON 文件比對與關聯／金額／日期重驗通過 |
| 獨立營收對照 | Atlas 依台北月份聚合，與 Python 標準答案一致 |
| 既有資料 | 商品／SKU 完整快照雜湊不變；既有庫存未扣減，其他集合筆數不變（新遷移紀錄除外） |

Atlas 外掛要求重新登入，實際操作使用專案既有受忽略設定與 PyMongo，先驗證固定 host／DB。不輸出 URI、不更動 Cluster 方案、網路白名單或帳號權限。

English: Imported 600 synthetic customers, 3,000 demo orders and 8,969 order items into the explicitly requested database. Transaction dry-run, full BSON readback, relationships, amounts and independent Atlas monthly aggregates passed. Existing products and stock were unchanged.

## 證據 / Evidence

- [生成清冊與雜湊](../VibeCart_AI/MongoDB/test_data/generated/manifest.json)
- [每日／每月／熱銷／人口標準答案](../VibeCart_AI/MongoDB/test_data/generated/expected_metrics.json)
- [交易試寫回滾](../VibeCart_AI/MongoDB/test_data/generated/dry-run_report.json)
- [正式匯入與完整讀回](../VibeCart_AI/MongoDB/test_data/generated/apply_report.json)
- [再次唯讀核對](../VibeCart_AI/MongoDB/test_data/generated/verify_report.json)：全數通過，新增 0 筆，未重複匯入。
- 遷移前結構：`test_data/generated/migration_before.json`（原工作目錄私有快照，不推送 GitHub）
- [遷移後結構驗證](../VibeCart_AI/MongoDB/test_data/generated/migration_after.json)

CSV 預覽及完整 Extended JSON 位於 `VibeCart_AI/MongoDB/test_data/generated/`，另以目錄的 .gitignore 排除大型輸出；會員 CSV 只含合成識別與人口欄位，沒有登入密碼。

## JEFF／HEN 如何使用 / Handoff

1. JEFF 後台連指定 v4 資料庫，查詢 `synthetic_batch_id` 可限定本批；日期須以台北日界轉 UTC。
2. 驗證某月 KPI／每日營收，對照 expected_metrics.json；不要一次查跨三年而突破後台 366 天上限。
3. 全部／僅示範應能看到本批；排除示範時本批為 0，空畫面屬預期，不是匯入失敗。
4. 本批會員全部停用，不能拿來驗證登入；需另配置少量私有登入帳號。婚姻資料僅為截止日狀態，歷史年齡應由生日另算。
5. 本批不生成 behavior_events、評價、向量或 AI 執行資料；這些仍可能顯示空狀態。JEFF D1／D2 有超市商品與照片，D3 本次完成，D4 行為事件及 D5 寫入契約待後續。
6. 日期篩選、下架商品推薦及 AI 請求預覽等原型問題仍須 JEFF 串接後重測。不得把資料生成成功當作實際模型推論或網站驗收通過。

本機程式與文件已保存；本次任務沒有提交／合併其他工作中的 GitHub 分支，也沒有修改 JEFF 原型或替 HEN 接受邀請。
