# REN N06 內部故障檢查｜2026/10/19 08:56（台灣時間）

## 檢查基線與範圍

以 08:53 從 GitHub main 取得的 `c538e28aebce6a75fd5a994b625dd9b06a05bd70` 為基線；本輪只做本機隔離檢查與文件補登，未部署服務、未寫入 Atlas。N06 交易服務 `VibeCart_AI/services/cart_service.py` 的 SHA-256 為 `2d78ae601f6cd90077bb152ac5f52a87763785d1e119a7621d23c81ee3934edb`；故障工具的 SHA-256 為 `f4ec2bcc140ac23e0299002b65afd944945175db756284d9d8f762c2d6805219`，與兩份報告相同。

使用本機 Docker `mongo:8`（mongod 8.3.11）、Python 3.12、PyMongo 4.14.1、Flask 3.1.2；每輪建立三個一次性 `127.0.0.1` mongod 節點、獨立 replica set 與測試庫，透過 Flask 本機 WSGI 路由注入故障。工具不接受 Atlas URI；原始報告明記 `atlas_accessed=false`、`remote_acceptance=false`，每輪完成後 `processes_stopped=true`、`fixtures_removed=true`。

## 實測結果

| 故障 | 單次故障 HTTP／耗時 | 持續故障 HTTP／耗時 | 故障解除後 |
|---|---:|---:|---|
| socket timeout | 200／6.088 秒 | 503／8.006 秒 | 同 checkout ID 200；重送同單；異內容 409 |
| 連線重置 | 200／0.331 秒 | 503／8.004 秒 | 同上 |
| code 112 交易衝突 | 200／0.187 秒 | 503／8.005 秒 | 同上 |
| code 91／pool clear | 200／0.352 秒 | 503／8.003 秒 | 同上 |
| commit 結果不明 | 200／0.326 秒 | 503／8.003 秒 | 同一交易重試 commit；同 checkout ID 找回同單 |
| 真 primary 切換 | 200／1.149 秒 | 本輪未列持續案例 | 同 checkout ID 200；重送同單；異內容 409 |

六個單次與五個持續案例均 `passed`；恢復後 orders／order_items 各一筆、庫存只扣一次、無關集合雜湊不變，總共覆核 28 個集合。持續故障前四案在 503 時回滾一致；commit 不明案在 503 前可能已提交，故以同一操作識別碼找回，**不把已提交案例誤寫為回滾**。持續故障的恢復步驟使用新的 MongoClient 模擬新 worker，不能因此宣稱原 worker 的連線池即刻恢復。

[六案原始 JSON](inventory/REN_N06_INTERNAL_SINGLE_2026-10-19.json) SHA-256 `46f9ad062360fbf2abe074ab4d9865827ce8376ae3fe1bf13fe3c1e5229a7fd5`；[五案原始 JSON](inventory/REN_N06_INTERNAL_SUSTAINED_2026-10-19.json) SHA-256 `b69121b3443ddf3738d191685804df9619280dcd33e251c8c6c1a57dbf112906`。兩輪皆由工具確認節點停止、fixture 移除。另有相同交易程式來源的 [GitHub PR #107 CI #555](https://github.com/SamWang61/LLM_PJ/actions/runs/39182672114) 成功，含網站離線測試及真本機 MongoDB 交易檢查；本報告的故障矩陣為本輪另外執行，並非該 CI 的輸出。

## 待辦與證據界線

這次確認 N06 的**內部故障矩陣**通過，尚未完成同版私有遠端 HTTPS／Atlas 故障矩陣、正式流量版本對帳或 REN 本人具名接收；N06 仍列待結案，V5 仍為 2/14。較早[正式 N06 修訂版 08:45 讀回](CURRENT_CONTEXT.md)記錄的 Cloud Run 來源為 `7aeb77c`，與本輪 main 基線不同，不把本機結果冒稱該正式映像的交易驗收。

同輪依使用者澄清，重新核對[H01～H09 原始截圖](../簡報文件/screenshots/REN_H01-H09_手機模擬_2026-10-18/README.md)：12 張 JPEG 均是未編修、實際擷取的頁面截圖，雜湊與取圖索引相同；8 張公開網站、4 張本機隔離頁面。取圖設備環境是桌面瀏覽器的手機尺寸視窗，並非 iPhone 實機畫面；來源區分已補入原截圖說明。
