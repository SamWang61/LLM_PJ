# REN 命名修正紀錄 / REN naming correction log

日期：2026-10-18（Asia/Taipei）。依使用者要求，仁千英文名統一為 REN。

## 檔名修正 / Filename changes

檢查基線：`d269dd6`。本輪將舊稱檔名改為 REN，其他字元、日期及副檔名不變；沒有刪除文件內容。改名前的路徑可由該提交的 Git 歷史追溯。

| 項目 | 現行檔名 |
| --- | --- |
| 交付紀錄 | `docs/REN_DELIVERY_2026-10-14.md` |
| 多裝置部署 | `docs/REN_MULTIDEVICE_DEPLOY_2026-10-14.md` |
| R02 契約 | `docs/REN_R02_CONTRACT_2026-10-14.md` |
| 當日工作清單 | `專題進度/REN_今日工作清單_2026-10-14.md` |

## 內容修正 / Content changes

同步替換文件中的人物稱呼及文件路徑；不修改分工、驗收數字或功能實作。改動清單（改名前路徑）：

- `deploy/README.md`
- `deploy/RENDER_DEPLOYMENT.md`
- `docs/CURRENT_CONTEXT.md`
- `docs/REN_DELIVERY_2026-10-14.md`
- `docs/REN_MULTIDEVICE_DEPLOY_2026-10-14.md`
- `docs/REN_R02_CONTRACT_2026-10-14.md`
- `docs/JEFF_REPLY_SAM_PLAN_2026-10-11.md`
- `docs/PROJECT_BLOCKERS_2026-10-07.md`
- `docs/PROJECT_PROGRESS_2026-10-07.md`
- `docs/REN_R02_INTERFACE_2026-10-17.md`
- `docs/SAM_ACCEPTANCE_2026-10-11.md`
- `docs/SAM_DATA_CONTRACT_2026-10-07.md`
- `docs/SAM_DELIVERY_2026-10-07.md`
- `docs/SAM_INTEGRATION_BASELINE_2026-10-16.md`
- `docs/SAM_JEFF_1017_HANDOFF.md`
- `docs/SAM_OUTSTANDING_2026-10-11.md`
- `docs/SAM_PR21_ACCEPTANCE_2026-10-16.md`
- `docs/SAM_PUBLICATION_2026-10-07.md`
- `docs/SAM_TODAY_CHECKLIST_2026-10-07.md`
- `docs/SAM_TODAY_COMPLETED_2026-10-11.md`
- `專題進度/REN_今日工作清單_2026-10-14.md`

## 保留的原始識別 / Preserved identifiers

- 本機 MongoDB 測試環境變數與測試檔已同步更名；現行命令保持可執行。
- 歷史分支及固定 commit URL 不更名；修改前機器證據可從 Git 歷史取得。
- 改名前對照可由 Git 歷史追溯；現行文件及檔名一律使用 REN。

## 驗證 / Validation

提交前核對四筆新檔名與 Git rename 紀錄一致；受追蹤文件檔名沒有剩餘舊稱。文件檢查器與差異空白檢查須通過後推送。此輪沒有部署或資料庫寫入。

English: Use REN in current document names, person references, test identifiers, and document paths. Git history preserves the former paths and raw evidence.

## 10/18 追加：一致性修正

依最新指示，測試檔、示範腳本、證據目錄及本機測試環境變數也統一使用 REN。文件中的執行命令與連結同步更新。既有 JUnit XML 僅將測試識別與本機路徑標籤正規化，測試數字、結果與時間未改；原始產出可從修改前的 Git 版本讀取。歷史 Git 分支及工作樹名稱屬當時實際路徑，不作假改名。

在本輪修正工作樹使用無帳密的 `127.0.0.1:27029` MongoDB 8.0.20 單節點 replica set，設定 `REN_TEST_MONGO_URI` 執行網站完整測試：**186 passed、0 skipped（36.36 秒）**。測試產生的資料庫已清除，讀回僅 `admin`、`config`、`local`，本機測試服務已停止。這是本機回歸，不代替遠端部署或組員簽收。
