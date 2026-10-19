# H08 手機尺寸模擬初版草稿（2026-10-19 08:27，台灣時間）

此目錄保存第一輪 Chrome headless／Playwright 擷取，供比較與追溯；[定稿](../REN_H08_手機尺寸模擬_2026-10-19_定稿/README.md)是簡報引用版本。圖片來自本機 `127.0.0.1`、`mongomock` 隔離商品與帳號，並非 2026/10/18 iPhone 實機畫面、正式站操作、iOS 鍵盤或 REN 本人接收。當輪未擷取公開網站首頁，亦未連接 Atlas。

初版商品直向圖停在頁面上部，尚未把數量輸入焦點完整納入畫面；後續 v2 與定稿調整了該畫面位置。保留原始 PNG，不以較晚結果回寫草稿。

| 項目 | 圖片 |
|---|---|
| S03 商品直向／橫向／錯誤數量 | [直向](S03-product-portrait-focus.png) · [橫向](S03-product-landscape.png) · [錯誤數量](S03-invalid-quantity.png) |
| S04 錯誤登入／Email 焦點 | [錯誤登入](S04-invalid-login.png) · [Email 焦點](S04-login-email-focus.png) |
| S05 購物車直向／橫向／不收款示範訂單 | [直向](S05-cart-portrait.png) · [橫向](S05-cart-landscape.png) · [示範訂單](S05-demo-order.png) |

每張圖的擷取時間、視窗尺寸、來源與 SHA-256 載於 [capture-records.json](capture-records.json)。截圖只能證明當時本機模擬畫面；H08 逐步實機結果與 H01～H09 具名簽收仍以[驗收矩陣](../../../docs/REN_H08_DEVICE_MATRIX_AND_RECEIPT_2026-10-19.md)為準。
