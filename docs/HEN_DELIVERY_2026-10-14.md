# HEN 交付回報｜2026-10-14

後續更新：使用者已确认多裝置同時登入並授權發布，最新結果見 [多裝置與部署交付](HEN_MULTIDEVICE_DEPLOY_2026-10-14.md)。本頁以下保留較早本機單一登入草稿歷史，不能作為目前登入政策。

## 結果與工作順序

本輪依提供的進度表／HEN 指南完成可獨立進行的本機工作，原 `C:/LLM/LLM_PJ` 髒目錄保留。使用乾淨工作樹 `C:/Users/USER/.codex/worktrees/hen-r08/LLM_PJ`，分支 `codex/hen-r02-r08-20261014`。10/14 核對遠端 main `066e9da`、HEN `e66e06c`，後者已包含於 main。沒有混入 SAM／JEFF 未合併分支。

|順序|工作|本輪成果|交付狀態|
|---|---|---|---|
|1 R02|接口契約|[契約與未決事項](HEN_R02_CONTRACT_2026-10-14.md)，現有路由／輸入／錯誤／重送／主責|草稿完成，單一登入政策尚待確認|
|2 R08 會員|註冊／登入／登出／撤權|輸入與重複 email、固定 customer、即時 active/role、v4 登入世代、POST/CSRF 登出、JEFF 可信撤權函式|本機實作／離線測試完成；不是已部署接口|
|3 R08 購物|SKU 購物車／checkout|沿用原交易層；表單 revision、同鍵重送／不同內容衝突、後端重新計價與庫存檢查|本機／離線／瀏覽器示範完成；真交易待驗|
|4 事件|四事件與隔離|補 SEARCH、驗證瀏覽會員；加購／購買保留同交易去重；demo PURCHASE 排除歸因；伺服器 synthetic 設定，前台查詢先排除再 sort/limit|本機測試完成；所有遠端消費者需 JEFF／SAM 驗證|
|5 交付驗證|測試、證據、操作步驟|84 passed／4 skipped，XML 與瀏覽器截圖，獨立 replica set 測試|本機交付完成；未推送／未合併／未部署／未整合簽收|

## 真實執行的檢查

在 `MuscleCore分析資料/website` 執行：

```powershell
& 'C:/Users/USER/.codex/worktrees/hen-r08/LLM_PJ/.venv/Scripts/python.exe' -m pytest tests -q --junitxml='C:/Users/USER/.codex/worktrees/hen-r08/LLM_PJ/docs/inventory/hen_20261014/offline-tests.xml'
```

結果：**84 passed, 4 skipped in 13.12s，exit 0**。[JUnit 證據](inventory/hen_20261014/offline-tests.xml)。Python 3.14；依專案 requirements 安裝 Flask 3.1.2、Werkzeug 3.1.3、PyMongo 4.14.1、pytest 8.4.2、mongomock 4.3.0、原 LangGraph/LangChain 測試依賴。CI 的 Python 3.11 尚未執行，不能當作已通過 CI。

涵蓋：重複 email（含 unique index 競爭例外）、非法輸入、錯密碼、未登入、停用、customer 越權、已登入降權、登出／新登入／明確撤權後原 cookie 重播、CSRF；購物 owner 取 server session、非法數量／版本、下架商品／SKU／庫存、重送／不同 payload、重新計價、四事件標記、排序／limit 前隔離、legacy 與既有 AI 回歸。

瀏覽器（Codex in-app browser，僅 127.0.0.1 的 mongomock 隔離網站）：登入 → SKU 選擇 → 加購 2 件（20.50）→ 更新 3 件（30.75）→ demo 下單成功／库存 10→7 → 登出 → 再開購物車轉登入。下單頁明示未串接付款。v4 登入頁已核對不顯示 legacy demo 帳密。註冊、重播／降權與重送由離線 HTTP 測試驗證，沒有宣稱瀏覽器逐項執行。手機 RWD、正式網址與 Atlas 未驗。

截圖：[購物車](inventory/hen_20261014/cart.png)、[demo 下單](inventory/hen_20261014/checkout.png)、[登出](inventory/hen_20261014/logout.png)。這些是本機隔離測試，不是正式訂單。

## SAM／JEFF 接續順序與前置

