# SAM／REN 同映像私有真交易驗收｜2026-10-18 02:10（Asia/Taipei）

正式 Cloud Run `vibecart-web-00015-nlk` 承接 100% 流量；私有隔離 `vibecart-acceptance-pr21-00005-5j5` 承接其服務 100%。兩者來源標籤 `1d2abf2cfa7465636e49474062e11f6aca571dda`、不可變映像 `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b` 相同。私有服務限單一 service account invoker、獨立 `vibecart_acceptance_pr21` 資料庫與該庫 readWrite 帳號；全區清單只有正式與私有兩個 Cloud Run 服務，Job 0、Pub/Sub topic／subscription 0、worker API 0，`me-central2` 因政策限制無法讀取。這是私有服務的實際遠端 HTTP／Atlas 交易，沒有在正式業務庫建立帳號或訂單。

固定範圍腳本先做唯讀盤點，再以限時 `roles/iam.serviceAccountOpenIdTokenCreator` 取得私有服務 ID token；Mongo URI、ID token 與一次性密碼只在程序記憶體／stdin 傳遞。測試建立唯一 `ren-txn-288a7901f41016f8` 標記的會員、商品與 SKU，兩個獨立 cookie session 登入後驗證：

| 驗收項 | 遠端及 Atlas 讀回 |
|---|---|
| 兩裝置／角色 | 同會員 2 筆有效 session；兩裝置購物車可讀；會員後台拒絕。 |
| 加購與結帳 | JSON 加購 200；示範訂單與 1 筆明細持久化，SKU 可用庫存 2→1。 |
| 冪等與衝突 | 相同 checkout ID／內容重送 200，仍只有 1 訂單、1 明細、庫存 1；同 ID 改 revision 得 409，數據未再變。 |
| 個別撤權 | 第一裝置登出後購物車轉登入，第二裝置仍回 200。 |
| 清理 | 訂單／明細各 1、cart 1、cart event 2、behavior event 2、session 1、會員／SKU／商品各 1 清除；九範圍殘留均 0。獨立 Atlas 連接器複查此 marker 的訂單、會員、SKU、商品各 0。 |
| IAM | 探針 finally 撤銷臨時角色；獨立 IAM 讀回 token creator binding 0。 |

[無憑證結果](inventory/sam-remote-transaction-20261018.json)保留 revision、映像、各項結果與清理數字；[Node 固定範圍執行器](../scripts/run_remote_transaction_acceptance_probe.cjs)和[Python 交易探針](../scripts/remote_transaction_acceptance_probe.py)保留可重現來源。早先三輪因測試腳本使用 `/admin` 而非 `/admin/`、JSON 未帶 CSRF header、從空購物車頁抓 CSRF 而提前停止，均未建立訂單；每輪已核對夾具殘留 0 和 IAM 撤權。修正腳本後的上述結果為唯一通過輪次。

本次驗證的是同映像隔離庫的登入、權限、購物、重送與單裝置撤權。rollback 故障注入與最後庫存併發有[前一來源基線 186 項本機測試](SAM_RELEASE_2026-10-18.md)及較早[隔離 Atlas 直接交易](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)證據；新映像只有 CSS 原始檔不同，但這兩項**沒有在本輪新修訂遠端重跑**。正式業務庫的寫入、真付款、真模型、D5 管理寫入、實機與具名簽收仍未完成。
