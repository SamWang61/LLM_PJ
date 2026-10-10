# 最新專案上下文 / Current project context

## 2026-10-11 接續入口

先讀 [JEFF 回覆核對與 SAM 合併清單](JEFF_REPLY_SAM_PLAN_2026-10-11.md)：PR #8 v1.1 已補五項文件修正，JEFF #12～#15 已交付但未驗收；SAM #11 已推送未合併。D4 離線生成器與測試已新增，尚未入库。synthetic 消費隔離由 JEFF 先完成；稽核 migration 與私有帳號仍待後續，依賴見合併表。以下 10/7 記錄依原日期解讀。

更新：2026-10-07（Asia/Taipei）。這是後續工作的精簡入口，取代舊狀態摘要；舊文件、程式與遷移全部保留。動態狀態以下次實際核對為準。

## 讀取原則

接續 SAM 工作時，另讀 [2026-10-07 交接摘要](HANDOFF_SAM_2026-10-07.md)。切換對話前僅完成工作目錄檢查，未新增功能、提交 GitHub 或更動 Atlas；此次只補交接文件。

先讀本頁，再按任務讀一份必要文件。不要每次重掃全專案、舊週計畫或舊聊天。優先順序：使用者最新決策 → 即時驗證 → 本摘要／最新專項文件 → 歷史資料。只核對本次會影響操作的 Git、資料庫或權限狀態；查歷史、追錯或核對 migration 才開舊版本。

## 現行分工

- SAM：資料庫、測試、組長協調及交付文件。
- JEFF：AI／管理後台；不把其設計或實作列為 SAM 成果。
- HEN（@1dcvgieok4gm）：已選 B 會員／購物流程，使用 feature/auth-order。10/7 已核實 GitHub Write 生效，邀請待接受為零；**不是仍負責前台／RWD**。
- 前台／RWD、最終整合驗收由 SAM 負責（2026-10-07 組長最新指示）。

## 已核實基線（10/7）

- Atlas vibecart_ai：336 商品、336 SKU、600 合成客戶、3,000 訂單、8,969 明細。
- 測試批次 sam-synthetic-20261005-v1；跨 2024～2026 年；全部訂單 is_demo=true，600 客戶停用，不可登入。67 人無訂單。
- 27 集合、86 索引為 10/5 完整驗證結果；10/7 核對 5 筆 migration 全部 succeeded、users 有 demographics。現行契約是原 v4 加 test_data/schema_test_profile.py overlay，**不是僅四筆 migration 的原 v4**。
- behavior_events、product_embeddings、ai_requests、recommendation_logs 在 10/7 均為 0；不據此推定記憶體快取狀態。
- 政策：PURCHASE=4、ADD_TO_CART=3、SEARCH=2、PRODUCT_VIEW=1；2 分不是收藏。
- 10/5 資料生成、交易試寫回滾、正式匯入、完整讀回及每月金額比對已通過；不重複生成／匯入，不重設庫存。這不是模型、登入或全站 UAT 完成證據。

## GitHub／本機界線（10/7）

- main：066e9da，PR #9 查詢手冊已合併；PR #1／2／3／4／6／7 已合併。
- JEFF PR #8：e7df815，4 份文件、無功能程式；檢查通過、可合併但未合併。
- PR #5 計分候選仍為草稿，由 JEFF 決定；PR #10 Network Access 文件未合併。
- 本機有超市前台、測試資料生成器／overlay／證據、SAM 工作文件等未提交工作。**Atlas 已匯入，不代表 GitHub 已交付**。不可混入他人的異動、強制覆蓋或直接切換髒工作目錄。

## SAM 下一步（依序）

1. 整理並提交上述本機交付，補最新文件入口。
2. 更新現行 schema 檢查器；main 仍按舊 validator／四筆 migration，會對現在資料庫報差異。保留歷史 migration checksum。
3. 與 JEFF／HEN 定義後台寫入契約 D5，以及補貨／促銷／期間比較的 AI 白名單資料。
4. 補 D4 行為事件測試資料、少量私有登入測試帳號。
5. 以同批標準答案完成畫面/API 對帳及邊界測試。

JEFF 規格須補：有效訂單分子／全部範圍訂單分母、有效可售 SKU／最低價條件、更新 D1～D3 已有資料狀態，以及本機推論與整站網路依賴的區別。現有 summary_metrics 不足以支援完整商品與趋势問答。

## 按需查閱

- [最新推送審查與 SAM 缺口](JEFF_PUSH_REVIEW_2026-10-07.md)
- [測試資料規範](TEST_DATA_SPEC.md)／[匯入證據](TEST_DATA_IMPORT_2026-10-05.md)
- [SAM 工作與預計項目](../專題進度/至今SAM完成的工作與預計項目_2026-10-05.md)
- 備份任務才讀 [BACKUP](BACKUP.md)：機密私有／加密方案仍待決定；未核實共用切換及雲端完成前不得複製。固定連結不變；同一阻礙不重複通知。

English: Start here; read only task-relevant evidence. Historical documents remain intact. Distinguish local work, GitHub delivery, Atlas data, and acceptance. Recheck mutable state before acting; never reinterpret historical plans as completed work.

## 本次接續入口

2026-10-07 已在獨立 worktree 整理 SAM 本機資料，檢查器改用 schema_active_v4；詳見 [交付結果](SAM_DELIVERY_2026-10-07.md) 及 [契約提案](SAM_DATA_CONTRACT_2026-10-07.md)。此更新不代表 D4、登入或畫面驗收完成。

## 最新交付與團隊執行入口（本次發布）

本分支已補今日清單、具名殘留責任與GitHub全專案盤點，並整合SAM超市前台；新版資料checker/工具/證據已交付本分支，main合併狀態見 [發布紀錄](SAM_PUBLICATION_2026-10-07.md)。

接續工作只讀 [專案進度](PROJECT_PROGRESS_2026-10-07.md)／[殘留責任](PROJECT_BLOCKERS_2026-10-07.md)，依編號處理，不重掃舊計畫。D4由SAM負責，入庫端到端需JEFF先確認事件消費隔離與HEN先確認觸發；私有登入由SAM配置，需HEN/JEFF先交授權/撤權接口；稽核新migration由SAM，需JEFF先確認D5。SAM午後AI時間留EDI，晚上上課才轉回LLM_PJ。
