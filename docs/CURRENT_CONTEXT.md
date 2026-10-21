# 最新專案上下文 / Current project context

更新：2026/10/22（Asia/Taipei）。先讀本頁，再選一份相關來源；舊時點不當成現況。完整舊入口原文保留於[歷史快照](CURRENT_CONTEXT_HISTORY_2026-10-22.md)。

## 現行版本與資料

- 程式：前台效能／操作改善已由PR #166合併，完整發布、量測、候選與正式桌面操作見[效能交付](FRONTEND_PERFORMANCE_2026-10-21.md)；七個前後台PR與同交易裝置撤銷／180天稽核收據見[優化系統](優化系統.md)。
- 本輪：分頁圖示缺檔修正、正式修訂／digest／來源及公開驗證見[SAM圖示發布紀錄](SAM_FAVICON_2026-10-22.md)。以當次讀回的100%流量修訂為準，不能用latestReady或私有預設入口冒充正式版本。
- Atlas：`vibecart_ai` active contract為30集合／96索引／8筆migration；10/22本輪唯讀稽核通過，12組關聯0 orphan。[去敏讀回](inventory/SAM_ATLAS_READBACK_2026-10-22.json)。既有migration checksum不修改。
- 簡報：使用者指定v5原檔已由PR #165合併，14頁、3,262,322 bytes，SHA-256 `4aa9b13286fe98574d3dd648889545ad196d92cea9aebb9a143c794ad392d193`；[主檔入口](../簡報文件/超市AI版_2026-10-18/README.md)。舊13頁或其他hash是歷史版本，勿混用。

## 完成範圍與真正待辦

V5正式清單仍為 **3/14結案、11待結案**；不是功能失敗比例。10/20篩選的五項技術／素材工作已完成，不能反覆把舊「未部署」或「瀏覽器受阻」當成新待辦。[技術總表](SAM_FIVE_TECH_EXECUTION_2026-10-20.md)與[三人回填表](../專題進度/待結案篩選與三人實作表_2026-10-20.md)分開閱讀。

| 下一步 | 主責與完成條件 |
| --- | --- |
| 本人接收及手機範圍 | JEFF覆核AI／後台／S06～S08，REN覆核會員／購物／S03～S05，SAM覆核資料／整合／交付。按三人表填實際時間、設備、URL、版本、逐案結果與原圖；代理桌面測試不代簽。 |
| 每日固定Drive備份 | SAM／目錄擁有人補齊可恢復permission ID、專案／資料夾／子檔案直接與繼承ACL撤銷與恢復，及本次機密方案與雲端對帳；最新前置未齊，未複製或改共用。[備份規範](BACKUP.md)。 |
| 復原副本處理 | 同機完整USB復原子項已依[SAM決定](SAM_ACCEPTANCE_DECISIONS_2026-10-20.md)接受；設備仍照實記同機，不代填REN簽名。自動核准審查拒絕刪除的私有明文仍待SAM本機處理，保留密文／分離金鑰及原報告。 |
| 展示與最終接受 | 各段採用圖／版本、實體離線與投影、本人講述計時及同版全站接受依[N18／三人工作表](../專題進度/待結案篩選與三人實作表_2026-10-20.md)記實際證據。機器建包不當現場演練。 |
| 10/31管理覆核 | SAM依仍需使用情況覆核三條工作站/32規則並移除或展延；這是管理期限，未宣稱Atlas已設定自動到期。[主責／用途](SAM_ACCEPTANCE_DECISIONS_2026-10-20.md)。 |

## 固定協作界線

- JEFF：AI／推薦／後台；REN：會員／購物／Session；SAM：資料庫／測試／整合交付及前台技術補件。依現行分工，不從歷史分支作者推定主責。
- 不重匯D1～D4，不為補畫面捏造正式評價、訂單或6＋4候選。評價與顯示進位規則、去重及synthetic排除維持既定契約。
- N07～N10是後續階段；廣泛D5狀態編輯不由裝置撤銷功能推定完成。
- 正式庫故障、其他人的Session或權限不任意變更；固定Drive專案／連結與目的地額外檔案保留，金鑰不上傳。
- 原目錄未提交修改保留；在乾淨工作樹做範圍明確的修改。分開記錄本機、CI／合併、部署、Atlas持久化、代理操作及本人驗收。

English: Start here and read only the relevant linked source. Current technical delivery, the 30/96/8 data contract and the 14-slide user-supplied presentation are distinct from named acceptance, physical-device evidence and the fixed-project daily backup. All historical context remains available in the unchanged snapshot.
