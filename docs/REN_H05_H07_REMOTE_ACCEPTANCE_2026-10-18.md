# REN H05～H07 遠端技術驗收｜2026-10-18

狀態：**H05～H07 指定遠端技術案例通過**。16:49～16:55 的[恢復成功紀錄](inventory/REN_H05_H07_REMOTE_RECOVERY_2026-10-18.json)及 16:55 [獨立回查](inventory/REN_H05_H07_RECOVERY_CLEANUP_2026-10-18.json)已完成；另以固定工具版本重跑，最終結果見下方交付紀錄。真人接收欄仍待本人填寫。

## 版本與隔離範圍

- 本輪 Git 基線：`20ee040110cbd6f02abb35aefde532a54d2fb120`（PR #84 合併後）。
- 實際驗收部署來源：`e000d952d22a64b568903641893f4ffdc71accd3`。
- 正式 `vibecart-web-00019-phf`、私有 `vibecart-acceptance-pr21-00011-2hq` 各 100% 流量，映像皆為 `sha256:7199fa08c711917a80e5f54dbfd580ed96f3ef632bda7337b4aa2bde2325c992`。
- 實際 HTTPS 呼叫私有服務；僅使用 `vibecart_acceptance_pr21` 與其限定 readWrite 帳號，新建商品／SKU／會員均有唯一 marker，測後刪除。正式購物車、訂單、庫存與 D1～D4 不寫入、不重匯。
- main 後續增加推薦行為範圍等 JEFF 變更；本報告只驗證上述實際部署，不宣稱 main 新功能已部署。購物交易與事件寫入路由契約可直接對照該來源。

## 阻礙與處理

[前置讀回](inventory/REN_H05_H07_PREFLIGHT_2026-10-18.json)記錄既有使用者 ID token 呼叫私有登入為 401，服務帳號取 token 為 403／`IAM_PERMISSION_DENIED`。使用者明確允許這次直接探針暫授 `cashsam@gmail.com` 對指定驗收服務帳號的 `roles/iam.serviceAccountOpenIdTokenCreator`，最多 20 分鐘，測後立即撤銷。這次不重啟先前遭自動核准審查拒絕的瀏覽器代理。

[首次直接嘗試](inventory/REN_H05_H07_REMOTE_FIRST_ATTEMPT_2026-10-18.json)於 16:41 啟動，IAM 傳播 9 次後取得憑證；登入後頁面傳輸 ReadTimeout，尚未完成 H05。當輪九範圍均清理讀回 0、臨時 IAM 已撤銷。16:44 Cloud Logging 唯讀診斷顯示已收到的 GET `/` 於 08:43:21Z 回 200、耗時 1.505 秒，其他登入／購物車約 1～2 秒；這支持用戶端回應鏈路不穩的判斷，沒有把該輪列為驗收通過。

補強 `page()`：僅針對 GET 傳輸例外，最多 3 次、連線 10 秒／讀取 45 秒，清掉舊連線並保留 cookie；不自動重送 POST，錯誤只留路徑／例外型別。讀取重試可能多產生 SEARCH／PRODUCT_VIEW，因此以事件唯一 ID、型別及關聯驗證，不以固定讀取次數冒稱恰一次。重試權限仍固定於原期限 **17:01:18.897（台灣時間）**，不重新延長 20 分鐘。

[第二次嘗試](inventory/REN_H05_H07_REMOTE_SECOND_ATTEMPT_2026-10-18.json)仍在登入回應傳輸 ReadTimeout；建立 2 個一次性 session、未進入購物車變更，九範圍清理讀回 0、IAM 撤銷。Cloud Run 兩個 login POST 均約 1.4 秒回 302，本機 requests 2.34.2／OpenSSL 3.5.7 沒有環境 proxy；完整傳輸根因尚未定位，不把逾時歸咎為 Atlas 或業務交易失敗。

H05～H07 模式改用 Node 24.16.0 直接 HTTPS：每個請求經 stdin/stdout 子程序管線交換，Python requests 繼續處理 cookie／redirect；Node每次請求整體上限60秒、Python子程序監督65秒；不開本機監聽埠。僅接受既定私有 hostname、TLS 驗證保持開啟；遇其他 hostname、代理設定或停用 TLS 驗證即拒絕。GET 可有限重試，POST 每次只送一次；舊 cookie 重播也保留相同傳輸介面。匿名實際 GET 為 403，沒有將私有服務公開。此變更只改驗收工具，未部署應用程式。

第三輪期間進一步將子程序在回應寫出後確實結束，避免等待閒置連線；DNS 也改為同網域 IPv4 優先，未覆寫位址或關閉 TLS。新增含常駐 handle 的離線重現測試，驗證子程序確實 flush／退出。只記錄 method、path、時間、狀態與大小的傳輸紀錄不含 query、cookie、header 或帳密。因第三輪曾調整工具收尾，另以固定七個執行檔 hash 重跑，並核執行前後 hash 一致。

## H05～H07 結果

