# SAM 固定 Drive 機密修復與全量備份準備 / Encryption and backup preparation

更新：2026-10-22 13:40（Asia/Taipei）。本紀錄接續[原始隔離](SAM_DRIVE_ISOLATION_2026-10-22.md)，以本輪[去敏證據](../inventory/SAM_DRIVE_ENCRYPTION_2026-10-22.json)為準。

## 已完成的機密修復

- 完整檢查 10,611 個雲端一般檔案的可列版本，包含目的地額外檔案；另核對固定專案引用的 Google 文件。固定專案、來源資料夾與文件的 ID 及原連結保留。
- 共 980 個檔案／984 個版本依敏感路徑或內容規則改以 AES-256-GCM 保存，包括原先確認的 3 份含憑證設定檔及 Git 內部資料。這個數量是保守加密範圍，不是有效憑證數量。
- 每個版本均先下載、加密、以原檔案 ID 上傳密文、從雲端獨立下載並認證解密、比對明文 SHA-256，才移除對應明文版本。密文版本保留 keepForever；原檔名、父資料夾及檔案 ID 不變，未刪除目的地額外檔案。
- 普通檔案版本檢查的 119 筆保留標記，91 筆回讀為 false；28 筆共 209,235 bytes 受 Google 的 `illegalKeepForeverModification` 限制，不能改回 false，故保留原版本，未為取消標記而刪除它們。[Google 版本保留限制](https://developers.google.com/workspace/drive/api/guides/handle-errors#illegalkeepforevermodification)。金鑰、OAuth token、完整 ACL、版本對照及復原副本只保存在專案外的受限本機區域，未上傳金鑰或明文憑證。
- 最終重新列舉 11,780 個雲端物件，原 ID 全保留、非擁有者權限 0；機密密文雜湊／認證復原及原明文版本移除證據均通過。

第一次批次在 633 個檔案完成後，遇到一筆版本保留回讀未生效，立即停止並取消尚未開始的工作。重讀確認 false 後，重新設定已回讀 true；已保存第一次失敗紀錄。補上有界、先讀後重試的保留設定及回歸測試，依原日誌續做，未重建檔案或重跑撤權。未保存到第一次失敗的服務端原因，因此不臆測成因。

## 全量來源尚未完成

本機已準備 **47,557 個可讀檔案／5,296,813,561 bytes**，其中 **3,407 個**完成加密與本機認證解密，包含 Git 未追蹤及歷史資料。這是私有準備資料，尚未執行來源全量雲端傳輸；不是完整備份完成。

`MuscleCore分析資料/website/.pytest_cache` 被 Windows 拒絕讀取。尚未獲准排除，也沒有變更該目錄 ACL 或刪除它；來源清冊維持 `complete=false`。需要 SAM 決定是否明確排除可重建的測試快取，或先修復本機讀取權限。GitHub 發布及其他來源變動後，須重新核對／產生最終清冊，不能沿用準備資料的數量當作當下全備份。

**共用仍停止。** 必須完成來源全量傳輸、全部相對路徑／大小／可用雜湊／來源穩定性核對，以及必要的復原驗證後，才按原私有 ACL 計畫恢復 4 筆原直接授權並回讀整棵樹。原 ACL、restore-plan 及 active-isolation 指標不得被目前 owner-only 清冊覆蓋。

## 工具與測試

- `drive_backup_payload.py`：完整檔案／空目錄清冊、串流雜湊、機密規則、認證加密與私有暫存。可讀部分準備不會把不可讀來源改標完整，也不自動排除快取。
- `drive_backup_remediate.py`：以原 ID 保存各版密文、遠端認證復原、保留版本、移除已證明可復原的原明文版本及可續作日誌。
- `drive_backup_transfer.py`：預先配置 ID、multipart／resumable 傳輸、收到範圍回讀及上傳後雜湊核對；不確定回覆不盲目重建檔案。
- `drive_backup_sync.py`／`drive_backup_run.py`：全量計畫、空目錄、保留目的地額外檔案、來源與雲端核對。CLI 須使用完整私有 manifest、完整機密稽核與已暫停共用的原恢復狀態；不完整來源會在傳輸前拒絕。這些工具不會自行恢復共用。
- 本輪 **133 項本機測試通過**；涉及來源變動、密文竄改、遺失傳輸回覆、續傳範圍、路徑衝突、空目錄、目的地額外內容、原生文件歷史缺項與失敗時禁止移除明文。大規模來源全量傳輸與最終 ACL 恢復尚未實跑，不以測試通過取代驗收。

## OAuth 與排程

[工具用途](https://vibecart-llmai.web.app/backup/)、[隱私說明](https://vibecart-llmai.web.app/backup/privacy.html)及[使用說明](https://vibecart-llmai.web.app/backup/terms.html)已於 Firebase Hosting 發布，三頁 HTTP 200 且與來源逐位元相同。原 404 頁及 Cloud Run rewrite 保留，未重新部署 Cloud Run。Google OAuth 品牌欄位及既有專案網域已保存，發布按鈕已可用。

目前仍為 **External／Testing**。轉 Production 會改變授權期限及可申請的使用者範圍，瀏覽器安全規則要求操作當下確認，故已向 SAM 詢問，尚未執行發布；不是重問先前同意的 Drive scope。Google 文件載明 Testing 的授權及 refresh token 於 7 天後到期：[官方說明](https://support.google.com/cloud/answer/15549945?hl=en)。不得宣稱長期免登入已就緒，也不能把新品牌頁上線當成 OAuth 正式發布。

每日 23:30 heartbeat 保留，持續先讀最新狀態並避免重疊；固定來源未完整可讀或最終驗證未過時維持隔離。相同待決定事項不重複通知。

English: Confidential existing Drive blobs have encrypted, pinned replacements under their original IDs, with independent cloud recovery verified before plaintext revision removal. All original objects remain owner-only. The readable local source has been staged, but one inaccessible cache directory prevents a complete source manifest. Full source upload, final reconciliation, ACL restoration and OAuth production publication remain pending. Local tests and Hosting information pages are separate evidence, not a completed daily backup.
