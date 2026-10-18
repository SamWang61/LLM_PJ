# SAM N14 最新快照與 Atlas 完整資料還原｜2026-10-18

整體檢查點：2026/10/18 15:52（台北；最後清冊內容讀回15:49:47之後）。主責：[SAM](mailto:cashsam@gmail.com)。本輪依使用者授權處理最新快照及正式Atlas備份／隔離還原，測試與CI通過後合併；原髒工作樹保留。

## 本次驗收結果

| 項目 | 證據與範圍 |
|---|---|
| 最新來源快照 | 15:30開始、15:36:37完成重建核對；13,976檔、4,109,781,733 bytes，包含Git資訊、忽略檔及未提交內容。原分支HEAD `bbb8e9c`，擷取時追蹤main為 `5eb392fdd9620f3dcd2745c2cb76f57baf1f6d54`。**這是原目錄快照，不是乾淨main checkout；擷取後的新提交不在其中。** |
| 明列排除 | 只排除存取被拒的 `MuscleCore分析資料/website/.pytest_cache` 暫存目錄；本次沒有Office鎖檔。其餘目錄不可讀、link或來源變動均拒絕接受。未依Git忽略規則刪減原始碼、環境或憑證。 |
| 完整重建 | 以先前已認證的05:28完整ZIP為基底，加上983個新增／變更檔及1個刪除項目，重建全部13,976檔；雜湊差異0、額外檔案0。差異ZIP 40,278,773 bytes，SHA-256 `904a2b850df294bfab79da9eb2562e2567895c01f105052856e5792f9fa8b260`。**差異包不能單獨還原，必須保留原25片基底與外部金鑰。** |
| 正式Atlas一致性匯出 | `vibecart_ai` 全部28集合、14,689筆、89個標準索引、3個TTL、集合validator／validationLevel／validationAction；Atlas Search索引已查為0。資料由同一snapshot session讀取，時間戳 `Timestamp(1792308144,20)`；集合UUID、options、索引及Search metadata在匯出前後相同。檔案與資料庫是兩個有各自時間戳的快照，未宣稱同一秒。 |
| 本機完整資料還原 | 首輪本機備份與第二輪**雲端認證解密後的備份**均在全新、只綁127.0.0.1的credential-free replica set還原。28集合原始BSON雜湊／筆數一致，89索引的複合鍵順序與options、validator／TTL全部相同；資料雜湊差異0。 |
| TTL與負向檢查 | 還原時停用TTL monitor，避免到期歷史資料在對帳前被刪除；TTL定義照原樣復原。另以獨立fixture驗證唯一鍵錯誤11000、validator錯誤121。這些負向fixture不代稱逐一測過所有正式validator拒絕案例。 |
| 隔離與清理 | Atlas 8.0.34 → 本機8.0.20（同8.0系列）；只有本機產生的 `sam_n14_restore_<uuid>` 可作還原目標。來源沒有insert／update／delete／DDL；兩輪還原庫均刪除、mongod程序均停止，明文資料與log仍在USER／SYSTEM私有目錄，未放GitHub。 |
| 雲端保存 | 最新差異包＋全部Atlas BSON／metadata＋復原工具封裝成42,063,392-byte ZIP，AES-256-GCM加密後42,063,468 bytes。已上傳私有Drive、檢查owner-only ACL、獨立下載完整密文SHA並認證解密；ZIP與本機相同。遠端解出的差異ZIP hash也與已完整重建的差異包相同；未重複解壓13,976檔，來源重建採此內容一致性銜接。 |
| 自動回歸 | 備份相關79 passed／0 skipped，涵蓋Atlas本機目標限制、TTL guard、BSON／metadata完整性、複合索引順序，以及差異包的刪除／新增／路徑／Windows裝置名稱安全；CI加入同一組測試。 |

最新密文SHA-256：`cbe9c33fffa9cc973f56ab249583401c7046a278e4d3a6525cbc5059b4126776`；ZIP SHA-256：`4f94608463d0d08807b4eede218799eccd9929899483b8a8e8a0724d013ed07b`。雲端清冊沿用原ID更新為20,456 bytes，再完整讀回核對SHA-256 `9b5dc440190cfed11313ef8b2885a5265701b34f36994e938df6c6386ad64cdd`、owner-only。基底25物件ID與重建關係保存在加密capsule及清冊；金鑰未上傳。

## 重現與交付

1. 安裝 `scripts/requirements-backup.txt`，先準備USER／SYSTEM可讀的私有目錄與獨立金鑰位置。
2. 下載並逐片驗證[歷史基底](SAM_N14_ENCRYPTED_RESTORE_2026-10-18.md)，重組密文後用 `encrypted_backup.decrypt` 認證解密成原ZIP（SHA-256 `75f91fcf4b490a112ec1672393600d7cab5c649e60282d9f1203cc3516d9a291`）。
3. 下載最新密文、核對上方SHA，再以同一外部金鑰認證解密；確認ZIP hash後才驗路徑及解壓。不得把金鑰放在密文或Git旁。
4. `source_snapshot_delta.restore_delta(base_zip, extracted/'source/latest-source-delta.zip', new_destination)` 完整重建目錄，會拒絕既有目的地、錯基底、路徑穿越、Windows別名及不符清冊內容。
5. Atlas內容在 `atlas-snapshot/`：連到全新localhost mongod，綁定127.0.0.1、停用TTL monitor，選全新 `sam_n14_restore_`＋32位hex名稱，再呼叫 `atlas_snapshot_backup.restore_snapshot(client, name, directory)`。函式會在任何還原寫入前驗證完整BSON／metadata hash及目標身分；實際使用程序還須像本輪一樣驗PID、dbpath並清理自建程序。
6. 匯出使用 `atlas_snapshot_backup.export_snapshot(source_client, 'vibecart_ai', new_private_directory)`；URI只在授權程序記憶體讀入，禁止放命令列或報告。工具鎖定PyMongo4.14.1的snapshot時間記錄，沒有可用時間戳便拒絕接受。

[機器紀錄](inventory/SAM_N14_CURRENT_ATLAS_2026-10-18.json)只發佈摘要；完整檔名清冊、BSON、UUID、憑證、log及金鑰不進Git。snapshot語意依[PyMongo官方文件](https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html#snapshot-reads)，原始BSON格式依[MongoDB官方文件](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/data-formats/bson/)。

## N14仍未結案

本輪已完成「最新原目錄快照鏈」與「正式應用資料庫全部集合／標準索引／validator／TTL的雲端備份及隔離還原」。**不包含Atlas平台帳號、IAM、其他資料庫或整個cluster的災難復原。** 尚缺異機金鑰保管及獨立復原、每日23:30固定專案的ACL切換／完整雲端流程；同一台電腦的金鑰與備份不同目錄不是異機備援。V5仍14關卡、2完成／12待結案，沒有因本次PR或兩個子項通過而關閉N14。D1～D4、主站流量、Cloud Run部署不變。
