# 每日備份 / Daily backup

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
