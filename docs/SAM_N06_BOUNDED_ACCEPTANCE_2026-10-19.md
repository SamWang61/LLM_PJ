# N06 持續故障請求期限與具名技術驗收

更新：2026/10/19（Asia/Taipei）。執行／已驗範圍接受者：[汪文彥（SAM）](mailto:cashsam@gmail.com)。REN 本人接收仍待其本人記錄。

## 原因與修正

REN 原始故障矩陣發現，外層 `pymongo.timeout(2)` 未能把 `session.with_transaction()` 的內部重試限制在兩秒：四種持續故障約 120 秒才返回，並反覆執行交易 callback。原始數值與來源保留在 [REN 初輪報告](REN_PR97_MERGE_N06_2026-10-19.md)；PyMongo 的 [`with_transaction` 文件](https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html)載明其交易重試可持續至 120 秒，故改以 v4 購物車服務自行控制交易。

- 每個請求的交易與 commit 重試時間上限為 **1.5 秒**；在此範圍內，對明確的伺服器端暫時性交易錯誤採 25、50、100、200 毫秒（最高 200 毫秒）退避。這是程式內的交易期限，不代表整個 HTTP 請求一定在 1.5 秒完成。
- 交易期限結束後，使用**獨立的 1 秒**期限盡力送出 `abortTransaction`。這可避免過期的同一 CSOT context 阻止 abort 送達，讓同一 `checkout_id` 在故障解除後即時重送。commit 結果不明時不能假定已回滾；先重試**同一 session／transaction**的 commit，最後回 503 供同 ID 查清結果。
- 插入時連線遺失、socket reset 或 pool 故障等網路結果不明，不在伺服器端重跑整個 callback；回可重試的 503，由呼叫端用**同一 `checkout_id`**重送。這防止前次交易尚未終止時在新交易重複寫入或持續碰撞。
- 本機 N06 驗收門檻：三節點一次性 replica set 上，單次與持續故障的**每個受測請求須小於 3 秒**；持續故障須 503、callback 少於 40 次、故障撤除後同 ID 恢復、相異內容 409。這是本機觀察門檻，**尚非正式 HTTPS 服務 SLO**。

## 實際矩陣與結果

測試只啟動本輪三個無憑證 `127.0.0.1` mongod，對此一次性應用的命令注入 failpoint。請求走真 Flask `/checkout` 路由與真 replica set；前後讀回 28 集合的筆數與 SHA-256、訂單／事件／庫存，然後關閉本輪節點並清除其資料目錄。未連 Atlas、未部署、未改正式庫。

| 故障 | 單次回應／秒 | 持續回應／秒 | 故障解除後同 ID | 特別核對 |
| --- | ---: | ---: | --- | --- |
| 網路逾時 | 503／2.531 | 503／2.437 | 200 | callback 各 1 次；不盲目重跑 |
| socket reset | 503／0.203 | 503／0.172 | 200 | pool clear、單次 callback |
| 112 寫入衝突 | 200／0.203 | 503／1.500 | 200 | 單次重試 2 次；持續重試 6 次 |
| 91 pool 故障 | 503／0.250 | 503／0.203 | 200 | pool clear、單次 callback |
| commit 結果不明 | 200／0.234 | 503／1.625 | 200 | 同交易重試 commit，callback 各 1 次 |
| 真正 primary 切換 | 200／1.172 | 未注入 | 200 | 三節點 primary 前後不同、callback 2 次 |

兩輪全部案例通過；同 ID 再送回原訂單 200、異內容／版本回 409，庫存僅扣一次，無關集合前後相同。持續故障除 commit 結果不明外，28 集合故障後快照等於前值；commit 結果不明只能以同 ID 恢復證明未重複落單，不能把 503 當成 rollback 證據。單次／持續原始命令、failpoint、快照及清理回條分別在 [單次 JSON](inventory/SAM_N06_SINGLE_FAULT_2026-10-19.json) 與 [持續 JSON](inventory/SAM_N06_SUSTAINED_FAULT_2026-10-19.json)。[SHA-256 清單](inventory/SAM_N06_BOUNDED_ACCEPTANCE_2026-10-19.json)用於核對來源與兩份報告。

以相同修正來源及另建的三節點本機 replica set 跑完整網站測試：**274 passed／0 skipped**，90.70 秒，測試節點清理完成。首輪把多個節點寫進 `REN_TEST_MONGO_URI`，13 項在 fixture 的「只接受單一 localhost 種子位址」檢查中止（其餘 261 passed）；改用同一 replica set 的單一種子位址後全數通過，首輪不計最終驗收。

## 具名接受與保留項

- 2026/10/19 08:10（Asia/Taipei），使用者在本對話以「**我以 SAM 身分接受已驗範圍**」回覆，接受對象限於本報告的**本機請求期限、回滾、同 ID 重送**技術證據；具名者記為汪文彥（SAM）。接受不等於聲稱本人操作 REN 交接，也不代簽 REN。
- 本輪尚未把修正後的來源部署至無流量預覽或正式服務，因此**沒有修正後同版遠端延遲與 Atlas 全面中斷的驗收**。此前私有遠端受控資料庫錯誤／撤權案例屬先前映像，不能算這一版的遠端故障矩陣。不得在正式 Atlas 製造全面停機。
- N06 保留待結案：由 REN 本人記錄接收姓名、時間、版本、逐項結果；隔離遠端對等矩陣及更廣 outage 情境按安全方案另驗。正式流量、D1～D4、庫存基線不因本輪修改；V5 完成數仍為 **2／14**。

## 重現與發布界線

需有本機 `mongod` 與 Python 依賴，對**一次性 localhost**執行 `python scripts/run_local_checkout_fault_matrix.py --mongod <本機 mongod 路徑> --report <新 JSON 路徑>`，再加 `--sustained` 跑持續組。工具拒絕覆寫既有報告，且只建立自己命名的資料庫與本輪節點。報告中的 `remote_acceptance=false`、`atlas_accessed=false` 為驗收邊界。此 PR 推送只交付程式與證據；GitHub CI 與實際遠端內容須在推送後另行核對。
