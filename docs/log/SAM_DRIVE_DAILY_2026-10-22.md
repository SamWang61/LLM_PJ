# SAM 每日完整備份 / Daily full backup

更新：2026-10-23 00:55:52（Asia/Taipei）。本頁與[去敏收據](../inventory/SAM_DRIVE_DAILY_2026-10-22.json)記錄本次完整備份及原共用恢復；[前階段機密修復](SAM_DRIVE_ENCRYPTION_2026-10-22.md)與其他歷史文件保留。

## 本次完成結果 / Verified result

- 來源清冊時間：**2026-10-22 21:19:10**；完整備份於 **2026-10-23 00:55:52** 完成。共 **47,743 檔、5,310 個子目錄、5,301,622,386 bytes**；Git 歷史、未追蹤檔與空目錄均包含。
- 唯一排除為 SAM 明確核准的 `MuscleCore分析資料/website/.pytest_cache`。沒有擴大排除或修改該目錄的 Windows ACL。[正式政策](../../config/drive-backup-policy.json)。
- 雲端完整列舉 **53,836 個物件**，所有來源相對路徑、名稱、父目錄、大小及可用雜湊一致；原 ID、目的地額外內容和固定專案兩個來源均保留。
- **3,566 個機密檔案**以 AES-256-GCM 保存於原相對路徑；全部從雲端獨立下載、認證解密並比對來源明文雜湊。金鑰、OAuth 憑證、原 ACL 及恢復身分只留在專案外私有目錄，未上傳 GitHub 或 Drive。
- 所有內容及來源穩定性檢查通過後，才恢復原 **4 筆直接非擁有者授權**；再對 **53,836 個物件**完整讀取權限，核對原直接／繼承授權、內容及來源仍一致，完成收據才成立。**原共用已恢復。**
- 固定連結維持：[LLM_PJ](https://drive.google.com/drive/project/1rQrO8v6bl3_y_B0BwpZXhlHFHS8swQc5?usp=drive_link)。沒有刪除或重建專案、資料夾或同名檔案。

English: The complete source snapshot at 2026-10-22 21:19:10 Taipei time was verified in Drive, including 47,743 files and 3,566 independently downloaded and authenticated encrypted files. Only then were the original direct grants restored and all 53,836 object ACLs read back. The fixed project, object identities and destination-only content were preserved.

## OAuth 與每日執行 / OAuth and scheduling

`LLM_PJ Daily Backup` 已發布為 **Production／實際運作中**；Google 應用程式驗證仍未完成，Production 不等於通過驗證或永久免登入。[Google token 期限說明](https://developers.google.com/identity/protocols/oauth2/#expiration)。Production 發布後的新離線授權已於 2026-10-22 20:28:47 完成；2026-10-22 21:57:36 再核對目前憑證，確認對應原核准用戶端、refresh token 已更新、重新整理與擁有者身分均通過。原「稍後處理」待辦已由實際收據取代，多餘授權頁與等待程序已關閉，不需重複授權。憑證繼續以 Windows DPAPI 保存在專案外。

每日 23:30 Asia/Taipei 的 Codex heartbeat 保持 ACTIVE。需要本機開機、連網及 Codex 執行環境可用；這是本次實際成功加上後續排程，不能預先宣稱未來每日必定成功。後續若授權失效、遠端內容／權限變動或來源無法完整讀取，會保留證據並停止，不能冒稱完成。

## 中斷、續傳及來源差異 / Retry and source reconciliation

第一個完整快照有 47,658 檔、5,301,373,391 bytes、3,492 加密檔。建立目錄時曾有 1 個已預配 ID 無法回讀；後續上傳另有 6 個新檔 ID 無法回讀。各自獨立查詢確認 HTTP 404，保留同 ID 重試後成功；最初服務端失敗原因未保存，不推定成因。續傳保留原計畫、原物件 ID 及完整日誌，後段並行數為 32。

之後執行工作階段曾中斷於 47,429 個已核對檔案；重新檢查時沒有相符執行程序，也沒有完成收據，中斷原因未確立。取得同一執行鎖後重新完整讀回雲端，沿用保存的計畫及 ID 續傳；沒有把已送出請求等同成功，也沒有以中斷前進度當作最終驗證。

整體對帳另發現固定專案容器的 `version` 35→36，重新開啟來源清單後讀到 37。唯讀比對 751 個目的地額外檔案／原生物件，只有該容器版本不同；其餘已讀欄位（含修改時間）相同，兩個原來源 ID 也經 UI 重核。另存單次審查與驗證基準，原傳輸計畫／原 ACL 不改寫，未變更雲端內容；實際服務端原因未確立。[Google 說明 `version` 也反映使用者不可見的伺服器變更](https://developers.google.com/workspace/drive/api/reference/rest/v3/files#File.FIELDS.version)，所以不把版本號直接等同內容雜湊。

後續每日前置檢查已補上限定規則：只有固定 `application/vnd.google-apps.project` 容器、操作者明確重新核對原兩個來源、版本遞增且其他所有已讀欄位完全相同時，才保存版本審查並繼續。來源準備後須與本輪已接受的前置快照嚴格比較；版本再次增加仍須重新核對來源，不能沿用先前 UI 確認。一般檔案、原生 Google 文件、ACL、修改時間、來源物件集合或其他欄位變動仍須停下重新稽核；不是全域略過版本檢查。15 個新增回歸案例覆蓋這些界線。

PR #180／#181 發布使本機文件及 `.git` 改變，所以先完整核對第一個雲端快照，再重新建立最新來源清冊，以原 ID 補齊變動，最後重做完整雲端、來源及加密復原驗證。沒有跳過來源差異檢查。

相較第一份快照，最新來源新增 87 個檔案、24 個檔案內容變動；2 個已不在來源的舊檔仍保留在 Drive，沒有鏡像刪除。

差異補傳另遇 2 筆 multipart POST `ReadTimeout`；回讀確認原預配 ID 為 404，且固定根物件及父目錄仍 owner-only，逐一以同 ID 重試後兩筆均通過名稱／父目錄／雜湊驗證。之後執行全量唯讀對帳與來源檢查，沒有因單筆重試成功就提前恢復共用。相關錯誤與重試收據私有保存。

第一輪授權恢復後，完整 `permissions.list` 核對於約 9,000 個物件時遇到 HTTP 403 `rateLimitExceeded`，因此該輪未產生完成收據。程式撤回已恢復的 4 筆授權並逐筆確認刪除；當下全樹檢查也受限流影響，未把根物件結果冒稱全樹成功。22:21 的重新列舉亦曾遇到存取狀態不一致，因此再次停止，沒有採納未完成清冊或據以恢復。後續重新完整讀回全部物件確認 owner-only，與恢復前快照逐欄比較，另發現直接撤權的 3 個根物件修改時間恰在該次權限操作時段更新。22:43 的嚴格欄位比對因而停止；沒有直接略過。原生 Google 文件文字 SHA-256 與內容版本清單重新核對仍與原始稽核相同，資料夾完整內容／路徑未變，專案兩個原來源也重新以 UI 確認；其他欄位除授權影響的版本號外完全相同。限定保存這 3 筆修改時間審查；另存稽核與後續驗證計畫，原計畫及原 ACL 保留。

依 [Google Drive 現行限額說明](https://developers.google.com/workspace/drive/api/guides/limits)，批次內的各次列舉仍消耗配額單位。本輪將 100 個唯讀請求的批次啟動間隔由 1 秒調整為 3 秒；明確的 403 限流原因及 429 採最多 8 次、上限 32 秒並加隨機差值的退避，其他 403／TLS 失敗不重試，權限 POST／PATCH／DELETE 不自動重送。16 個新增測試驗證這些界線。重新核對當前遠端密文雜湊未變後，對已獨立下載的 3,566 份密文再次驗雜湊、認證解密並比對來源；再次完整來源／雲端核對成功後，重新恢復 4 筆原授權並完成全樹讀回。沒有重新上傳內容或更換 ID 來迴避限流。

本輪也修正授權恢復後的原生物件核對：記錄直接授權變更完成後的版本與修改時間，要求版本增量恰為本輪已驗證的直接授權次數，再與最後整樹讀回比較；其他原生物件修改時間仍須不變。原生 Google 文件在恢復前後另比對文字 SHA-256 與完整可見內容版本清單，避免把權限造成的時間更新誤判為內容變更，也不把真正內容／版本變動放過。7 個新增測試覆蓋時間更新、文字／格式版本變更、額外專案版本、未支援格式與不完整證據。

第二輪恢復完成了全部 53,836 個物件的權限端點列舉，未再遭遇配額錯誤；後續檔案清冊與該權限快照不一致，程式因此再次撤回 4 筆授權。該版未保存衝突物件的兩份原始回覆，不能推定確切成因。之後完整重讀確認所有物件 owner-only，原生文件文字與可見版本再次吻合，原來源重核後另存新計畫，原計畫與失敗日誌均保留。

修正後先落盤全量權限快照；遇到清冊與權限結果不一致，先保存該物件的兩份觀測，再最多 3 次獨立呼叫 `permissions.list` 與 `files.get`。只有兩個新回覆的 permission ID、角色、可見度等語義完全一致，且完整直接／繼承權限精確符合原規範，才採納；省略欄位不推定為安全值，持續差異仍停止並撤權。8 項新增案例覆蓋過時清冊／權限快照、角色／可見度／繼承／額外授權／缺漏欄位及完整恢復流程。本次最終逐物件重新核對共 167 筆，全部具備成功的私有證據；其中 167 筆較早的權限端點回覆只列擁有者，較新檔案清冊則顯示原授權。新的兩個獨立端點均重新確認精確原權限，每個物件實際最多使用 1 次重核。這是本輪已保存的觀測差異，不能倒推前一輪未留存的衝突成因；全部 53,836 個物件仍接受完整檢查。

English: A second restoration was rolled back after conflicting ACL observations. The repair persists the full ACL checkpoint and resolves any disagreement only through fresh file and permission endpoints that both match the original permissions. It does not infer missing fields or waive changed access. All per-object reconciliation evidence is kept private.

**時間界線：本頁完成紀錄、每日前置檢查、限流與原生文件補修及後續 GitHub 合併在上述來源清冊時間之後發布，會進入下一輪每日備份。** 本次完整一致的對象是該清冊及完成前再次核對的來源；不聲稱 Drive 已包含事後生成的本頁、補修或後續 Git 歷史。本機與 GitHub 文件的一致性在推送／合併後另外核對。

## 驗證與證據 / Validation and evidence

本輪備份相關測試共 **207 項通過**（190 項 Drive 備份＋17 項加密封裝）；其中新增 15 項專案版本審查案例。前階段 161 項測試的實作已由 [PR #180](https://github.com/SamWang61/LLM_PJ/pull/180) 與 [PR #181](https://github.com/SamWang61/LLM_PJ/pull/181) 合併，兩個 PR 的測試提交各有兩項 GitHub CI 成功。本次補修與完成紀錄在新 PR 發布，CI／合併結果以該 PR 為準；未重新執行整站或正式站部署。

一般 `files.list` 不保證子物件的 `permissionDetails`，因此每個物件另以完整 `permissions.list` 讀回，再核對新目錄清冊。每個批次最多 100 個純 GET；檢查 response ID、分頁、缺漏與重複，失敗項目完整重讀。撤權與恢復仍單筆依序進行。[Google 批次規範](https://developers.google.com/workspace/drive/api/guides/performance#batch-requests)。

公開去敏收據保留數量、時間、核對結論及私有完成收據 SHA-256；原始雲端清冊、檔案雜湊、權限身分、下載密文與恢復日誌存於 `C:\Users\USER\.llm-pj-backup`。980 個舊雲端檔案／984 版本的機密修復另有前階段證據，不用它替代這次全量驗證。

## 後續操作入口 / Next daily run

1. 先讀本頁與 `docs/BACKUP.md` 最新段落；以 `backup-execution.lock` 的非阻塞鎖確認沒有其他備份正在執行，才開啟固定專案核對原資料夾及原 Google 文件。鎖正被持有時不開啟專案頁、不重疊執行；鎖檔存在本身不表示仍在執行。
2. 讀取 `active-isolation.json`、`latest-complete-backup.json` 及實際收據，執行時持有同一個 `backup-execution.lock`。若上輪尚未恢復共用，沿用其原恢復資料續做，不能重開一輪或覆蓋原 ACL。
3. 上輪完成時，使用 `scripts/drive_backup_daily.py --run-directory <新的私有目錄> --key <既有私有金鑰> --project-sources-reconfirmed`。設定 `PYTHONDONTWRITEBYTECODE=1`，金鑰及工作目錄均在專案外。
4. 每輪完整讀回權限與雲端狀態，保存新的原 ACL 後才暫停共用；傳輸、全雲端／來源核對、所有密文認證復原全部通過，才恢復原權限並再次完整回讀。
5. 失敗保留停止共用及可恢復狀態；不刪除目的地額外檔案、不上傳金鑰。只在完成、失敗、新阻礙或必要本人動作時通知，狀態不變不重複通知。

English: Production publication is complete; a new post-publication offline consent is recorded separately. Subsequent daily runs retain fresh original ACLs, reject unexpected remote changes, perform full source/cloud/recovery verification, and restore sharing only after every gate passes. A fixed project container version increase is reviewed only after its sources are reconfirmed and every other available metadata field is equal; this does not waive document or permission changes. All 207 backup tests passed. Completion records, the daily preflight, quota and native-document fixes and their Git publication are after this backup cutoff and belong to the next cycle.
