# SAM 每日完整備份 / Daily full backup

更新：2026-10-22 19:22（Asia/Taipei）。接續[機密修復紀錄](SAM_DRIVE_ENCRYPTION_2026-10-22.md)，以本頁最新狀態與[去敏收據](../inventory/SAM_DRIVE_DAILY_2026-10-22.json)判讀，歷史文件保留。

## 本輪已核准及完成

- SAM 明確核准只排除 `MuscleCore分析資料/website/.pytest_cache`。其他快取、Git 歷史、未追蹤檔案及空目錄仍納入完整清冊；未刪除來源或改動該快取的 Windows ACL。政策保存在 [config/drive-backup-policy.json](../../config/drive-backup-policy.json)。
- `LLM_PJ Daily Backup` 的 OAuth 已切換 Production，Google Cloud 畫面回讀「實際運作中」。Google 應用程式驗證仍未完成，發布狀態不等同驗證或永久免重新登入；Testing 時簽發的 token 不宣稱已自動延長。[Google token 期限說明](https://developers.google.com/identity/protocols/oauth2/#expiration)。既有授權用於本輪，憑證繼續 DPAPI 私有保存。
- 重新開啟固定專案，核對原資料夾與 Google 文件兩個來源 ID；固定連結、專案及來源物件均保留。
- 新完整來源清冊 `complete=true`：47,658 檔、5,301,373,391 bytes；3,492 檔完成 AES-256-GCM 與本機認證復原，唯一排除項符合 SAM 決定。這是初次全量快照的數字；最後 GitHub 發布後若來源改變，必須產生新清冊並重新對帳。
- 161 項本機備份測試通過，涵蓋原授權恢復、直接／繼承權限、遺失 API 回覆、部分恢復失敗後撤回、雲端／來源／機密復原不足時禁止恢復，以及密文重用需同來源與同金鑰。

## 執行狀態及驗收界線

全量雲端程序已啟動，原共用維持停止。**本段記錄時尚未完成全量傳輸、最終遠端認證復原或 ACL 恢復，不宣稱每日備份完成。** 980 個舊雲端檔案／984 版本的機密修復是前一階段，不能替代本次完整來源備份。

每一輪會比對所有相對路徑、大小及可用雲端雜湊，保存空目錄，保留原 ID 及目的地額外檔案。所有加密來源檔都要從雲端獨立下載、認證解密並比對明文雜湊。全部成功後才依原私有計畫恢復 4 筆直接授權，再列舉全部子項核對繼承權限；任何恢復失敗會撤回本輪恢復的授權並驗證停止共用。原始 ACL、permission ID、身分及恢復日誌不進 GitHub，金鑰不進 GitHub 或 Drive。

GitHub 推送／合併會改變來源文件與 `.git`。工具把先前雲端快照與新的來源清冊分開驗證，以原 ID 補齊差異；不把舊快照驗證當成目前來源一致。最終完成收據只在來源再次通過及原 ACL 完整回讀後產生。

## 首輪傳輸中斷與續傳

首輪建立目錄時，有一個已預配 ID 的新目錄未能回讀，程序在內容上傳前停止。獨立重查該 ID 為 HTTP 404；原請求的服務端失敗原因未保存，不推定成因。已保留進度日誌，補上「只有確認不存在才以同 ID 有界重試」及回歸測試。續傳使用相同完整快照與預配 ID，並行工作數上限 48；不以新 ID 重建、不刪除目的地內容。GitHub 發布後的來源差異仍須於最後補齊，`--resume-snapshot` 不會略過完成前的來源穩定性檢查。

## 完整權限讀回 / Complete ACL readback

實際雲端清冊的子物件省略 `permissionDetails`，不能以一般檔案清冊推定直接／繼承來源。`drive_backup_acl_batch.py` 會對每個物件讀取完整 `permissions.list`，每批最多 100 個純 GET，驗證 response ID 無遺漏／重複／越界；失敗或有下一頁的項目改用完整分頁端點。外層雖為 multipart POST，內層只有讀取；撤銷及恢復授權仍依序單筆進行。[Google 官方批次規範](https://developers.google.com/workspace/drive/api/guides/performance#batch-requests)。

本輪已在原專案及原資料夾做唯讀實測，兩個批次結果均與獨立權限端點相同，仍 owner-only。正式恢復後會批次讀回每個子項，再和新雲端清冊及原授權／繼承預期核對。這個兩物件實測僅證明 API 能力，不替代最後全樹驗收。新增含中文、多部件亂序、缺項、重複、越界、分頁、讀取錯誤及重試上限測試；備份相關本機測試總計 161 項通過。

English: File-list responses omit child inheritance details. Full ACL readback therefore uses read-only permission batches for every object, validates response identities and handles pagination without omissions. The two fixed roots passed a live read-only comparison; the final whole-tree acceptance remains a separate gate.

## 操作入口 / Runbook

所有命令由持有專用 OAuth 的本機帳號執行；路徑與證據置於 `C:\Users\USER\.llm-pj-backup`。執行時設定 `PYTHONDONTWRITEBYTECODE=1`，避免備份程式自行改動來源快取；各階段共用 `backup-execution.lock`。

1. 首輪隔離已完成，沿用 `active-isolation.json` 指向的原 ACL，不能重跑撤權或用 owner-only 清冊覆蓋原權限。
2. `drive_backup_run.py`：完整來源清冊、完整舊雲端稽核、固定來源 UI 重核後，以原 ID 傳輸；保存計畫可續做。
3. `drive_backup_reconcile.py`：若 GitHub 發布等造成來源改變，先證明前輪雲端內容完全符合舊計畫，再以新完整清冊補齊差異。來源仍須於傳輸前後通過。
4. `drive_backup_finish.py`：逐一獨立下載加密檔並認證復原；加 `--restore` 才在重新核對全部條件後恢復原 ACL。失敗保留私有日誌，不能反覆重建授權。
5. 第一輪完成後，後續使用 `drive_backup_daily.py --run-directory <新的私有目錄> --key <既有私有金鑰> --project-sources-reconfirmed`。先確認固定專案仍為兩個原來源；遠端內容或授權相較上輪有變化時，停在前置檢查要求重新稽核，不盲目覆寫。每輪先保存新原始 ACL，再暫停共用、傳輸、對帳、復原驗證及恢復授權。已有未完成隔離時，沿用原日誌續做，不開新輪覆蓋。

每日 23:30 Asia/Taipei 的 Codex heartbeat 保留，已移除快取與 Production 尚待答覆的舊阻礙；只在完成、失敗、新阻礙或必要本人動作時通知。它仍需本機與 Codex 執行環境可用，不是獨立 Windows 常駐服務。

English: SAM approved one exact cache exclusion and OAuth Production publication. The complete first source snapshot has 47,658 files (5,301,373,391 bytes), including 3,492 encrypted files. Transfer is in progress; this record does not claim completion or sharing restoration. New recovery gates require complete cloud/source reconciliation and independent authenticated recovery of every encrypted payload before restoring original direct and inherited permissions. Failed restoration rolls back only those original grants. Daily subsequent runs retain fresh original ACLs and fail preflight if remote content or access changes require a new audit.
