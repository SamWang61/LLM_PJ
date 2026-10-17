# SAM PR #21 同版零流量預覽與遠端驗收｜2026-10-17

時間基準：2026-10-17 11:16（Asia/Taipei）。本頁只記錄當次讀回，不把預覽、HTTP 成功或資料庫可連線當作最終簽收。使用者已同意以本版建立**無流量、唯讀**預覽修訂；本輪未變更正式流量、未向 Atlas 寫入測試事件或 D4。

## 來源、映像與修訂

- GitHub SAM [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21) 來源完整 SHA：`3842893904e54e638e1fc88346c85d90e5beb22b`；`main` 讀回為 `4059f42d75ec773e7f6eda434cde124333ff268b`，PR 仍為草稿。
- `scripts/prepare_cloud_source.py` 封裝 **47 個白名單檔案**；每個封裝檔案與該提交的 Git blob 位元組相同（47/47）。封裝 tar SHA-256：`e575f444fc956ca1f7448eeab8ab682a9eed25009542c0eba1dbaaa7645d8be3`。本機 `docker build --pull` 成功；使用假 URI 的唯讀容器啟動後，`/health/live` 200、`/health/ready` 503（預期無資料庫）、`/auth/login` 403、`/admin/` 403，容器已停止。
- Artifact Registry 推送的 OCI index digest 為 `sha256:331f6d00e72e6f0e1dfe607e9e873a6403b973f5bcff426df5169dc9322a7929`。Cloud Run 管理端讀回新修訂 `asia-east1/vibecart-web-00009-xfq` 的 linux/amd64 image digest 為 `sha256:d7bcded0c84fc3b5af058b02f9e8aaa47b34e2fbfbc6ff7f2ae75887c9f8ca52`，與本機建置的 amd64 manifest 相同。revision label `codex-source-sha` 為上述完整提交，`Ready`、`Active`、`ContainerReady` 與 `ContainerHealthy` 皆成功。
- 修訂環境讀回 `CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`；`MONGO_URI`、`SECRET_KEY` 仍以 Secret Manager 參照注入，未讀取或記錄密鑰值。服務流量讀回：`vibecart-web-00007-m9k` **100%**，較早的 `vibecart-web-00008-5bw` 和新修訂 `vibecart-web-00009-xfq` 均為標籤網址的 **0%**。新預覽網址：<https://pr21-3842893---vibecart-web-m44ncgz5ta-de.a.run.app>。

## 遠端唯讀行為

| 檢查 | 新修訂讀回 | 判定範圍 |
|---|---|---|
| `/health/live`、`/health/ready` | 各 200，動態回應 `Cache-Control: private, no-store` | 程序存活及當時資料庫／商品 ready；不代表交易安全。 |
| 首頁、無結果搜尋、商品明細 | 各 200；首頁呈現 336 件商品，商品頁可見 NT$ 80.00、模擬庫存 3、展示環境僅供瀏覽文字，無加入購物表單。瀏覽器畫面已檢視首頁與首件商品。 | 證明所測匿名唯讀路徑；尚無手機實機、鍵盤完整巡檢或截圖封存。 |
| 登入、後台、購物車、結帳 GET；加購、結帳 POST | 全部 403 | 確認預覽拒絕所測寫入入口；不宣稱全路由安全稽核。 |

## 管理端與 Atlas 唯讀盤點

- Cloud Run 全區服務清單讀回只有 `asia-east1/vibecart-web`。Cloud Run Job 逐區讀回 43 個支援區域：42 區無 Job，`me-central2` 回 403，故不能把全區 Job 清單宣稱完整。Cloud Functions 與 Cloud Scheduler API 在此專案顯示未啟用；Cloud Asset API 不可用。需補專案資產與外部排程／其他 consumer 清單，才能斷言全數隔離。
- Firebase Hosting 最新正式 release 的版本 `c3772dcc7c906211` 建於 10/14，其 rewrite 指向 `asia-east1/vibecart-web`。本次沒有發布 Hosting；正式網站仍經由舊的 100% 修訂，不能當成 PR #21 同版畫面或交易證據。
- MongoDB Atlas 連接器對 `vibecart_ai` 唯讀計數：D4 指定 `metadata.synthetic_batch_id=sam-behavior-20261011-v1` 的 `behavior_events` **0**；原 D1～D3 `synthetic_batch_id=sam-synthetic-20261005-v1` 的 `orders` **3,000**；原批次以外 `is_demo=true` 的 `orders` **2**。本輪未寫入或清理任何 Atlas 文件。

## 尚未完成的最終驗收

1. 此新修訂是唯讀預覽，登入、角色、跨裝置撤權、SKU cart／checkout、訂單／庫存讀回與管理員 AI 畫面**無法**在此修訂驗收。先建立受限且可撤回的隔離遠端交易環境，再逐項留同版請求、資料庫讀回、清理及畫面證據；不得對目前正式資料庫直接做示範交易探針。
2. 每個實際部署的推薦、評分、歸因與排程 consumer 都需同版 synthetic／正常對照，證明在排序與上限前隔離，並對目的地讀回。上述管理端盤點仍有權限／API 缺口，故 [D4 閘門](D4_REMOTE_GATE_2026-10-17.md)未解除，D4 不得 apply，D1～D3 不重匯。
3. 線上 Claude、BGE、自由提問維持關閉；D5 仍是規格。Hosting 同版發布、手機／鍵盤及完整畫面、真模型與具名簽收仍待完成。PR #21 繼續保持草稿，不合併 `main`。
