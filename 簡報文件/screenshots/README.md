# 操作截圖與完成標準

2026/10/18更新：依使用者指定V5範圍取證，S01～S12主圖與補圖已補入此目錄。**取證齊備與最終簽收分開記**；[逐圖步驟、實際結果與限制](S01-S12_同版取證_2026-10-18.md)，[機器可讀時間／URL／角色／版本／hash](S01-S12_取證索引_2026-10-18.json)。

每張圖須記：編號、台灣時間、URL、Git SHA／revision、角色、資料範圍、步驟、預期／實際、證據及核對人。瀏覽器原始JPEG已保留於私有位置；本目錄轉碼為真正PNG，逐張確認解碼後RGB像素及尺寸完全相同、無裁切。不修改介面、無假UI、無帳密／token／真實客戶個資。原有歷史圖片仍保留；被替換的S01／S03原圖在history-20261017；舊S01原bytes實為JPEG，現以.jpg正確副檔名保留。

| ID／檔名 | 本輪操作與素材 | 主責／狀態 |
|---|---|---|
| S01-home.png | 正式匿名首頁、教學聲明與瀏覽入口 | [SAM](mailto:cashsam@gmail.com)；已拍、待具名覆核 |
| S02-search.png | 關鍵字一件結果；補search-result全頁與empty零件提示 | [SAM](mailto:cashsam@gmail.com)；已拍；單品價庫另對Atlas |
| S03-product.png | 正式SKU／價格79／庫存95／規格，Atlas同時段一致 | [REN](mailto:chen2000401@gmail.com)接回核對；已拍 |
| S04-auth.png | 同映像私有customer登入成功；補customer-admin-denied拒絕 | [REN](mailto:chen2000401@gmail.com)；停用／舊cookie自動探針另附，非全部負向畫面均已拍 |
| S05-order.png | 同映像私有示範結帳成功；補cart數量2→1；Atlas訂單／明細各1 | [REN](mailto:chen2000401@gmail.com)操作、[SAM](mailto:cashsam@gmail.com)資料；缺貨／冪等自動證據另附，任意DB故障／交易中撤權仍待 |
| S06-admin.png | 私有後台10/18僅示範KPI：1單10元，與本次Atlas一致 | [JEFF](mailto:jeff841117@gmail.com)核對；已拍、待具名 |
| S07-recommend.png | 正式匿名冷啟動四商品及本週熱門理由 | [JEFF](mailto:jeff841117@gmail.com)；已拍，不冒充個人歷史／真BGE驗收 |
| S08-ai.png | 現行雲端洞察未設定；補compare實測欄尚未量測 | [JEFF](mailto:jeff841117@gmail.com)；依V5 p12，真模型／受控自由提問屬下一階段，不列本輪缺功能 |
| S09-ci.png | 程式來源ff65eae合併fffa8aa的Actions success | [SAM](mailto:cashsam@gmail.com)；文件最終SHA／CI另於交付紀錄，不稱已最終凍結 |
| S10-data.png | 真實Atlas唯讀結果JSON：schema4、示範標記、明細／關聯、本次孤兒0 | [SAM](mailto:cashsam@gmail.com)；是查詢結果畫面，非Atlas Console UI |
| S11-deploy.png | Google APIs真實讀回JSON的revision／digest／100%流量；補health | [SAM](mailto:cashsam@gmail.com)；完整JSON另附，非Cloud Console UI |
| S12-mobile.png | 390×844首頁，補非空cart／admin；無水平溢出 | [REN](mailto:chen2000401@gmail.com)前台、[JEFF](mailto:jeff841117@gmail.com)後台；**僅瀏覽器窄視窗，實機待驗** |

完成勾選必須同時滿足：原圖＋可重現步驟＋預期符合＋關鍵資料/API對帳＋同一程式版本＋具名簽認。圖片存在不等於整個功能或全站驗收完成。核對人均待實際簽認，未替任何人簽名。最終展示帳號需另建立／限時交付，不能使用已清除的一次性探針帳號。

S04～S06／S08與cart／admin窄視窗是**私有隔離Cloud Run07**的真實回應，透過127.0.0.1暫時IAM代理呈現；正式18與私有07同映像，資料庫不同。不可將私有數字稱為正式營運數字。代理及fixture已清理，重現時由SAM依最小權限驗收流程重新建立，不把臨時登入憑證放本目錄。
