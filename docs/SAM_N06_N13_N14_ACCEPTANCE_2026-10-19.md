# SAM N06／N13／N14 驗收進度｜2026/10/19 08:51（台灣時間）

本報告只記實際觀察，尚未代填 SAM／REN／JEFF 的具名接收。正式系統逾 10/18 20:00 原期限，本輪仍按 V5 的 N01～N06、N11～N18 共 14 關統計；下階段 N07～N10 排除，**目前仍是 2/14 結案**。

## 08:51 最新同版部署與遠端矩陣

- [PR #103](https://github.com/SamWang61/LLM_PJ/pull/103) 已合併 main `7aeb77c0a615260986d990d37fe699719f3bed1b`，main [CI #541](https://github.com/SamWang61/LLM_PJ/actions/runs/39180827187) 成功。其 56 個已提交部署檔建置成 digest `sha256:c31acb1fb3949995fb7cecb0e56d59f9adee9331826f369f829326dfe1158ca0`，先經私有四案通過及正式100%切換。隨後 [PR #104](https://github.com/SamWang61/LLM_PJ/pull/104) 合併 main `294c1fac26d6785054063b8be6eb7d9e61075be4`，交易重試程式有新差異，main [CI #545](https://github.com/SamWang61/LLM_PJ/actions/runs/39181816375) 成功；因此重新封裝該 SHA 的 56 個已提交部署檔（archive SHA-256 `3998b7b76c546f94eb26348fed2e88af0a43e805455dc4485d8f9ddabd7e295a`），[Cloud Build `97f935ec`](https://console.cloud.google.com/cloud-build/builds;region=asia-east1/97f935ec-399e-4fbb-b6f9-cda90dc697b8?project=278483818008) 成功，產出 digest `sha256:796a42b6d5fd80099900abc381d4c954d21ed1bea162ad0a9a49a89355deb40a`。稍後 main 前進至 `ce50239`，本次比對 `294c1fa..ce50239` 只有文件與 H08 截圖變更，部署執行檔仍對應 `294c1fa`；`38ee951` 的 main [CI #553](https://github.com/SamWang61/LLM_PJ/actions/runs/39182432469) 已成功，最新 `ce50239` 的 [CI #559](https://github.com/SamWang61/LLM_PJ/actions/runs/39183109751) 於本次讀回仍執行中。
- 最新映像先以 0% 候選部署到正式與私有服務；私有一般修訂升 100%，再短暫升私有專用交易 barrier 修訂執行隔離探針。[去敏遠端報告](inventory/SAM_N06_REMOTE_MAIN294_2026-10-19.json)於 08:48～08:49 對**同一 digest**驗證四案：實際 DB 唯一索引錯誤 409 回滾、受控 `AutoReconnect` 503 回滾、`PURCHASE` 寫入途中撤 session 400 回滾、途中停用會員 400 回滾；各自後續拒絕或同 checkout_id 恢復及重送單據。暫時 IAM 已撤除；測試商品、SKU、會員、購物車、訂單、事件、控制列與臨時索引清理讀回均為 0。`AutoReconnect` 是私有受控注入，**不是正式 Atlas 全面斷線證據**。
- 08:50 私有 barrier 已切回一般修訂並移除 0% 測試標籤網址。正式 `vibecart-web-n06-294c-1019`、私有 `vibecart-acceptance-pr21-n06-294c-1019` 均讀回 100%，來源標籤 `294c1fa`、相同 digest `796a42b6…`、專用 VPC `vibecart-egress-20261019` 與 `ALL_TRAFFIC`。正式 Firebase `/`、`/recommendations`、`/auth/login` 各回 200；這只代表該路由與目前讀取可用，不代替人員簽收。N06 仍待 REN 本人覆核及真實遠端任意 Atlas 故障擴展；N13 還須確認其他三條工作站白名單是否仍必要，故兩關暫不逕自結案。

## N13 固定出口與正式站恢復

- Google Cloud `vibecart-llmai/asia-east1` 已啟用 Compute API，建立專用 VPC `vibecart-egress-20261019`、子網 `10.91.0.0/24`、Cloud Router 與手動固定 IP Cloud NAT。保留外部 IP `35.229.228.204`；無機密的臨時 Cloud Run Job 從該 VPC 使用 `ALL_TRAFFIC` 連到外部 IP 回顯，實際讀回同 IP，Job 已刪除。此設定會產生雲端網路費用。
- 08:10 Atlas 唯讀回查只有 3 條舊工作站規則，`0.0.0.0/0` 已不在，正式推薦頁回 503；不能判定規則由誰移除。Atlas 連接器新增規則遭「使用者未確認執行」拒絕，未由工具變更。使用者其後自行加入 `35.229.228.204/32`；08:14 再查為 4 條，其中固定出口 `/32` 在列且萬用規則不存在。
- Cloud Run 私有 `vibecart-acceptance-pr21` 先建 `vibecart-acceptance-pr21-nat-1019` 0% 再升 100%；正式 `vibecart-web` 先建 `vibecart-web-nat-1019` 0%，與舊正式修訂的非網路設定及映像 digest 比對一致，候選 `/`、`/recommendations`、`/auth/login` 各回 200，後升 100%。正式新修訂與舊正式同映像 `sha256:8755ccb82902cf59430d5b2b76505c3fb6e4ed265d0ef98ba42821769edbcbdd`，來源標籤 `b038aaca2d2553a39d8fd958100f277c64a75486`；私有新修訂沿用原私有 100% 映像與來源 `e000d952d22a64b568903641893f4ffdc71accd3`。兩個新修訂均讀回專用 VPC／子網與 `ALL_TRAFFIC`，各自 100%。
- 08:19 切換後公開 `https://vibecart-llmai.web.app/`、`/recommendations`、`/auth/login` 分別 200；`/recommendations` 的應用程式路由會執行 Mongo ping 及多項讀取。08:19:33 後針對**新正式 revision**的 Cloud Logging 唯讀讀回 3 筆 HTTP 200、資料庫不可用記錄 0。這是恢復的技術證據，仍需後續持續觀察、實際登入／交易與人員簽收；私有修訂尚無具權限的 HTTPS 交易重跑。其他三條工作站 `/32` 尚未逐一確認不再需要，未移除。

## N06 故障矩陣

- 基於 [REN #97／#101 初次矩陣](REN_PR97_MERGE_N06_2026-10-19.md)，本分支改交易重試：不再交給 PyMongo `with_transaction()` 固定約 120 秒的重試視窗，而是 8 秒內啟動重試，單次 socket／server selection 各設 2.5 秒上限；commit 結果不明只重試**同一交易的 commit**。新本機三節點真 mongod／Flask WSGI 隔離矩陣：六類單次故障及四類持續故障全通過；持續案例在 8.1～9.3 秒回 503，故障解除後相同 checkout_id 成功 200，重送同單，異內容 409，庫存只扣一次，28 集合回滾／無關集合雜湊相同。[去敏摘要](inventory/SAM_N06_BOUNDED_LOCAL_MATRIX_2026-10-19.json)；詳細清冊僅留 SAM 本機私有目錄。三節點與測試庫均清除。
- 08:20 時最新整合版在可拋棄本機 Docker replica set 跑會員／網站／管理員交易回歸 **287 passed／0 skipped**，容器與測試庫已移除；這是該時點的本機證據。之後的最新正式同版私有遠端四案見上方 08:51 更新；真實遠端全面 Atlas 中斷與 REN 具名接受仍未完成，N06 不結案。

## N14 私有加密備份與異機復原

- 08:05 SAM 的電腦 `ASUS-VIVO-SAM` 對既有 05:28 基底和 15:30 差異／Atlas 兩份密文，使用單獨保存的 32-byte 金鑰完成認證解密與全新 localhost 復原：13,976 檔 hash 差異 0；28 集合／14,691 筆／89 索引／3 TTL，BSON 差異 0；一次性資料庫與 mongod 已清理。完整報告留在私有 `N14_OFFDEVICE_DRYRUN_20261019_0800/recovery-report.json`，未進 GitHub。
- REN 的異機電腦（Windows） 預計 14:00 操作；使用者指定 D:／F: 兩支獨立 USB。08:27 在 SAM 電腦已分別存入加密資料＋13 檔工具包、32-byte 金鑰，實際從 D:／F: 讀回的兩份密文 SHA-256、全部工具檔 SHA-256 與金鑰比對均通過，D: 本次資料夾無金鑰；[操作卡](N14_REN_異機復原_2026-10-19.md)已按實際磁碟代號更新。這仍**不是異機驗證**。F: 為 exFAT，需由 SAM 實體保管並現場收回；每日固定專案 ACL 備份流程仍待落實，N14 不結案。
- 08:35 額外將 Python.org 官方 3.13.13 x64 可攜式執行環境與固定版依賴置於 D:，官方 ZIP SHA-256 已核對；實際由 D: 啟動並載入復原入口，工具包新增後共 962 檔讀回雜湊一致。REN 的異機復原尚未執行，故不將此列為異機成功。
- 08:49～08:54 使用**D: USB上的可攜Python／兩份密文**與**F: USB上的獨立金鑰**，在 SAM 原電腦完成完整同機預演：[去敏結果](inventory/SAM_N14_USB_PORTABLE_SAMEHOST_2026-10-19.json)為 AES-GCM 認證成功、13,976 檔雜湊差異0、Atlas快照28集合／14,691筆／89索引／3TTL／原始BSON差異0，隔離localhost資料庫與mongod均已清理，從未接觸來源資料庫。完整報告另複製留在SAM本機私有目錄。這份成功**不能替代REN異機復原**。本次預演的私有明文測試目的地在 `N14_USB_PORTABLE_DRYRUN_20261019_0850`；自動核准審查拒絕對其遞迴刪除（僅回「blocked by policy」），需SAM在核對報告後由本機手動清理，不宣稱已清除。

## 14:00 人員接收

SAM 預計 14:00 在正式站操作；REN 預計同時在異機電腦（Windows）驗收會員／購物／撤權及異機復原。[逐項空白簽收表](../專題進度/2026-10-19_具名接收與異機復原表.md)保留本人姓名、時間、設備、版本與結果。JEFF 時段仍未知。預約時間不是簽收；手機實機、完整故障矩陣、私有交易復跑、離線排練與最終全站具名簽收仍待真實證據。
