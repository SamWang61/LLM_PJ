# Cloud Run 冷啟動與首次登入設定

本設定針對既有 `vibecart-web` 的一個 8080 HTTP 容器。將 [cold-start-settings.json](cold-start-settings.json) 套用至已讀回的 revision template，可用 [applyStartupSettings](../scripts/cloud_run_startup_config.cjs) 產生副本。呼叫端仍需核對服務、固定 image digest、來源標籤、IAM、VPC、Hosting 及 100% 流量基線，先建立 0% 候選再驗證與提升流量。

| 設定 | 原值 | 本設定 |
| --- | --- | --- |
| Startup CPU boost | 未啟用 | `true` |
| 啟動健康路由 | `/health/live` | `/health/ready` |
| 間隔／單次逾時 | 10／1 秒 | 2／2 秒 |
| 失敗次數／最大啟動窗 | 12／120 秒 | 60／120 秒 |
| 最低／最高執行個體 | 0／1 | 0／1 |
| 平時 CPU／記憶體 | 1 vCPU／2 GiB | 1 vCPU／2 GiB |

`/health/ready` 已有資料庫 ping 與有效商品存在檢查；本設定讓同一工作程序的 MongoClient 在接收流量前建立連線。此路由沒有帳號、Session 或訂單寫入。不新增持續性的資料庫 liveness probe；正式庫不可用或目錄無有效商品時，新執行個體會暫停接流，超過啟動窗則失敗。這是明確的就緒條件，不可改用忽略錯誤的假成功來通過檢查。

Cloud Run 的 startup CPU boost 對 1 vCPU 容器暫時提供 2 vCPU，於啟動期間及啟動後 10 秒計費；最低個體仍為零，閒置後仍會有冷啟動。見 [Google CPU 設定](https://docs.cloud.google.com/run/docs/configuring/services/cpu)及[啟動檢查規則](https://docs.cloud.google.com/run/docs/configuring/healthchecks)。`timeoutSeconds` 不大於 `periodSeconds`；API 可能省略預設的 `initialDelaySeconds: 0`，比對時可正規化此欄，其他差異不可忽略。

## 發布與重現

1. 讀回正式 100% revision、完整 template 與 IAM，將含機密的原始回應保存在 Git 外；記錄固定 digest。使用同映像測試本設定，避免同時更換套件造成混淆。
2. 使用固定 Git 提交的設定及 helper 建立新 template。`codex-source-sha` 保留映像來源；`codex-config-sha` 另記本次設定提交。先建立自有、0% 的候選 tag，正式流量保留在舊版。
3. 執行 `node --test scripts/test_cloud_run_startup_config.cjs`，網站的 `tests/test_cloud_runtime.py` 與 `tests/test_db_pool.py`。核對兩個設定以外的 template 完全相同；不同 minScale、port 或多容器時 helper 拒絕套用。
4. 分開記錄新修訂 Ready 時間、第一筆登入 POST、登入後落地頁、完整端到端時間。真縮零冷啟動須有 `Starting new instance` 的 `AUTOSCALING` 日誌及該請求的新 instance 關聯；僅新建 revision 或清除瀏覽器 Cookie 不足以證明縮零。
5. 同 Email 的會員／管理員各自登入，驗證 Session、CSRF、後台授權及一次登出。GitHub 固定 HEAD CI 通過並合併後，核對候選來源、健康狀態與設定，提升至正式 100%；再由公開 Firebase 網域做實際瀏覽器操作。
6. 刪除本輪受控帳號與所屬 Session／事件，獨立唯讀確認 30 集合／96 索引／8 migrations 及關聯。移除本輪試驗 tag／暫存 Job，保留新正式版與舊回退版。完整分頁讀取發布觀察窗日誌；不得只憑第一頁或 HTTP 200 宣稱功能驗收。

若需回退，重新核對舊 revision `vibecart-web-icon-1af3959-1022`、固定 digest、VPC 及資料契約，將流量回到該版並重驗公開入口。回退會恢復舊啟動設定；本輪不改 migration，沒有資料回滾步驟。實際採用版本與測量結果另記優化系統文件，這份設定說明本身不代表已部署。

English: Prewarm the existing per-worker database client through the startup readiness probe, shorten the probe interval and enable temporary startup CPU boost. Keep zero minimum instances and preserve image provenance separately from configuration provenance. Deployment readiness, request-triggered cold starts and browser acceptance are separate measurements.
