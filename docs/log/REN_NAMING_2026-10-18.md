# REN 命名修正紀錄 / REN naming correction log

日期：2026-10-18（Asia/Taipei）。依使用者要求，仁千英文名統一為 REN。

## 檔名修正 / Filename changes

檢查基線：`d269dd6`。本輪僅將下列檔名的 HEN 替換成 REN，其他字元、日期及副檔名完全不變；沒有刪除文件內容。

| 原檔名 | 新檔名 |
| --- | --- |
| `docs/HEN_DELIVERY_2026-10-14.md` | `docs/REN_DELIVERY_2026-10-14.md` |
| `docs/HEN_MULTIDEVICE_DEPLOY_2026-10-14.md` | `docs/REN_MULTIDEVICE_DEPLOY_2026-10-14.md` |
| `docs/HEN_R02_CONTRACT_2026-10-14.md` | `docs/REN_R02_CONTRACT_2026-10-14.md` |
| `專題進度/HEN_今日工作清單_2026-10-14.md` | `專題進度/REN_今日工作清單_2026-10-14.md` |

## 內容修正 / Content changes

同步替換文件中的人物稱呼及文件路徑；不修改分工、驗收數字或功能實作。改動清單（改名前路徑）：

- `deploy/README.md`
- `deploy/RENDER_DEPLOYMENT.md`
- `docs/CURRENT_CONTEXT.md`
- `docs/HEN_DELIVERY_2026-10-14.md`
- `docs/HEN_MULTIDEVICE_DEPLOY_2026-10-14.md`
- `docs/HEN_R02_CONTRACT_2026-10-14.md`
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
- `專題進度/HEN_今日工作清單_2026-10-14.md`

## 保留的原始識別 / Preserved identifiers

- `HEN_TEST_MONGO_URI` 是程式目前讀取的環境變數，不是人物稱呼；保持命令可執行。
- 不修改既有程式、測試 classname、機器產生的 JSON/XML 證據、歷史分支及固定 commit URL。改寫證據會使紀錄不再忠於當時執行。
- 本 log 的改名前對照，以及 `docs/DOCUMENT_SYNC_2026-10-17.md` 的既有改名稽核對照，保留舊字樣供追溯。

## 驗證 / Validation

提交前核對四筆新檔名均等於原檔名僅替換 HEN 為 REN；受追蹤文件檔名沒有剩餘舊稱。文件檢查器與差異空白檢查須通過後推送。此輪沒有部署或資料庫寫入。

English: Rename only the HEN substring in document filenames to REN, and update person references and document paths. Preserve executable identifiers and historical machine evidence. Old names in this audit log are intentional provenance, not active document links.
