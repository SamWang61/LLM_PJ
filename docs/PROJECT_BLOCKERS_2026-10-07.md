# 殘留問題與具名責任｜2026-10-07

依組長最新指示：AI/後台 JEFF；會員/購物 HEN；未屬二者的項目由 SAM 負責，沒有「待分配」責任欄。以下是協作前置清單，不代表對方已接受契約或已完成實作。HEN/JEFF 已有 GitHub Write，不再列邀請為阻礙。

|編號|殘留問題|單一負責人|先完成/等候條件|完成標準|GitHub參考|
|---|---|---|---|---|---|
|R01|確認/修訂 D5 與 AI 契約、更新 PR #8 口徑|JEFF|無；先處理|補有效訂單分子/全訂單分母、可售SKU最低價、D1–D3已存在、模型離線界線、自由文字/intent選擇；回覆可接受欄位與缺口|[docs/SAM_DATA_CONTRACT_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_DATA_CONTRACT_2026-10-07.md)|
|R02|確認登入/撤權與購物流程契約|HEN|無；先處理|明確 active/role/session 撤銷、結帳 demo 與庫存交易、接口/測試路徑；同步最新 main|[docs/HEN_AUTH_ORDER.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/HEN_AUTH_ORDER.md)|
|R03|D4 合成行為事件|SAM|離線設計可先做；入庫/端到端前需 JEFF 完成事件隔離/消費口徑、HEN 完成觸發路徑|新批次合法參照/時序、四權重、冪等、標準答案；不讓合成事件冒充正式歸因|[docs/TEST_DATA_SPEC.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/TEST_DATA_SPEC.md)|
|R04|少量私有 customer/admin 登入帳號|SAM|需 HEN 先完成登入/停用/撤權接口，JEFF 先提供後台授權路徑|個別私有憑證、測完停用/撤session；不啟用600人、不提交密碼|[docs/SAM_DATA_CONTRACT_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_DATA_CONTRACT_2026-10-07.md)|
|R05|後台共用版型/總覽/推薦監控改版|JEFF|可與R01並行；有資料讀取可先接|新導覽/RWD/空錯誤狀態；現行政策4/3/2/1；所有數字有範圍|[docs/AI_DASHBOARD.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/AI_DASHBOARD.md)|
|R06|後台商品/SKU/訂單/會員寫入功能|JEFF|需R01/R02確認；稽核schema先由SAM(R07)交付|實作D5服務/頁面/CSRF/衝突/冪等與回滾，外部退款不能假成功|[docs/SAM_DATA_CONTRACT_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_DATA_CONTRACT_2026-10-07.md)|
|R07|稽核/必要Schema新migration|SAM|需 JEFF 先確認R01稽核欄位/保留期限及寫入需求|新增版本化 migration、讀回與拒絕/交易測試；不改五筆歷史 checksum|[VibeCart_AI/MongoDB/schema_active_v4.py](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/schema_active_v4.py)|
|R08|會員/購物流程完成與提交|HEN|R02、最新基底及既有v4服務|註冊登入登出、會員状態、SKU購物車、checkout重送/錯誤/權限等；完整PR與回讀證據|[docs/HEN_AUTH_ORDER.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/HEN_AUTH_ORDER.md)|
|R09|Local BGE / Cloud洞察 / AI比較功能與真實模型驗證|JEFF|R01；Local/摘要可先以D1–D3驗證，個人化依賴R03|真實推論、來源/退回、候選過滤、延遲/成本量測與白名單；未實測不填數字|[docs/FLASK_SKU_AI_INTEGRATION.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/FLASK_SKU_AI_INTEGRATION.md)|
|R10|完整6+4推薦/計分衰減/排程/回購與跨類統計|JEFF|R01/R03；PR #5採用由JEFF決定|計分排程冪等與算法版本、分母/評價門檻/推薦池更新；不得造ACTUAL評價填池|[docs/AI_DASHBOARD.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/AI_DASHBOARD.md)|
|R11|前台/RWD與超市瀏覽完善|SAM|可直接做；登入購物互動依賴HEN(R08)，推薦區依賴JEFF(R09/R10)|本次已有超市程式交付；補桌面/手機實際瀏覽、圖片故障/空篩選/導航與無障礙|[VibeCart_AI/MongoDB/supermarket/README.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/supermarket/README.md)|
|R12|畫面/API與同批標準答案對帳|SAM|需 JEFF 先交付R05/R06/R09、HEN先交付R08；各模組可分段驗收|日期/閏日/demo/退款取消/零值/366天與5000單/可售最低價/交易並發/稽核回滾|[VibeCart_AI/MongoDB/test_data/generated/expected_metrics.json](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/test_data/generated/expected_metrics.json)|
|R13|部署目標與展示環境|SAM|可先規劃；發布驗收需R08/R09/R11/R12與私有配置/選定平台|WSGI/HTTPS/秘密配置、非seed現有庫、公開網址/圖片/Atlas依賴、遠端瀏覽驗證|[docs/FLASK_SKU_AI_INTEGRATION.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/FLASK_SKU_AI_INTEGRATION.md)|
|R14|PR #10 Network Access文件審查與合併處理|SAM|無JEFF/HEN前置；Atlas狀態須另即時核實|處理既有PR，不能將0.0.0.0/0文件描述當成新權限調整或永不過期證明|[VibeCart_AI/MongoDB/01_Cluster設定與狀態.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/VibeCart_AI/MongoDB/01_Cluster%E8%A8%AD%E5%AE%9A%E8%88%87%E7%8B%80%E6%85%8B.md)|
|R15|Drive備份可恢復方案|SAM|無JEFF/HEN前置；需SAM決定私有/加密方案及取得可靠ACL/雲端核對能力|固定連結、共用切換與恢復、完整manifest/hash；未符合BACKUP不開始普通複製|[docs/BACKUP.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/BACKUP.md)|
|R16|最終展示/報告/整合簽收|SAM|需 JEFF 先完成R05/R06/R09/R10，HEN先完成R08，SAM完成R12/R13|錄製實際流程、實測比較與限制、測試證據、已知問題、組员成果歸屬；驗收不等於CI|[docs/DOCUMENT_INDEX.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/DOCUMENT_INDEX.md)|
|R17|本次SAM分支審查與main合併|SAM|推送/CI完成後；未要求本輪自動合併|PR保留SAM資料/前台/盤點，審查後合併；不混入JEFF #5/#8或直接覆寫main|[docs/SAM_PUBLICATION_2026-10-07.md](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-delivery-20261007/docs/SAM_PUBLICATION_2026-10-07.md)|

