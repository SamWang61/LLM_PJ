# SAM PR #21 同版驗證與最終驗收缺口｜2026-10-16

**10/17 最新遠端讀回**：同版無流量唯讀修訂 `vibecart-web-00009-xfq` 已 Ready，匿名唯讀路徑與寫入拒絕通過所測檢查，正式流量仍由舊修訂承接；完整來源、映像、流量、Atlas 計數與缺口見 [10/17 遠端預覽紀錄](SAM_PR21_REMOTE_PREVIEW_2026-10-17.md)。下方 10/16 預覽資料保留歷史，不能代表最新修訂。

**10/17 最新同版交易測試**：在 PR #21 程式 `c678133be5cdaa89acdf9c18cd7fb97f2dd44d60` 的乾淨工作樹，以 Docker `mongo:8` 建立一次性、無憑證且只繫結 `127.0.0.1:27017` 的 replica set `rsSAM20261017`；測試環境設 `REN_TEST_MONGO_URI=mongodb://127.0.0.1:27017/?replicaSet=rsSAM20261017`，於 `MuscleCore分析資料/website` 執行 `python -m pytest tests -q -p no:cacheprovider`，結果 **178 passed、0 skipped（38.92 秒）**。測試 fixture 只建隨機 `ren_acceptance_*` 資料庫並在結束後刪除；涵蓋 rollback、最後庫存並發、checkout 重送與管理員撤權 rollback。沒有使用 `.env`、正式 Atlas 或線上帳號。容器測後停止並移除。此結果對應該程式版；後續文件提交不改程式，仍須分別核對 CI 與遠端文件位元組。本機真交易測試不構成線上角色、交易或 D4 consumer 最終驗收。

**10/17 更新**：JEFF T5 PR #23 已以 `6e401ef459b4ca5e002c22ee225cb4c63375ec3a` 合併入本 PR；下方 10/16 的 Docker／Cloud Run 證據屬 T5 前的 `88dca3b` 映像，不能延伸為 T5 同版遠端驗收。新合併提交的 [push CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38991253680) 與 [PR CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38991257679) 通過。完整新範圍、consumer 審查與展示決定見[10/17 交付核對](SAM_JEFF_1017_HANDOFF.md)；PR 仍為草稿、`main` 未合併。

**10/17 D4 後續**：程式原因、修正與遠端隔離證據缺口見 [D4 遠端閘門](D4_REMOTE_GATE_2026-10-17.md)。新增離線測試通過不改變下方最終驗收缺口；新程式尚未有同版 Cloud Run／Hosting／consumer 讀回。

本紀錄針對 [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21) 的修正後程式來源 `7798bc5d682fbf85408b74e6f07bf60ed7dfbfa9`；預覽映像取自含驗證文件的同版提交 `88dca3b8bbec5d5510fedaa37b6231c6f125220c`，程式內容未再修改。驗證在獨立工作樹執行；原 `C:\LLM\LLM_PJ` 的未提交修改未變更。本輪完成本機封裝、容器啟動、隔離交易測試與零流量遠端唯讀預覽；**最終驗收尚未完成**。

## 已核實的同版證據

| 項目 | 結果 | 邊界 |
|---|---|---|
| GitHub | `main=00a1d21d9613b2b916cf3de8ce7e215eddaa5a9a`；PR #21 程式修正 `7798bc5d682fbf85408b74e6f07bf60ed7dfbfa9`，仍為草稿；該提交的 [PR CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38844059373) 成功。 | CI 不含遠端交易及人工畫面驗收；後續文件提交也須另核對 CI。 |
| 文件政策與附件 | `python scripts/check_repository.py`：281 files、263 UTF-8 texts、0 errors；`git lfs fsck` 通過，四個 PDF 由 LFS 管理。 | 已核對本地 LFS 物件；遠端發布後須再核對可讀性。 |
| 白名單封裝 | `python scripts/prepare_cloud_source.py` 封裝 47 個檔案；將獨立工作樹的換行與 Git 提交位元組對齊後，tar SHA-256=`1ed8b875194e3eff9b9d4e74e32350193d690f0e8af1cd50d6b837bce4dedf94`。 | tar 雜湊屬本次建置產物，不代表遠端映像 digest。 |
| Docker build／boot | 使用上述封裝內容執行 `docker build --pull` 成功；本地映像 ID=`sha256:c608f42c439eeb720b922480881d2f6aafd5b50772262bc39ec3ac7039ea8161`。容器以假 URI／假 session key 啟動，`/health/live` 為 200、`{"status":"ok"}`；唯讀模式 `/auth/login` 為 403。 | 假 URI 不連 Atlas；未以此測 `/health/ready`、商品資料或真實登入。容器已停止。 |
| 網站與交易 | 在無憑證的一次性 localhost MongoDB replica set 執行完整 `pytest tests -q -p no:cacheprovider`：**171 passed、0 skipped**，含 rollback、最後庫存並發、撤權回滾與自由提問啟用閘門。測試使用隨機 `ren_acceptance_*` DB，結束後刪除；容器已停止。 | 僅證明本機隔離環境與此 SHA；不等於 Atlas 或展示站交易驗收。 |