| 項目 | 實際步驟及證據 | 結果 |
|---|---|---|
| H05 購物車 | 加入 2→改 1→重載→以舊 revision 修改→移除→重載空車→重新加入 1；Atlas 對帳 items／revision／cart_events | 通過：四個變更均 200，revision 1→2→3→4；舊 revision 409，資料不變 |
| H06 結帳 | 不收款訂單與明細、庫存扣減、相同 checkout_id 重送、不同 revision 409、最後一件兩客戶競爭、第二 SKU 缺貨後第一 SKU 與全集合回滾 | 通過：checkout／重送均 200，衝突 409；競爭一個 200／一個 400、庫存 0；缺貨 400、首 SKU／revision 保留，orders 2／items 2／behavior 9／cart_events 9 前後相同 |
| H07 四事件 | 真實 HTTPS 產生 SEARCH／PRODUCT_VIEW／ADD_TO_CART／PURCHASE；核 schema、唯一 event_id、session、會員／商品／購物車／訂單關聯、demo purchase 歸因排除 | 通過：依序 1／1／2／1；ADD 有兩次有效加入，PURCHASE 重送未重複 |
| H07 consumer | 另一組隔離 fixture：正常事件 1 筆使後台／推薦變化，synthetic 1,001 筆不增加後台筆數、不改推薦；讀完清理 | 通過：後台 13→14→14；正常事件改推薦，synthetic 後推薦不變 |

## 清理、交付與界線

交易探針九個清理範圍全部剩餘 0，consumer 五個範圍全部剩餘 0；兩次失敗也清理完畢。獨立回查另核四個交易 marker 與兩個 consumer marker 的 users／products／product_skus、訂單 checkout 前綴、cart operation 前綴及 consumer event marker，全為 0；本輪臨時 IAM binding **0**，既有 invoker 授權維持原狀。獨立 marker 回查與原探針的完整相依集合清理各有列明範圍，不擴稱重新掃過所有相依資料。憑證、URI、帳密均只在記憶體／子程序 stdin，不寫入 Git。

本輪不改寫[手機尺寸截圖](REN_MOBILE_H01_H09_2026-10-18.md)的 localhost 來源；遠端 HTTP／Atlas 證據另存。06:36～06:38 的受控資料庫錯誤／交易中撤權仍依[原始故障報告](../專題進度/REN_0900展示帳號與故障驗收_2026-10-18.md)時間記錄；[原 JSON](inventory/REN_REMOTE_FAULT_FIXED_2026-10-18.json)為 private revision 9 的暫時 barrier entrypoint，這次 revision 11 為正常入口，沒有冒稱重新注入。正式 D4 1,240／四類各 310 的唯讀數據仍依[11:17 原讀回](inventory/ren_handoff_20261018/public-verification.json)時間；本輪驗的是新隔離四事件與 consumer，不重匯正式 D4。真實 Atlas outage、擴大故障矩陣、手機實機、[陳仁千（REN）](mailto:chen2000401@gmail.com)本人接收及展示後帳號回收仍各自待辦；V5 維持 **2/14 完成、12 項待結案**。

交付順序：[REN](mailto:chen2000401@gmail.com)依[H05～H07 接回欄](../專題進度/REN_1200逐項交接清單_2026-10-18.md)具名覆核→[JEFF](mailto:jeff841117@gmail.com)接事件介面／consumer→[SAM](mailto:cashsam@gmail.com)維持資料庫、故障矩陣及展示後回收。Codex 技術執行紀錄不代簽本人接收。

## 重跑與本機檢查

入口 `scripts/run_remote_transaction_acceptance_probe.cjs --run-h05-h07-isolated` 只執行固定兩支私有探針。需要該次有效授權及既有 Firebase CLI 身分；預設不帶參數為唯讀。`REN_IAM_DEADLINE` 可限制重試仍使用既定期限；超過未來 20 分鐘／已過期／格式錯誤直接拒絕。H05～H07 模式只接受既有指定 service account 與可選的指定維運使用者作 invoker，拒絕公開、其他使用者、重複或條件式 invoker；不修改現行 invoker。

本機範圍／清理／事件／GET 重試／直接傳輸檢查：Python **30 passed**、Node **9 passed**；[檢查清冊](inventory/REN_H05_H07_LOCAL_CHECKS_2026-10-18.json)，新增檢查已納入 GitHub CI。交付分支 `codex/ren-h05-h07-remote-20261018`，CI／PR 狀態以 GitHub 該分支最新 HEAD 為準。

## 固定版本最終交付

16:56 起完整重跑，16:58:03輸出最終結果（檔案mtime記錄），17:05完成獨立回查；已取得[最終遠端通過結果](inventory/REN_H05_H07_REMOTE_2026-10-18.json)與[最終獨立清理](inventory/REN_H05_H07_INDEPENDENT_CLEANUP_2026-10-18.json)。上述表格的H05／H06／H07結果均再次通過；七個執行檔在執行前後無變更，[SHA-256清冊](inventory/REN_H05_H07_SOURCE_2026-10-18.json)有完整hash。本輪所有臨時權限皆在原17:01:18.897期限內撤銷，正式／私有流量與映像讀回未變。
