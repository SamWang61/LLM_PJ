# V5版本／部署／私有驗收證據｜2026-10-18

取證截至2026/10/18 05:58（台灣時間）。[SAM](mailto:cashsam@gmail.com)彙整；[REN](mailto:chen2000401@gmail.com)／[JEFF](mailto:jeff841117@gmail.com)仍須依範圍具名覆核。

## GitHub與正式部署

PR #65合併 `db4eb00d3ecdc89d586f3b77feac74d21b3a7150`、#67合併 `9ee4ec8b7b59d04d43148f51a0f729f6ab7dcf4a`；#71修正JEFF頁尾信箱，程式來源 `ff65eaef0f6db932f844893cf2f8dc42eac5b5f7`、合併 `fffa8aae87dff9af706dfcb3caf8ac31a8aa477c`，[CI 39070827406](https://github.com/SamWang61/LLM_PJ/actions/runs/39070827406) success。

Cloud Build `976b8ed9-c1d3-406b-afc1-567f83c36ffb`成功；51檔來源封裝hash `f31b961fafdc878fc6e8a7c962c673ef63bb98fb96584a3cca68ba1e5c3bf98a`。Pinned image：
`asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web@sha256:ba7d34787ffda32cb944022494c0dd5da64600df64ea05c49a79c41473404f5f`。

[05:57 Google APIs讀回](inventory/sam-delivery-cloud-20261018-current.json)：正式 `vibecart-web-00018-s59` **100%**、庫vibecart_ai；私有 `vibecart-acceptance-pr21-00007-wcd` **100%**、指定隔離庫vibecart_acceptance_pr21、專用IAM、匿名403。Hosting release1791982222797000／version c3772dcc7c906211未改，仍重寫至asia-east1/vibecart-web。Hosting／Run首頁與live／ready共6 GET皆200；這只是路由與健康，非全站簽收。零流量回退保留。程式／文件SHA分開記，文件更新不代表重新部署。

06:04再次鎖定遠端main 625f703，核對其40個變更檔與GitHub位元組差異0；51檔封裝與ff65eae部署來源差異0、重複封裝hash一致，見[來源重核報告](inventory/V5_SOURCE_RECONCILIATION_2026-10-18.json)。本輪文件／PNG不進執行來源白名單。

## 本機、私有遠端與正式環境分開記

ff65eae本機localhost MongoDB replica set **201 passed／0 skipped**。新映像正式切換前的[私有交易／帳號報告](inventory/sam-final-candidate-business.json)通過，當時候選正式18為0流量、私有07為100%；正式100%由後續05:57讀回證明，不混淆階段。

私有已驗兩裝置、customer後台拒絕、cart／demo checkout、Atlas持久化、重送同單、409、單裝置登出、重登入舊cookie、全撤權及停用。最後庫存HTTP[200,400]只一成功；第二SKU缺貨回滾order／item／behavior／cart event前後2／2／6／6不變。七項帳號生命週期通過；清理0、IAM撤回。**任意DB fault、checkout進行中撤權仍缺遠端證據**，不以受控缺貨代替。

[新映像consumer對照](inventory/sam-final-ff65ea-staged-d4.json)：正常事件13→14、1001 synthetic後14、推薦不變、五範圍清理0；42區可讀、me-central2政策拒絕，該區未核實。正式D4本輪僅唯讀重查：四事件各310、共1240，全具synthetic／exclude標記；D1～D4不重匯。

## 同版瀏覽器素材與清理

[S01～S12原圖／資訊](../簡報文件/screenshots/S01-S12_同版取證_2026-10-18.md)公開圖走Hosting；會員／購物／後台圖經僅綁127.0.0.1的臨時代理，**實際上游是同映像私有Cloud Run07，非本機重製UI**。代理僅在記憶體持有IAM與驗收庫憑證，未改HTML／CSS、未寫正式庫、未將憑證存圖或Git。私有資料量不同於正式，必須保留圖說。

[取證及清理報告](inventory/sam-screenshot-proxy-final.json)：
- 一次性customer/admin實際登入，customer進admin被302拒絕。
- 商品加2→調1，實際checkout303及成功提示；Atlas schema4示範訂單1／明細1、庫存6→5、本次SKU孤兒0、行為3。
- 10/18僅示範KPI為1單／10元；與本次訂單一致。之後另加購物車供窄視窗取證，未再結帳。
- 訂單／明細／cart events／carts／behavior／sessions／users／SKU／product九範圍remaining全0；本次IAM condition撤回。獨立連接器重查user／product／SKU三根marker0，見[Atlas讀回](inventory/V5_ATLAS_SCREENSHOT_READBACK_2026-10-18.json)。
- S10是實際Atlas查詢JSON，S11是Google APIs報告JSON，並非仿造Console介面。S12是390×844瀏覽器、所拍頁無水平溢出，**非手機實機**。
- S08呈現BGE未安裝／雲端未設定，不冒充真模型量測；依V5下一階段排除本輪未完成數。

最終帳號、09:00具名接回、故障／交易中撤權、手機實機、固定出口／Atlas收斂、私有加密備份與復原、排練／簽收仍見[V5工作清單](../專題進度/專案未完成工作清單_2026-10-18.md)。
