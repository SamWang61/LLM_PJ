# REN 多裝置登入與發布｜2026-10-14

使用者於本對話確認平台允許同一會員多裝置同時登入，並授權推送 LLM_PJ、部署 Firebase `vibecart-llmai`。本文件取代本日較早契約／回報中的單一登入草稿與「尚未授權發布」狀態。

## 已實作與驗證

- 每個裝置登入建立獨立 `auth_sessions`，cookie 只持有隨機 session 識別；資料庫存 SHA-256 digest，沒有明文 token／密碼。伺服器每請求確認 active／role、session 存在、30 日期限及 credential fingerprint。
- 新裝置登入保留其他裝置；POST／CSRF 登出僅撤銷目前 session，複製舊 cookie 無法重播。管理員可信函式 `revoke_user_sessions(db, uid, mongo_session=...)` 撤銷所有裝置；停用／角色與授權每請求重新讀取，密碼更新會使舊 fingerprint 無效。最後管理員／退款／取消仍由 JEFF 接續。
- 新增獨立 migration `20261014_06_member_device_sessions_v4`，嚴格 validator、user_id index、expires_at TTL；舊五筆 migration 未改。Atlas 已 apply／讀回 28 集合、89 索引及六筆 migration。TTL 清理是背景工作，應用仍明確拒絕已過期 session。
- `last_login_at` 恢復紀錄實際登入時間，不作撤權世代；原 600 位合成客戶不啟用、不重匯 D1～D4、不重設庫存。
- 為保留已部署功能，整合既有 `a0fcad0` 的超市頁面、AI／後台、synthetic 隔離及 Cloud Run 工具；解決 store_v4 的頁面分頁／事件衝突，保留雙方功能。原始工作目錄未改。
- 網站完整回歸 **163 passed, 3 skipped（22.30s），exit 0**；[JUnit](inventory/ren_20261014/multidevice-tests.xml)。跳過的是獨立 localhost replica set 真 checkout rollback／並發與管理員撤權 rollback，不能宣稱已完成真交易驗收。
- 包裝 47 個白名單檔案，最終 archive SHA-256 `7a1945cb92df718ea23b4d04c91faa0b35c258942a7f92710a7df77d4d5f038e`；沒有 `.env`、密碼、URI、測試帳號或資料匯出。容器 boot／health smoke 通過。

## 部署目標與界線

Firebase Hosting [vibecart-llmai.web.app](https://vibecart-llmai.web.app) rewrite 至 asia-east1 的 `vibecart-web`。沿用 runtime 身分、Secret Manager 明確版本與既有最少 0／最多 1 instance 配置；沒有增加 IAM 或重新發布秘密。

本輪將 `CLOUD_PREVIEW_READ_ONLY=false`，開放會員／購物路由；`ENABLE_CHECKOUT=true` 開放既有示範訂單，仍不串接真正付款／退款。AI 模型旗標維持既有配置，不能將本轮交付當成真模型驗收。

Cloud Build `ffc65096-2db2-444c-93ab-aaba493b1153` SUCCESS；最終映像 digest `sha256:934921d212a5bdbd9b22beada27a9b48f1fc189319d0b5f2a6ad4a80208b10d5`。Cloud Run `vibecart-web-00006-pvf` 回讀為 Ready，Firebase Hosting 發布成功。

最終 revision 的遠端 [QA 證據](inventory/ren_20261014/remote-qa.json) 於 2026-10-14 21:06（台北）通過：公開路由、註冊、第二裝置登入後第一裝置仍有效、單裝置登出後舊 cookie 拒絕且其他裝置仍有效、停用會員拒絕、Atlas schema／索引／migration 讀回。隔離測試帳號已停用並撤銷 session，未建立訂單。這是自動 HTTP／資料庫檢查，並非人工瀏覽器、真交易並發或全站整合驗收。

GitHub 交付與逐項後續狀態見 [REN 今日工作清單](../專題進度/REN_今日工作清單_2026-10-14.md)。

SAM 接續：正式展示帳號、checkout 真交易與手機整合驗收；JEFF 接續：停用／降權流程呼叫全裝置撤權，取消／退款／稽核語義、所有外部推薦與排程消費者。D4 仍以遠端隔離全部通過後才 apply。
