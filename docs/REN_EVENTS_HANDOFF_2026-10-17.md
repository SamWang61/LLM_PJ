# REN 四事件觸發：SAM 代理驗證與接手｜2026-10-17

執行角色：**SAM 代理 REN（24 小時）**；實際 GitHub 帳號 `SamWang61`。授權與異常見已併入 `main` 的 [PR #27](https://github.com/SamWang61/LLM_PJ/pull/27)。本工作接續 [REN R08 PR #25](https://github.com/SamWang61/LLM_PJ/pull/25)，只驗 REN 的觸發端；JEFF 負責推薦、評分、歸因及排程 consumer，SAM 負責整合與同版驗收。

## 已完成

- 新增 `MuscleCore分析資料/website/tests/test_ren_events.py`，由實際網站路由觸發 SEARCH、PRODUCT_VIEW、ADD_TO_CART、PURCHASE，核對會員身份、事件欄位與唯一 ID；匿名搜尋／商品瀏覽不產生會員事件。
- 加購與 demo checkout 各重送一次，確認只有單一事件；非法商品與數量不寫入事件。客戶端提供的 `synthetic` 值不能更改伺服器標記。沒有設定合成批次時，正常搜尋／瀏覽／加購可進入正式事件範圍；示範 PURCHASE 帶 `demo_checkout=true`、`exclude_from_attribution=true`，不進歸因。
- 定向測試 **2 passed**。在一次性、無正式憑證 localhost MongoDB 8 replica set `rsRENevents` 執行完整網站測試：**181 passed、0 skipped（34.54s）**，含三項真 transaction 測試。測後僅有 `admin`、`config`、`local` 系統資料庫，容器已停止並由 `--rm` 移除。這是本機同版證據，不是遠端服務或 Atlas 驗收。

## 下一位接手者依序處理

1. **SAM／REN 整合**：先審查並整合 PR #25 的同瀏覽器舊 session 撤銷，再審查本 PR 的四事件測試；確認 PR #21 最終程式 SHA、CI 與 `main` 合併順序。任何 rebase／合併後的最終版都須重跑同版測試。REN 軟體設定恢復尚無證據；2026-10-18 11:10（Asia/Taipei）代理授權到期前交還已交／未交清單。
2. **JEFF 先交 consumer 清單**：列出每個實際部署的推薦、評分、歸因與排程 consumer，以及版本、revision／映像 digest、讀取事件的查詢位置。逐一證明 synthetic／demo 排除發生在 sort／limit 前，並以正常事件對照，不能只引用本地程式測試。
3. **SAM 遠端同版驗收**：在獲授權、可寫且隔離的環境，以少量私有帳號跑搜尋、商品瀏覽、加購、demo checkout；讀回事件 ID、欄位、重送筆數與 consumer 輸出，保存 URL、時間、SHA、revision／digest 和清理／撤權證據。S03～S05 畫面素材需同版桌面與手機流程，不以舊零流量唯讀預覽作為交易證據。
4. **D4 閘門**：所有 consumer 的同版遠端隔離讀回完成之前，D4 不 apply；D1～D3 不重匯。現行 PURCHASE 全為 demo，沒有真付款或正式購買歸因驗收。

重跑網站測試時，在 `MuscleCore分析資料/website` 設定 `HEN_TEST_MONGO_URI=mongodb://127.0.0.1:27017/?replicaSet=rsRENevents`，使用空的一次性 localhost replica set，再執行 `python -m pytest tests -q -p no:cacheprovider`。不可指向正式 Atlas 或使用專案私人帳密。完整的容器建立與清理步驟亦見 [R08 代理驗證紀錄](REN_R08_SAM_VERIFICATION_2026-10-17.md)。
