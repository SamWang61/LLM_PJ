# 每日備份 / Daily backup

## 2026-10-22 13:40 機密修復與全備份狀態 / Latest status

**已完成 980 個雲端檔案／984 個版本的加密修復及遠端認證復原，原明文版本已確認移除；原物件 ID 與固定連結保留。共用仍停止。** 最終完整回讀 11,780 個物件皆 owner-only。詳細[處理紀錄](log/SAM_DRIVE_ENCRYPTION_2026-10-22.md)及[去敏證據](inventory/SAM_DRIVE_ENCRYPTION_2026-10-22.json)優先於下方早先隔離狀態。

來源已私有準備 47,557 個可讀檔案、3,407 個加密檔，但 `MuscleCore分析資料/website/.pytest_cache` 拒絕讀取，尚待 SAM 同意明確排除或修復讀權限。未自動排除，manifest 仍不完整，來源全量上傳為 0；不能將雲端舊內容修復或本機準備冒稱完整備份。最終清冊須在來源變動後重新核對。133 項本機測試通過；全量雲端核對及原 ACL 恢復尚未執行。

OAuth 用途／隱私／使用說明頁已上線，品牌欄位已保存；Testing 轉 Production 的操作當下確認仍待答覆，目前仍有 7 日限制。每日 23:30 排程保持；未通過全部備份條件前不恢復共用、不覆蓋原恢復計畫。

English: Existing confidential content has been encrypted and independently recovered from Drive. Full source backup is still blocked by one unreadable cache directory; sharing remains suspended. OAuth branding is ready, but production publication is pending.

## 2026-10-22 最新決定與權限修復進度 / Current decision

SAM已明確同意專用Desktop OAuth與Drive管理授權，並選定**一般檔案同步；機密以密文存於原固定目錄**，金鑰與OAuth憑證放在專案外，不上傳。此決定取代下方9月「方案尚待選擇」；不是本次加密或備份驗收完成。

SAM已完成本人授權，DPAPI token、Drive scope、擁有人身分及refresh均已核實。SAM後續明確同意「先暫停共用至修復完成」；12:16（Asia/Taipei）已撤銷固定專案及兩個來源的4筆直接非擁有者授權，完整回讀11,780物件皆為owner-only、非擁有者授權0。原ACL、身分／permission ID及還原計畫在第一筆撤權前完整保存於專案外；固定物件ID與連結不變。78項本機測試通過。詳細[實際隔離與恢復限制](log/SAM_DRIVE_ISOLATION_2026-10-22.md)優先於[07:23～09:33授權／探針歷史](log/SAM_DRIVE_BACKUP_2026-10-22.md)及下方舊段落。

**目前維持停止共用，不能提前恢復。** Testing模式7日期限、既有機密內容及其歷史版本處理、全量機密封裝／復原、雲端清冊／大小／雜湊／來源穩定性對帳，以及真實ACL恢復仍待完成；0專案檔案複製，不宣稱每日備份完成。不再要求SAM重做已完成的安全提示、重選機密方案或重答延長停止共用。

排程先讀專案外的 `active-isolation.json`，沿用其中的原始還原資料；不得用目前owner-only清冊覆蓋原ACL，也不得重跑撤權。`scripts/drive_backup_isolation.py --verify-active` 僅重新讀回雲端並保存另一份檢查結果，不變更共用、原始還原資料或專案內容。所有備份階段使用同一執行鎖，失敗保持停止共用。

English: SAM approved extended suspension. Four original non-owner grants were removed; a complete readback verified all 11,780 objects are owner-only. Original ACLs and restore identities are preserved privately. Sharing stays suspended until confidential-content remediation, encrypted recovery and full cloud verification succeed. No project data or keys have been uploaded; this is not a completed daily backup.

<!-- SAM REMOTE ROLE RESULT 20261020 BEGIN -->
**2026/10/20 REN復原子項接受方式**：依[SAM本輪決定](SAM_ACCEPTANCE_DECISIONS_2026-10-20.md)，接受完整同機模擬通過；本輪[USB來源／資料庫還原對帳](inventory/SAM_PROXY_N14_RESTORE_2026-10-20.json)已通過，實際環境與機器不同與否照實保留。此決定未補齊每日固定Drive可逆ACL／排程，亦未清除自動核准審查拒絕刪除的私有明文；詳[執行與待辦](SAM_ROLE_PROXY_REMOTE_EXECUTION_2026-10-20.md)。
<!-- SAM REMOTE ROLE RESULT 20261020 END -->

## 2026-10-19 每日固定專案前置核對

本輪重新以Drive metadata核對固定project仍為原ID、owner 1／writer 2；目標folder仍為原ID、owner 1／anyone reader 1，canShare均為true。但補選grantee欄位後可讀回收件身分，但連接器回覆仍省略permission ID，現行工具只有新增分享，沒有撤銷權限操作；無法可靠保存並恢復專案、資料夾及個別子檔案的原ACL，故本輪未變更共用或開始複製，固定連結不變。完整結果見[線上持續檢查與備份缺口](SAM_ONLINE_FOLLOWUP_2026-10-19.md)。

每日23:30自動化仍ACTIVE、時間不變；已更新提示，先讀最新私有加密快照及復原證據，不再將其與固定共用專案每日流程混為一談。私有加密子項已有驗證，不代表每日固定目的地機密方案及ACL前置已全部完成；不將歷史備份當成本次成功。只在新的阻礙、必要動作、失敗或完成時通知，同一阻礙維持安靜。

