# SAM 每日 Drive 備份權限處理紀錄 / Drive backup access log

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
| 憑證保存 | 新用戶端設定已以 Windows DPAPI 加密，另存 `C:\Users\USER\.llm-pj-backup`；目錄 ACL 限目前 Windows 使用者及 SYSTEM。暫存明文用戶端檔已移除。refresh token 尚未取得，不將「用戶端建立」當作「擁有人授權完成」。 |
| 本機驗證 | 40 項測試通過，含 Windows DPAPI 往返與竄改拒絕、完整分頁、權限繼承／身分缺漏、範圍檢查、空白探針成功／失敗恢復狀態。Linux CI 的 DPAPI 一項依平台跳過，不能冒稱在 Linux 驗證 Windows 加密。 |
| 真正備份 | **0 個專案檔案複製、0 個既有共用變更；未完成本次全量雲端備份。** |

## 尚待本人及後續技術驗證 / Remaining gates

Google 顯示「這個應用程式未經 Google 驗證」，已保留授權頁供 SAM 本人接手。此為 Google 網頁安全提示；不能代按、擷取既有瀏覽器登入憑證或換用其他程式繞過。收到回覆後仍須確認 `owner-oauth.dpapi` 實際產生，並以 API 讀回擁有人身分及範圍。

OAuth 目前為 External / Testing；[Google 說明](https://developers.google.com/identity/protocols/oauth2#expiration)此情況的 Drive refresh token 有 **7 日**期限。發布介面目前要求補齊品牌設定；尚未完成 Production 發布／長期授權驗證。因此本輪不宣稱已永久免登入或每日備份已啟用成功。

授權完成後的順序：

1. 在新空白物件驗證 grant → revoke → owner-only 回讀 → exact restore → 回讀；最後移除探針共用並移入垃圾桶。這只是能力測試，不動固定專案 ACL，不放入專案內容。
2. 官方 API 完整分頁讀取固定專案、目標資料夾與全部子檔案的 ACL。遇到缺 ID／身分／繼承資訊、外部父層授權、混合繼承、轉移擁有權、到期權限、未擁有檔案或外部捷徑即停止，不能猜測還原。
3. 補齊固定專案來源關係與來源全量清冊；依本輪決定建置機密加密與復原對帳。一般檔案按相對路徑；密文須保留來源對應、原始 hash 與密文 hash，金鑰不入來源或目的地。對有憑證可能的未追蹤／忽略內容採保守加密，不以 Git 清單代替全量來源。
4. 在原 ACL 可完整恢復、全量加密與驗證流程就緒後，才暫停真實共用並複製；雲端清冊／大小／可用 hash／來源穩定性全部通過後才恢復。任何失敗保留恢復狀態且不提前恢復共用。

## 工具與執行 / Tools

- [OAuth 工具](../../scripts/drive_backup_auth.py)：Google 官方 OAuth library、PKCE 與 loopback callback；token 以目前 Windows 帳號 DPAPI 保存。授權網址亦僅寫在私有目錄。
- [ACL 工具](../../scripts/drive_backup_acl.py)：預設只讀取並產生私有 snapshot／restore plan；`--probe-empty-object` 才操作新建空白測試物件。**此版本不會撤銷固定專案 ACL，也不包含正式傳檔流程。**
- [測試](../../scripts/test_drive_backup_acl.py)／[依賴](../../scripts/requirements-drive-backup.txt)。Git policy 拒收 DPAPI 與 client-secret 檔；只提交去敏結果。

在 Windows 專案根目錄執行，私人輸出必須是尚未存在的新目錄：

```powershell
& "$env:USERPROFILE\.llm-pj-backup\venv\Scripts\python.exe" scripts/drive_backup_auth.py --client-json "$env:USERPROFILE\.llm-pj-backup\client.dpapi"
& "$env:USERPROFILE\.llm-pj-backup\venv\Scripts\python.exe" scripts/drive_backup_acl.py --private-output "$env:USERPROFILE\.llm-pj-backup\acl-NEW-RUN"
```

每日 `llm-pj-23-30` 提示已同步本輪決定、官方 API 工具入口及授權限制，保持 ACTIVE、Asia/Taipei 23:30，既有完成／失敗通知及同阻礙安靜規則不變。

English: The dedicated OAuth client and Drive API are configured, but owner consent is paused at Google's unverified-app warning. Secrets-in-place encryption is now explicitly authorized. The tested tooling captures raw ACLs and can rehearse transitions on an empty probe; it has not suspended real sharing or copied the project. Testing-mode token expiry, full target ACL coverage, encryption, transfer and cloud verification remain separate completion gates.

官方依據：[Drive permissions](https://developers.google.com/workspace/drive/api/reference/rest/v3/permissions)、[直接與繼承共用](https://developers.google.com/workspace/drive/api/guides/manage-sharing)、[Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)、[Desktop OAuth／PKCE](https://developers.google.com/identity/protocols/oauth2/native-app)。
