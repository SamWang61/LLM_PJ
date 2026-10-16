# SAM PR #21 同版驗證與最終驗收缺口｜2026-10-16

本紀錄針對 [PR #21](https://github.com/SamWang61/LLM_PJ/pull/21) 的整合來源 `3eaaf95de0687a7797eb77a57b92a5000dbf2018`。驗證在獨立工作樹執行；原 `C:\LLM\LLM_PJ` 的未提交修改未變更。本輪完成本機封裝、容器啟動及隔離交易測試；**最終遠端驗收尚未完成**。

## 已核實的同版證據

| 項目 | 結果 | 邊界 |
|---|---|---|
| GitHub | `main=00a1d21d9613b2b916cf3de8ce7e215eddaa5a9a`；PR #21 head=`3eaaf95de0687a7797eb77a57b92a5000dbf2018`，仍為草稿、可合併；[push CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38826558034) 與 [PR CI](https://github.com/SamWang61/LLM_PJ/actions/runs/38826561345) 成功。 | CI 不含遠端交易及人工畫面驗收。 |
| 文件政策與附件 | `python scripts/check_repository.py`：281 files、263 UTF-8 texts、0 errors；`git lfs fsck` 通過，四個 PDF 由 LFS 管理。 | 已核對本地 LFS 物件；遠端發布後須再核對可讀性。 |
| 白名單封裝 | `python scripts/prepare_cloud_source.py` 封裝 47 個檔案，該次 tar SHA-256=`1b173e8af0b299e7239d8f6d217f6244e4b3cec3ddb0f3e92c70f10ae6017c46`。 | tar 雜湊屬本次建置產物，不代表遠端映像 digest。 |
| Docker build／boot | 使用封裝內容執行 `docker build --pull` 成功；本地映像 ID=`sha256:5a40c312221c7cce27d98ca4f20ebb91853d35d7a071d2e7d5a9bc27ee7bc281`。容器以假 URI／假 session key 啟動，`/health/live` 為 200、`{"status":"ok"}`；唯讀模式 `/auth/login` 為 403。 | 假 URI 不連 Atlas；未以此測 `/health/ready`、商品資料或真實登入。容器已停止。 |
| 網站與交易 | 在無憑證的一次性 localhost MongoDB replica set 執行完整 `pytest tests -q -p no:cacheprovider`：**167 passed、0 skipped**，含 rollback、最後庫存並發及撤權回滾。測試使用隨機 `hen_acceptance_*` DB，結束後刪除；容器已停止。 | 僅證明本機隔離環境與此 SHA；不等於 Atlas 或展示站交易驗收。 |

## 尚未達到的最終驗收條件

1. **同版部署與讀回（SAM）**：以審查通過的來源建置不可變遠端映像，讀回 Cloud Run revision／image digest 與 Hosting release；驗 `/health/ready`、商品與 SKU 價格庫存、搜尋及錯誤處理。現有線上 revision 不可當作 PR #21 的證據。
2. **角色與交易（HEN 接口、SAM 驗收）**：在經授權的隔離或展示環境實測匿名、customer、admin、跨裝置撤權、cart／checkout 重送、庫存及訂單明細回讀；保存同版證據，測後撤權。
3. **AI／後台（JEFF 接口、SAM 對帳）**：依 v1.2 契約驗真模型與規則退回、自由提問旗標和輸入防護、D5 寫入／審計／批量冪等；目前文件契約不等於功能實作。
4. **D4（JEFF consumer、SAM 閘門）**：列全所有推薦、評分、歸因及排程 consumer，在遠端同版確認 synthetic 隔離後才能正式匯入與讀回；D1～D3 不重匯。
5. **交付與簽收（SAM 彙整）**：依 22 項清單完成 S01～S12 同版素材、手機／鍵盤畫面、最終 PPTX、離線備援、排練與具名簽收。PR、CI、本機測試與容器啟動均不能替代這些項目。

下一步先完成 PR #21 的跨組程式審查與遠端部署計畫，再以同一來源版本執行遠端驗收。未取得上述證據前，PR 保持草稿，專案狀態維持「本機整合可驗，最終驗收未完成」。