## 零流量預覽修訂與遠端讀回（10/16）

使用者授權在 `vibecart-llmai` 建立不接正式流量的預覽修訂。從 `88dca3b` 的 47 個白名單檔案重新封裝，逐檔比對工作樹與 Git 提交，47/47 位元組一致；本次 `source.tar.gz` SHA-256 為 `101111f0e4dcf3a903df1aaff2544b8cb760526c7b6ee4cf7cdd69e0eef00231`。本機 `docker build --pull`、boot、`/health/live` 200 與唯讀 `/auth/login` 403 通過；映像推送至 Artifact Registry 後，OCI index 遠端讀回 digest `sha256:ae3dbfbd9863e1264dfb840714101f8d80be0d8a0b44bf8119ef9c91c0f18783`，其 linux/amd64 manifest 為 `sha256:f1c437e7e3dda072de508631edf350ca6baeb586925df5cbc1d21ad11e7c0d53`。Cloud Run 修訂讀回的映像為後者，與 index 的 amd64 子 manifest 一致。

Cloud Run `asia-east1/vibecart-web-00008-5bw` 的 `Ready` 成功，修訂環境為 `CLOUD_PREVIEW_READ_ONLY=true`、`ENABLE_CHECKOUT=false`；`MONGO_URI` 與 `SECRET_KEY` 仍引用原 Secret Manager 版本 1，未讀取密鑰值。服務讀回的流量配置：`vibecart-web-00007-m9k` **100%**，新修訂 `pr21-preview` 標記 **0%**；預覽網址為 <https://pr21-preview---vibecart-web-m44ncgz5ta-de.a.run.app>。標記網址可直接存取，但一般服務網址及 Hosting 不會導向本修訂。

預覽網址遠端 HTTP 讀回：`/health/live` 200 `ok`、`/health/ready` 200 `ready`、首頁 200、無結果搜尋 200、實際商品明細 200 且顯示價格／庫存／唯讀提示、不顯示加入購物車表單；`GET /auth/login`、`/admin/`、`/cart`、`/checkout` 及 `POST /cart/add/...`、`/checkout` 均為 403。動態回應皆有 `Cache-Control: private, no-store`。Chrome 實際瀏覽預覽首頁顯示 336 項商品、14 頁，點入首項商品可見價格 NT$ 80.00、模擬庫存 3 與唯讀提示，沒有購物按鈕。這證實該修訂可讀取 Atlas 供商品瀏覽，並在所測入口拒絕寫入；尚未對每個 API 做完整安全驗收，也未測正式交易、管理員、真模型或手機畫面。

## 本輪修正

審查發現原程式在管理員 AI 頁面顯示自由提問，伺服器也接受 `free_question`，未遵守 v1.2 的獨立預設關閉條件。`7798bc5` 增加 `AI_FREE_QUESTION_ENABLED=false` 預設值；只有該旗標、`AI_SUMMARY_ENABLED` 與 `DATA_MODE=v4` 同時成立時才顯示輸入欄並接受 POST。關閉時伺服器回 403，固定 intent 保持可用。這只修復啟用閘門；遠端真模型、安全與同版畫面驗收前仍維持關閉。

Windows 工作樹起初有 28 份文字檔為 CRLF，Git 提交與遠端為 LF；已在獨立乾淨工作樹把這些純換行差異校正，對 PR 相對 `main` 的 146 個變更路徑逐一確認來源、提交及遠端原始位元組相同，再使用該工作樹重新封裝和建置。原 `C:\LLM\LLM_PJ` 工作目錄未改動。

## 尚未達到的最終驗收條件

1. **同版部署與讀回（SAM）**：零流量 Cloud Run 預覽的不可變映像、revision、`/health/ready`、首頁／商品明細／搜尋及唯讀拒絕已驗。仍須核對完整 SKU 價格／庫存及錯誤處理、同版 Hosting release 與正常流量的功能；`vibecart-web-00007-m9k` 不可當作 PR #21 的證據。
2. **角色與交易（REN 接口、SAM 驗收）**：在經授權的隔離或展示環境實測匿名、customer、admin、跨裝置撤權、cart／checkout 重送、庫存及訂單明細回讀；保存同版證據，測後撤權。
3. **AI／後台（JEFF 接口、SAM 對帳）**：依 v1.2 契約驗真模型與規則退回、自由提問旗標和輸入防護、D5 寫入／審計／批量冪等；目前文件契約不等於功能實作。
4. **D4（JEFF consumer、SAM 閘門）**：列全所有推薦、評分、歸因及排程 consumer，在遠端同版確認 synthetic 隔離後才能正式匯入與讀回；D1～D3 不重匯。
5. **交付與簽收（SAM 彙整）**：依 22 項清單完成 S01～S12 同版素材、手機／鍵盤畫面、最終 PPTX、離線備援、排練與具名簽收。PR、CI、本機測試與容器啟動均不能替代這些項目。

下一步先完成 PR #21 的跨組程式審查、零流量預覽瀏覽器與資料對帳，再安排有授權的角色／交易與 Hosting 同版驗收。未取得上述證據前，PR 保持草稿，專案狀態維持「本機整合與遠端唯讀預覽可驗，最終驗收未完成」。
