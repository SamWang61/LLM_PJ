# 2Gi／三執行個體、PR #171 與 BGE 冷啟動修正 / Production release

更新：2026/10/22（Asia/Taipei）。SAM 已明確授權先調整資源，再審查、測試、合併並部署 PR #171，接續 Drive 權限驗證。實際操作為 Codex；這份技術證據不代填組員本人實機簽收。

## 已完成的資源與 PR #171 / Delivered

- 正式服務 `vibecart-llmai / asia-east1 / vibecart-web`：原記憶體已是 **2Gi**，原 revision 上限 1（service 上限 20）。本輪將 service 與 revision 上限都設為 **3**；CPU 1、min 0、concurrency 20 保留。[現行資源設定](../../deploy/runtime-capacity.json)。最多 3 是擴展上限，不是常駐三台，也不是負載或故障切換驗收。
- 資源先以原 digest 建立 `vibecart-web-capacity-1022`，08:29 讀回正式流量 100%。IAM、環境與 Secret Manager 引用、VPC、啟動探針及 Hosting release 保留。
- [PR #171](https://github.com/SamWang61/LLM_PJ/pull/171) HEAD `8c09489b70eff1f3e57c26c8a7ae2bae8960766a` 審查與同版 GitHub CI 通過；整合網站離線測試 **405 passed / 35 skipped**，檔案政策 1,078 檔／803 UTF-8／0 錯誤。35 項需要另外環境的測試未在本輪離線結果中完成。
- 合併 main `1d9c3b9417c7bb1aa02932f42bd9723015dc966b`；白名單 76 個來源項目，與原映像僅 7 個執行檔差異。Cloud Build `a05de77d-a2ca-420b-854a-bfda936153f6` SUCCESS，容器內核對 74 個執行檔 hash、UID 10001、離線 BGE 512 維、favicon 200/304、健康端點。
- 映像 digest `sha256:802af6a8f24bb0e8af077ae96cd909f84fefc3918e5c6f477f36fce26fa8e842`；修訂 `vibecart-web-pr171-1d9-1022` 於 08:37 切換、08:38 讀回 **100%**，2Gi／雙層 max 3 保留。Hosting release `1792363722745000` 未重發。

## 真實操作與後續發現 / Observed behavior

- 正式 Chrome 管理員頁面顯示中文日期範圍與規則說明；本輪單次 Claude POST 200，頁面量測 14.1 秒，5,286 input／387 output tokens。程式與測試驗證防重送標記；本輪未取得送出瞬間的「分析中」畫面，不冒稱已有該張視覺證據。
- Local 首次 324 個商品向量請求 HTTP 200、約 91.96 秒；暖快取後頁面 Top 5，324/324 命中、計算 96ms。這只是記憶體快取，不是向量預先計算或持久化已完成。
- **完整延後日誌發現三次 504**：08:40:54～57 起始的 Local GET，在約 180 秒逾時。另一新執行個體於 08:41:24 同時載入三份 BGE 權重。不能用前述成功請求或早期無錯誤日誌掩蓋後續失敗。
- 原本 `bge_embeddings()` 只有「不存在就建立」檢查；模型載入釋放 GIL，三執行緒可各建一份模型及快取。補上初始化鎖、只發布完整建成的模型，並避免失敗呼叫刪掉其他執行緒剛建好的模型。商品向量仍沿既有 cache lock 只計算一次。新增三個並行冷請求共用模型／一次向量計算，以及載入失敗後重試的回歸測試。
- Local 提示從「30 秒」改為「可能需要一至兩分鐘，請勿重複送出」，對應本輪真實量測；不是延長 Cloud Run timeout 或保證所有請求低於兩分鐘。

## 補修已完成發布 / Follow-up delivered

[PR #175](https://github.com/SamWang61/LLM_PJ/pull/175) 的 HEAD `dedd60d881514ba72ba3507662a83c8e43d806ed` 兩個 GitHub CI 檢查均成功，合併為 main `453600ada83fd041c5c1aa8f1040f75093d50fc1`。本機整合 **407 passed / 35 skipped**；首次 CI 因連到尚未合併的備份文件而失敗，已改為有效的 PR 連結後通過，沒有略過檢查。

Cloud Build `b95871b7-7a29-45ad-a6ce-ce2dc49f17d8` SUCCESS。在 **1 CPU／2Gi**、無網路容器內重新核對 74 個執行檔 hash、非 root、真 BGE 512 維，三個並行呼叫只建一份模型並共用快取。PR HEAD 與合併 main 的 76 個白名單來源完全一致；僅 3 個 runtime 檔相對 PR #171 更新。

09:00 讀回 `vibecart-web-bge-lock-1022` **100% 正式流量**；digest `sha256:e9ca69abaacb70fa85c732b71317598c0955e3cc378cb09443911ab75e822b63`。2Gi、service／revision max 3、CPU 1、min 0、concurrency 20、IAM、Secret Manager 引用、VPC 與 Hosting release 均核對。候選及正式健康／登入／favicon 可用；GET logout 405 是預期拒絕，不列為故障。

09:00:44 同時在三個 Chrome 分頁送出不同有效商品的 Local 推薦，三個請求落在同一個新 instance，HTTP 均 **200**，耗時 **85.935／85.935／85.923 秒**；該 instance 日誌只有一次模型載入。三頁都顯示各自商品與 Top 5。後續完整日誌還觀察到其他 Local GET／重試，合計 21 次均 200，三個 instance 各載入一份模型；冷請求最慢約 95.16 秒。本輪只主動送出上述三個瀏覽器導航，不把其他請求冒稱為預先設計的 21 人負載測試。

09:05 完整分頁日誌覆蓋 08:59 起的 85 筆紀錄、1 頁、無下一頁，**5xx／資料庫／其他 ERROR 均 0**。這是指定觀察區間的結果，並非永遠無錯誤或高可用保證。瀏覽器控制讀取期間曾逾時；最終以實際 HTTP 日誌和三張可見結果畫面核對，沒有把工具逾時當作網站 504。

[去敏版本、資源與完整日誌清冊](../inventory/SAM_PR171_PRODUCTION_2026-10-22.json)。三張原圖與 SHA-256 同列清冊：[商品一](../inventory/pr171_production_20261022/pr175-production-cold-1.png)、[商品二](../inventory/pr171_production_20261022/pr175-production-cold-2.png)、[商品三](../inventory/pr171_production_20261022/pr175-production-cold-3.png)。

## 保留的限制與後續 / Remaining work

| 項目 | 主責／狀態與下一份證據 |
| --- | --- |
| BGE 冷啟動競爭 | SAM 補修已由 #175 合併並正式發布；同 instance 三並行請求通過，完整日誌無新增 5xx。首次載入仍約 86～95 秒，速度改善須依下一列預先計算另行處理。 |
| Claude 跨執行個體去重 | JEFF：PR #171 僅 process-local，最多 3 instances 時，分流到不同 instances 仍可能各呼叫一次。分散式去重未實作。 |
| 商品向量預先計算／持久化 | JEFF：目前每個程序各自載入與計算；新 instance 仍有冷啟動。需要獨立契約及驗證，不能由 324/324 記憶體命中推定結案。 |
| 模型中文輸出 | 頁面與規則文字已中文；實際 Claude 仍出現 change_pct／null，JEFF 後續改善輸出用語。 |
| Drive 每日固定專案 | 依[權限修復 PR #174](https://github.com/SamWang61/LLM_PJ/pull/174)；OAuth、空白探針、完整 ACL、真正備份分開驗收。 |

完整私人原始服務設定、ACL 與授權資料留在專案外。公開清冊僅記去敏版本、雜湊及驗證結果。回復策略以先前已驗證 revision 做 traffic 回復，仍保留 2Gi／max 3；本輪未執行回復演練。

English: Capacity and PR #171 were deployed. A successful cold Local request was followed by three 180-second timeouts on another instance loading three model copies concurrently. Follow-up PR #175 was merged and deployed at 100% traffic. Three concurrent production requests on one cold instance completed in about 86 seconds with one model load; the complete observation window had no 5xx. The patch serializes construction and retains one cache per process. Distributed Claude deduplication, persistent vectors and named acceptance are separate gates.

官方依據：[Cloud Run memory](https://docs.cloud.google.com/run/docs/configuring/services/memory-limits)、[maximum instances](https://docs.cloud.google.com/run/docs/configuring/max-instances)。
