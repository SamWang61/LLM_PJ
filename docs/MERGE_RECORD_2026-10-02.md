# 2026-10-02 合併與 Atlas 連線管理紀錄 / Merge and connection record

本紀錄使用 Asia/Taipei 時間，記錄已完成的 GitHub 合併、驗證證據與連線保存決策。中文為準，英文輔助。This record documents completed merges and credential handling; Chinese is authoritative.

## 合併結果 / Merge results

| 時間（台北） | 變更與方向 | 結果與提交 |
|---|---|---|
| 2026-10-02 04:25:11 | [PR #3](https://github.com/SamWang61/LLM_PJ/pull/3)：`feature/ai-dashboard` → `feature/flask-sku-ai-integration` | 已合併；`1b6ea47618f8dda12d91f73098b6856c08c4df84` |
| 2026-10-02 04:25:53 | [PR #2](https://github.com/SamWang61/LLM_PJ/pull/2)：`feature/flask-sku-ai-integration` → `main` | 已合併；`4d972d5711817873020562bb2af5529767454189` |

PR #3 起初保留待審查，並非因測試失敗或分支衝突。使用者指示按順序合併後，先完成 PR #3，再更新 PR #2 的說明、解除草稿，確認更新後檢查通過才合入 main。保留 merge commit，讓相依分支歷史可追溯；沒有強制推送或刪除原分支。

Both pull requests are merged in dependency order. PR #2 was marked ready after its description and validation evidence were updated. Main now includes the integration and dashboard work.

## 已交付修改 / Delivered changes

- Flask 可選 v4 SKU 購物車、會員與交易式示範結帳介接；保留 legacy 模式。
- SAM 後台新增台北日期與示範訂單篩選、營收、每日統計、熱銷、目前低庫存及推薦行為監測。
- AI 摘要的統計範圍與快取跟隨篩選；保留權限、CSRF、錯誤退回及模型預設關閉設定。
- 加入私有設定檔選擇、真實 Atlas 驗證工具、中文優先雙語文件與交付清冊；既有路徑與 migration 保留。

詳細路徑、操作方式與限制見 [SAM 交接文件](AI_DASHBOARD.md)；整合架構見 [Flask／SKU／AI 文件](FLASK_SKU_AI_INTEGRATION.md)。The existing architecture is preserved; see the handoff for file ownership and operational details.

## 驗證證據 / Validation evidence

| 項目 | 結果 |
|---|---|
| 離線測試 | 38 項通過 |
| 合併前倉庫檢查 | 127 檔、122 個 UTF-8 文字檔、0 錯誤 |
| 真實 Atlas | 27 集合、86 索引（59 自訂）；[讀回報告](V4_TEST_VERIFICATION.json) |
| 實際交易驗證 | 註冊登入、購物車增刪改、結帳重送、管理員撤權、rollback、最後庫存併發通過；本次測試資料已清理，前後集合筆數一致 |
| PR #3 檢查 | [成功](https://github.com/SamWang61/LLM_PJ/actions/runs/36917075753) |
| PR #2 更新後檢查 | [成功](https://github.com/SamWang61/LLM_PJ/actions/runs/36921431535) |
| main 合併後檢查 | [成功](https://github.com/SamWang61/LLM_PJ/actions/runs/36921507265) |

以上是該次交付的時間點證據，不代表持續監測。BGE／Claude 真實模型、完整 6+4 推薦、排程計分及正式金流仍未完成驗收；合併不等於部署或啟用付費模型。These are dated verification results, not continuous monitoring or production certification.

## Atlas URI 與資料庫決策 / Atlas URI and database decision

「已配置私有 v4 Atlas URI」表示本機 `MuscleCore分析資料/website/.env.v4-test` 已保存可用連線，受 Git 忽略與本機檔案權限保護；不是建立新的 Atlas cluster、資料庫或 GitHub Secret。

本次使用既有 `vibecart_ai` v4 資料庫。當時可用帳號的權限限於該資料庫，不能據此建立另一個隔離測試庫或新帳號。因此使用已授權的既有 v4 環境完成驗證，沒有宣稱另建隔離環境；也沒有把 legacy seed 寫進 v4。

The private local profile connects to the existing v4 database. Available credentials were scoped to that database; no separate test database, cluster or user was created.

| 資料或用途 | 保存方式 | 本次狀態 |
|---|---|---|
| 無密碼設定範本、Schema、程式、驗證摘要 | GitHub 版本控制 | 已提交 |
| 含帳密的完整 URI | 本機受忽略的 `.env.v4-test` | 已配置，未寫入 Git、PR 或此文件 |
| 未來 GitHub 自動測試需要 URI | GitHub Actions／Environment Secret，例如 `MONGO_URI` | 僅說明方案，尚未建立或上傳 |
| 同學本機開發 | 各自授權的 Atlas 帳號與私有設定檔 | 不由 Git clone 分發帳密 |

完整 URI 不提交到 Git，因為帳密可能被讀取、複製並永久留在歷史。GitHub Secrets 是供授權 workflow 使用的獨立保存機制，不會隨 clone 下載，也不是讓組員查看密碼的共用文件。現行 CI 仍只做離線檢查，不會因本次合併而連接 Atlas。[GitHub Secrets 官方說明](https://docs.github.com/en/actions/concepts/security/secrets)。

Credentials remain outside version control. A future Actions Secret may supply an authorized workflow, but none was uploaded by this work. Existing CI remains offline.

本次合併亦未變更 Google Drive 共用、備份或機密保存決策；備份狀態仍以 [BACKUP.md](BACKUP.md) 為準。Drive backup remains a separate workflow.
