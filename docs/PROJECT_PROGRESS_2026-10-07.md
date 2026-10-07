# LLM_PJ 全專案進度與先後順序｜2026-10-07

核對時間：2026-10-07 11:16（Asia/Taipei，GitHub快照03:16 UTC）。來源：GitHub LLM_PJ main、遠端功能分支與PR/CI/協作者即時回讀；本機SAM交付另列。只閱讀現行入口及與本次盤點有關的專項文件。未以歷史週計畫推定完成率；未提供百分比，因沒有全團隊一致的驗收分母。沒有GitHub提交證據只表示未交付，不能推定同學本機毫無工作。

## GitHub 實際狀態

|項目|已核實|判讀|
|---|---|---|
|main|066e9da；最近main CI success|既有Flask/v4 adapter與後台基礎已合併；本次SAM分支尚待合併|
|已合併PR|#1/#2/#3/#4/#6/#7/#9|資料層/Flask SKU/AI workflow基礎、後台基礎、責任文件與查詢手冊；不能等同完整模型/全站驗收|
|JEFF #8|open、非draft、e7df815；4份Markdown，分支CI success|後台設計文件，沒有新功能實作；需JEFF更新資料口徑|
|JEFF決定的#5|open、draft、dc3114d|計分候選未合併，不算SAM本次成果|
|SAM #10|open、8a6edb1；分支CI success|Network Access說明待審查/合併，本輪不改Atlas權限|
|feature/auth-order|e66e06c，沒有超出main的新提交|HEN需同步main後交付會員/購物增量與驗收；不能把落後分支差異當新功能|
|feature/store-ui|5ee398b，沒有超出main的新提交|前台/RWD現由SAM承接；本機超市差異本次送審|
|協作者|SAM admin；JEFF/HEN push=true；pending invitations=[]|HEN已接受，不再卡在GitHub邀請|
|Issues|open issues=0|缺口集中在本盤點與PR，零issue不等於零待辦|

證據：[GitHub JSON快照](inventory/PROJECT_GITHUB_SNAPSHOT_2026-10-07.json)。該快照為本次發布前的真實紀錄，新增SAM PR/CI另見 [發布紀錄](SAM_PUBLICATION_2026-10-07.md)，不改寫舊快照。

## 模組進度

|模組|已有成果|未完成/未驗收|負責人|
|---|---|---|---|
|資料庫|27集合/86索引、SKU交易/評價服務、5筆migration；本次current checker與Atlas只讀通過|D4、D5稽核新migration、新增功能資料庫回歸|SAM|
|測試商品/客戶/訂單 D1–D3|336/336、600停用、3000demo、8969明細與標準答案；本次工具/證據交付|不得當成真實客戶交易；私有登入與事件另批|SAM|
|會員/購物|main既有auth與SKU購物車/checkout adapter；歷史Atlas交易證據保留|HEN新功能PR、active/撤權接口與私有帳號驗收、全流程UAT|HEN（SAM驗收）|
|超市前台/RWD|本次完整分頁/分類/搜尋/圖像/來源/規格與本機入口|桌面/手機瀏覽UAT、登入/推薦接線、公開展示|SAM（HEN/JEFF先交對應功能）|
|後台總覽|main已有篩選/KPI/最近單/低庫存/摘要/事件監控|JEFF新sidebar版型、管理頁/寫入功能及當前資料對帳|JEFF|
|AI工作流|已有LangGraph/BGE/Claude adapter與規則退回、離線替代模型測試|真實BGE/Claude、完整問答輸入、6+4推薦/排程計分/回購跨類統計、比較實測|JEFF|
|資料契約|SAM D5/AI proposal已交付|JEFF/HEN確認後落實API/稽核/欄位；不能把提案稱已接受|JEFF/HEN各自確認，SAM追蹤與schema|
|整合與展示|既有基礎驗證、查詢手冊與CI|同批畫面/API對帳、部署目標/公開網路UAT、最終報告/演示|SAM|
|維運/備份|BACKUP規範存在|秘密私有/加密、權限切換/恢復、雲端manifest核對|SAM|

## 全團隊執行順序（同階段可並行）

每項僅一位主責，驗收/協作分別列明；詳細完成標準見 [具名殘留問題](PROJECT_BLOCKERS_2026-10-07.md)。

