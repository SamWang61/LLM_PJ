# SAM 資料庫檢查與測試 / Database testing handoff

依 [現行分工](TEAM_OWNERSHIP.md)，SAM 負責資料庫與測試。本輪新增只讀查核工具及離線回歸測試，重新檢查既有 Atlas v4；不修改 JEFF 的 AI／後台與 HEN 的前台。

## 交付檔案 / Files

| 路徑 | 用途 |
|---|---|
| `scripts/check_v4_database.py` | 只讀 v4 檢查，多項差異合併報告 |
| `MuscleCore分析資料/website/tests/test_database_readiness.py` | 17 項離線檢查器回歸案例，無 Atlas 憑證、無寫入 API |
| [檢查前證據](SAM_DATABASE_CHECK_2026-10-02.json) | validator、索引、遷移與 12 組關聯的讀回 |
| [測試摘要](SAM_DATABASE_TESTS_2026-10-02.json) | 資料庫專項測試結果與執行前後筆數比較 |
| [測試後證據](SAM_DATABASE_POSTCHECK_2026-10-02.json) | 資料庫測試完成後的只讀查核 |

## 只讀查核 / Read-only audit

從倉庫根目錄執行，設定檔沿用本機受保護的 v4 URI。每次使用新的報告檔名；工具拒絕覆寫舊證據。

```powershell
& '.\MuscleCore分析資料\website\.venv\Scripts\python.exe' scripts/check_v4_database.py --env-file 'MuscleCore分析資料/website/.env.v4-test' --relationships --report docs/SAM_DATABASE_CHECK_YYYY-MM-DD_HHMM.json
```

- 檢查 27 集合的完整 validator、strict/error 模式、索引名稱、複合鍵順序、唯一性、partial／TTL／sparse 選項。
- 比較文件總數與合規數；回報缺少、異動與額外集合，不自動修復或刪除。
- 確認四筆既有 migration succeeded、沒有額外／未完成 migration，以及唯一有效推薦政策。
- `--relationships` 執行 12 組 v4 ObjectId 參照存在性檢查，涵蓋商品分類、SKU 商品、會員購物車／訂單、訂單明細與評價；只輸出孤兒數，不輸出會員或訂單內容。
- 退出碼：0 通過、1 發現差異、2 無法完成。發現差異時仍保存報告；連線或執行錯誤不宣稱完成。

Reports contain metadata and counts only. The tool has no write or migration operation and never overwrites historical evidence. Exit codes distinguish detected drift from incomplete execution.

## 測試分層 / Test layers

| 層級 | 本輪用途 | 界線 |
|---|---|---|
| 離線檢查器 17 項 | 模擬格式、索引順序／選項、資料合規、孤兒、migration 與政策異常 | 不依賴雲端、不驗證真實 MongoDB transaction |
| 既有網站離線測試 38 項 | 確認新增檢查器沒有破壞既有測試集合 | 並非本輪新增跨模組功能或最終驗收 |
| 既有 `VibeCart_AI/MongoDB/test_complete_v4.py` | 真實 v4 格式約束、SKU 交易及評價契約回歸 | 測試寫入以 transaction abort 或本次專用 ID 清理；只用已授權測試資料庫 |

執行離線測試：

```powershell
cd MuscleCore分析資料\website
.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

真實資料庫套件沿用既有 `bootstrap_schema.connect`，從 `VibeCart_AI/MongoDB` 執行；其本機 `.env` 與 `.env.schema` 必須已私下配置正確目標，不能上傳或以 legacy seed 初始化。執行前後均跑只讀查核。不要在 CI 自動連線 Atlas；現有 GitHub workflow 僅執行離線檢查。

## 解讀限制 / Limits

目前業務集合為空，孤兒數為 0 不代表已有真實資料或業務流程通過驗收。關聯檢查驗證被參照文件存在，不涵蓋所有跨集合欄位相等或付款業務規則。多個只讀查詢不是一致性交易快照，並行寫入可能造成暫時差異；應在安靜時段重跑後判讀。

本工具查核 migration ID／狀態，不重新執行 migration，也不把本機換行差異當成 migration checksum 證據。完整程式碼 checksum 鑑識屬另項工作。

Business collections are currently empty. Reference existence checks and passing database tests do not establish end-to-end acceptance, which remains unassigned. No new database, credentials, Secrets, scheduler or deployment is created.

## 本次結果 / This run

2026-10-02：資料庫套件 **66 項通過**；前後 27 集合筆數一致，27 個 validator 與 86 個索引符合來源，12 組參照未發現孤兒。業務集合仍為空，保留的資料只有四筆 migration 與一筆政策。檢查器 17 項離線測試通過。

Live database regression passed 66 tests. Before/after counts match and the read-only checks pass; no end-to-end acceptance claim is made.
