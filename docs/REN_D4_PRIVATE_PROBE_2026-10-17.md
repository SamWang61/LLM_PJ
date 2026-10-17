# REN／SAM D4 私有 consumer 對照探針｜2026-10-17

狀態：**程式已備妥，尚未執行遠端驗收；D4 閘門仍關閉。** SAM 在 REN 24 小時代班期間接續此項。正式批次不可當探針，D1～D3 不重匯。

## 目標與資料範圍

本探針只允許連至 `vibecart-ai-free.odqe25w.mongodb.net/vibecart_acceptance_pr21`，帳號須為只對該庫具 `readWrite` 的 `sam_pr21_acceptance_20261017`；HTTP 目標只允許 `vibecart-acceptance-pr21-*.a.run.app` 私有服務。腳本在程序記憶體接收短期 ID token 與 Mongo URI，不接受正式 `vibecart_ai` URI，也不將憑證寫入檔案、命令列或輸出。

隔離庫現有一件 active 商品但 SKU 庫存已為 0，因此探針會**新增兩件自己標記的可販售商品／SKU**，沿用既有驗收分類 ID，不修改其他夾具；另建一位測試會員、一位測試管理員。先讀管理員推薦監控和會員前台推薦基線，再加一筆正常 `PRODUCT_VIEW`，確認管理員計數加一、前台推薦改變。之後加 **1,001 筆較新的 synthetic `PRODUCT_VIEW`** 到另一商品，超過監控的 1,000 筆和前台的 50 筆 limit；兩端結果都必須維持正常事件之後的值，證明查詢在排序／limit 前排除合成事件。任何錯誤都嘗試依唯一 `probe_id` 與新建 ID 刪除本次事件、session、帳號、SKU、商品，並讀回殘留數。清理未證實為 0 時必須標為 `cleanup_failed`，先處理隔離庫殘留，不得繼續 D4。

## 執行前置與命令

1. 重查正式與私有 Cloud Run revision、映像 digest、私有 invoker、全部部署 consumer／Job／Scheduler 清單。需確認私有服務與正式站承接的 consumer 為同版；先前 [PR #38](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)只記錄 16:06 的部署快照。
2. 本機 Firebase CLI 現顯示 `cashsam@gmail.com` 已登入，但對私有驗收 service account 產生短期 ID token 的權限尚未恢復。先前供交易驗收用的 `serviceAccountTokenCreator` 已撤銷；本次呼叫 Google API 取得 ID token 回 `HTTP 403`，在讀取 Secret Manager 或連接資料庫前即停止，**沒有探針資料寫入**。若需重授權，須限時授予並於測後撤銷；目前等待此項明確授權。
3. 在乾淨工作樹執行 `node scripts/run_remote_d4_consumer_probe.cjs`。它只在記憶體讀 Secret Manager `vibecart-pr21-acceptance-mongo-uri` 版本 1、取得私有服務 ID token，再以 stdin 將憑證交給 `scripts/remote_d4_consumer_probe.py`。可設定 `REN_PYTHON` 指向已安裝 `requests`、`beautifulsoup4`、`pymongo`、`werkzeug` 的 Python；不要把 URI／token 放入環境變數或命令列參數。
4. 保存 JSON 輸出中的 revision、image、基線／正常／synthetic 計數、商品 ID、逐集合清理筆數與 `*_remaining=0`、`verified=true`；再以 Atlas 連接器唯讀複查 `probe_id`。報告沒有密碼、token、URI 或測試帳號密碼。

這支探針只檢查已部署的前台推薦與管理員監控；評分排程、正式歸因及其他 consumer 仍須用[部署清單](D4_DEPLOYED_CONSUMER_INVENTORY_2026-10-17.md)逐項重查。兩端通過也不直接授權 D4 apply；需先完成正式流量同版核對、全 consumer 隔離證據、正式 preflight、交易 dry-run，之後才可 apply、讀回與重送冪等驗證。

## 本次靜態檢查

`remote_d4_consumer_probe.py` 通過 `py_compile`，`run_remote_d4_consumer_probe.cjs` 通過 `node --check`；以錯誤的非驗收 URI 執行時在連線前退出，回報 `RuntimeError`，沒有資料庫操作。這些不是遠端 consumer 通過證據。
