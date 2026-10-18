# SAM 商品評價與6＋4｜無流量同版遠端驗收

日期：2026/10/18（Asia/Taipei）。本次由使用者授權部署最新main至無流量預覽，實測並修正驗收工具後交付。最終雲端狀態讀回時間：2026-10-18T13:41:12.391Z。

## 來源與部署

- 固定main：`9a76b1d4dd5a13aac4beeb7065702c3d58dd6abd`；56檔Git blob精確封裝，2,156,454 bytes。SHA-256 `755974a9887eca66234359bc12ce8351962fb2fba9ebf86ecd3c73a0dfff99a9`，已從GCS指定generation完整下載重算相同。
- [Cloud Build](https://console.cloud.google.com/cloud-build/builds;region=asia-east1/ae8a4735-c2d8-464f-baa5-b03b0f6345fc?project=278483818008)三步SUCCESS：映像build、factory boot與真BGE離線載入。映像digest `sha256:15d359548b7e7343a1051b4907f78bf667cf36856a3c2680577a3ac989ea1c79`。
- [BGE私有預覽](https://rv9a76-ai---vibecart-acceptance-pr21-m44ncgz5ta-de.a.run.app)：`vibecart-acceptance-pr21-rv9a76-2117`；[規則私有預覽](https://rv9a76-rules---vibecart-acceptance-pr21-m44ncgz5ta-de.a.run.app)：`vibecart-acceptance-pr21-rv9a76-rules-2117`。兩者同image／source、**各0%流量**、180秒request deadline、僅接受既有授權呼叫。
- runtime SA固定`vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com`；URI只引用既有密鑰版本1，連線實際權限經探針驗證僅`readWrite`於`vibecart_acceptance_pr21`。未擴權或建立Atlas帳號。
- BGE預覽開啟推薦，規則預覽關閉推薦模型；兩者Claude摘要與自由提問均關閉。本輪不需要重新設定Claude Key，也未讀取其內容。

## 最終遠端驗收

Job execution：`projects/vibecart-llmai/locations/asia-east1/jobs/sam-rv9a76-acceptance3-20261018/executions/sam-rv9a76-acceptance3-20261018-z7shw`。最後一輪**4探針全部passed**，各自清理讀回通過，Job已刪除且GET404。實際Job啟動碼SHA與7份探針逐檔讀回一致，探針提交`4ae7969f9fe75dda18b3f3156c000a1aea29fdf6`；應用程式封裝與main仍相同，未因工具修正更換runtime。

| 範圍 | 實際驗證 |
|---|---|
| 評價資格與拒絕 | 未付款、未完成、取消、其他人的明細400；缺CSRF400；錯誤型別／範圍拒絕且無寫入 |
| 評價與平均 | 首筆取代預設計數；4＋4＋5→sum13／count3／顯示4.4，Atlas及遠端HTML一致 |
| 重送／並行 | 相同明細同內容並行200、相同receipt；變更內容409；不同明細並行後sum19／count5／顯示3.8 |
| 真交易回滾 | 隔離fixture建立暫時唯一索引，讓review插入後的商品更新衝突；既有交易契約409，商品完整快照與review數維持原狀；解除索引後同內容重試成功 |
| HTML與撤權 | 已送達狀態可評價，無JS表單303；請求前撤回session後302且無review寫入。本輪沒有將此項擴稱遠端「寫入途中」撤權 |
| 6＋4 | 6個人＋4跨類、10項去重；小類上限3／2；跨類星等5.0、4.9、4.8、4.7；排除缺貨、停用、預設星等與不足4.5；候選不足不拿不可售商品補數 |
| synthetic與歸因 | 插入1,001筆隔離synthetic，推薦與歸因監控不變，其他會員推薦不受影響；BGE版及規則版都重跑通過 |
| 真BGE | 遠端實際相似度0.94～0.96；首次向量命中0/9、第二次9/9。兩次HTTP約1.376／1.301秒為已暖模型的量測，不當冷啟動SLO |
| 角色與交易 | 同版匿名／customer／admin、兩裝置、重登入舊cookie、停用與恢復、單裝置登出、整體撤權；真Atlas購物車revision、結帳持久化／冪等／409、最後庫存競爭及缺貨回滾通過 |

[完整機器紀錄](inventory/SAM_REVIEWS_6PLUS4_PREVIEW_2026-10-18.json)含各探針結果、清理與獨立讀回；規則版驗的是關閉模型功能後的規則模式，沒有宣稱注入BGE供應商故障。

## 實際畫面與資料讀回

[原始圖與步驟](evidence/reviews-preview-2026-10-18/README.md)：瀏覽器經僅轉送HTTP的授權loopback relay，呼叫固定Cloud Run修訂；Flask與Atlas執行於遠端。商品頁只有一次GET及一次review POST，無重載即4.0／2筆→4.4／3筆、成功訊息／表單停用。Atlas另讀回sum13、count3、display4.4及3個review；首頁DOM兩區為6與4。桌面原圖與SHA保留，沒有代填手機或真人接收。

目標評價的已付款／完成明細與其他推薦卡片aggregate都屬隔離fixture；不代表真實付款、正式評價池品質或營業統計。測後全部移除，原基底資料保留。

## 修正與失敗紀錄

1. 舊HTTP工具只接受未帶tag的私有host，擋住本輪URL；已限定同一私有服務的短tag入口並保留TLS、userinfo／外站／非標準port拒絕，模型request最多200秒。共46項相關離線安全測試通過，新增測試已加入CI。
2. Job JSON布林值須透過json.loads，並先本機compile；初次Job在探針啟動前失敗，已刪除。
3. 原探針把受控唯一索引衝突誤設503；檢查既有共用交易契約後改為嚴格409並保留完整快照／review回滾斷言，重跑通過。原失敗與清理結果保留於機器紀錄摘要。
4. 暫時OIDC權限生效期間403、空IAM policy讀回與Logging429均已修正／重試；沒有擴大role，最後grant為0。首頁第一次等待較久曾快照逾時，後續同頁完成；未宣稱冷啟動效能關卡通過。

## 安全讀回與交付邊界

- 正式`vibecart-web-00019-phf`與私有base`vibecart-acceptance-pr21-00011-2hq`仍各100%，原來源e000d95與digest7199fa…不變；服務IAM與Hosting release `sites/vibecart-llmai/releases/1791982222797000`保持原值。
- 正式Atlas synthetic事件**1,240→1,240**、product_reviews **0→0**。D1～D4沒有重匯，沒有修改正式付款、配送或庫存。
- 所有本輪Job已刪除、暫時token grant為0、fixture／依賴資料／暫時索引清理及獨立查詢為0。原目錄同步將保留既有髒工作樹與無關修改，GitHub交付SHA／CI見本輪審查PR。
- 本次達成私有同版技術驗收。正式切流量、正式新評價流程、真實金流、全量評價品質、冷啟動SLO、手機實機與具名最終簽收仍需各自證據。V5維持**2/14完成**；本次後續授權增量單獨記錄。
