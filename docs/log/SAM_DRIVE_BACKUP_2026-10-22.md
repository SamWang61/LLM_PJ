# SAM 每日 Drive 備份權限處理紀錄 / Drive backup access log

> **後續現況（12:16）**：SAM已明確同意延長停止共用，4筆直接非擁有者授權已撤銷，11,780物件完整回讀owner-only。共用持續暫停，0專案複製；原ACL與還原計畫保存在專案外。請先讀[實際隔離紀錄](SAM_DRIVE_ISOLATION_2026-10-22.md)。下列07:23～09:33授權、探針與「尚待答覆／0既有共用變更」均為隔離前歷史，不是目前狀態。

更新：2026/10/22（Asia/Taipei）。本輪基線為 GitHub main `72ae3c8e5f6f0b125fbee257b8a9a105667483a1`。實際操作者為 Codex，SAM 已在對話中確認授權；下列分開記錄雲端設定、本機工具與真正備份驗收。

## 本輪決定 / Decisions

1. SAM 同意 Google API 使用者資料政策、建立 **LLM_PJ Daily Backup** 桌面 OAuth 用戶端，以及 Drive 完整管理範圍。此範圍在 Google 層級可存取整個 Drive；程式固定目標是下列專案／資料夾，額外的空白 ACL 探針只驗證 API 能力，不裝入專案內容。程式目標檢查不等於 OAuth 憑證本身只有單一資料夾權限。
2. **一般檔案同步；機密以密文存於原固定目錄**。此決定取代舊文件「尚待選私有或加密」的狀態。金鑰、OAuth 憑證與完整私人 ACL 清冊留在專案外；不能把「已選方案」寫成「加密封裝與雲端復原已驗收」。
3. 原連結、Drive 物件 ID、同名覆蓋與目的地額外檔案保留規則不變。

## 已核實結果 / Verified results

| 項目 | 本輪讀回 |
| --- | --- |
| 固定專案 | `1rQrO8v6bl3_y_B0BwpZXhlHFHS8swQc5`，名稱 LLM_PJ，project MIME；owner 1／writer 2，canShare=true。 |
| 備份資料夾 | `1lXZv3hn3CgYmotpxgcna8i27wEodL8Gh`，名稱 LLM_PJ，folder MIME；owner 1／anyone reader 1，搜尋探索關閉。 |
| 專案來源關係 | Chrome 專案來源顯示上述資料夾，另有一份 9/30 Gemini 匯出文件；專案並非資料夾的 parent，不能用 parents 欄位臆測關係。 |
| 現有連接器 | 補選 permission ID／permissionDetails 欄位後，正規化回覆仍省略這些欄位；分享工具只新增授權，沒有撤銷。已改準備官方 Drive API 流程。 |
| Google Cloud | 在既有 `vibecart-llmai` 建立 OAuth 品牌及 Desktop 用戶端，僅配置 Drive scope，擁有人為唯一測試使用者。Service Usage API HTTP 200 讀回 `drive.googleapis.com` 為 **ENABLED**。 |
| 憑證保存 | 新用戶端設定已以 Windows DPAPI 加密，另存 `C:\Users\USER\.llm-pj-backup`；目錄 ACL 限目前 Windows 使用者及 SYSTEM。建立流程的暫存明文已移除；原專案 docs 另有使用者下載的 client-secret JSON，仍保留原檔並以 Git ignore／政策拒收，未提交或上傳，正式備份前必須加密。SAM 已親自完成 Google 安全提示；07:23 實際取得 refresh token，`owner-oauth.dpapi` 已加密保存，08:38 再次以官方 API 讀回 cashsam@gmail.com 與 Drive scope。不是只依使用者回覆推定成功。 |
| 本機驗證 | 57 項測試通過，含 Windows DPAPI、完整分頁、My Drive 單一 parent 鏈、範圍與還原身分、空白探針、網路有限重試、失敗 checkpoint；不重試不確定的寫入或 invalid_grant，也不略過 TLS 驗證。Linux CI 的 DPAPI 一項依平台跳過，不能冒稱在 Linux 驗證 Windows 加密。 |
| 真正備份 | **0 個專案檔案複製、0 個既有共用變更；未完成本次全量雲端備份。** |

## 授權完成與後續技術驗證 / Remaining gates

SAM 已完成需要本人接手的未驗證應用程式提示。官方 API 身分、scope 及重新整理 token 已讀回成功；不再要求 SAM 重做同一次授權。單層空白資料夾及雙層空白 parent/child 探針都完成 grant → revoke → owner-only → restore → 回讀，permission ID 保留；最後回到 owner-only 並移入垃圾桶。雙層探針實證父層撤銷及恢復會反映在子項權限。探針不含專案資料，既有專案與資料夾未改權限。

