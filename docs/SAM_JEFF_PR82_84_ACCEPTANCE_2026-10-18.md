# SAM：JEFF PR #82～#84 整合與驗收｜2026-10-18

檢查點：2026/10/18 16:30（台北）。主責：[SAM](mailto:cashsam@gmail.com)，依使用者授權接手[JEFF交接](../討論的相關記錄/JEFF_to_SAM_2026-10-18.md)、修正、測試及合併，不等待其他人確認。

## 程式交付

| PR | 本輪結果與範圍 |
|---|---|
| [#82](https://github.com/SamWang61/LLM_PJ/pull/82) | head `d71d894` 通過CI後合併為 `e47fb0c8717b29273f8039e3edac24e40558d41e`。三AI旗標讀環境、預設false、無效值拒絕；保留URI／secret／preview／acceptance guard。精簡／AI映像可選，合併不觸發部署。 |
| [#83](https://github.com/SamWang61/LLM_PJ/pull/83) | head `f3af26a` 通過CI後合併為 `bfff03420f5089c39323227d49b45dc26a7d95a8`。政策4／3／2／1、SEARCH與legacy映射；補settings／weights錯誤容器與NaN／Infinity防護，7新回歸，政策測試共17項。 |
| [#84](https://github.com/SamWang61/LLM_PJ/pull/84) | 已改base為main，保留#83安全修正及雙方CHANGELOG。個人推薦只排除synthetic／batch標記，保留真實會員示範購買；查詢仍先限定user_id、排除synthetic，再sort／limit。`production_*`與監控／歸因維持排除示範購買。實際合併SHA／時間以此PR紀錄為準。 |

本次#84修正後執行來源 `7e7b57826041c1c05c31e50410f6e55eb0f612aa`，與已驗整合候選 `8c0fe9f1db582de1829d4a352253019ef0d9d47a` 的52檔白名單封裝**逐byte相同**，tar.gz SHA-256 `9d0544fb3393566c759546feb46da421e9e3f4202f36b59ccff4d0e04defd285`。測試目錄與執行程式亦無差異；中間新增的REN #88只影響文件／素材。相同封裝比只比短SHA更能說明本機映像對應哪一版原始碼；本機Docker image ID不是遠端registry digest。

## 實際測試與驗收

- **239 passed／0 skipped**：以一次性、credential-free localhost MongoDB replica set執行完整網站及admin audit migration測試；包含真交易、角色、冪等、故障回滾、synthetic隔離、推薦與AI fallback。測後只剩admin／config／local，測試庫與該容器已清理。
- **32 passed**：合成資料與來源封裝／交付對帳工具；無Atlas寫入、無D1～D4重匯。
- 兩種映像實際build成功（快取建置6.11秒／3.45秒）；本機inspect大小54,442,294／505,795,251 bytes。兩者以真正Gunicorn啟動、HTTP驗live200、admin403、登入POST403，程序與容器均清理。這是預覽guard／boot證據，沒有把liveness當資料庫ready。
- AI映像斷網、2Gi／1CPU，實際BGE載入及推薦輸出512維；示範購買可形成個人推薦，加入60筆synthetic不改結果。首次載入與本次流程15.477秒，非Cloud Run冷啟動或穩態延遲。最初探針用錯假hostname被既有cluster guard拒絕，修正測試資料後重跑通過；未放寬guard。
- Claude固定intent、權限、失敗fallback等離線測試通過，但未呼叫真Claude。沒有把替身模型或本機結果當線上模型證據。

[機器紀錄](inventory/SAM_JEFF_PR82_84_ACCEPTANCE_2026-10-18.json)含52檔相對路徑／SHA-256、同版封裝、測試／容器與唯讀設定。CI以各PR最新head為準；本文件與進度隨#84交付。

## 部署與V5界線

16:22唯讀雲端讀回：正式 `vibecart-web-00019-phf`、私有 `vibecart-acceptance-pr21-00011-2hq` 仍來源 `e000d952d22a64b568903641893f4ffdc71accd3`、同digest `sha256:7199fa08c711917a80e5f54dbfd580ed96f3ef632bda7337b4aa2bde2325c992`，各服務現有流量100%；**本輪未部署或切正式流量**。兩者無 `BEHAVIOR_SYNTHETIC_BATCH`；`ANTHROPIC_API_KEY` secret仍HTTP404。

程式合併不等於線上行為更新。真Claude、同版私有雲端BGE／角色／四個intent／fallback／畫面驗收尚缺，線上AI與自由提問仍關閉；secret由有權者在Secret Manager輸入，不在聊天／Git／命令列放Key。完成私有驗收與正式發布決策後才可稱線上啟用。

V5仍14關卡、2完成／12待結案；N07～N10仍是下一階段，不把程式PR合併或本機真BGE變成全站簽收。N14異機金鑰與每日流程等既有缺口保留。專案主目錄同步採逐檔備份與來源核對，原分支／未提交內容保留；乾淨交付工作樹才是本輪完整測試版本。