下方「機密保存方案仍待選擇」為9月固定共用目的地的原始限制；10/18私有加密子項與10/19雙USB同機預演依上方及專項紀錄判讀。REN異機復原、人員簽收及每日固定專案ACL流程仍待辦。

## 2026-10-18 16:10 最新快照與正式Atlas子項驗收

[完整證據](SAM_N14_CURRENT_ATLAS_2026-10-18.md)：13,976檔原目錄快照以歷史基底＋差異包完整重建，全部hash一致；正式vibecart_ai28集合／89索引／validator／3TTL完成雲端認證解密後的隔離還原。差異包不是獨立全備份，原25片基底及外部key必須保留。異機key及下方每日固定專案／ACL流程仍待辦。舊05:28段落為歷史。

## 2026-10-18 N14 本次私有快照復原

[加密與隔離復原證據](SAM_N14_ENCRYPTED_RESTORE_2026-10-18.md)：歷史05:28快照13,048檔通過認證解密、逐檔hash、internal Docker來源啟動與本機fixture BSON復原。私有目錄owner-only，金鑰另存；本次不是每日固定專案備份完成。25/25片密文已獨立遠端SHA驗證、重組與認證解密通過；ZIP與05:28原備份相同。最新快照／異機key／正式Atlas資料與中繼資料完整復原仍待辦。下方固定連結、ACL切換與每日23:30需求繼續保留；9月的共用狀態須執行時重新讀回。

## 固定需求 / Fixed requirements

- 來源：`C:\LLM\LLM_PJ`。Source: the complete project directory, independent of Git tracking rules.
- 每日台北時間 23:30（Asia/Taipei，UTC+08:00）。Schedule: 23:30 Taipei time every day.
- 同路徑同檔名覆蓋，不刪除目的地額外檔案。Overwrite matching relative paths; do not mirror-delete destination-only files.
- 複製前關閉共用，全部上傳與驗證成功後才恢復原共用。Suspend sharing before transfer; restore exactly the original permissions only after cloud verification.
- 固定連結：[LLM_PJ 專案](https://drive.google.com/drive/project/1rQrO8v6bl3_y_B0BwpZXhlHFHS8swQc5?usp=drive_link)。不得刪除、重建或改換此專案。Preserve this exact project and link.

## 已確認對應 / Verified mapping on 2026-09-27

固定連結是 Google Drive 專案，引用的實際資料夾為 [LLM_PJ](https://drive.google.com/drive/folders/1lXZv3hn3CgYmotpxgcna8i27wEodL8Gh)。本機 Drive 同步路徑為 `C:\Users\USER\我的雲端硬碟\LLM_PJ`。專案與資料夾是不同物件，必須分別核對共用設定。

The fixed link is a Drive project referencing a separate folder. Sharing on both objects must be checked; updating a folder does not require replacing the project link.

## 前置條件與目前限制 / Prerequisites and limitations

已建立 Codex 聊天自動化 `llm-pj-23-30`，每日 23:30 喚醒本聊天執行前置檢查及符合條件的備份。此為 Codex 本機自動化，不是 Windows 常駐服務，也不是已驗證成功的備份；前置條件未解決時會停止於檢查階段。

The Codex heartbeat `llm-pj-23-30` is active at 23:30 daily. It runs preflight checks and proceeds only when prerequisites are met. This is not an independent Windows service or evidence of a successful backup.

目標資料夾目前任何持有連結者均可讀取，而來源有 `.env` 與資料庫憑證。機密需另存私有備份或先加密；不得在恢復共用後暴露明文機密。此處理方式尚待使用者決定。

The destination is link-readable and the source includes credentials. Secret handling requires a private destination or encryption before sharing is restored; the user's choice is pending.

目前 Drive 連接器沒有撤銷權限功能；讀寫檔案不代表能完成共用切換。桌面複製成功也不代表雲端同步完成。未核實這兩項之前，禁止以普通排程複製冒充完成要求。

The current connector cannot revoke permissions. Local copy completion is not cloud-sync completion. Do not report a compliant backup until permission transitions and cloud completion are verified.

## 執行與失敗處理 / Execution and recovery

1. 確認來源可讀、目的地 ID 與固定專案關係未變；避免同時執行兩次備份。Validate source, destination identity and exclusive execution.
2. 私下保存專案、資料夾及個別檔案的原權限；檢查繼承與直接共用，不能只切換資料夾的連結權限。Capture original ACLs and inspect direct child shares and inherited access.
3. 撤銷非擁有者存取並回讀確認；無法隔離時不開始複製。Verify access is suspended before transferring.
4. 逐路徑覆蓋，保留 Drive 物件 ID。機密依核准方案處理，不能套用 Git 排除清單而宣稱全量備份。Overwrite by path while retaining Drive IDs; handle secrets under the approved policy.
5. 等待雲端上傳結束，比較清冊、大小與可用的 checksum；來源複製中變動時重試或回報不一致。Verify cloud contents and detect changing source files.
6. 全部驗證成功才恢复原權限，回讀權限及固定連結。Restore original ACLs only after complete verification.
7. 任何失敗留下可恢復狀態與錯誤摘要；若已停止共用則保持停止，通知維護者。Persist recovery state and report failure without premature resharing.

電腦須開機、連網且執行環境可用；本機備份不是雲端常駐工作。The computer and execution environment must be available at run time.