OAuth 目前為 External / Testing；[Google 說明](https://developers.google.com/identity/protocols/oauth2#expiration)此情況的 Drive refresh token 有 **7 日**期限。09:07 重新讀回發布按鈕 disabled，品牌的首頁／隱私政策／授權網域尚空白；尚未完成 Production 發布／長期授權驗證。因此本輪不宣稱已永久免登入或每日備份已啟用成功。

本輪後續順序與已完成項目：

1. **已完成**單層與雙層空白探針，包含繼承撤銷／還原；只是 API 能力證據，不是固定專案備份成功。
2. 官方 API 已找到 **11,780 個物件**，包括固定專案、資料夾完整樹及 Chrome 獨立確認的另一份 Google Doc 來源。**09:33 全量 ACL 讀取完成**：4 筆直接授權、11,777 筆繼承授權，還原計畫 0 阻礙。完整身分、permission ID 與原權限留在專案外，公開只保留統計及雜湊。My Drive 不提供 `inheritedFrom` 是官方欄位規則；工具改為依完整 snapshot 的單一 parent 鏈逐層核對相同 permission ID、身分、role、探索與期限設定，直到確認直接授權來源。外部／多重 parent、混合權限、資料缺漏、循環、limited access 或內容不一致仍停止。此來源是依官方 parent 與 ACL 推導，並非宣稱 API 回傳 inheritedFrom。
3. **待完成**長期 OAuth 發布設定、備份來源全量清冊，以及機密加密與復原對帳；固定專案來源關係與目的地 ACL 已完成本輪核對。一般檔案按相對路徑；密文須保留來源對應、原始 hash 與密文 hash，金鑰不入來源或目的地。對有憑證可能的未追蹤／忽略內容採保守加密，不以 Git 清單代替全量來源。
4. 在原 ACL 可完整恢復、全量加密與驗證流程就緒後，才暫停真實共用並複製；雲端清冊／大小／可用 hash／來源穩定性全部通過後才恢復。任何失敗保留恢復狀態且不提前恢復共用。

盤點曾遇到記憶體不足與網路逾時；已保留前次完整 checkpoint，改以串流原子寫入與有限重試續查，最終 11,780 個物件全部取得 ACL，沒有把部分結果當完成。這是分段讀回的清冊，不是鎖定中的原子快照；真正撤權／複製前必須重新核對根物件、來源關係與清冊變動。空白探針證明 API 可撤銷／恢復，完整計畫則證明本輪物件都有可還原資料，仍不代表固定專案已實際隔離。

既有內容的機密處置明細另存本機私有紀錄；延長停止共用時間的決定已向 SAM 提出，目前尚未收到答覆，既有共用維持原狀。不得把沉默視為同意，也未執行帳密有效性測試或輪替。

## 工具與執行 / Tools

- [OAuth 工具](../../scripts/drive_backup_auth.py)：Google 官方 OAuth library、PKCE 與 loopback callback；token 以目前 Windows 帳號 DPAPI 保存。授權網址亦僅寫在私有目錄。
- [ACL 工具](../../scripts/drive_backup_acl.py)：預設只讀取並產生私有 snapshot／restore plan，`--project-source-file` 補入已從專案來源 UI 確認的 Google Doc；`--probe-empty-object` 才操作新建空白測試物件。**此版本不會撤銷固定專案 ACL，也不包含正式傳檔流程。**
- [測試](../../scripts/test_drive_backup_acl.py)／[依賴](../../scripts/requirements-drive-backup.txt)。Git policy 拒收 DPAPI 與 client-secret 檔，檔案清冊亦將兩者列為機密而不讀取內容；只提交去敏結果。

在 Windows 專案根目錄執行，私人輸出必須是尚未存在的新目錄：

```powershell
& "$env:USERPROFILE\.llm-pj-backup\venv\Scripts\python.exe" scripts/drive_backup_auth.py --client-json "$env:USERPROFILE\.llm-pj-backup\client.dpapi"
& "$env:USERPROFILE\.llm-pj-backup\venv\Scripts\python.exe" scripts/drive_backup_acl.py --private-output "$env:USERPROFILE\.llm-pj-backup\acl-NEW-RUN" --project-source-file 1F0K89qC8R6QBietjvY8-NABrTWoWenVyXeayodLFfl4
```

每日 `llm-pj-23-30` 提示已同步本輪決定、官方 API 工具入口及授權限制，保持 ACTIVE、Asia/Taipei 23:30，既有完成／失敗通知及同阻礙安靜規則不變。

English: Owner OAuth consent, token refresh and identity/scope readback succeeded. Empty single-folder and inherited parent/child ACL probes verified revoke, isolation, restoration and cleanup. The fixed project remains unchanged. The full ACL inventory contains 11,780 objects, four direct grants and 11,777 inherited grants, with no restore-plan blockers. Durable authorization, encryption, actual target isolation, transfer and cloud verification remain separate gates; no project file has been copied.

官方依據：[Drive permissions](https://developers.google.com/workspace/drive/api/reference/rest/v3/permissions)、[直接與繼承共用](https://developers.google.com/workspace/drive/api/guides/manage-sharing)、[Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)、[Desktop OAuth／PKCE](https://developers.google.com/identity/protocols/oauth2/native-app)。
