# 本人操作與截圖上傳 / Personal acceptance evidence

日期：2026-10-19（Asia/Taipei）。依專案負責人要求，REN、JEFF、SAM 各自用電腦或手機模擬操作並上傳截圖，作為本人驗收證據。郵件提醒不等於本人已執行或接收。

## 操作與上傳順序

1. 先看 [未完成清單](../../../專題進度/專案未完成工作清單_2026-10-18.md)及[具名表](../../../專題進度/2026-10-19_具名接收與異機復原表.md)，由 SAM 提供當下部署 revision／source SHA／digest。正式入口是 <https://vibecart-llmai.web.app>。
2. 依本人主責逐項操作。REN：H01～H09、S03～S05 的會員／購物／撤權；JEFF：唯讀後台／推薦／目前 AI 狀態、consumer、S06～S08；SAM：部署與資料對帳、錯誤處理、備份／離線展示及最後整合。
3. 在本目錄下建立 `REN/`、`JEFF/` 或 `SAM/` 個人子目錄，放原始 PNG/JPEG 與一份依 [填寫模板](TEMPLATE.md)完成的紀錄。建議檔名 `REN_H02_20261019_1730_01.png`；時間採台北時間，每張圖有對應測項。
4. 提交到本人的 GitHub 分支並建立 PR；在[具名表](../../../專題進度/2026-10-19_具名接收與異機復原表.md)填本人姓名、實際時間、版本、結果與證據連結。失敗也上傳，寫重現步驟；未測記原因及下一時段。

## 取證界線

- 每張圖附：測項編號、電腦／手機機型、OS／瀏覽器完整版本、URL、角色、來源 SHA／revision、步驟、預期與實際結果、檔案 SHA-256。以原始畫面為準，不拼貼或製造結果；敏感內容在取圖前隱藏。
- 電腦瀏覽器的手機尺寸模擬可列為模擬證據；需要手機實機的 H08／N12 及第二台電腦的 N14 仍須在指定設備親自測試，不能用模擬代填。
- 不上傳密碼、cookie、token、金鑰、含憑證 URI 或明文備份；固定帳密由既有私有交付取得。
- 加購／demo checkout／撤權／故障測試先由 SAM 配置隔離環境及測後清理；不對正式服務或正式資料庫製造停機，不重匯 D1～D4。
- 正式真模型／自由提問、D5 管理寫入、真金流與物流仍依現行清單列下一階段，不為展示強行開啟。

English: Each owner must personally execute and record their tests, upload original screenshots under their own folder, and submit a PR with name, time, version, results and evidence. Label desktop mobile simulation accurately; it cannot replace physical-device or off-device recovery requirements.
