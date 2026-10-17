# 10/18 交付準備計畫

**10/17 狀態**：JEFF T5 的 PR #23 已合併進 SAM PR #21；S06～S08 依[截圖規範](screenshots/README.md)留在本簡報 PR #19。雲端預覽仍封鎖後台，線上 Claude／BGE 維持關閉；T5 本機模型數值須以來源 SHA 與執行環境標示。D5、6+4 推薦、排程及 D4 正式匯入仍未完成，不能以規格或 CI 取代操作驗收。詳見 [10/17 核對](https://github.com/SamWang61/LLM_PJ/blob/codex/sam-final-baseline-20261016/docs/SAM_JEFF_1017_HANDOFF.md)。

以下為提議時程，尚非各組員已承諾的完成時間。指導講師為 [簡志璁 Alvin](mailto:fcaibialvin@gmail.com)；報告時長、評分規則與最終簽收人待補。

| 日期 | 主責 | 先決條件／提供人 | 產物與完成條件 |
|---|---|---|---|
| 10/15 四 | [SAM](mailto:cashsam@gmail.com) | 既有文件及main | 建立簡報目錄、12頁內容、架構、素材盤點與截圖標準；本輪交付 |
| 10/16 五 | [JEFF](mailto:eff841117@gmail.com) | AI／後台可驗版本與配置，由[JEFF](mailto:eff841117@gmail.com)提供 | S06～S08、模型啟用／規則退回說明、consumer 清單與同輸入結果 |
| 10/16 五 | [REN](mailto:chen2000401@gmail.com) | 會員／購物與事件接口，由[REN](mailto:chen2000401@gmail.com)提供 | S03～S05、成功與失敗步驟、最終commit與訂單結果 |
| 10/17 六上午 | [SAM](mailto:cashsam@gmail.com) | [JEFF](mailto:eff841117@gmail.com)／[REN](mailto:chen2000401@gmail.com)功能版本及契約先交 | 整合 final SHA；同版離線CI、角色、庫存／訂單／KPI對帳與遠端功能驗收 |
| 10/17 六下午 | [SAM](mailto:cashsam@gmail.com)（簡報整理與前台／RWD）；各功能主責核對 | 同版驗收與S01～S12素材 | PPTX排版、素材註記、講稿與展示備援；[SAM](mailto:cashsam@gmail.com) 核對前台／RWD |
| 10/18 日 | [SAM](mailto:cashsam@gmail.com)協調；最終簽收人待確認 | 最終PPTX、版本、URL、驗收記錄 | 全組排練、凍結展示版本、簽收；未通過項目明列限制 |

## 專案完成條件

- README／架構／setup／環境範例能對應同一交付 SHA；新環境可啟動，無秘密進Git。
- Dockerfile可建置與啟動，compose用途清楚；CI有同版成功run，不只存在工作流。
- 商品、會員、SKU購物、示範訂單、推薦與後台具操作截圖及必要API／資料讀回；真付款出貨不在目前教學範圍。
- 模型型號、啟用狀態與規則退回可辨識；無實測的AI效果不列完成。
- 部署URL與revision一致，匿名／customer／admin權限及撤權完成核對。
- D4如列交付範圍：[JEFF](mailto:eff841117@gmail.com)列全部consumer、[REN](mailto:chen2000401@gmail.com)交事件接口，[SAM](mailto:cashsam@gmail.com)先部署並遠端驗synthetic隔離，再正式apply／讀回／重送；未完成就列未完成，不為趕簡報跳過前置。
- PPTX與操作素材可離線展示；來源、負責人、限制和完成項目經組員核對。

本輪不修改功能、不重匯入資料、不代替同學做簽收；後續依上表補證據與定稿。