## 目前真正卡住的位置

1. 資料庫 D1–D3 已存在，checker 已修正；它們不再是後台實作的「無資料」阻礙。
2. JEFF #8 是四份文件，尚未有新版後台功能PR；JEFF須先把資料口徑與D5/AI接口定清，再交付功能。SAM可先寫標準答案與測試，不能先宣稱畫面通過。
3. HEN 已有權限，但 feature/auth-order 尚無超出 main 的新功能提交；HEN須先交付登入/撤權/購物流程，SAM才能驗證私有帳號與會員流程。
4. D4 的離線生成可由SAM先做；共享入庫與端到端必須等JEFF確認synthetic隔離與事件消費、HEN確認觸發路徑，避免假資料進入正式成效。
5. D5 稽核schema需JEFF先確認，再由SAM新增 migration；功能寫入由JEFF完成、SAM測試。
6. 全站/模型/部署驗收不能由本次70項離線測試或Atlas結構通過取代。

SAM 今天中午過後將AI時間先留給EDI，晚上上課時才轉回LLM_PJ；HEN/JEFF可先完成上述前置，不以SAM午後即時回覆作為今日完成承諾。

English: Every outstanding item has one owner. JEFF owns AI/admin implementation, HEN auth/order, SAM everything else and acceptance. Blocking prerequisites name the person who must deliver first.
