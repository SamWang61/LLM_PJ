# SAM N06／N13／N14 驗收進度｜2026/10/19 08:20（台灣時間）

本報告只記實際觀察，尚未代填 SAM／REN／JEFF 的具名接收。正式系統逾 10/18 20:00 原期限，本輪仍按 V5 的 N01～N06、N11～N18 共 14 關統計；下階段 N07～N10 排除，**目前仍是 2/14 結案**。

## N13 固定出口與正式站恢復

- Google Cloud `vibecart-llmai/asia-east1` 已啟用 Compute API，建立專用 VPC `vibecart-egress-20261019`、子網 `10.91.0.0/24`、Cloud Router 與手動固定 IP Cloud NAT。保留外部 IP `35.229.228.204`；無機密的臨時 Cloud Run Job 從該 VPC 使用 `ALL_TRAFFIC` 連到外部 IP 回顯，實際讀回同 IP，Job 已刪除。此設定會產生雲端網路費用。
- 08:10 Atlas 唯讀回查只有 3 條舊工作站規則，`0.0.0.0/0` 已不在，正式推薦頁回 503；不能判定規則由誰移除。Atlas 連接器新增規則遭「使用者未確認執行」拒絕，未由工具變更。使用者其後自行加入 `35.229.228.204/32`；08:14 再查為 4 條，其中固定出口 `/32` 在列且萬用規則不存在。
- Cloud Run 私有 `vibecart-acceptance-pr21` 先建 `vibecart-acceptance-pr21-nat-1019` 0% 再升 100%；正式 `vibecart-web` 先建 `vibecart-web-nat-1019` 0%，與舊正式修訂的非網路設定及映像 digest 比對一致，候選 `/`、`/recommendations`、`/auth/login` 各回 200，後升 100%。正式新修訂與舊正式同映像 `sha256:8755ccb82902cf59430d5b2b76505c3fb6e4ed265d0ef98ba42821769edbcbdd`，來源標籤 `b038aaca2d2553a39d8fd958100f277c64a75486`；私有新修訂沿用原私有 100% 映像與來源 `e000d952d22a64b568903641893f4ffdc71accd3`。兩個新修訂均讀回專用 VPC／子網與 `ALL_TRAFFIC`，各自 100%。
- 08:19 切換後公開 `https://vibecart-llmai.web.app/`、`/recommendations`、`/auth/login` 分別 200；`/recommendations` 的應用程式路由會執行 Mongo ping 及多項讀取。08:19:33 後針對**新正式 revision**的 Cloud Logging 唯讀讀回 3 筆 HTTP 200、資料庫不可用記錄 0。這是恢復的技術證據，仍需後續持續觀察、實際登入／交易與人員簽收；私有修訂尚無具權限的 HTTPS 交易重跑。其他三條工作站 `/32` 尚未逐一確認不再需要，未移除。

## N06 故障矩陣

- 基於 [REN #97／#101 初次矩陣](REN_PR97_MERGE_N06_2026-10-19.md)，本分支改交易重試：不再交給 PyMongo `with_transaction()` 固定約 120 秒的重試視窗，而是 8 秒內啟動重試，單次 socket／server selection 各設 2.5 秒上限；commit 結果不明只重試**同一交易的 commit**。新本機三節點真 mongod／Flask WSGI 隔離矩陣：六類單次故障及四類持續故障全通過；持續案例在 8.1～9.3 秒回 503，故障解除後相同 checkout_id 成功 200，重送同單，異內容 409，庫存只扣一次，28 集合回滾／無關集合雜湊相同。[去敏摘要](inventory/SAM_N06_BOUNDED_LOCAL_MATRIX_2026-10-19.json)；詳細清冊僅留 SAM 本機私有目錄。三節點與測試庫均清除。
- 最新整合版在可拋棄本機 Docker replica set 跑會員／網站／管理員交易回歸 **287 passed／0 skipped**，容器與測試庫已移除。這些是**本機新版**，不是已部署映像；完整同版私有遠端、Atlas 故障與交易中撤權矩陣仍須重新測試並由 REN 具名覆核，N06 不結案。

## N14 私有加密備份與異機復原

- 08:05 SAM 的電腦 `ASUS-VIVO-SAM` 對既有 05:28 基底和 15:30 差異／Atlas 兩份密文，使用單獨保存的 32-byte 金鑰完成認證解密與全新 localhost 復原：13,976 檔 hash 差異 0；28 集合／14,691 筆／89 索引／3 TTL，BSON 差異 0；一次性資料庫與 mongod 已清理。完整報告留在私有 `N14_OFFDEVICE_DRYRUN_20261019_0800/recovery-report.json`，未進 GitHub。
- REN 的第二台 Windows ASUS VivoBook 預計 14:00 操作；使用者指定 D:／F: 兩支獨立 USB。08:27 在 SAM 電腦已分別存入加密資料＋13 檔工具包、32-byte 金鑰，實際從 D:／F: 讀回的兩份密文 SHA-256、全部工具檔 SHA-256 與金鑰比對均通過，D: 本次資料夾無金鑰；[操作卡](N14_ASUS_VIVOBOOK_異機復原_2026-10-19.md)已按實際磁碟代號更新。這仍**不是異機驗證**。F: 為 exFAT，需由 SAM 實體保管並現場收回；每日固定專案 ACL 備份流程仍待落實，N14 不結案。
- 08:35 額外將 Python.org 官方 3.13.13 x64 可攜式執行環境與固定版依賴置於 D:，官方 ZIP SHA-256 已核對；實際由 D: 啟動並載入復原入口，工具包新增後共 962 檔讀回雜湊一致。REN 的 ASUS 尚未執行，故不將此列為異機成功。

## 14:00 人員接收

SAM 預計 14:00 在正式站操作；REN 預計同時在第二台 ASUS VivoBook（Windows）驗收會員／購物／撤權及異機復原。[逐項空白簽收表](../專題進度/2026-10-19_具名接收與異機復原表.md)保留本人姓名、時間、設備、版本與結果。JEFF 時段仍未知。預約時間不是簽收；手機實機、完整故障矩陣、私有交易復跑、離線排練與最終全站具名簽收仍待真實證據。
