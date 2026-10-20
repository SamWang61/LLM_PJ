# SAM PR #95／#96 審查、同版遠端驗收與合併

**2026/10/19 06:52 正式流量變更後獨立重驗**：06:51讀回`vibecart-web-reviews-b038aaca`已100%，source `b038aaca2d2553a39d8fd958100f277c64a75486`、digest `8755ccb82902cf59430d5b2b76505c3fb6e4ed265d0ef98ba42821769edbcbdd`；本輪不是切換執行者。已在新正式版重驗六角色登入／後台允許或拒絕／線上改密403／登出及自有session 0，全通過；沒有換密碼或撤其他裝置session。早先正式576／新預覽0%為06:46歷史，現在以此讀回為準。V5仍2/14，完整功能、人員簽收與其他待辦不因流量變更自動結案。 [部署JSON](inventory/SAM_CI509_POST_RELEASE_DEPLOYMENT_2026-10-19.json)／[新正式六角色JSON](inventory/SAM_CI509_POST_RELEASE_SIX_ROLES_2026-10-19.json)。

更新：2026/10/19 06:30（Asia/Taipei）；主責[SAM](mailto:cashsam@gmail.com)。本次依使用者授權完成審查、必要測試與同版驗收後整合。

## 合併與版本

- [PR #95](https://github.com/SamWang61/LLM_PJ/pull/95) HEAD `e5788ce12339370a8afb5e2c824a6ecd24e5f602`，實際合併main `8a29f5fbbb05deb09c2e23324f1769c5bf86c0b3`，時間2026/10/19 06:26:40。PR兩組CI成功；合併後與本PR最終CI分別由GitHub讀回，不用舊CI替代新HEAD。
- [PR #96](https://github.com/SamWang61/LLM_PJ/pull/96)原HEAD `14cffba70f80adaed9a5fd044e38486f793f3fca`僅交05:45登入修復歷史；已整合新main並處理CURRENT_CONTEXT／V5衝突，保留雙方時間序列及原始紀錄。最終HEAD `6e4bd15602eb34a1e866ae7133bd93394dcac667`已於2026/10/19 06:37:12合併main `b038aaca2d2553a39d8fd958100f277c64a75486`；合併後[main CI #509](https://github.com/SamWang61/LLM_PJ/actions/runs/39173026751)同SHA於06:39:20完成success。
- 正式仍是原展示基線加兩檔登入增量的`576b474822efd7464d650d7af2aa245e07fbc911`，不是完整main新評價／6＋4版本。只有`app/auth.py`與`app/templates/auth/login.html`兩個執行檔與原正式e000d95不同，兩檔與PR95逐byte相同。

## 本輪測試與真遠端

| 項目 | 實際結果 |
|---|---|
| 真localhost MongoDB完整測試 | 新建無憑證Docker replica set，275 passed、0 skipped；包含六帳號原子回滾、真交易／session、評價與推薦。資料庫僅餘admin/config/local，自建容器已刪除 |
| 新探針安全 | 5項範圍／註冊ID／清理讀回回歸通過；只准固定私有驗收庫及本次六個ObjectId |
| 完整同版私有預覽 | PR95的56檔Git blob封裝，GCS完整下載SHA相同；私有修訂`vibecart-acceptance-pr21-role95-e5788ce`、tag `role95-full`、0%流量、匿名403、資料庫`vibecart_acceptance_pr21` |
| 同Email雙角色 | 三組隔離email各customer/admin共六身分；正確密碼選角色、前端role參數無法升權、切角色撤舊裝置、其他裝置保留、錯密／停用／同密命中兩角色拒絕、改密403；自有session清理0 |
| 同版關聯回歸 | 同映像四探針全部passed：雙角色、評價／6＋4規則、帳號及Atlas交易。評價4＋4＋5→4.4，重送／並行／409回滾、1001 synthetic隔離、cart／checkout／最後庫存與缺貨回滾等通過 |
| 正式實際六角色 | 從既有版本庫外DPAPI在記憶體取用已授權憑證；六次新client依角色登入302、admin200或customer拒絕302，GET／無新密碼POST改密403；以server-issued token查到session，僅登出本次裝置並獨立讀回自有sessions0 |
| 正式Atlas唯讀 | 28集合／89索引／7 migration／12項關聯全通過；全域(email,role)唯一索引及舊migration checksum吻合。SKU庫存、全部行為事件hash、訂單／明細／評價數前後一致；除正常登入session與last_login外未改正式資料 |

來源archive SHA-256 `bd85ba17567bfdcff4b7d633551841df4b02a6dafee0a701fac46d969cf7fb4e`，2,157,908 bytes，GCS generation `1792361421014751`；[Cloud Build](https://console.cloud.google.com/cloud-build/builds;region=asia-east1/4e12f368-f6fd-41a7-9404-86b276e3e66b?project=278483818008)成功，映像`sha256:8755ccb82902cf59430d5b2b76505c3fb6e4ed265d0ef98ba42821769edbcbdd`。本次為登入驗收使用精簡映像，AI檢查步驟正常跳過；BGE、Claude摘要、自由提問均關閉，沒有宣稱本次新模型驗收。

實際成功execution：`projects/vibecart-llmai/locations/asia-east1/jobs/sam-role95-acceptance3-20261019/executions/sam-role95-acceptance3-20261019-2984n`。部署Job啟動碼SHA `2a164aa976aa11f5f6392bba743adc001915d4929ed5a4f023a87a7bfe92bd72`已讀回相符，8份實際探針與交付bytes一致。隔離email及密碼為本次隨機fixture；不是正式三人的憑證或付款。 Job wrapper交付版依Git政策採LF；原執行wrapper為CRLF，正規化後完整bytes相同，兩種SHA分別保留，沒有冒稱原始壓縮／換行bytes相同。

## 失敗、修正與清理

1. 首個Job在探針啟動前因精簡映像缺requests停止；只補驗收工具requests／BeautifulSoup依賴，沒有更換正式映像。
2. 第二個Job在全庫(email,role)索引建立階段遇到驗收庫既有重複fixture；沒有刪除或改寫既有資料，索引讀回已還原。第三個Job改為只覆蓋本次acceptance_run的partial unique index；四探針後移除此暫時索引，before／after均為原來的_id_索引。正式全域索引另以實際Atlas唯讀稽核驗證。
3. 三個臨時Job均刪除並GET404；probe fixture／依賴資料清理讀回通過，暫時索引還原。本輪沒有新增IAM授權、Atlas帳號或正式密碼，也沒有寄信。

## 文件與V5邊界

- PR96舊密碼修復是在05:45的歷史，不回收或回灌其舊憑證；目前以05:52後固定雙角色清冊及授權的私有憑證來源為準。原「未證實舊輸入／密碼管理器故障」的結論保留。
- 既有三封通知屬REN原交付，本輪不重寄、不從郵件或對話取密碼；報告不含密碼、hash、salt、URI、cookie或token。
- CURRENT_CONTEXT、文件索引、部署入口、執行紀錄與V5均更新；原工作樹及已備份的既有變體保留，不reset或覆蓋他人修改。來源／提交／GitHub blob／本機雜湊由最後交付收據逐項對帳。
- V5仍**2/14完成**。正式登入增量已上線，但完整main仍只在0%預覽；真人具名接收、手機完整矩陣、N13固定出口、N14異機key／每日流程及最終簽收未因此結案。兩個較早限時展示帳號的回收與新固定六角色分開記錄。

[機器紀錄](inventory/SAM_PR95_PR96_MERGE_REVIEW_2026-10-19.json)／[REN原雙角色交付](REN_DUAL_ROLE_LOGIN_2026-10-19.md)／[PR96歷史修復](SAM_ADMIN_LOGIN_REPAIR_2026-10-19.md)。

## main CI #509後續核對

[本輪驗收與優先清單](SAM_CI509_ACCEPTANCE_2026-10-19.md)補兩個舊展示帳號的獨立inactive／session 0／登入拒絕、正式資料關聯稽核及雲端consumer／網路清冊；歷史測試保留原時間，沒有把後續文件CI當新正式部署或真人簽收。
