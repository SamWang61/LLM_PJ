# 正式部署讀回｜2026-10-18

核對時間：2026/10/18 00:12（Asia/Taipei）。正式流量已由 `vibecart-web-00012-85f` 切至 **`vibecart-web-00013-ds5` 100%**；舊修訂保留 `rollback-00012` 零流量標籤。部署、公開路由與頁尾修正已核實，全站具名簽收仍待完成。

## 固定來源與建置

- 來源為當時最新 main [`80513a951d0dff67fd47a153a45918522b5ffbb5`](https://github.com/SamWang61/LLM_PJ/commit/80513a951d0dff67fd47a153a45918522b5ffbb5)，[同版 CI #39047572571](https://github.com/SamWang61/LLM_PJ/actions/runs/39047572571) success。相對先前正式程式，變更為 JEFF 的正確 `mailto:jeff841117@gmail.com`、VibeCart 會員頁名稱及安全的登入後站內返回路徑。
- 同 SHA 在既有 Python 虛擬環境、一次性無憑證 localhost `mongo:8` replica set `rsSAMRelease` 執行完整網站測試：**186 passed、0 skipped，37.86 秒**，含 rollback、最後庫存併發與撤權 rollback。[JUnit](inventory/sam-release-80513a9-tests.xml)保留測試範圍。測後僅餘三個 Mongo 系統庫，容器已停止並自動移除。
- 封裝直接從固定 SHA 的 Git blob 讀出 **47 個白名單檔案，0 差異**；[檔案 manifest](inventory/sam-release-archive-20261018.json)列各檔 SHA-256，archive SHA-256 為 `3a9a175bdc145a8202e98366b86e310266571f063e8b0a210821a085b9069721`。首次從 Windows 工作樹封裝的換行與 Git 不同，該映像已排除，正式修訂使用重新封裝的精確來源映像。
- [Cloud Build `7971f814-f43f-41e3-8a2c-adb893a51156`](https://console.cloud.google.com/cloud-build/builds;region=asia-east1/7971f814-f43f-41e3-8a2c-adb893a51156?project=278483818008) SUCCESS，包含容器建立及 `create_cloud_app()`／`/health/live` boot smoke。正式 immutable image 為 `asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web@sha256:57c8fd038d7c231a4e417471a66b9c7996c296efd2d7b1ff70302c46a45f0fab`。

## 部署與公開檢查

[管理端讀回](inventory/sam-release-20261018.json)包含 Ready／Active 修訂、來源標籤、映像、流量及既有 secret 參照。先以 `release-80513a9` 標籤在零流量修訂完成檢查，再切換 100% 流量；保留舊版本供回退。執行身分維持 `vibecart-web@vibecart-llmai.iam.gserviceaccount.com`；Mongo URI 與 session key 維持 Secret Manager 版本 1，`CLOUD_PREVIEW_READ_ONLY=false`、`ENABLE_CHECKOUT=true`。本輪沒有更改 IAM、秘密值、Atlas 權限或模型旗標。

[預覽檢查](inventory/sam-release-preview-smoke-20261018.json)的 10 項與[切換後公開檢查](inventory/sam-release-live-smoke-20261018.json)的 20 項全部通過：Cloud Run／Hosting 的 live、ready、首頁、單品、搜尋、空結果、登入、註冊回 200；匿名 cart／admin 回 302 至帶 `next` 的登入路徑。HTML 與瀏覽器讀回 JEFF 的正確 mailto；登入頁 title 為「登入｜VibeCart」，註冊頁為 `JOIN VIBECART`，動態頁均 `private, no-store`。

[正式站](https://vibecart-llmai.web.app/auth/login?next=/cart)的[實際瀏覽器畫面](../簡報文件/screenshots/S11-login-deploy-20261018.png)為匿名登入表單與頁尾，未輸入帳密。Hosting 既有 release `1791982222797000`／version `c3772dcc7c906211` 的 rewrite 仍指向 `asia-east1/vibecart-web` 且未 pinTag，因此此次後端切換不需要重新發佈 Hosting。00:12 對新修訂查 00:10:50 後 ERROR 日誌返回 0 筆；只是該時間窗的結果。

## 資料與剩餘驗收

00:10 以新的「MongoDB」連線唯讀重查正式 `vibecart_ai`：28 集合、active 商品 336、原 `sam-synthetic-20261005-v1` 訂單 3,000、批次外 demo 訂單 2、指定 `sam-behavior-20261011-v1` D4 事件 0。本輪沒有建立正式帳號、下正式訂單、寫 Atlas、重匯 D1～D3 或執行 D4 apply。

186／0 是同版本機測試；本次遠端操作限匿名與公開頁面，沒有重跑新修訂的登入成功、跨裝置撤權、遠端交易或管理員操作。先前 [PR #21 私有隔離 Atlas 交易](SAM_PR21_LIVE_ACCEPTANCE_2026-10-17.md)保留其原 SHA／修訂，不自動轉成此版全站簽收。D4 全 consumer 遠端 synthetic／正常對照、真 BGE／Claude／自由提問、D5／180 天稽核與冪等服務實作、S01～S12 同版素材、最終 PPTX／離線備援／排練與具名簽收依[工作清單](../專題進度/專案工作清單_2026-10-17.md)繼續追蹤。REN 代班於 **10/18 11:10** 到期，須逐項確認交回，不能自動延長。

**2026/10/18 20:00（台灣時間）必須完成系統，確保 GitHub 的資料正確、系統正確上線、簡報可順利完成。** 本次核對時距期限約 19 小時 48 分；上述未驗項目仍是交付風險。

## 01:58 商品標題 RWD 正式升版（Asia/Taipei）

上方 00:12 記錄保留當時快照；本節為較新的讀回。[PR #56](https://github.com/SamWang61/LLM_PJ/pull/56) 已合併 main `ef79076`，最終修正來源 `1d2abf2cfa7465636e49474062e11f6aca571dda` 的兩個 CI 作業成功。精確來源 47 檔中僅 `main.css` 與上一正式版本不同；Cloud Build `f0f1fbc2-2980-477e-8a77-d9eb467ad503` 成功，映像 `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b`。先在零流量 `vibecart-web-00015-nlk` 驗四個 viewport 與公開路由，證據見 [S02 排版紀錄](../簡報文件/screenshots/S02-tablet-layout-20261018.md)。

切流量前，同一映像部署至既有私有隔離服務 `vibecart-acceptance-pr21-00005-5j5`，保留 `vibecart_acceptance_pr21`、原 runtime 身分及單一 service account invoker。43 區 consumer／Job 清單讀回僅正式與私有兩個 Cloud Run 服務、Job 0、Pub/Sub topic／subscription 0、worker API 0；`me-central2` 受位置政策限制，未冒稱讀取成功。隔離探針 `ren-d4-6efcf1dbe36f02d8` 的管理計數 **13→14→14**（基線、正常、加入 1,001 筆較新 synthetic 後），會員前台正常事件可見且 synthetic 不改結果；1,002 事件、各 2 筆 session／user／SKU／product 清除後逐集合殘留 **0**。Atlas 連接器獨立核對 event、user、SKU、product marker 均 0；service account 的臨時 ID-token 角色撤銷，獨立 IAM 讀回 token creator binding 0。[無憑證報告](inventory/sam-catalog-release-d4-20261018.json)保留同映像與清理數據。這是 D4 consumer 對照，不代替新正式版本的會員交易與真模型驗收。

正式 Cloud Run 管理端讀回 `vibecart-web-00015-nlk` **100%**，舊 `vibecart-web-00013-ds5` **0%** 並保留 `release-80513a9` 標籤供回退。兩修訂均 `CLOUD_PREVIEW_READ_ONLY=false`、`ENABLE_CHECKOUT=true`。Firebase Hosting 原 rewrite 指向此 Cloud Run 服務，無需重新發佈 Hosting；[正式站](https://vibecart-llmai.web.app/)的 `/`、`/auth/login`、`/health/live`、`/health/ready` 均回 200。Chrome 模擬 320／375／768／1280 px 均無水平溢出，商品標題在分類上方橫排：[768 px 正式畫面](../簡報文件/screenshots/S02-tablet-live-20261018.png)、[1280 px 正式畫面](../簡報文件/screenshots/S02-desktop-live-20261018.png)。此處僅證明部署、公開頁面與 S02 排版；登入成功、跨裝置撤權、真交易、後台寫入、真模型、實機及具名簽收仍按工作清單追蹤。

**02:10 後續：**同映像私有隔離庫已補[兩裝置登入、示範訂單、重送、409 與個別撤權遠端驗收](SAM_REMOTE_TRANSACTION_2026-10-18.md)；正式業務庫未建立測試訂單。上段「真交易未驗」為 01:58 快照。新修訂的遠端故障注入／最後庫存併發、後台寫入、真模型、實機與具名簽收仍待辦。
