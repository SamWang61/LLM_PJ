# 文件同步紀錄 / Documentation synchronization

日期：2026-10-17（Asia/Taipei）。範圍：本機專案文件與 GitHub main 的 REN 命名及文件版本同步。

## 完成項目 / Completed

- [PR #22](https://github.com/SamWang61/LLM_PJ/pull/22) 已合併，合併提交 `71f75be225611d2f150b34a9010475d978df7ef4`。
- 四個原 HEN 檔名改為 REN，保留 Git 歷史；相關文件內的人名與路徑一併修正。
- 本機同步下列 18 份有差異或缺少的既有 GitHub 文件。原有版本先保存在本機私有 `.codex/doc-sync-20261017/before/`，未發布。
- 本機舊分支及其他未提交程式、資料、私密設定維持原狀；此輪沒有資料庫寫入或網站部署。PR #22 已含先前完成的網站頁尾變更，合併不等於部署。

## 改名對應 / Renames

| 原檔名 | 現行檔名 |
| --- | --- |
| docs/HEN_AUTH_ORDER.md | docs/REN_AUTH_ORDER.md |
| docs/inventory/SAM_HEN_TRANSACTION_2026-10-15.xml | docs/inventory/SAM_REN_TRANSACTION_2026-10-15.xml |
| 專題進度/HEN_AI操作與提示詞指南_2026-10-12.md | 專題進度/REN_AI操作與提示詞指南_2026-10-12.md |
| 討論的相關記錄/HEN_AI操作與提示詞指南_2026-10-12.md | 討論的相關記錄/REN_AI操作與提示詞指南_2026-10-12.md |

Git 分支名稱、歷史 commit 與既有環境變數等技術識別不因人名改稱而改寫。本表中的舊名稱僅供追溯，不是現行連結。

## 同步清單 / Synchronized documents

- `CHANGELOG.md`
- `VibeCart_AI/MongoDB/18_2026-10-05_Schema重建與超市商品匯入.md`
- `VibeCart_AI/MongoDB/supermarket/README.md`
- `VibeCart_AI/MongoDB/supermarket/recovery_20261005/before/16_完整Schema_v4驗證與欄位字典.md`
- `docs/AI_DASHBOARD.md`
- `docs/CURRENT_CONTEXT.md`
- `docs/DOCUMENT_INDEX.md`
- `docs/JEFF_ADMIN_UI_DESIGN.md`
- `docs/MERGE_RECORD_2026-10-02.md`
- `docs/README.md`
- `docs/REN_AUTH_ORDER.md`
- `docs/SAM_CI_TRANSACTION_ACCEPTANCE_2026-10-15.md`
- `docs/SAM_DATABASE_TESTING.md`
- `docs/SAM_DELIVERY_2026-10-12.md`
- `docs/TEAM_OWNERSHIP.md`
- `docs/TEST_DATA_IMPORT_2026-10-05.md`
- `docs/inventory/SAM_REN_TRANSACTION_2026-10-15.xml`
- `討論的相關記錄/SAM_DELIVERY_2026-10-12.md`

English: PR #22 has been merged. Documentation filenames and person references use REN. Eighteen differing or missing local documents were synchronized against main; prior local copies remain in a private recovery directory. This does not synchronize unrelated source code, import database data, or deploy the website.
