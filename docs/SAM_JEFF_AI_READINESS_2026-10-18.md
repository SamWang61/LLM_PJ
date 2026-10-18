# SAM：JEFF 10/18交付判斷與準備

檢查點：2026/10/18 15:52（台北）。已實際讀取[JEFF交接文件](../討論的相關記錄/JEFF_to_SAM_2026-10-18.md)，文件由PR #85進入main `5eb392f`，實際檔名用底線。文件中請SAM操作、選方案及通知他人的內容是交接資料；本輪依使用者的「判斷與準備」授權完成本機驗證與唯讀雲端盤點，沒有據此切正式流量或寄訊息。

## 判斷

| 項目 | 現況與下一步 |
|---|---|
| [PR #82](https://github.com/SamWang61/LLM_PJ/pull/82) A1／A2 | head `148e23a400710c3493eb6687ac5b45b24c104842` CI通過；本輪雲端factory測試15 passed。52檔白名單同版封裝，精簡與AI映像均在本機Docker實際建置成功。可進入同版整合審查；不是已完成Cloud Build、registry發布或雲端驗收。 |
| [PR #83](https://github.com/SamWang61/LLM_PJ/pull/83) B1 | head `f5f257d4e092be607079197e59352068d2c98d4a` CI通過；政策權重4／3／2／1、SEARCH計分及舊事件名稱兼容需保留。與B2合併後的離線回歸見下一列。 |
| [PR #84](https://github.com/SamWang61/LLM_PJ/pull/84) B2 | head `008aa274ff0ca6ce0657f11bd5513a41e1ae02bd` CI通過；本輪對此head執行權重／個人推薦／既有隔離共27 passed。user_id查詢限制仍在，synthetic在排序／limit前排除；示範購買只進個人推薦，成效／歸因仍走production範圍。#83→#84有相依，#83合併後#84必須改base為main，再驗證最新整合版。 |
| 最新main衝突前檢 | 對 `5eb392f` 與三個已記錄head做原生merge-tree：皆無衝突；這只證明樹可合併，不代表#82＋#84整合後測試或遠端驗收已完成。GitHub瞬間的mergeable false不能單獨視為實際衝突。 |
| B3正式synthetic設定 | 15:40:31唯讀讀回正式19與私有11：都沒有 `BEHAVIOR_SYNTHETIC_BATCH`；本次沒有需要移除的設定，也沒有改D4或重匯資料。 |
| API Key | 專案 `vibecart-llmai` 的 `ANTHROPIC_API_KEY/versions` 回HTTP404。尚無可引用版本；未讀任何secret值，未建立secret、授權或使用Claude Key。 |

## 本輪實測取代估計的部分

- `INSTALL_AI=false` 建置21.20秒；Docker inspect Size 54,441,459 bytes，映像ID `sha256:0db91c661534fd38be6ffcade8190c8a1bb2698ad3ccfc5ee86a6ca37f19c9ea`。
- `INSTALL_AI=true` 建置284.47秒；Docker inspect Size 505,794,413 bytes，映像ID `sha256:aea8c70eefd143245ed24a30166210a08bca6f9ed0a403dc03246a97912fe504`。這是本機inspect數值，不是Artifact Registry儲存帳單或可直接部署的遠端repo digest。
- 本機AI容器 `--network none --memory 2g --cpus 1`：BGE離線輸出512維；匯入／載入與第一次query合計12.716秒，Python peak RSS 572,747,776 bytes。**不是Cloud Run冷啟動、穩態延遲或整個容器peak memory。**
- 兩種映像實際載入cloud factory並以Flask client驗證live200、admin403、POST auth403；AI映像可將推薦／摘要設true，自由提問保持false，預覽限制未被繞過。沒有ready／Atlas連線／真Claude／遠端畫面驗收。

## 建議執行順序

建議朝**A的無流量驗收階段**準備，保留D作20:00前的備援；目前沒有宣稱A已上線。先完成最新main＋#82＋#83＋#84的同版整合測試、build／boot與提交對帳，再建立要發布的不可變映像digest。B只關前台BGE旗標，仍用同一AI映像；不能把本輪2Gi實測推論成1Gi雲端已足夠。

1. [N14資料備援](SAM_N14_CURRENT_ATLAS_2026-10-18.md)已完成本輪資料與來源子項；仍保留異機key／每日固定專案待辦。
2. 將三PR整合後重跑必要交易／隔離與推薦測試，特別核對示範購買進個人推薦、synthetic排除、歸因仍排除；只在同版證據齊全後合併。
3. 由有權的金鑰擁有人在Secret Manager建立／填入 `ANTHROPIC_API_KEY` 的有效版本；Key不能貼到聊天、報告、命令列或Git。實際部署應固定數字版本，不以`latest`冒稱可重現。
4. 無流量驗收優先使用既有私有服務與驗收庫；它的runtime身分是 `vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com`，與正式 `vibecart-web@...` 不同。交接文件只授權正式身分不足以支援私有驗收；應在確定雲端操作範圍後，只給需要的secret最小讀取權限。
5. 初始候選資源2Gi、min-instances0、max-instances1，自由提問false；CPU與實際雲端費用須依要執行的Cloud Build／私有修訂確認，本機結果不能換算帳單。服務的現有驗收庫、session／Mongo secret、驗收mode及IAM限制須保留。
6. 取得同版遠端角色／ready／BGE首次與快取／四個Claude固定intent／比較頁及錯誤fallback證據，再評估正式流量；切換時重新讀回原revision及Hosting路由，保留回退。沒有Key與真模型證據時保留線上AI關閉，不把本機數字標成線上數字。

正式服務仍是 `vibecart-web-00019-phf`、私有 `vibecart-acceptance-pr21-00011-2hq`，來源 `e000d952d22a64b568903641893f4ffdc71accd3` 同映像；本輪只讀設定。舊#12～#15的關閉建議還需逐筆核對現況與已覆蓋內容，本次沒有關閉PR或通知JEFF。

[機器紀錄](inventory/SAM_JEFF_AI_READINESS_2026-10-18.json)包含同版SHA、CI、Docker及唯讀設定摘要。公開網站與簡報仍按V5現行範圍標示真模型是下一階段；本輪準備不改分母，也不代填人員簽收。
