# REN H08 手機尺寸模擬截圖｜2026-10-19

2026/10/19 08:29（Asia/Taipei）以本機 Chrome headless／Playwright 的 390×844 直向及 844×390 橫向視窗取圖。這是**桌面瀏覽器的手機尺寸模擬**，不是 iPhone 實機或 iOS 原生鍵盤，也不是陳仁千本人接收。每張原始 PNG 的 URL、時間、尺寸與 SHA-256 見 [capture-records.json](capture-records.json)。

| 畫面 | 來源與可觀察內容 |
|---|---|
| [S00 正式站首頁](S00-public-site-readback.png) | `https://vibecart-llmai.web.app/` 於 08:29 回 HTTP 200 的當下公開頁面；不代表 10/18 14:00 或 17:00 的實機狀態。本輪稍早另曾回 503，故保留兩次讀回。 |
| [S03 直向 SKU／數量焦點](S03-product-portrait-focus.png) | localhost `mongomock` 隔離商品與選定規格，沒有正式庫存寫入。 |
| [S03 橫向 SKU](S03-product-landscape.png) | 同一隔離商品的 844×390 視窗。 |
| [S03 錯誤數量](S03-invalid-quantity.png) | 輸入 `0`；HTML `checkValidity()` 為 false，呼叫 `reportValidity()`，未送出購物車。圖片顯示欄位值，不把未入鏡的瀏覽器提示冒稱可見。 |
| [S04 錯誤登入](S04-invalid-login.png) | localhost 虛構帳號輸入錯誤後，頁面顯示通用錯誤訊息；沒有使用真實帳號。 |
| [S04 Email 焦點](S04-login-email-focus.png) | Chrome 焦點框；**無 iOS 軟體鍵盤**。 |
| [S05 直向購物車](S05-cart-portrait.png)／[橫向購物車](S05-cart-landscape.png) | localhost 記憶體 fixture 一件隔離 SKU；沒有 Atlas 資料。 |
| [S05 示範訂單](S05-demo-order.png) | localhost 不收款示範訂單；`mongomock` 不驗證真 MongoDB 交易。 |

本機八張圖的 `documentElement.scrollWidth` 均未超過 `clientWidth`；此為上述視窗與畫面的版面讀值，不代替 iPhone 觸控、鍵盤遮擋、真遠端結帳或 H01～H09 本人驗收。臨時 fixture 只綁 `127.0.0.1`，自行到期關閉；正式站只做匿名 GET。重現腳本：[fixture](../../../scripts/run_h08_local_visual_fixture.py)／[capture](../../../scripts/capture_h08_mobile_simulation.cjs)。
