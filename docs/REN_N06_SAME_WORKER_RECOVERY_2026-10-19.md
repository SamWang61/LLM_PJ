# REN N06：保留原工作程序的故障恢復驗證

日期：2026/10/19（Asia/Taipei）。本輪接續 REN 的會員／購物驗證，從 GitHub main `e203f89060b3a9ff04d6e9dcbec1a450edf85e2c` 建立乾淨工作樹。原 `C:/LLM/LLM_PJ` 的異動保留。

## 補上的驗證缺口

先前[持續故障矩陣](REN_PR101_MERGE_N06_BOUNDED_2026-10-19.md)在解除故障後會新建 MongoClient，證明的是新 worker 能以原 checkout ID 恢復。本輪修改[本機故障工具](../scripts/run_local_checkout_fault_matrix.py)：解除注入後保留原 Flask app、原 MongoClient／連線池與登入 cookie，禁止以更換 client 隱藏連線池恢復問題；逐次記錄 HTTP、恢復次數與耗時。應用程式交易服務未變更。

工具在 `--network none` 的本機 Docker 中，啟動三個一次性 localhost mongod；無 Atlas URI、秘密或外部網路。持續故障後以原 checkout ID 重送，核對單筆訂單／明細、庫存只扣一次、PURCHASE／CHECKOUT 事件各一筆、不同內容同 ID 回409，並比對28集合。原始報告保留工具 SHA、模式、每次命令與清理結果：

- [五類持續故障／同一 worker](inventory/REN_N06_SAME_WORKER_SUSTAINED_2026-10-19.json)。
- [六類單次故障／同一 worker](inventory/REN_N06_SAME_WORKER_SINGLE_2026-10-19.json)。
- [本機回歸 JUnit](inventory/REN_N06_SAME_WORKER_TESTS_2026-10-19.xml)。

## 持續故障結果

| 注入故障 | 故障 HTTP／耗時 | 原 client 第一次恢復 | 重送與資料結果 |
|---|---|---|---|
| socket timeout | 503／8.010秒 | 200 | 同單、庫存只扣1；異內容409 |
| 連線重置／清 pool | 503／8.004秒 | 200 | 同上 |
| code112交易衝突 | 503／8.007秒 | 200 | 同上 |
| code91／pool clear | 503／8.006秒 | 200 | 同上 |
| commit結果不明 | 503／8.004秒 | 200 | callback僅1次、同txn commit17次；以原ID找回已提交同單 |

前四類在503後的28集合快照與故障前相同；commit不明可能已提交，依原始資料記為找回同單，不誤記回滾。這些耗時是該次本機請求觀察值，不是全站HTTP SLO。每案都明記 `recovery_client_replaced=false`；未藉程序／client重啟通過測試。

六類單次故障全部200，包含真primary切換；故障解除後六案原client的第一次重送均200、重送同單、異內容409。網站與D5 migration回歸 **287 passed／0 skipped／0 errors（93.13秒）**。最終[機器摘要](inventory/REN_N06_SAME_WORKER_SUMMARY_2026-10-19.json)核對兩份矩陣均使用現行工具SHA、11案不換client、28集合對帳及測試容器清理。

本機矩陣可在已安裝專案測試依賴與mongod的隔離環境重現；每次使用新的report檔名，工具拒絕覆寫舊證據：

```powershell
python scripts/run_local_checkout_fault_matrix.py --mongod <本機mongod完整路徑> --mode single --report <新單次報告路徑>
python scripts/run_local_checkout_fault_matrix.py --mongod <本機mongod完整路徑> --mode sustained --report <新持續報告路徑>
```

本輪以Docker斷開外網執行；回歸最初因容器缺LangChain依賴、以及測試入口拒絕多seed URI而停下，均屬本機測試配置。補齊專案requirements並改用同一隔離replica set的單一本機seed後，上述287項全部通過；沒有修改產品程式來繞過測試入口限制。

## 與線上版本的關係

17:01台灣時間[唯讀部署回查](inventory/REN_N06_SAME_WORKER_DEPLOYMENT_2026-10-19.json)：正式 `vibecart-web-n06-294c-1019`、私有 `vibecart-acceptance-pr21-n06-294c-1019` 均100%，來源 `294c1fa`、digest `sha256:796a42b6d5fd80099900abc381d4c954d21ed1bea162ad0a9a49a89355deb40a`，沿用固定VPC `ALL_TRAFFIC`；兩者均無command override。Firebase live／ready／登入頁回200。

本機基線的 `cart_service.py`、`sku_cart_service.py`、`auth.py`、`store_v4.py` 與部署來源 `294c1fa` 的 Git diff 為0。這輪只改驗證工具與文件，沒有變更部署、IAM、Atlas或帳號。既有同映像私有四案與評價／推薦驗證仍依[原遠端報告](inventory/reviews_n06_remote_20261019.json)，不能將本機server failpoint說成遠端Atlas故障。

原遠端故障runner的唯讀前檢查曾回 `Private barrier command mismatch`，原因是現行100%私有修訂版已還原正常command；此防護按預期拒絕在非barrier服務執行，沒有因此變更服務或授權。

## 尚須接續

N06 的原worker恢復子項已有本機證據；真正遠端Atlas故障的可控範圍與REN本人逐案接受仍未完成。H08完整實機矩陣、H01～H09本人接收、ASUS VivoBook異機復原及最終素材簽收仍需實際操作結果。V5維持 **2/14**；工作與前置詳[REN今日工作清單](../專題進度/REN_今日工作清單_2026-10-19.md)。
