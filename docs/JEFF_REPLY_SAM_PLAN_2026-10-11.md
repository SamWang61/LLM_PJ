# JEFF 回覆核對與 SAM 合併工作清單

核對：2026-10-11，Asia/Taipei。郵件為 JEFF 2026-10-09 03:54:28 的 PR #8 通知；[原回覆](https://github.com/SamWang61/LLM_PJ/pull/8#issuecomment-6067889418)。Gmail 全串與 GitHub 畫面回覆一致。依即時 Git fetch 核對分支原始碼，未改寫同學分支、未寄信、未合併或寫入 Atlas。

## 已核對的變更

main 仍為 `066e9da`。PR #8 開啟中，最新 head 是 `fe0a4ea`，不是郵件提及的 `94b6d6c`。v1.1 已補 KPI 分子／分母、active 可售 SKU／最低價、本機推論離線界線、D1～D3 現況、AI 白名單與 D5 回覆；不再將五項文件修正列為未做。第 7.5 節的 Atlas 數字是 JEFF 10/9 回報，本次沒有重新讀 Atlas。

SAM [PR #11](https://github.com/SamWang61/LLM_PJ/pull/11) 分支 `e80d251` 已有現行五筆 migration checker、test_data、契約、前台及工作清單，GitHub 畫面仍顯示 Open；「尚未交付 GitHub」已不適用，但合併及驗收仍須分開。

JEFF 已提交 [#12](https://github.com/SamWang61/LLM_PJ/pull/12) `042ba98`、[#13](https://github.com/SamWang61/LLM_PJ/pull/13) `f1b8517`、[#14](https://github.com/SamWang61/LLM_PJ/pull/14) `b929738`、[#15](https://github.com/SamWang61/LLM_PJ/pull/15) `9d38712`；PR #8 畫面均顯示 Open。這些是功能交付，不能再寫成「只有設計文件」。本次針對契約相關函式讀碼，沒有全面審查或執行這四個 PR 的測試。HEN `origin/feature/auth-order` 為 `e66e06c`，未見新的分支交付；不據此推定 HEN 的本機工作狀態。

## 回覆遺漏／實作差異表

| 優先 | 核對項目與證據 | 尚缺／影響 | 負責人 | 前置負責人與完成條件 |
|---|---|---|---|---|
| P1 | 第 12.1 接受 D4 隔離；#12 `recommendation_monitor` 仍用 `behavior_events.find({})`，只投影 product_id/event_type | 沒有 metadata 批次排除或標示；入庫後 synthetic 會混入統計。需同步推薦消費者與正式歸因的排除測試 | JEFF | SAM 提供本批 metadata／fixture；JEFF 完成批次篩選與正式成效排除後，SAM 才做共享入庫 |
| P1 | 第 12.2 寫自由輸入防護「實作前與 SAM 確認」；#13 已有 free_question 路由、PII 規則、限流與 prompt | 六項方向已有實作，不能稱完全遺漏；但決策／測試驗收未閉環，PII regex 不保證所有個資被阻擋 | JEFF | SAM 定義拒送案例；JEFF 明訂自由輸入啟用條件與去識別化契約 |
| P1 | #13 `insight_answer` 將 request（含問題全文）與 answer 放入 32 筆、300 秒 process cache | 呼叫紀錄不記全文已做到，但快取仍保存問題與回答；與「單次問答不保留歷史」需釐清，文件未交代記憶體保留界線 | JEFF | SAM 提供驗收案例；JEFF 確認是否禁用自由文字快取及明訂保留／清除政策 |
| P1 | `94b6d6c` 之後 `fe0a4ea` 移除「不提供硬刪除」條款 | 移除禁止不等於已授權刪除；硬刪除對象、歷史參照、稽核與恢復契約仍未定義。D5 v1 保持只處理明列更新，不自行新增刪除 API | JEFF | SAM 提供參照限制；JEFF 補刪除範圍或明確列後續版本 |
| P1 | 稽核已接受欄位與 180 天 TTL，業務／稽核同交易 | request_id 唯一範圍、批量逐筆識別、失敗稽核另存策略、TTL 到期後冪等重送保存期限仍需定義；稽核集合不能直接充當永久冪等紀錄 | SAM | JEFF 先確認批量／重送行為；SAM 可先做新增 schema/migration 草案，保留五筆歷史 checksum |
| P1 | 第 12.3 customer 停用撤 session，管理員不能後台停用 | 需 HEN 提供實際 session/token 撤銷接口與重播測試；只每次檢查 active 不代表完整 token 撤銷驗收 | HEN | JEFF 已提供 @admin_required 路徑；HEN 交付撤權接口後 SAM 建立私有帳號／測試 |
| P2 | 第 12.3 接受訂單合法順序、v1 不退款 | SAM 提案中的 confirmed=paid、shipping=shipped、completed=delivered 仍須落實；paid 取消後的庫存／付款責任未形成可驗收實作 | JEFF | HEN 先提供購物庫存／付款接口；SAM 定義交易與跳躍拒絕案例 |
| P2 | #13 白名單有 totals/daily/products/demo/filter、排序截斷提示 | 接受版契約提到的來源批次／資料截止尚未完整表達；目前 source 沒有批次，generated_at 是生成時間，不能代替資料截止 | JEFF | SAM 提供批次／資料品質標準答案；JEFF 補欄位或正式修訂契約 |
| P2 | 第 3、10 節仍有 D5「待 SAM 確認」，第 6.1 表單比第 12.3 v1 寫入白名單更廣 | 需區分展示／可寫入／後續欄位，避免 UI 暗示分類、品牌、圖片、AI 週期均可修改 | JEFF | SAM 已有 D5 提案；JEFF 同步前後節及管理功能交付 |

## 與 SAM 清單合併後的執行順序

沿用 10/7 R 編號與分工，歷史清單保留。

| 順序／原編號 | 工作 | 負責人 | 現況與本輪處理 | 依賴／完成標準 |
|---|---|---|---|---|
| 1 R01/R07 | D5 決策合併、新稽核 migration | SAM | JEFF 已接受基本欄位／TTL；剩餘語義見上表，migration 尚未實作／部署 | JEFF 明訂重送、批量及失敗紀錄；新增版本，不改五筆歷史 |
| 2 R03 | D4 新批次 fixture／標準答案 | SAM | 本輪已實作離線生成與破壞拒絕測試；尚未匯入 | JEFF 完成所有事件消費路徑的 synthetic 排除；HEN 完成觸發接口後驗端到端 |
| 3 R04 | 私有 admin/customer 帳號 | SAM | 不啟用既有 600 人，尚未建立 | HEN 撤權／登入接口與 JEFF 授權驗收；密碼僅私有保存，測後撤銷 |
| 4 R05/R09/R12 | 四個 JEFF PR 與同批資料分段對帳 | SAM | #12～#15 已交付，改為待審查／整合／真模型驗證 | JEFF 先補上表差異；SAM 日期/demo/零值/上限/最低價對帳，保留退回與未量測界線 |
| 5 R06/R08/R10 | 後台寫入、登入購物、完整推薦／排程 | JEFF（R06/R10）；HEN（R08） | 尚未由本次核對證明完成；不列 SAM 功能成果 | SAM 交稽核／fixture；JEFF/HEN 各交功能與測試，再由 SAM 整合 |
| 6 R11/R13/R16 | 前台實際 RWD、部署、展示／簽收 | SAM | 保留未完事項 | JEFF/HEN 功能及 SAM 整合驗收先完成；CI 不代替瀏覽器與真模型驗收 |
| 7 R14/R15/R17 | Network Access文件、備份、PR #11 審查合併 | SAM | 本次未重核 #10／備份條件，保持原清單待辦；#11 未合併 | 備份依 BACKUP 規範，合併另依審查結果處理 |

## 本輪 D4 交付與操作

`test_data/behavior_fixture.py` 接受既有來源資料與 catalog，預設選最早 100 筆本批 paid／非 cancelled demo 訂單；每明細產生四事件。ID、排序、時間可重現；metadata 標 synthetic／新批次／來源批次／order_item_id／exclude_from_attribution。沒有 recommendation_id、processed_at，不修改訂單、庫存、會員或分數。四事件是測試練習，不假稱真實購買前旅程；全部在下單／註冊之後。

`expected()` 給四事件筆數及權重檢查和，該檢查和不是正式推薦分數。生成器無資料庫連線或匯入功能。實際匯入前還須讀回現存參照、驗 MongoDB validator／唯一索引及全消費路徑隔離，再另做冪等交易匯入工具。離線來源重建不會重新匯入 D1～D3。

測試命令（專案根目錄）：`python -m pytest VibeCart_AI/MongoDB/test_data/test_behavior_fixture.py -q`。

本輪 D4 專項 14 項通過；完整 test_data 23 項、網站既有離線測試 61 項，共 84 項通過（14 已包含在 23 內，不重複加總）。repository checker：0 errors；`git diff --check` 通過。此結果只證明離線 fixture 及既有回歸案例，不代表 MongoDB validator、共享入庫、推薦消費者、畫面或模型驗收。程式基底為 SAM PR #11，沒有將 JEFF 四個功能分支混入本輪測試。

English: Reconciles JEFF's Gmail reply with current PR heads and SAM's existing delivery. Old design findings are resolved; implementation gaps and owner dependencies remain explicit. This batch adds deterministic offline D4 fixtures and corruption tests without database writes or production attribution.
