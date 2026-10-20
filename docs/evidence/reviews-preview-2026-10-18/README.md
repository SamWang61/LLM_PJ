# 商品評價與6＋4｜同版遠端畫面證據

來源main `9a76b1d4dd5a13aac4beeb7065702c3d58dd6abd`；私有Cloud Run修訂`vibecart-acceptance-pr21-rv9a76-2117`，映像digest `sha256:15d359548b7e7343a1051b4907f78bf667cf36856a3c2680577a3ac989ea1c79`。

畫面由內建瀏覽器經127.0.0.1授權relay轉送至固定遠端修訂；relay只轉送HTTP，Flask與MongoDB執行於Cloud Run／Atlas。測試資料只存在`vibecart_acceptance_pr21`。桌面瀏覽器畫面不替代手機或具名真人接收。

| 原始圖 | 實際結果 |
|---|---|
| [review-before.png](review-before.png) | 兩筆4星已經HTTP提交；4.0／2筆，第三個表單可用 |
| [review-after.png](review-after.png) | 真實瀏覽器提交5星，未重載即4.4／3筆、成功訊息及表單停用；Atlas讀回sum13／count3／display4.4 |
| [home-6plus4.png](home-6plus4.png) | 首頁兩區DOM實際6與4，個人偏好與跨類高星探索分開顯示 |

[機器紀錄](browser-result.json)含原圖SHA-256與時間、單次商品GET／單次review POST、資料讀回與清理。PNG保存瀏覽器原始像素，未重繪或修改畫面。

目標商品的3筆評價由隔離的模擬已付款／完成訂單明細驗證；推薦卡片使用受控隔離排名aggregate，畫面上的星等與筆數為測試初值。這些fixture只供可重現的排序／去重驗證，測後已清理，不是正式商品評價、實際付款或營業統計。原正式資料庫的評價沒有因此增加。

第一次切換首頁等待較久，出現一次瀏覽器快照逾時；後續同一頁完成，未重新導航即取得6＋4。此證據未宣稱冷啟動或正式效能SLO通過。
