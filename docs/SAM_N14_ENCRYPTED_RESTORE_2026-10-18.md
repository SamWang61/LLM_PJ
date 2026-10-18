# SAM N14 加密備份與隔離復原｜2026-10-18

主責：[SAM](mailto:cashsam@gmail.com)。本輪基線 main `40dbd24abd8041c66e0642f14c4dd4cc727638a9`，PR #74 已合併。依使用者授權由 SAM 實作、測試與技術覆核，通過 GitHub CI 後直接合併；不代填其他人的具名接收。

## 本輪已完成

| 項目 | 實際結果與邊界 |
|---|---|
| 完整歷史來源 | 05:28:12（台北）私有快照，13,048檔、4,069,976,322來源bytes，包含當時未追蹤／忽略檔與Git資訊；原清冊明列排除1個Office暫存鎖檔。**不是08:00後最新main／工作目錄快照**。 |
| 客戶端加密 | 串流AES-256-GCM、隨機32-byte金鑰、每次獨立96-bit nonce、完整128-bit tag；header／長度／來源SHA-256一起認證。工具不執行上傳或解壓。 |
| 金鑰分離 | 本機資料與金鑰在不同目錄，兩個新目錄ACL只有目前Windows使用者與SYSTEM；金鑰未入Git／Drive／報告。**同一台電腦的兩個目錄不等於異機災難復原**。 |
| 加解密與還原 | 2,439,493,848-byte原ZIP認證解密後hash相同；全新目錄逐檔核對13,048檔，差異0。五個密文分片重組hash等於完整密文。 |
| 復原啟動 | 使用還原app來源，既有本機runtime依賴映像；Docker internal網路、來源唯讀、0公開port、停用dotenv載入、無Atlas連線。首頁／商品／登入／CSS四個實際本機HTTP GET皆200。不是使用還原Windows虛擬環境，也不是重新部署。 |
| 本機資料演練 | 3個fixture集合、3筆BSON資料匯出→刪除隔離庫→還原、unique index重建；內容hash差異0，啟動後資料差異0。**不是正式Atlas匯出或正式資料復原驗收**。 |
| 安全回歸 | 44 passed／0 skipped：錯key、header／密文／tag竄改、截斷／附加、空檔、來源變動、不可覆蓋及並行輸出保護；外部網路拒絕、host直接啟動拒絕、既有報告保護。 |
| 清理 | 最後一次本機啟動08:43執行；fixture DB、兩個自建容器與internal network已清除。失敗首輪也已清除。 |

原ZIP SHA-256：`75f91fcf4b490a112ec1672393600d7cab5c649e60282d9f1203cc3516d9a291`。

密文2,439,493,924 bytes，SHA-256：`328b9aa8194589d53d8f18e7d41b0e96809335a1329bd23ed3ba95d992fe51d5`。五片各自大小、SHA-256／MD5與runtime映像ID見[機器紀錄](inventory/SAM_N14_ENCRYPTED_RESTORE_2026-10-18.json)。雜湊證明本次內容一致，不代表來源是最新版本。

首輪本機HTTP驗收因本工具的category fixture使用`category_name`、還原服務實際讀`name`而得到500；已修正fixture欄位，最後兩次隔離啟動皆通過。沒有更動還原來源來掩蓋失敗。

## 雲端與N14仍缺

08:34～08:40透過Google Drive連接器讀回[既有私有備份位置](https://drive.google.com/drive/folders/1VXRIgBOG7mj2b3funYY0i46mdYpJ0DfS)為owner-only，與歷史共用的每日固定專案分開。已上傳並讀回672-byte加密索引檔（僅索引、無金鑰）；**索引檔不是資料備份**。原480MiB分片在操作呼叫前被連接器以HTTP413拒絕（單檔上限100MiB，未新增雲端資料）；已改成25片各≤96MiB上傳，完整密文hash不變。小片尚未全數完成獨立遠端hash／重組／解密驗證，不標雲端完成。

N14仍待：25小片雲端讀回、最新穩定來源快照、金鑰異機保管與獨立解密、正式Atlas一致性匯出／所有集合與索引／validator／TTL中繼資料／隔離還原對帳，以及每日23:30固定專案ACL流程。現有本機資料演練只包含三筆自建fixture，不能代替正式Atlas資料備援。

**V5仍14關卡，2完成／12待結案；N14保留待結案。** N07～N10下一階段不計入；正式Cloud Run／Hosting／Atlas／D1～D4不變。本次只合併備份工具與已驗證的本機部分，不把雲端或Atlas缺口視為合併完成。

## 重現方式（私有目錄，先配置ACL）

安裝獨立工具環境：`python -m pip install -r scripts/requirements-backup.txt`。

```powershell
python scripts/encrypted_backup.py keygen --key-file <獨立私有目錄/recovery.key>
python scripts/encrypted_backup.py encrypt --source <既有私有ZIP> --output <私有資料目錄/archive.vcbak> --key-file <獨立私有目錄/recovery.key>
python scripts/backup_archive_parts.py split --source <私有資料目錄/archive.vcbak> --directory <全新小片目錄>
python scripts/backup_archive_parts.py join --directory <雲端讀回小片目錄> --output <全新重組密文路徑>
python scripts/encrypted_backup.py decrypt --source <私有資料目錄/archive.vcbak> --output <私有資料目錄/new-restored.zip> --key-file <獨立私有目錄/recovery.key>
python scripts/run_backup_restore_acceptance.py --restored-root <新解壓來源根目錄> --runtime-image <已快取的依賴映像ID> --report <新報告路徑.json>
```

每次輸出必須不存在，解密最後認證完成前不發布結果；目的地檔案系統須支援hard link。先驗整體ZIP hash與成員路徑、link／重複檔名，再解壓至全新私有目錄及逐檔hash核對。金鑰應獨立複製到受控異機媒體，不能和密文／完整清冊一起上傳或放入Git。舊明文ZIP／分片仍是私有本機歷史，沒有自動刪除或上傳。

加密使用[cryptography官方GCM文件](https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/)的隨機nonce、AAD、完整tag與認證後使用明文方式；依賴只屬備份工具，不加入網站映像。復原probe固定credential-free `backup-db` internal Docker alias，不接受Atlas URI；報告紀錄的是本機fixture範圍。
