# SAM 固定 Drive 共用暫停紀錄 / Fixed Drive sharing suspension

更新：2026/10/22（Asia/Taipei）。來源基線 `4ce6cf5af3b026fdb8b3127d94f1954ea96888ed`。實際操作者 Codex；SAM在本聊天明確選擇「先暫停共用至修復完成」，允許超過一般備份的短暫停止時間。此紀錄接續[OAuth與空白探針](SAM_DRIVE_BACKUP_2026-10-22.md)，不重新要求已取得的同意。

## 實際結果 / Result

- 撤權前重新確認固定專案的來源關係、擁有人及完整ACL：11,780物件、4筆直接授權、11,777筆繼承授權，還原計畫0阻礙。約12:03～12:13完成本次讀取，不使用09:33清冊直接寫入。
- 在第一筆撤權前，將完整原ACL、受權者身分／permission ID、還原內容及操作日誌保存於專案外的私有目錄。目錄僅目前Windows使用者及SYSTEM可存取；原始清冊、金鑰及OAuth憑證不上傳GitHub或Drive。
- 依序撤銷來源資料夾的連結讀取、另一份來源Google Doc的連結讀取，以及固定專案的兩筆使用者寫入權限。**4筆撤銷皆回讀確認不存在**，擁有人權限保留。
- 第一次全樹驗證未通過，程式保留已撤銷狀態及恢復資料，未自動恢復共用。三個根物件獨立回讀均為owner-only；之後僅重做讀取，於 **12:16:14** 完整確認 **11,780物件、非擁有者授權0**。未重送撤權請求；第一次錯誤原因未被證實，不推定是傳播延遲。
- Chrome資料夾共用對話框另顯示「限制」及唯一擁有人；API全樹讀回涵蓋子項，不能只以畫面代替子項權限驗證。
- 固定專案、資料夾與來源Google Doc的物件ID均保留；[原專案連結](https://drive.google.com/drive/project/1rQrO8v6bl3_y_B0BwpZXhlHFHS8swQc5?usp=drive_link)不變。**0專案檔案複製、0內容修改／刪除、0恢復共用**；本次完成的是存取隔離，不是每日全量備份。

[去敏驗證摘要與私人證據雜湊](../inventory/SAM_DRIVE_ISOLATION_2026-10-22.json)只公開統計、時間及完整性摘要，不列出機密檔案路徑、內容或私人授權身分。

## 排程與恢復規則 / Scheduler and recovery

1. `active-isolation.json` 指向專案外的原始還原目錄。後續檢查不得以現有owner-only狀態取代原ACL，亦不得因檢查失敗而自動恢復。
2. [隔離工具](../../scripts/drive_backup_isolation.py)使用Windows獨占鎖、固定範圍、完整還原計畫、撤權前日誌及寫入後讀回；不確定回覆不能盲目重送寫入。新隔離操作需要明確的核准參數，已有active marker即拒絕新一輪。
3. `--verify-active` 只讀既有恢復資料並重新檢查雲端；不修改ACL、不傳檔、不覆寫原ACL／還原計畫／執行日誌。任何新權限、物件遺漏／增加、根物件改名或身分不符都停止，不默認為成功。
4. 每日23:30排程繼續ACTIVE，但需依最新狀態先檢查。相同阻礙不重複通知；不得以歷史私有快照、空白探針或本次隔離取代每日雲端驗證。

```powershell
& "$env:USERPROFILE\.llm-pj-backup\venv\Scripts\python.exe" scripts/drive_backup_isolation.py --verify-active
```

## 尚待完成 / Remaining work

- 既有共用內容的機密修復，包括確認歷史版本是否仍有明文；不能僅覆寫最新版本後就宣稱已移除所有明文。
- 來源全量清冊、一般檔案同步與機密密文封裝、獨立解密復原。金鑰不上傳；目的地額外檔案及Drive ID保留。
- 雲端清冊、大小、可用雜湊、來源穩定性對帳全部成功後，才依原計畫恢復並回讀原ACL。本次未驗收真實固定專案的恢復。
- OAuth仍為External/Testing；7日refresh token限制與長期發布設定仍待。不重新要求已成功的本人授權，除非實際失效。

上述項目未完成前維持停止共用。Atlas `0.0.0.0/0` 另依[SAM已接受的網路例外](SAM_ATLAS_NETWORK_EXCEPTION_2026-10-22.md)處理；該決定不改變機密或Drive恢復條件，也未授權公開資料庫帳密。

## 驗證 / Validation

本機Windows：`pytest scripts/test_drive_backup_acl.py scripts/test_drive_backup_isolation.py -q -p no:cacheprovider`，**78 passed**。包含先保存再撤權、失敗保持隔離、不確定寫入只讀回、原清冊不可覆寫、漏項／殘留授權拒收，以及唯讀重查不產生雲端寫入；不是以單元測試代替實際API結果。

12:23:20以正式 `--verify-active` 入口再次完整讀回11,780物件、非擁有者授權0；本次重查不覆寫原ACL、還原計畫與執行日誌。另已唯讀查閱已知機密檔案的版本中繼資料，尚未執行密文替換或版本刪除，不能據此宣稱內容修復完成。

English: SAM explicitly approved extended sharing suspension. Four original direct grants were revoked after complete private recovery capture. A full readback at 12:16 verified 11,780 owner-only objects. The initial verification failed closed; a subsequent read-only retry succeeded without replaying deletions. All original object IDs and the fixed link remain unchanged. Sharing remains suspended pending secret and revision remediation, encrypted recovery, full cloud reconciliation and exact ACL restoration. No project content was transferred or deleted.

官方依據：[Drive直接／繼承權限](https://developers.google.com/workspace/drive/api/guides/manage-sharing)、[My Drive完整permissions欄位](https://developers.google.com/workspace/drive/api/reference/rest/v3/files)。