|順序|項目|負責人|依賴／先由誰完成|應參考的GitHub文件|
|---|---|---|---|---|
|0|R17 本次SAM分支審查與main合併|SAM|推送/CI完成後；未要求本輪自動合併|[docs/SAM_PUBLICATION_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_PUBLICATION_2026-10-07.md)|
|1A|R01 確認/修訂 D5 與 AI 契約、更新 PR #8 口徑|JEFF|無；先處理|[docs/SAM_DATA_CONTRACT_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_DATA_CONTRACT_2026-10-07.md)|
|1B|R02 確認登入/撤權與購物流程契約|HEN|無；先處理|[docs/HEN_AUTH_ORDER.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/HEN_AUTH_ORDER.md)|
|1C|R11 前台/RWD與超市瀏覽完善|SAM|可直接做；登入購物互動依賴HEN(R08)，推薦區依賴JEFF(R09/R10)|[VibeCart_AI/MongoDB/supermarket/README.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/supermarket/README.md)|
|1D|R14 PR #10 Network Access文件審查與合併處理|SAM|無JEFF/HEN前置；Atlas狀態須另即時核實|[VibeCart_AI/MongoDB/01_Cluster設定與狀態.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/01_Cluster%E8%A8%AD%E5%AE%9A%E8%88%87%E7%8B%80%E6%85%8B.md)|
|2A|R03 D4 合成行為事件|SAM|離線設計可先做；入庫/端到端前需 JEFF 完成事件隔離/消費口徑、HEN 完成觸發路徑|[docs/TEST_DATA_SPEC.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/TEST_DATA_SPEC.md)|
|2B|R07 稽核/必要Schema新migration|SAM|需 JEFF 先確認R01稽核欄位/保留期限及寫入需求|[VibeCart_AI/MongoDB/schema_active_v4.py](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/schema_active_v4.py)|
|2C|R05 後台共用版型/總覽/推薦監控改版|JEFF|可與R01並行；有資料讀取可先接|[docs/AI_DASHBOARD.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/AI_DASHBOARD.md)|
|2D|R08 會員/購物流程完成與提交|HEN|R02、最新基底及既有v4服務|[docs/HEN_AUTH_ORDER.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/HEN_AUTH_ORDER.md)|
|3A|R04 少量私有 customer/admin 登入帳號|SAM|需 HEN 先完成登入/停用/撤權接口，JEFF 先提供後台授權路徑|[docs/SAM_DATA_CONTRACT_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_DATA_CONTRACT_2026-10-07.md)|
|3B|R06 後台商品/SKU/訂單/會員寫入功能|JEFF|需R01/R02確認；稽核schema先由SAM(R07)交付|[docs/SAM_DATA_CONTRACT_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_DATA_CONTRACT_2026-10-07.md)|
|3C|R09 Local BGE / Cloud洞察 / AI比較功能與真實模型驗證|JEFF|R01；Local/摘要可先以D1–D3驗證，個人化依賴R03|[docs/FLASK_SKU_AI_INTEGRATION.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/FLASK_SKU_AI_INTEGRATION.md)|
|4|R10 完整6+4推薦/計分衰減/排程/回購與跨類統計|JEFF|R01/R03；PR #5採用由JEFF決定|[docs/AI_DASHBOARD.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/AI_DASHBOARD.md)|
|5|R12 畫面/API與同批標準答案對帳|SAM|需 JEFF 先交付R05/R06/R09、HEN先交付R08；各模組可分段驗收|[VibeCart_AI/MongoDB/test_data/generated/expected_metrics.json](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/test_data/generated/expected_metrics.json)|
|6|R13 部署目標與展示環境|SAM|可先規劃；發布驗收需R08/R09/R11/R12與私有配置/選定平台|[docs/FLASK_SKU_AI_INTEGRATION.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/FLASK_SKU_AI_INTEGRATION.md)|
|7|R16 最終展示/報告/整合簽收|SAM|需 JEFF 先完成R05/R06/R09/R10，HEN先完成R08，SAM完成R12/R13|[docs/DOCUMENT_INDEX.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/DOCUMENT_INDEX.md)|
|維運並行|R15 Drive備份可恢復方案|SAM|無JEFF/HEN前置；需SAM決定私有/加密方案及取得可靠ACL/雲端核對能力|[docs/BACKUP.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/BACKUP.md)|

## JEFF 的設計來源（尚在PR分支）

[JEFF_ADMIN_UI_DESIGN.md](https://github.com/SamWang61/LLM_PJ/blob/docs/jeff-admin-ui-design/docs/JEFF_ADMIN_UI_DESIGN.md)，搭配 [PR #8](https://github.com/SamWang61/LLM_PJ/pull/8)。不可使用 main 路徑假裝該文件已合併。

## 舊驗收表如何解讀

docs/FLASK_SKU_AI_INTEGRATION.md 的舊待填交易項目，與後來 docs/AI_DASHBOARD.md、V4_TEST_VERIFICATION.json 的實際證據一起判讀：基礎交易曾驗證，不重複稱全數沒做；HEN/JEFF的新功能仍需重做對應整合驗收。此次Atlas結構回讀沒有重新跑付款、登入或並發寫入。

## 下午與晚上安排

今天中午後 SAM 的AI時間先給EDI專案，晚上上課時再轉回LLM_PJ。JEFF先處理1A/2C，HEN先處理1B/2D；SAM晚上接續自己負責的項目與整合。尚未訂定同學承諾完成時間。

English: Inventory is based on the live repository and PRs. Existing integrations remain credited, while model/browser/deployment acceptance is pending. The dependency table names the owner and who must deliver first.
