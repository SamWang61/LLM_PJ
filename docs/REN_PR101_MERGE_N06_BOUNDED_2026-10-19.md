# REN PR 整合與 N06 持續中斷重試改善

更新：2026/10/19 08:20（Asia/Taipei）。執行角色 REN；[陳仁千](mailto:chen2000401@gmail.com)本人簽認仍待實際紀錄。

## 未合併 PR 審查

2026/10/19 07:53 查得 12 個 open PR。[#101](https://github.com/SamWang61/LLM_PJ/pull/101) 的 11 檔為本機隔離故障工具、範圍測試及文件；HEAD `ea7f4612cd823a8dc402c52a3a4d060f8007a9a4`、[CI #535](https://github.com/SamWang61/LLM_PJ/actions/runs/39175344939)成功，無未解審查討論。已用固定 HEAD 合併 main `0467a598691f82f861df196c51a79f49e38224ab`；[main CI #536](https://github.com/SamWang61/LLM_PJ/actions/runs/39178338662)成功。

其餘 11 項未直接合併：#86／#76 為舊基底且與目前 main 衝突；#10 同樣衝突，內容涉及尚未結案的 Atlas 網路開放狀態；#19／#5 為歷史草稿；#18 為草稿且目標不是 main；#13～#17 是早期串接分支、base 均非 main，不能將其當作已對當前主幹覆核的增量。保留這些 PR 供主責人重接現行 main、釐清重複內容與執行新 CI；沒有關閉或代改舊分支。逐項 HEAD／base／狀態見[PR 清冊](inventory/REN_OPEN_PR_REVIEW_2026-10-19.json)。

08:36 再讀時，[#103](https://github.com/SamWang61/LLM_PJ/pull/103) 已進 main `7aeb77c`，另有重疊 N06 的草稿 #102 與本輪 #104，當時 open PR 共 13。#86／#76／#10 仍顯示不可直接合併；#102 尚為草稿，#13～#17 仍非 main 目標。新版逐項快照附在同一 PR 清冊的 `latest_open_snapshot`；#104 需解衝突及 CI 後才可合併。

## 交易重試變更

[交易服務](../VibeCart_AI/services/cart_service.py)改由應用程式控制交易：整次重試窗 8 秒、單次 callback／commit 操作窗最多 6 秒，TransientTransactionError 以 50／100／200／400 毫秒後續上限 400 毫秒退避，最多四次重試既有唯一索引衝突。PyMongo `with_transaction` 內建約 120 秒且不能調整；本次移除對它的依賴。失敗結帳仍由原路由回 503，文案要求保留原操作識別碼。

重做交易時先結束前次 session；遇到 `UnknownTransactionCommitResult` 時只在**同一個 session／txn**重試 commit，絕不重新執行 callback。若期限耗盡，503 代表結果尚待確認；相同 `checkout_id` 再送會由既有冪等收據查回或完成原操作。單次正常成功仍維持200，異內容同 ID 為409。

8 秒是交易重試政策，不是整個 HTTP 請求的絕對截止：既在途命令、best-effort abort、登入與頁面其他查詢可能延長觀察時間。本機單次阻塞命令案例實測 6.109 秒成功、持續故障最多觀察到 8.032 秒回503；未宣稱全站 8 秒 SLO。沒有修改正式部署、Atlas 連線、索引或資料。

## 本機真 MongoDB 驗證

使用三個一次性 `127.0.0.1` mongod、隨機 replica set／DB、真 Flask WSGI 登入／購物車／結帳路由。工具只接受本機 binary，不讀 `.env` 或 Atlas URI；測後節點停止、fixture data 目錄清除。兩份完整原始 JSON 的工具來源 SHA 均為 `f4ec2bcc140ac23e0299002b65afd944945175db756284d9d8f762c2d6805219`，與本次工具檔逐 byte 一致。

| 故障 | 單次故障 HTTP／callback | 持續故障 HTTP／callback | 持續故障耗時 |
|---|---:|---:|---:|
| socket timeout | 200／2 | 503／2 | 8.032 秒 |
| 關連線 | 200／2 | 503／15 | 8.000 秒 |
| code 112 交易衝突 | 200／2 | 503／16 | 8.016 秒 |
| code 91／pool clear | 200／2 | 503／10 | 8.031 秒 |
| commit 結果不明 | 200／1 | 503／1；同 txn commit 17 次 | 8.000 秒 |
| 真 primary 切換 | 200／2 | 未列持續故障案例 | 單次 1.187 秒 |

持續故障前四類在 503 後 28 集合快照與故障前相同。commit 不明案例則**已在 503 前落下一筆訂單**，不誤列回滾；關閉注入後，以原 `checkout_id` 收回同一筆訂單，未重扣庫存。六個單次及五個持續案例全部在恢復後同 ID 重送200、同 order，orders／order_items各1筆、庫存只扣1，異內容409且28集合不變。持續案例的恢復步驟使用**新 MongoClient 模擬新 worker**；早期同一 worker 的 pool 故障恢復曾再回 503，所以不能據此宣稱舊 worker 立刻恢復。工具對後續 503 會以相同 ID 有界重試，這一輪五例均在第一次恢復請求200。[六類單次完整資料](inventory/REN_N06_BOUNDED_SINGLE_MATRIX_2026-10-19.json)／[五類持續完整資料](inventory/REN_N06_BOUNDED_SUSTAINED_MATRIX_2026-10-19.json)。

真本機 replica set 的交易、撤權及工具範圍測試 **22 passed／0 skipped**；全站 website 測試 **272 passed／0 skipped**。兩次測試節點／資料目錄均由工具清理。`git diff --check` 與 repo 檔案政策另以本分支提交前結果為準。

## 與 #103 最新 main 的整合

本輪分支納入 #103 的 N13 固定出口／Cloud Run 記錄、`app/db.py` 每次連線的 2.5 秒 timeout，以及 N14 工具／文件；N06 交易服務與故障工具的重疊處採本報告已驗的 8 秒整體／最多 6 秒單次操作、同 transaction commit 重試及五類持續故障（含 commit 結果不明）。保留 SAM 在 #103 的 08:20 報告作其當時證據，沒有把兩種矩陣混寫成同一次測試。整合後以一次性本機 replica set 跑網站與新 N14 工具測試 **277 passed／0 skipped**，節點已清理。正式站在本輪稍早一度 503、08:29 匿名首頁回200；[公開畫面](../簡報文件/screenshots/REN_H08_手機尺寸模擬_2026-10-19_定稿/S00-public-site-readback.png)只證明該時點 GET。N06 本分支程式仍未部署。

本輪是本機故障注入；尚未做隔離遠端等價矩陣，也未在正式 Atlas 製造中斷。正式服務仍使用既有部署來源，新的重試政策待此分支整合與部署後才能說已在線上生效。N06 技術期限子項已驗，整項仍待遠端範圍與 REN 具名接收；H08 與 V5 2/14 依[實機接收表](REN_H08_DEVICE_MATRIX_AND_RECEIPT_2026-10-19.md)保留。