1. **SAM／HEN 先確認 R02 撤權政策**：本輪實作 v4 單一有效登入，既有 last_login_at 作登入世代；新登入、登出、撤權使全部舊 cookie 失效。last_login_at 在撤權時也會推進，因此須確認其他讀寫者接受此語義。若需要多裝置独立 session，另訂 schema/migration，不能直接按本輪方案部署。legacy 不宣稱伺服器撤權。
2. **JEFF 接停用／降權**：在已驗 admin 身分與 CSRF 的寫入服務呼叫 `app.services.member_sessions.revoke_user_sessions(db, user_id, mongo_session=...)`；可與停用／角色改動使用同一 transaction。只改 inactive 會暫拒絕，但重新啟用前必須撤權，否則未推進世代的舊 cookie 仍可能恢復；最後管理員／自己停用由 JEFF 定案。函式不是公開 API。
3. **SAM 提供獨立 localhost replica set**：Docker CLI 存在但引擎未啟動；未發現 mongod。4 項 opt-in 測試跳過原因是 HEN_TEST_MONGO_URI 未設定。測試只接受無帳密 localhost mongodb URI，建立隨機 hen_acceptance_* 庫，最後只刪除自身庫；不讀 .env、不連正式 Atlas。涵蓋真 rollback、最後庫存並發、登入 CAS 並發、撤權 transaction abort。其測試未安裝完整 validators，SAM 仍須以現行 v4＋overlay 驗證文件／索引；不改歷史 migration。

```powershell
# 請在已備妥的獨立本機 replica set 填入正確 port／setName
$env:HEN_TEST_MONGO_URI = 'mongodb://127.0.0.1:<port>/?replicaSet=<setName>'
# 工作目錄：MuscleCore分析資料/website
& 'C:/Users/USER/.codex/worktrees/hen-r08/LLM_PJ/.venv/Scripts/python.exe' -m pytest tests/test_hen_transactions.py -q
```

4. **SAM／JEFF 整合原 PR #17**：保留 SAM 前台／synthetic 消費者改動；本輪提供 server `BEHAVIOR_SYNTHETIC_BATCH`（非瀏覽器欄位），四事件 metadata 使用 synthetic／synthetic_batch_id／exclude_from_attribution。demo PURCHASE 一律 exclude_from_attribution；JEFF 核對所有外部評分／歸因／排程，SAM 部署并驗證後才可 apply D4。
5. **SAM 驗少量私有帳號與端到端流程**：不啟用 600 合成會員；正式資料、validator、遠端登入／購物、手機 RWD、demo 取消與庫存補回由既定主責接續。付款／退款未串接，不以 paid 示範欄位宣稱真付款完成。
6. 本機成果審查後再授權推送／PR；文件中的 F 提示詞沒有當作本輪發布指令。推送前先查同分支 PR／CI、重新核對遠端分歧，不 force push；不合併／部署／寄信。

## 可重現本機瀏覽器測試

在 `MuscleCore分析資料/website`：

```powershell
$env:PYTHONPATH = (Get-Location).Path
& 'C:/Users/USER/.codex/worktrees/hen-r08/LLM_PJ/.venv/Scripts/python.exe' tests/run_hen_demo.py
```

僅啟動 127.0.0.1:5084；使用 tests fixture 的假帳號與記憶體資料，synthetic batch 固定 hen-browser-20261014。程式結束即丟棄資料。測試帳號請讀測試 fixture，不以真實帳號登入。這不是可部署 WSGI 入口。

## 相容界線與已知限制

- checkout 本身強制 cart_id/revision；新增 cart mutation 的 expected_revision 對舊 API 暫為 optional，購物車更新／移除表單已傳版本，舊 client 未帶版本仍維持既有行為。若要所有 mutation 強制版本，須協調呼叫者與新增商品頁版本接口。
- 同 ID 重送契約只比較既有已定業務欄位，忽略前端 user_id／金額；GET 搜尋／瀏覽每次代表一次新行為，沒有宣稱 GET 的跨網路重播去重。
- generation 方案會拒絕舊部署未持有世代的 v4 cookie，使用者須重新登入；不觸碰 .env、帳密、正式庫、庫存基線、D1～D4 或歷史 migrations。
- 原始進度表未被覆寫；沒有將本機測試轉記成部署／Atlas／全站完成。
