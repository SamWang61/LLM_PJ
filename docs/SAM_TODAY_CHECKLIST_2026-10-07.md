# SAM 今日工作清單｜2026-10-07

時區：Asia/Taipei。負責人 SAM。最新盤點以 GitHub 即時回讀與本機證據為準；不將資料庫已匯入、分支已推送、PR 已合併及全站已驗收混為一談。

## 今日完成

- [x] 先讀 CURRENT_CONTEXT 與必要交接／專項文件，核對 main=066e9da；使用獨立 codex/sam-delivery-20261007 worktree，未切換或覆寫原髒工作目錄。
- [x] 整理已完成的 SAM test_data：固定種子生成器、人口 overlay、測試、清冊、標準答案與摘要證據；既有 600 會員／3000 demo 訂單／8969 明細不重複匯入，未重設庫存。
- [x] 整理 supermarket 商品／來源資料、匯入及核對工具與歷史報告；私有設定、快取、復原快照及大型完整訂單資料不推送。
- [x] 新增 schema_active_v4.py 作為現行 schema 入口，檢查器改認五筆 migration 及 users demographics／三集合 batch 欄位；未知／缺失／失敗 migration 仍判失敗。
- [x] 保持歷史 migration 與 overlay 原始位元不變；.gitattributes 關閉 overlay 換行轉換，保護 checksum。
- [x] Atlas 唯讀核對通過：27 集合、86 索引、12 項關聯、五筆 succeeded；第五筆 checksum 相符，前後筆數一致。沒有執行資料庫生成、migration、匯入或回寫。
- [x] 補 D5／AI 白名單資料契約提案：權限、CSRF、狀態轉移、版本衝突、冪等、稽核與交易／外部退款界線、期間比較、零分母與資料上限；核對實際 product_name、available_quantity、safety_stock 欄位。
- [x] 三方分工更新：JEFF=AI/後台；HEN=會員/購物；其餘（含前台/RWD、部署協調、資料測試、整合驗收）=SAM。
- [x] 即時查證 HEN/JEFF 均具 GitHub Write，無待接受邀請；不再以 HEN 未接受邀請當作阻礙。
- [x] 整合 SAM 超市前台本機差異：超過200商品完整分頁（24/頁）、大/小類篩選、搜尋、SKU規格、圖片與來源、替代圖片、本機入口。採差異合併保留 main 後台 CSS；未將其他人的 AI/會員新功能算入 SAM 成果。
- [x] 補五筆 migration／舊 validator 回退回歸案例；網站61項＋獨立 fixture 9項，共70項離線案例通過（以本次最終執行為準）。既有專項28項含重疊，不另加總。
- [x] 補齊必要 SAM 審查／清冊文件，修復私有快照的失效連結；文檔不宣稱快照已公開。
- [x] 建立今日清單、具名殘留問題及依 GitHub 的全專案進度與先後順序，更新 README／文件中心／CURRENT_CONTEXT。

## 交付與證據

本次內容集中在本分支；推送、PR、CI 與寄信完成狀態另記 [發布紀錄](SAM_PUBLICATION_2026-10-07.md)。核心提交 62beaa7；後續前台／盤點提交以該紀錄為準。

- [現行資料庫讀回](inventory/SAM_DATABASE_CURRENT_2026-10-07.json)
- [GitHub盤點快照](inventory/PROJECT_GITHUB_SNAPSHOT_2026-10-07.json)
- [資料契約提案](SAM_DATA_CONTRACT_2026-10-07.md)
- [最新進度盤點](PROJECT_PROGRESS_2026-10-07.md)
- [具名殘留問題](PROJECT_BLOCKERS_2026-10-07.md)

## 今日資源安排

依 SAM 指示：今天中午過後，SAM 將今日 AI 時間先留給 EDI 專案；晚上上課時才開始將 AI 資源轉回 LLM_PJ。本文件不是自動排程或晚上完成時限承諾。HEN/JEFF 可先處理自己的前置項目，SAM 晚上接續整合與驗收。

English: SAM completed the local data/document delivery, current five-migration checker, read-only audit, contract proposal, storefront integration, tests and team inventory. Afternoon AI time is reserved for EDI; LLM_PJ resumes during the evening class. Remaining acceptance is tracked separately.
