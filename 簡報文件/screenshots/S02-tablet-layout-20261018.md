# S02 商品篩選列的標題排版｜2026-10-18

在 768×844 的桌面 Chrome 模擬 viewport 開啟 [Firebase Hosting 首頁](https://vibecart-llmai.web.app/)，點「瀏覽商品」到 `#products`。正式 Cloud Run 管理端同日讀回 Ready／100% 修訂 `vibecart-web-00013-ds5`，來源標籤 `80513a9`，映像 digest 與[部署紀錄](../../docs/SAM_RELEASE_2026-10-18.md)相同。此為瀏覽器 viewport，並非平板實機。

正式頁面的分類篩選佔據同一行，將「超市商品」標題擠到 **47×169 px**，逐字換行：[原始畫面](S02-tablet-before-20261018.png)，SHA-256 `FE7E2DEAC61864E9752915C7B3B5BEA3F54CDF71B3A422DDD0E9E4ED526E2922`。把本分支 `main.css` 注入同一頁面作本機預覽後，標題成為 **691×42 px**，位於篩選列上方，文件水平溢出 0：[CSS 預覽畫面](S02-tablet-css-preview-20261018.png)，SHA-256 `4683516604F123E2603548FA8AD9BD98DC6E31978B4DBC1C1A3F419AFE729C54`。

1280×844 的桌面瀏覽器有相同問題：正式標題 **64×253 px**，見[桌面原始畫面](S02-desktop-before-20261018.png)，SHA-256 `EC9D9D66ECE2D055C3FA583C41DB1337E1F47B1E8578AD27AD0ACF00A7EA69AF`；注入修正 CSS 後為 **1152×63 px**，見[桌面 CSS 預覽](S02-desktop-css-preview-20261018.png)，SHA-256 `EADC29E9B80E9CCD93B8922C78D8C0E74B356A3BC8D9333A4E16166A79DE157A`，水平溢出 0。

修正只對 `#products .section-head` 改為上下排列，涵蓋各寬度而不影響其他區塊。320、375、768、1280 px 的公開首頁及商品錨點，本輪瀏覽器模擬於載入穩定後均無水平溢出。上列「CSS 預覽」是**本機注入**；零流量 Cloud Run `vibecart-web-00014-kq8` 尚是僅修正平板的第一版映像，桌面仍逐字換行。最終 CSS 需新建映像與修訂、重讀回四個 viewport，並依 D4 閘門驗 consumer 隔離後才可切正式流量；手機／平板實機及具名簽收仍未完成。
