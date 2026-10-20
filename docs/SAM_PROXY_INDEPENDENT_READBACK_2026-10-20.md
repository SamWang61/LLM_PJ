# SAM 代理工作：獨立讀回與離線備援｜2026/10/20

本頁記錄 Codex 在 SAM 工作站完成的技術操作。時間均為台灣時間（UTC+08:00）。代理操作不等於 SAM、REN 或 JEFF 本人簽收，也不等於手機實機、另一台電腦或現場投影驗收。[12 項執行順序](../專題進度/待結案12項_執行順序與分工_2026-10-20.md)的其餘關卡仍按各自證據結案。

## N15：版本與 PR

- 01:18 核對並合併 [PR #125](https://github.com/SamWang61/LLM_PJ/pull/125)，main 合併提交 `4a8018177623049cba043a82da6eb3e8d4941919`；12 項順序及代理清冊已入版控。
- 01:19～01:25 審查 [PR #121](https://github.com/SamWang61/LLM_PJ/pull/121) 的隔離界線、程式、啟動檔和測試。它原有的 N14 操作卡連結在更名後失效，已改指 `N14_REN_異機復原_2026-10-19.md`。本機檔案政策 833 檔、649 個 UTF-8 文字、0 錯誤；隔離測試 3 通過。首次 CI 在臨時 MongoDB 容器階段失敗；同一提交重跑的 [Actions #660](https://github.com/SamWang61/LLM_PJ/actions/runs/39293325112) 全步驟成功，包含真本機 MongoDB 交易。01:25 已合併，main `1b2fdcdaa887e88512aa7fc0b15efff3b3118251` 經遠端與乾淨 worktree 雙讀回一致。
- 01:26 再查開放 PR：[#5](https://github.com/SamWang61/LLM_PJ/pull/5) 為歷史候選草稿；[#126](https://github.com/SamWang61/LLM_PJ/pull/126) 為另一輪正在進行的 SAM 代理明細，與 #121 已合併內容重疊，當時對 main 有 README 衝突。其後續整合須看最新 PR HEAD／CI；本頁不把它標成已合併。
- 01:21 公開 `https://vibecart-llmai.web.app/` GET 200，頁名為 VibeCart｜超級市場。這只證明當時首頁可讀；正式 revision、digest 和 Firebase release 須依控制平面當次讀回，不以 HTTP 200 或 main SHA 推定。

## N02／N04 前置：SAM 同機模擬

在 main 合併前已用同一整合版的 `Start-SRJ.ps1 -PreflightOnly` 依 SAM、REN、JEFF 順序執行；三份本機去敏報告分別產於 01:22:45、01:22:48、01:22:51，均為 **12/12**。檢查涵蓋一次性本機登入、後台角色允許／拒絕、商品與購物車頁；範圍為 `127.0.0.1`／`mongomock`，`atlas_contacted=false`、`named_acceptance=false`。報告留於操作者私有 `%LOCALAPPDATA%\VibeCart\SRJLocalSimulation\reports`；本頁不發布電腦名稱或一次性密碼。另三項自動隔離測試本機通過。

這是同一台 SAM 電腦的三角色相容性預演。H01～H09 交接、六個正式角色、兩台實體裝置、舊 cookie 撤權、REN／JEFF 本機執行與具名接收均未因此完成；N02／N04 保持待結案。當前公開固定帳號的既有驗收應看其原始紀錄，不把隨機本機帳號當正式帳號。

## N13：Atlas 唯讀核對

約 01:24 以 MongoDB Atlas 連接器讀回專案 `vibecart_ai`：叢集 `vibecart-ai-free` 未暫停、狀態 `IDLE`；網路存取清單共 **4 條 `/32`**，沒有 `0.0.0.0/0`。一條註明 VibeCart 專用 NAT，兩條註明開發工作站，一條沒有用途註解。連接器這次未提供各條到期日，也未證明三條工作站出口仍必需；因此不刪除規則、不宣稱 N13 完整結案。這次沒有資料庫寫入。

## N16／N17：素材與離線備援

- 01:27 依 `簡報文件/screenshots/S01-S12_取證索引_2026-10-18.json` 逐張重算：**20/20 PNG 存在且 SHA-256 相符**，主圖 ID 為 S01～S12。索引仍是 10/18 的原始取證版本，具名覆核欄未簽；不可把舊截圖稱為 10/20 正式映像的當次畫面。
- V5 PPTX SHA-256 仍為 `43374f71c5e42fdc1725f38a8ac69ea0e2ccc696f6238ebb06425e58e00d7203`。乾淨 worktree 的 PDF 起初是 Git LFS 指標；以精確路徑 `git lfs pull` 取得實體後，SHA-256 為 `c5555c2a54d8a4200fd79fb8073d0fa5af691b40b13a4e031ddf9f8f6dc4535d`，與既有交付紀錄一致，工作樹保持乾淨。
- 01:27 以 main `1b2fdcdaa887e88512aa7fc0b15efff3b3118251` 重建 ZIP：40 個內容檔、9,917,409 bytes，SHA-256 `45bd30eac3ea21b8d1c7da08951817b7a4ab10f48bcebe74bfce996dbc4490c6`。全新目錄還原後 **40/40 雜湊驗證通過**；本機 ZIP 與還原目錄留在 `%TEMP%`。另將 ZIP 以不覆蓋既有包的檔名 `VibeCart_V5_offline_main-1b2fdcd_20261020.zip` 複製到主專案 `簡報文件/離線備援/`，複製後 SHA-256 相符。ZIP 依檔案政策不提交 GitHub；可由已推送工具與指定提交重建。新 ZIP hash 與舊版不同是來源提交及 manifest 已更新；PPTX／PDF 本體 hash 未變。
- 尚缺三人逐段具名覆核、實體斷網、第二台電腦開檔、投影及實際講者計時。N16／N17 的技術核對完成上述部分，原關卡維持待結案。

## 本輪限制

本機另嘗試完整交易腳本一次，隔離 Docker 容器與 fixture 均清理成功，但該專用 Python 環境缺 `langchain_core`，網站測試於收集階段報 5 個匯入錯誤，故**不計為交易通過**；GitHub CI 同提交重跑成功是獨立證據。本輪未部署 Cloud Run／Firebase、未改 Atlas 業務資料、未執行正式庫故障或會員 session 回收。
