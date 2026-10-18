# 文件中心 / Documentation hub

<!-- SAM N14 20261018 BEGIN -->
**2026/10/18 15:52 SAM N14**：[最新來源與Atlas完整還原](SAM_N14_CURRENT_ATLAS_2026-10-18.md)。15:30原目錄快照13,976檔／4,109,781,733 bytes，以已驗基底＋983變更／1刪除完整重建，hash差異0；Atlas28集合／14,689筆／89索引／3TTL及validator完成同一snapshot匯出、雲端讀回認證解密及全新localhost還原對帳。79安全測試通過，原Atlas未寫入。**差異包需保留原25片基底；異機key與每日固定專案ACL流程仍缺，N14保留待結案、V5仍2/14完成。**
<!-- SAM N14 20261018 END -->

<!-- SAM JEFF 20261018 BEGIN -->
**2026/10/18 15:52 JEFF交付判斷／準備**：[同版檢查與部署前置](SAM_JEFF_AI_READINESS_2026-10-18.md)。已讀JEFF交接，#82雲端設定15測試、#83／#84權重與隔離27測試通過；兩映像已建置，BGE斷網2Gi／1CPU輸出512維。正式synthetic batch未設定；ANTHROPIC_API_KEY尚無secret。未做三PR整合後驗收、雲端AI啟用、真Claude或切流量。
<!-- SAM JEFF 20261018 END -->

**2026/10/18 08:06 SAM PR #74 技術覆核**：[完整整合紀錄](SAM_PR74_MERGE_REVIEW_2026-10-18.md)。本輪208 passed／0 skipped、51執行來源對帳0差異；公開customer/admin登入、角色及單裝置登出通過，sessions0。另修正維運驗證清理可能誤刪並行session，4項回歸通過。正式19／私有10同映像、正常command、IAM0；故障報告仍依06:36～06:38原時間。本次PR將部署來源整合main，實際合併SHA／時間見[PR #74](https://github.com/SamWang61/LLM_PJ/pull/74)。V5仍2/14完成，具名交接／更廣outage／實機／備份／簽收待辦。

**2026/10/18 06:50 SAM N17 補強**：[V5 離線備援與還原](SAM_V5_OFFLINE_REHEARSAL_2026-10-18.md)完成40檔、雙建包相同雜湊、全新目錄還原差異0及18項安全回歸；補13頁無PDF外掛圖片閱讀版。原PPTX／PDF不變；實體斷網、第二台電腦／投影及真人計時仍待驗，14關卡仍2完成／12待結案。

**2026-10-18 05:12（Asia/Taipei）本輪整合**：#69 已修正 P2 並合併；#67 已完成衝突整合、本機 201 passed／0 skipped 與目前同映像私有交易／七項帳號驗收，最新文件 CI 通過後按使用者授權合併。正式 `00017-5xb` 100% 不變，私有已對齊 `00006-cb6`；清理 0、臨時 IAM 0、匿名 403。[PR #67／#69 驗收與同步紀錄](SAM_PR67_PR69_MERGE_2026-10-18.md)為本輪入口；下方舊修訂／待整合狀態按原時間解讀。N11 其餘 consumer 證據、N12～N18 及具名簽認仍待辦，不重複計分。

[10/18逐項工作與今日證據](WORK_EXECUTION_2026-10-18.md)；[下一階段D5本機演練](SAM_D5_LOCAL_REHEARSAL_2026-10-18.md)；[舊PR差異盤點](OPEN_PR_RESIDUALS_2026-10-18.md)。

**下一輪工作入口（2026-10-18）**：[專案未完成工作清單與估算](../專題進度/專案未完成工作清單_2026-10-18.md)，從N01開始；[全部60個PR核對清冊](PR_AUDIT_2026-10-18.md)。較早清單保留作歷史證據。

- [2026-10-17 專案工作清單與 REN 24 小時代班](../專題進度/專案工作清單_2026-10-17.md)
- [現行團隊分工](TEAM_OWNERSHIP.md)
- [2026-10-17 REN 文件同步紀錄 / Documentation sync](DOCUMENT_SYNC_2026-10-17.md)

**後續工作先讀：[最新專案上下文](CURRENT_CONTEXT.md)。** 舊文件保留供追溯，日常作業不需反覆全量閱讀。Start with the compact current context, then consult only task-relevant references.
本目錄提供跨模組索引與管理規則；原文件保留在既有目錄，以維持引用、來源快照與遷移可追溯性。This hub consolidates navigation while preserving original paths and historical evidence.

