# S02 商品篩選列的標題排版｜2026-10-18

在 768×844 的桌面 Chrome 模擬 viewport 開啟 [Firebase Hosting 首頁](https://vibecart-llmai.web.app/)，點「瀏覽商品」到 `#products`。正式 Cloud Run 管理端同日讀回 Ready／100% 修訂 `vibecart-web-00013-ds5`，來源標籤 `80513a9`，映像 digest 與[部署紀錄](../../docs/SAM_RELEASE_2026-10-18.md)相同。此為瀏覽器 viewport，並非平板實機。

正式頁面的分類篩選佔據同一行，將「超市商品」標題擠到 **47×169 px**，逐字換行：[原始畫面](S02-tablet-before-20261018.png)，SHA-256 `FE7E2DEAC61864E9752915C7B3B5BEA3F54CDF71B3A422DDD0E9E4ED526E2922`。把本分支 `main.css` 注入同一頁面作本機預覽後，標題成為 **691×42 px**，位於篩選列上方，文件水平溢出 0：[CSS 預覽畫面](S02-tablet-css-preview-20261018.png)，SHA-256 `4683516604F123E2603548FA8AD9BD98DC6E31978B4DBC1C1A3F419AFE729C54`。

1280×844 的桌面瀏覽器有相同問題：正式標題 **64×253 px**，見[桌面原始畫面](S02-desktop-before-20261018.png)，SHA-256 `EC9D9D66ECE2D055C3FA583C41DB1337E1F47B1E8578AD27AD0ACF00A7EA69AF`；注入修正 CSS 後為 **1152×63 px**，見[桌面 CSS 預覽](S02-desktop-css-preview-20261018.png)，SHA-256 `EADC29E9B80E9CCD93B8922C78D8C0E74B356A3BC8D9333A4E16166A79DE157A`，水平溢出 0。

修正只對 `#products .section-head` 改為上下排列，涵蓋各寬度而不影響其他區塊。上列「CSS 預覽」是**本機注入**；零流量 Cloud Run `vibecart-web-00014-kq8` 是僅修正平板的第一版映像，桌面仍逐字換行。

**01:45–01:48 雲端預覽覆核：**最終來源 `1d2abf2cfa7465636e49474062e11f6aca571dda` 的 Cloud Build `f0f1fbc2-2980-477e-8a77-d9eb467ad503` 成功，映像 digest 為 `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b`。Cloud Run `vibecart-web-00015-nlk` Ready，標籤 `pr56-1d2abf2` 承接 **0%**；正式 `vibecart-web-00013-ds5` 仍承接 **100%**。[零流量預覽](https://pr56-1d2abf2---vibecart-web-m44ncgz5ta-de.a.run.app/)的 `/`、`/auth/login`、`/health/live`、`/health/ready` 均回 200。GitHub [CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39055003280) 對相同 head 成功。

在預覽本身點「瀏覽商品」，Chrome 模擬 320、375、768、1280 px 四種 viewport 均回 200，`scrollWidth=innerWidth`；標題寬×高依序為 288×42、338×42、691×42、1152×63 px。檢視[768 px 雲端畫面](S02-tablet-cloud-preview-20261018.png) SHA-256 `C223F0D89A530DBAA31AABABA300DA751F361C3336CD6CA5158D3DECD25A4545` 與[1280 px 雲端畫面](S02-desktop-cloud-preview-20261018.png) SHA-256 `E7C534B36E4F855F64523FFB6D2DA4DC310E70418A93C81C0B5DA93B1D35D28D`，標題皆位於篩選列上方且橫排。手機／平板實機與具名簽收尚未完成；正式切流量前仍須依 D4 閘門處理新映像 consumer 同版隔離核對。

**01:58 正式站後續：**同映像 D4 隔離對照及撤權通過後，Cloud Run `vibecart-web-00015-nlk` 已讀回 100%，Firebase Hosting [正式站](https://vibecart-llmai.web.app/)四個公開檢查路由回 200。Chrome 在正式站 320、375、768、1280 px 模擬 viewport 均無水平溢出，標題與零流量預覽相同為橫排；[768 px 正式畫面](S02-tablet-live-20261018.png) SHA-256 `C223F0D89A530DBAA31AABABA300DA751F361C3336CD6CA5158D3DECD25A4545`、[1280 px 正式畫面](S02-desktop-live-20261018.png) SHA-256 `B834974A3FAECA8E209CB9F2E9580244B37910DC63F87BDBB78A08C4A63ADF98`。實機、其他操作流程及具名簽收仍待補。
