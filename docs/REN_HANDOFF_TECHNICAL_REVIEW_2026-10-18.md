# REN 接回技術覆核｜2026-10-18

**後續更新**：[PR #79](https://github.com/SamWang61/LLM_PJ/pull/79)已依使用者授權審查並合併 main `66a3b89`；[H01～H09手機尺寸模擬補件](REN_MOBILE_H01_H09_2026-10-18.md)另記本輪截圖與限制。H05～H07新圖採本機記憶體 UI fixture，與下方208項真localhost replica set證據分開；各份原始測試／部署時間保持不變。

本輪依使用者指定的 [REN](mailto:chen2000401@gmail.com) 工作角色，由 Codex 執行可重現的技術覆核，GitHub 帳號為 `SamWang61`。最新使用者計畫為 **2026/10/18 12:00（台灣時間），由[陳仁千（REN）](mailto:chen2000401@gmail.com)接手後續工作**，詳見[12:00逐項交接表](../專題進度/REN_1200逐項交接清單_2026-10-18.md)。這是預定接收安排；原SAM暫代上限11:10不自動延長，本文件的自動測試及畫面核對欄不代填人員簽名。本輪 14 關卡統計仍為 **2 完成、12 待結案**。

## 版本與環境

- 受測 main：`0b742bab73d9a99e28602a7b11dfd52e29cd40d9`（PR #78 合併後）。[51 個執行來源](inventory/ren_handoff_20261018/source-comparison.json)與已部署 `e000d952d22a64b568903641893f4ffdc71accd3` 的 Git blob 差異 **0**；各檔 SHA-256 已保存。
- 11:15 台灣時間的[部署讀回](inventory/ren_handoff_20261018/deployment.json)：正式 `vibecart-web-00019-phf` 與私有 `vibecart-acceptance-pr21-00011-2hq` 各 100%，映像均為 `sha256:7199fa08c711917a80e5f54dbfd580ed96f3ef632bda7337b4aa2bde2325c992`。本輪沒有部署或切流量。
- Git 2.45.1、Python 3.12.8、Node 24.16.0 可用。Docker Desktop 4.82.0 啟動曾依序遇到 Inference／Secrets Engine 的本機 socket 存取錯誤；`Docker/run` 已保留為 `run.ren-stale-20261018-111644` 並重建。終段獨立 `docker info` 已讀到 **Engine 29.6.1 ready**，其間另有 Desktop 啟動，因此不將恢復原因只歸於本輪處理。[環境紀錄](inventory/ren_handoff_20261018/environment.json)保留前後狀態；同型態錯誤參考 [Docker issue #448](https://github.com/docker/desktop-feedback/issues/448)。

## 本輪實際驗證

| 範圍 | 預期及實際結果 | 證據 |
|---|---|---|
| H01 本機重現 | 用新建、無憑證、只綁 `127.0.0.1` 的 MongoDB 8.0.20 replica set 執行網站與現有交易套件：**208 passed、0 skipped、0 failures、0 errors**。剩餘庫只有 admin／config／local；測試程序停止、暫存資料清除。 | [JSON](inventory/ren_handoff_20261018/local-transactions.json)、[JUnit](inventory/ren_handoff_20261018/transactions.xml) |
| H02 雙 session／登入回 cart | 公開 Hosting 使用既有短期 customer 帳號建立兩個獨立 HTTPS cookie session；兩次登入均 302 回 `/cart`，兩者 cart 均 200。登出第一個後，該 session 與舊 cookie 都 302，另一個仍 200；最後第二個正常登出後亦 302。這是兩個 HTTP session，實體裝置操作仍待接收。 | [雙 session 報告](inventory/ren_handoff_20261018/public-dual-session.json) |
| H03 角色與單裝置登出 | 既有 customer：登入 302、cart 200、admin 302；既有 admin：登入 302、cart 200、admin 200。兩者均正常單裝置登出 302，之後 cart 302；該次資料庫讀回各 sessions=0。僅撤銷本次裝置，保留並行持有人的 session。 | [公開角色驗證](inventory/ren_handoff_20261018/public-verification.json) |
| H04 S03 商品／SKU | 正式瀏覽器選中 `CF-SKU-1210303000104`，畫面與 11:17 Atlas 查詢皆為 **NT$79.00／庫存95／active**。Tab 從規格移到 quantity，焦點框可見；當下 innerWidth／scrollWidth 都為 1140。 | [價庫畫面](inventory/ren_handoff_20261018/S03-current-price.jpg)、[原始圖與 hash](inventory/ren_handoff_20261018/screenshots.json)、[Atlas 讀回](inventory/ren_handoff_20261018/public-verification.json) |
| H05～H06 購物與一致性 | 本輪 208 項本機測試通過；既有同執行來源的私有正常交易與四項受控錯誤報告仍可追溯。遠端故障取證時間保持 06:36～06:38，未改稱本輪重跑。正式庫本輪未 checkout。 | [既有正常報告](inventory/REN_NORMAL_REMOTE_ACCEPTANCE_2026-10-18.json)、[既有受控故障](inventory/REN_REMOTE_FAULT_FIXED_2026-10-18.json) |
| H07 事件／D4 | 正式庫唯讀讀回 D4 **1,240**，ADD_TO_CART／PRODUCT_VIEW／PURCHASE／SEARCH 各 **310**，全部 1,240 筆的 synthetic 與 exclude_from_attribution 標記齊全。D1～D4 不重匯，庫存維持查詢值。 | [資料讀回](inventory/ren_handoff_20261018/public-verification.json) |
| H08 S03～S05 素材 | 補本輪正式 S03 原始 JPEG；既有 S04 圖顯示隔離會員已登入及空 cart，S05 圖顯示示範訂單成功／未串接付款。兩張既有 PNG 與原索引 hash 相同；仍標示 `ff65eae`／正式18、私有07的歷史來源。 | [歷史圖核對](inventory/ren_handoff_20261018/historical-image-review.json)、[原素材索引](../簡報文件/screenshots/S01-S12_同版取證_2026-10-18.md) |
| H09 展示帳號 | 既有兩個短期角色仍可登入，期限仍為 **20:30 台灣時間**；本輪沒有建立副本或延長期限。密碼只從原 DPAPI 私有保管位置在記憶體使用，未進文件、命令列或畫面。 | [帳號報告](inventory/ren_handoff_20261018/public-verification.json) |

本機第一次 bootstrap 因初始化前指定 replica set 名稱而未進入 pytest，程序與暫存資料已清理；修正為先用 direct connection 初始化、再使用 replica set URI 後得到上述 208／0。[首次紀錄](inventory/ren_handoff_20261018/local-bootstrap-first-attempt.json)保留。測試命令為網站目錄下 `python -m pytest ../../scripts/test_admin_audit_migration.py tests -q -p no:cacheprovider --junitxml=<report>`；URI 僅經該測試程序的 `REN_TEST_MONGO_URI`／`D5_TEST_MONGO_URI` 指向新建 localhost，未用 Atlas 執行此套件。

Atlas 連接器本輪回覆需重新驗證；商品及 D4 查詢改由正式應用程式既有受限憑證在記憶體連線。上述公開登入會建立並正常登出自己的 session；商品、庫存與 D4 部分為唯讀查詢。本輪沒有新增 IAM 授權。

## 交接結案仍需的紀錄

1. 預定接收人[陳仁千（REN）](mailto:chen2000401@gmail.com)依[12:00 H01～H09 表](../專題進度/REN_1200逐項交接清單_2026-10-18.md)逐項填實際接收姓名、台灣時間、版本、步驟／結果與剩餘問題。預定12:00與技術執行時間都不當作人員實際接收時間。
2. [REN](mailto:chen2000401@gmail.com) 補手機實機型號／OS／瀏覽器、會員購物與錯誤／鍵盤操作紀錄；S03 本輪是桌面，既有 390px 圖仍是窄視窗。
3. [REN](mailto:chen2000401@gmail.com)／[SAM](mailto:cashsam@gmail.com) 依既有故障報告確認可接受範圍；真實 Atlas outage、網路／commit 不明等擴大故障矩陣仍依 N06 追蹤。
4. 展示結束後由 [SAM](mailto:cashsam@gmail.com) 停用兩展示帳號並撤 session／讀回；20:30 到期欄位不代替回收紀錄。[JEFF](mailto:jeff841117@gmail.com) 保持後台／consumer 及 S06～S08 覆核責任。

N02／N04／N05／N12／N16／N18 的具名接收、實機與最終簽收沿用 [V5 本輪清單](../專題進度/專案未完成工作清單_2026-10-18.md)。V5 原稿、PDF 及下一階段範圍保持原交付界線。
