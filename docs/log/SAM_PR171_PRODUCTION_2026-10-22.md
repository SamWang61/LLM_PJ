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

此補修的 CI、合併、部署與線上並行結果須在執行後追加；本段只記已觀察事實，不把尚未部署的修正當作正式成功。

## 保留的限制與後續 / Remaining work

| 項目 | 主責／狀態與下一份證據 |
| --- | --- |
| BGE 冷啟動競爭 | SAM 整合補修；待新映像與並行冷請求驗證、完整分頁日誌回讀。 |
| Claude 跨執行個體去重 | JEFF：PR #171 僅 process-local，最多 3 instances 時，分流到不同 instances 仍可能各呼叫一次。分散式去重未實作。 |
| 商品向量預先計算／持久化 | JEFF：目前每個程序各自載入與計算；新 instance 仍有冷啟動。需要獨立契約及驗證，不能由 324/324 記憶體命中推定結案。 |
| 模型中文輸出 | 頁面與規則文字已中文；實際 Claude 仍出現 change_pct／null，JEFF 後續改善輸出用語。 |
| Drive 每日固定專案 | 依[權限修復 PR #174](https://github.com/SamWang61/LLM_PJ/pull/174)；OAuth、空白探針、完整 ACL、真正備份分開驗收。 |

完整私人原始服務設定、ACL 與授權資料留在專案外。公開清冊僅記去敏版本、雜湊及驗證結果。回復策略以先前已驗證 revision 做 traffic 回復，仍保留 2Gi／max 3；本輪未執行回復演練。

English: Capacity and PR #171 were deployed. A successful cold Local request was followed by three 180-second timeouts on another instance loading three model copies concurrently. The follow-up patch serializes construction and retains one cache per process. Distributed Claude deduplication, persistent vectors and named acceptance are separate gates.

官方依據：[Cloud Run memory](https://docs.cloud.google.com/run/docs/configuring/services/memory-limits)、[maximum instances](https://docs.cloud.google.com/run/docs/configuring/max-instances)。
