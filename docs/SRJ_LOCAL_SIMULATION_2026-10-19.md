# S／R／J 單機模擬預演紀錄｜2026/10/19

本紀錄只收斂「電腦手機尺寸模擬及一鍵本機環境」範圍，對照[原具名接收表](../專題進度/2026-10-19_具名接收與異機復原表.md)與[三人單機操作卡](../單機模擬/README.md)。**原表的實際手機、REN 異機復原、正式遠端故障／交易、本人具名簽收欄仍未由此結案。**

## 本機已驗

- 對 GitHub main `f30254562bb3f9dfc4b7cb2db1dbb82b1515cfba` 唯讀讀回；[同 SHA Actions 執行](https://github.com/SamWang61/LLM_PJ/actions/runs/39244752477)完成且 success。此狀態是本輪讀回，不能推論 Cloud Run／Firebase 也在同 SHA。
- 正式 HTTPS 站在 SAM 既有工作階段以電腦 Chrome **390×844** 開啟：首頁、`/admin/`、`/product/02f9efd17210150f2eea7274`、`/cart` 可讀。首頁與商品頁 `documentElement.scrollWidth == clientWidth`；商品 79 元、SKU 庫存 95，數量輸入 0 為無效，改回 1 有效。商品頁 **844×390** 也無橫向溢出。購物車在本次只讀時為空；沒有建立正式訂單或改庫存。
- 正式後台在該既有工作階段可開總覽；顯示資料庫已連線，Local 推薦、雲端洞察、AI 比較頁可讀。頁面顯示雲端模型未設定／未啟用，BGE 未安裝退回規則；標題文字不視為真模型已部署。未以其他角色登入、未做手機實機或本人簽收。
- 三個一鍵腳本各在 SAM 本機的 Windows PowerShell 5.1 `-PreflightOnly` 執行：SAM、REN、JEFF 均 **12/12** 本機登入／角色權限／商品／購物車檢查通過，去敏報告各寫入 `%LOCALAPPDATA%\VibeCart\SRJLocalSimulation\reports`。實際 localhost HTTP 200，服務可正常停止。隔離、不漏密碼及記憶體內同 `checkout_id` 重送只建一單／庫存只扣一次共 **3 個自動測試通過**；此處仍沒有 MongoDB 真交易。這是**單台電腦的相容性預演**；REN／JEFF 的個人電腦尚須各自雙擊實測。
- Atlas 連接器當次唯讀讀回 `vibecart_ai` 28 集合、白名單四條 `/32` 且無 `0.0.0.0/0`；只證明此範圍的目前狀態，不代替 Cloud Run 100% revision、所有 consumer 或交易驗收。V5 PPTX SHA-256 `43374f71c5e42fdc1725f38a8ac69ea0e2ccc696f6238ebb06425e58e00d7203`，PDF SHA-256 `c5555c2a54d8a4200fd79fb8073d0fa5af691b40b13a4e031ddf9f8f6dc4535d`；S01～S12 主資料夾共 20 PNG。離線投影與計時尚未做。

## 模擬項目的結案方式

三人各自雙擊對應 `Start-*.cmd`，確認 12/12 報告及 localhost 網站，再依 [README](../單機模擬/README.md)逐項操作、保存不含密碼的時間／URL／截圖／結果。只有**各自個人電腦上的模擬項目**能在取得其報告後標「模擬結案」。SAM 本機預演不替 REN／JEFF 個人電腦結案；也不回填原表的本人簽收。原版次變動時須重新驗對照，不沿用這份預演。
