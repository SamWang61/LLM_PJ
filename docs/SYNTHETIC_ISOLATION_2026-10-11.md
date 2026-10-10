# D4 synthetic 隔離修正與正式匯入前置｜2026-10-11

使用者選擇「先完成並部署 synthetic 隔離，再正式匯入」。本輪先補程式；GitHub 推送不代表現有網站或排程已換版，不建立假的 isolation evidence。

## 已補程式

共用 `behavior_scope.py` 的 production 查詢排除 `metadata.synthetic=true`、非空 `metadata.synthetic_batch_id` 及 `metadata.exclude_from_attribution=true`。未帶測試標記的正常事件維持可讀。條件在排序／limit 前套用，避免大量測試事件擠掉真實事件。

| 消費路徑 | 修正／驗證範圍 | 部署狀態 |
|---|---|---|
| 後台推薦監控 | dashboard 的 production 查詢；1,001 筆較新 synthetic 不擠掉正常事件 | 待正式環境換版與驗證 |
| 前台會員推薦（v4／legacy） | user_id 與隔離條件同時套用；規則推薦及 BGE 圖形再次過濾事件 | 待正式環境換版與驗證 |
| 評分／衰減排程 | 目前分支未實作部署中的排程；不能以共用 helper 代替排程驗收 | JEFF／SAM 核對實際執行位置後接線 |
| 正式成效歸因 | 目前分支無獨立執行的歸因消費程式；不能宣稱已隔離 | JEFF／SAM 核對所有外部消費者 |

7 項新增離線回歸驗證各標記、監控與會員查詢先過濾再 limit、owner 條件、規則分數不受影響、直接呼叫 LangGraph 時 synthetic 不傳入 BGE。

驗證：完整網站＋test_data離線測試94項通過；最後調整圖形過濾順序後再次執行7項新增測試，全數通過。第一次完整執行曾有14項scrypt記憶體配置錯誤；改用低負擔的cmd啟動後，未改密碼雜湊或放寬測試即重跑通過。正式網站／真模型／排程驗收仍未完成。

## Atlas 與部署限制

[最新正式匯入前檢查](inventory/D4_FORMAL_PREFLIGHT_2026-10-11.json)：預期 1,240 筆、已存在 0、缺少 1,240、committed=false。沒有正式匯入。Atlas 管理插件需要重新登入；既有私有 PyMongo 連線可讀回資料。

尚未取得正式網站網址、部署主機／服務與排程位置，已向使用者詢問。部署前須核對實际啟動版本、所有使用同一 `vibecart_ai` 的消費者及未部署服務是否確實停用。SAM 驗證各路徑後才產生真實 isolation evidence、執行 gated apply、verify 與重送冪等驗證。稽核 migration 草案仍未定案，不隨 D4 匯入部署。

主責：SAM 接續修正、部署驗證、匯入及工作總表；前置責任：JEFF 提供評分／歸因消費者，部署位置由 SAM／使用者確認。保留歷史 migration、D1～D3 與庫存。
