# 正式管理者登入修復｜2026-10-19

時間：2026/10/19 05:38～05:45（Asia/Taipei）。使用者本輪直接要求核對正式 Cloud Run 的資料庫與登入設定、找出三個管理者登入失敗原因並修正。這是三個既有正式管理者的帳密修復，與先前兩個限時展示帳號不同。

## 實際核對與判斷

- Firebase Hosting 現有 `**` rewrite 指向 `asia-east1/vibecart-web`。控制平面在操作前後均讀回 `vibecart-web-00019-phf` 100%，程式來源 `e000d952d22a64b568903641893f4ffdc71accd3`，映像 `sha256:7199fa08c711917a80e5f54dbfd580ed96f3ef632bda7337b4aa2bde2325c992`。
- 正式修訂設定 `CLOUD_PREVIEW_READ_ONLY=false`、`ENABLE_CHECKOUT=true`，引用 Mongo 連線 secret 的明確版本1；沒有驗收庫覆寫。以此**正式修訂引用的連線**在程序記憶體連線，實際 ping 授權叢集及 `vibecart_ai` 成功。沒有因本機缺少 gcloud 就停止核對，沿用已登入 Firebase CLI 的授權呼叫 Google API；token及Mongo URI均未輸出或落盤。
- 已部署的 cloud factory 明確選擇 `DATA_MODE=v4`、`vibecart_ai` 及 Firebase 可轉送的 `__session` cookie。已部署來源與 main 的登入／session驗證程式相同。未發現連錯資料庫或登入程式版本分岔。
- 透過正式連線逐一查核SAM／JEFF／REN：每個身分恰有1筆，均為 `schema_version=4`、`auth_provider=local`、`role=admin`、`status=active`、`is_active=true`，未屬限時demo email。原密碼雜湊為正常可處理的scrypt格式；未將密碼、雜湊或salt寫入報告。
- 正式請求紀錄中，登入成功重新導向與失敗回登入頁交錯；沒有把單次失敗推論成全站資料庫故障。登入畫面的通用錯誤也不能獨自證明密碼輸入、密碼管理器或其他帳號條件哪一項出錯。
- 更正先前僅憑頁首顯示SAM推論「有效登入」的說法：頁首模板讀取cookie中的名稱，不能獨自證明伺服器session仍有效。本次成功依據是實際後台存取及獨立session讀回，沒有把頁首名稱當驗收。
- **定位結果：未發現正式連線／帳號啟用條件錯誤；本輪以更新三個既有帳號的登入憑證恢復存取。**本輪沒有取得或重播使用者原先輸入的明文密碼，不能聲稱證實了舊輸入內容或密碼管理器故障。原輸入為何與既有憑證不符沒有可追溯的明文紀錄；不從歷史對話回收密碼。

## 已執行修復

1. 為三個既有正式管理者各產生不同的隨機密碼；不新增帳號，不擴大角色。
2. 在寫入前建立目前Windows使用者的DPAPI加密憑證與加密回復資料，驗證可解密；目錄移除繼承權限，只保留該使用者與SYSTEM。私有檔案與位置不加入Git。
3. 在單一Atlas交易中，依既有ID／email／舊hash及啟用條件作compare-and-set，更新三筆密碼hash與更新時間，撤銷對應舊sessions。操作前sessions已為0；交易一次提交。
4. 透過正式 `https://vibecart-llmai.web.app/auth/login`，以每個新憑證實際登入、讀後台、登出，確認登出後後台拒絕，並檢查錯誤密碼仍被拒。
5. 獨立Atlas連接器重新確認三筆仍為啟用admin、更新時間一致，三個帳號的session合計0。PowerShell/.NET另驗DPAPI解密有3筆且密碼各不同，本機查看工具語法檢查通過。沒有顯示或提交明文密碼。

## 正式入口驗證

| 帳號標籤 | 登入 | 後台 | 登出 | 登出後後台 | 錯誤密碼 | 殘留session |
|---|---|---|---|---|---|---|
| SAM | 302 → `/admin/` | 200 | 302 | 302 → 登入 | 拒絕 | 0 |
| JEFF | 302 → `/admin/` | 200 | 302 | 302 → 登入 | 拒絕 | 0 |
| REN | 302 → `/admin/` | 200 | 302 | 302 → 登入 | 拒絕 | 0 |

安全結果摘要：[JSON](inventory/SAM_ADMIN_LOGIN_REPAIR_2026-10-19.json)。憑證僅由本機私有查看工具提供給目前Windows使用者，未寄信、未放入聊天或GitHub。

## 交付範圍

本次修改正式Atlas的三個既有管理者密碼及驗證過程中的session／last_login時間。Cloud Run設定、secret版本、流量、Hosting、正式商品／訂單及D1～D4均未變更；不需要為帳密修復重部署網站。此修復不代替REN逐項交接、最終展示帳號回收、手機完整矩陣、備份或全站具名簽收；V5關卡維持原來2/14，未擅自關單。