| 主題 / Topic | 入口 / Entry |
|---|---|
| SAM 私有帳號與撤權驗收 | [10/18 N04／N05 同映像七項遠端案例、清理與展演前待辦](SAM_ACCOUNT_ACCEPTANCE_2026-10-18.md) |
| SAM 新推送驗證 | [10/18 來源位元組、186/0 回歸、部署讀回與剩餘驗收](SAM_PUSH_VALIDATION_2026-10-18.md) |
| 10/17 JEFF 交付與 SAM 決定 | [PR #23 合併、D4 consumer 稽核及展示邊界](SAM_JEFF_1017_HANDOFF.md) |
| SAM PR #21 同版遠端預覽 | [10/17 無流量修訂、Atlas 唯讀盤點與剩餘驗收](SAM_PR21_REMOTE_PREVIEW_2026-10-17.md) |
| SAM Atlas 資料對帳 | [10/17 migration、商品／訂單關聯與 Network Access 唯讀核對](SAM_ATLAS_READONLY_ACCEPTANCE_2026-10-17.md) |
| SAM 遠端交易前置 | [10/17 隔離資料庫與私有驗收服務閘門](SAM_REMOTE_TRANSACTION_PREFLIGHT_2026-10-17.md) |
| SAM 遠端交易紀錄 | [10/17 私有服務、IAM、同版映像與未通過項目](SAM_REMOTE_TRANSACTION_ACCEPTANCE_2026-10-17.md) |
| D4 匯入驗收 | [10/18 同版隔離、1,240 筆合成事件與冪等重送](D4_IMPORT_ACCEPTANCE_2026-10-18.md)；[閘門歷史](D4_REMOTE_GATE_2026-10-17.md) |
| REN 會員／購物接口 | [R02 路由、session、交易與事件交接](REN_R02_INTERFACE_2026-10-17.md) |
| SAM 同版整合基線 | [2026-10-16 來源與驗證](SAM_INTEGRATION_BASELINE_2026-10-16.md) |
| SAM PR #21 本機驗證與最終缺口 | [2026-10-16 Docker／交易與遠端待驗](SAM_PR21_ACCEPTANCE_2026-10-16.md) |
| 部署方式 | [Firebase Hosting／Cloud Run](../deploy/FIREBASE_CLOUD_RUN_DEPLOYMENT.md)、[Render](../deploy/RENDER_DEPLOYMENT.md) |
| JEFF 管理後台設計與 D5／AI 契約 | [v1.2 設計規格與 10/16 啟用門檻](JEFF_ADMIN_UI_DESIGN.md) |
| SAM 最新 CI 與交易驗收 | [2026-10-15 修復與測試紀錄](SAM_CI_TRANSACTION_ACCEPTANCE_2026-10-15.md) |
| [Flask／SKU／AI 串接](FLASK_SKU_AI_INTEGRATION.md) | v4 routes, LangGraph workflows, setup and UAT. |
| 全部文件 / All documents | [逐份雙語索引](DOCUMENT_INDEX.md) |
| 目錄管理 / Repository management | [管理政策](REPOSITORY_GUIDE.md) |
| 分支協作 / Branch workflow | [分支規劃與協作機制](%E5%88%86%E6%94%AF%28Branch%29%E8%A6%8F%E5%8A%83%E8%88%87%E5%8D%94%E4%BD%9C%E6%A9%9F%E5%88%B6.md) |
| 備份 / Backup | [流程與狀態](BACKUP.md) |
| 現行資料層 / Current data layer | [MongoDB README](../VibeCart_AI/MongoDB/README.md) |
| 原始規格 / Source specifications | [規格與討論](../討論的相關記錄/README.md) |
| 歷史進度 / Historical progress | [進度入口](../專題進度/README.md) |
| 展示網站 / Demo website | [啟動說明](../MuscleCore分析資料/website/README.md) |
| 完整檔案清冊 / File inventory | [CSV](inventory/files.csv)、[摘要](inventory/summary.json) |

中文原稿是專題依據；英文摘要用於協助理解，不取代正式欄位定義。來源快照與原始報告不為了翻譯而覆寫。Chinese source specifications remain authoritative; English summaries do not replace field definitions or alter snapshots.

- [客戶／訂單測試資料規範](TEST_DATA_SPEC.md) / Synthetic test-data specification.
- [SAM 完成工作與預計項目](../專題進度/至今SAM完成的工作與預計項目_2026-10-05.md) / SAM delivery and next work.

- [REN 命名修正 log / Naming correction log](log/REN_NAMING_2026-10-18.md)

- [N03 最新來源與版本核對](SAM_VERSION_MAP_2026-10-18.md)
- [N02 交接來源補充](SAM_V1_DELIVERY_SCOPE_2026-10-18.md)
