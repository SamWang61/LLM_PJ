# 2026-10-23 每日完整備份 / Daily full backup

主責：SAM。對應 2026-10-23 23:30（Asia/Taipei）排程；完成於 **2026-10-24 02:48:00**。本次完整備份、機密認證復原及原共用恢復均已通過，依[每日備份規範](../BACKUP.md)與[去敏收據](../inventory/SAM_DRIVE_DAILY_2026-10-23.json)核對。

## 完成範圍 / Verified result

| 項目 / Item | 結果 / Result |
| --- | --- |
| 來源清冊 / Source snapshot | 2026-10-24 00:14:03（Asia/Taipei）；47,778 檔、5,309 個子目錄、5,301,769,589 bytes |
| 完整雲端與權限 / Cloud and ACLs | 53,876 個物件；原物件 ID、空目錄及目的地額外內容保留 |
| 機密復原 / Encrypted recovery | 3,601 份密文全部獨立下載，AES-256-GCM 認證解密及來源雜湊核對通過 |
| 實際傳輸 / Transfer | 新增 37 檔、3 個目錄；更新既有 28 檔；其餘 47,713 份來源檔以完整雜湊核對一致 |
| 原共用 / Original sharing | 全部內容與復原門檻通過後恢復 4 筆原直接授權，再完整回讀直接／繼承權限與來源；完成收據兩項旗標均為 true |
| 唯一排除 / Only exclusion | `MuscleCore分析資料/website/.pytest_cache`；未套用 Git ignore 或擴大排除 |

[固定專案連結](https://drive.google.com/drive/project/1rQrO8v6bl3_y_B0BwpZXhlHFHS8swQc5?usp=drive_link)及原資料夾、Google 文件來源均保留。Production OAuth 本次正常使用，沒有要求重做既有授權；金鑰、OAuth 憑證與原始權限清冊留在專案外。

## 隔離讀回與續作 / Isolation and recovery

00:49 已逐筆確認 4 筆原直接授權刪除，但隨後的子項目清冊仍回報非擁有者存取，因此程序停止，當時沒有複製專案檔案。失敗日誌及原 ACL／恢復身分完整保留，沒有重送刪除或以 owner-only 清冊覆蓋原 ACL。

後續唯讀檢查保存了一筆資料夾清冊仍顯示連結讀者、而新的 `permissions.list` 與 `files.get` 均顯示 owner-only 的原始差異。再完整讀回 53,836 個權限端點及全部目錄，確認非擁有者授權為 0。不能從未保存的第一次衝突推定後端原因；採納的是後續實際保存的獨立觀測。

撤權後另對每個物件重新稽核：53,833 個繼承物件的版本各增加 1，3 個直接操作物件的版本增量恰與已核對的移除授權數吻合。普通檔案的大小、可用雜湊、內容 revision、修改時間及所有其他已讀欄位完全一致；3 個直接物件的時間變更均位於本輪撤權操作區間。原 Google 文件文字 SHA-256 與完整可見內容版本亦吻合。這是有逐物件證據的本次授權變更審核，不是一般檔案版本豁免。

完成上述審核與來源核對後，沿用本輪原 ACL、原清冊及原物件 ID 繼續傳輸。全量雲端與來源核對、3,601 份密文認證復原通過後才恢復原共用。最終權限讀回另有 242 筆初始觀測差異；每筆均保存原差異，再以兩個獨立端點精確核對原 permission ID、語義及繼承關係，每筆實際均於第 1 次重核通過。最終重新計算全部 53,876 個物件的權限與原授權一致，完成前再次檢查來源。

## 程式補修與驗證 / Repair and validation

- 隔離遇到矛盾清冊時，先保存原始觀測，最多 3 次唯讀兩端點重核；必須兩者精確一致且只有原擁有者，才採納。持續的額外授權、缺漏欄位、身分／路徑／類型差異仍停止，沒有重送權限變更。
- 每日程式在長時間 ACL 掃描前即將固定專案檢查點落盤；已存在的檢查點不可覆寫。本輪私有啟動器已即時保存同一檢查點，補修讓此要求直接由正式入口執行。
- 撤權前後保存原生文件指紋及完整雲端觀測，逐物件核對版本增量只等於原已移除的授權數；普通檔案雜湊、revision、修改時間及其他欄位不可變。直接物件的時間變動須落在已保存的操作區間。
- **246 項本機測試通過**（229 項 Drive、17 項加密封裝），包括 33 項新案例；另以本輪 53,836 個真實保存快照做離線審核重播，全部通過。未重新執行整站部署、Atlas 或人員驗收。

**時間界線：本輪雲端執行使用原程式與上述保存證據的恢復流程；這份完成紀錄、補修程式及後續 Git 提交在來源清冊之後產生，納入下一輪每日備份。** 本機補修測試與離線證據重播不冒稱新版程式已另做一輪完整雲端備份；GitHub 發布見 [PR #183](https://github.com/SamWang61/LLM_PJ/pull/183)，CI／合併狀態以該 PR 實際紀錄為準。私有完成收據 SHA-256：`ec8630bff794dc5f00ffdd35cea01e72db9ce3fc4e3412dfd8f9febbb52d97aa`。

English: The October 23 scheduled backup completed on October 24 at 02:48:00 Taipei time. All 47,778 source files, 3,601 independently downloaded encrypted recoveries and 53,876 cloud objects/ACLs passed verification before the completion receipt. Original sharing and fixed IDs were restored. Conflicting isolation observations and permission-related version increments were independently reviewed without replaying mutations. The follow-up repair passed 246 tests and an offline replay of the real snapshot. This log, repair and Git publication are post-cutoff material for the next daily cycle.
