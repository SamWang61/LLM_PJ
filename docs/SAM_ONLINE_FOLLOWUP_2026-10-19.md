# SAM 線上持續檢查、PR 整理與本人取證提醒｜2026-10-19

本輪依「依序處理未完成工作，直到系統上線無錯誤」及「寄信提醒三人親自操作取證」執行。以下時間均為台北時間；機器檢查和本人簽收分別記錄。

## 本輪完成

| 項目 | 本次證據與界線 |
| --- | --- |
| 正式服務持續觀察 | 17:07:28～17:07:34 實際讀回正式／私有各100%，source `294c1fa`、digest `796a42b6…`、固定 VPC/NAT；正式首頁、推薦、登入、live、ready、空搜尋各200，匿名 admin／cart 各302，8項符合預期。[報告](inventory/SAM_ONLINE_HEALTH_2026-10-19_1710.json)。檔名是本輪報告標籤，以 JSON 內時間為準。 |
| 日誌 | 08:50～17:07:34，共110筆、2頁，無後續頁；HTTP 5xx、Mongo選主／連線、應用資料庫不可用及其他ERROR均0。兩筆404的路徑是登入URL誤帶右括號及後續中文句子，不是正常登入路徑；正常登入200。已補文件連結後空格，避免文字提取黏連。這是觀察區間，不保證未來零錯誤。 |
| 健康檢查器修正 | 原工具只看首100筆，且只有httpRequest.status而無文字payload的503會漏列。現在分頁讀完、直接按HTTP狀態碼判定；空結果與分頁上限不稱健康。8項回歸通過；[PR #113](https://github.com/SamWang61/LLM_PJ/pull/113)已合併 `2d28d80`，PR兩個offline檢查成功。 |
| 資料層 | 本輪透過既有私有PyMongo設定唯讀稽核28集合／89索引／7筆migration及checksum／12組關聯；狀態passed，各指定關聯孤兒0。沒有DDL或業務資料寫入。[報告](inventory/SAM_ONLINE_ATLAS_2026-10-19_1705.json)。Atlas連接器需重新登入，未把連接器錯誤當資料庫故障。 |
| 部署來源 | main `2d28d80`與目前部署來源 `294c1fa` 的56個白名單部署Git blob差異0；本輪只改驗證工具與文件，沒有重新部署。[來源比對](inventory/SAM_ONLINE_SOURCE_2026-10-19.json)。 |
| 寄信 | 17:00:49已寄REN、JEFF、SAM，Gmail已回讀SENT與三人To標頭；要求本人操作、原圖上傳、裝置／時間／URL／版本／預期與實際、hash及具名結果。[去敏紀錄](inventory/SAM_PERSONAL_ACCEPTANCE_NOTICE_2026-10-19.json)。 |
| 截圖操作卡 | 已發布[個人上傳目錄與模板](../簡報文件/screenshots/personal-acceptance-20261019/README.md)，各人建自己子目錄並開PR。電腦手機尺寸模擬、手機實機、第二台電腦復原分別標示。未替任何人填結果。 |
| PR清理 | #13～#18六個head均已是main祖先，逐一關閉冗餘相依鏈PR；#10全網段規則提案、#19早期簡報草稿、#102競爭的1.5秒交易重試提案依新版方案退役。全部保留原分支與commit，沒有刪除。#19仍有三份不同的舊版文件只在原commit，明列為歷史，不謊稱所有blob均在main。[逐筆回讀](inventory/SAM_PR_CLEANUP_2026-10-19.json)。 |

Google讀取在本輪中途短暫429，有限次重試後17:07控制平面與日誌讀回成功；保留實際完成時間，不沿用早先結果。

本機既有Firebase Admin SDK憑證檔另補專用Git忽略規則，避免文件同步誤收；未讀取、改寫或發布該檔內容。

## N15 尚有內容的舊PR

- #76的獨有[08:12原始交接JSON](inventory/REN_HANDOVER_READONLY_2026-10-18.json)按原bytes補存；其中舊展示帳號啟用狀態是10/18歷史，不得用來恢復已回收憑證。其餘舊上下文與清單由更新證據取代。
- #86的唯讀後台驗證模組及4項獨立計算／安全測試已移植；在既有隔離交易探針中，於測試管理員停用前執行。維持目前runner較嚴格的顯式maintainer規則，不回退舊IAM檢查。所測為固定規則問題、日期/demo金額、停用自由提問與D5連結；不啟用模型或D5。Python兩套12項、Node兩套10項通過；新增模組已在同digest私有服務完成5頁GET、12組固定規則問題及日期/demo/金額獨立對帳、錯誤區間400、未知意圖400、自由提問關閉403；會員交易同時passed，資料清理及暫時IAM撤除均true。隨後原D4探針因仍要求零評價fixture出現在冷啟動推薦而失敗，故[首輪整體結果保留failed](inventory/SAM_READONLY_ADMIN_INITIAL_2026-10-19.json)。已改為兩個不同大類的真實行為偏好與synthetic排除驗證，不造高星評價；20項Python回歸含實際排序器的洩漏反例已通過。第二輪同樣通過會員與唯讀後台，但[D4因隔離庫僅一個大類而停止](inventory/SAM_D4_CATEGORY_PREREQUISITE_2026-10-19.json)，零新增fixture且清理／IAM撤除通過。現已支援必要時建立自有兩筆分類，清理同時限制新ID及精確run代碼；21項Python測試含刪除範圍與真實排序洩漏反例通過。新增明確D4-only重跑選項，只跑失敗子項，不重播已通過的會員交易；Node對應7項通過。[最終D4-only重跑已passed](inventory/SAM_D4_CURRENT_POLICY_2026-10-19.json)：一般事件1筆改變偏好；另外大類synthetic1,001筆不改後台正式計數或個人推薦，沒有偽造評價。自有分類2筆、事件／session／會員／SKU／商品均清理讀回0，暫時IAM撤除true；正式／私有流量revision及digest在重跑前後一致。這是分開執行的兩組技術驗證，不將首兩輪失敗改為成功，也不代替本人簽收。
- #76／#86已由本輪替代PR #115接續並關閉，讀回state=closed，原head與分支均保留；替代程式與證據的主幹交付以#115實際合併及main CI為準。#109展示更新卡以57a67dd的兩個offline成功核對後，已合併main `913f3b6`；PPTX／PDF原檔及hash不變；#5為下一階段計分候選，保持草稿。

## 仍需本人或外部條件

本輪後續亦修復另一個外部Cloud Build check：#115合併main的GitHub Actions成功，但舊自動建置的repo根目錄Dockerfile設定失敗。已改用Git白名單封裝與零流量私有候選；#116兩項CI成功後17:55合併main `5d4cc2e`，main Actions及自動Cloud Build外部check均success。17:58新候選Ready／Healthy、0%、匿名403，原正式及私有流量各100%保持、公開五入口200；[建置修復完整證據](SAM_CLOUD_BUILD_PREVIEW_REPAIR_2026-10-19.md)。這是部署流程修復，新候選尚未提升或接受業務簽收。

1. **本人簽收／實機／第二台電腦**：REN、JEFF、SAM需各自按郵件及[具名表](../專題進度/2026-10-19_具名接收與異機復原表.md)操作與上傳。郵件寄出不代表收到或完成；N02／N04～N06／N12／N16～N18不代簽。
2. **每日固定Drive備份**：本輪重新確認固定專案為project、資料夾為folder；專案有2個writer、資料夾仍有anyone reader。本輪補選完整grantee欄位後可讀回收件身分，但連接器的權限摘要仍省略permission ID，現行工具沒有撤銷權限入口，無法可靠保存並恢復專案及所有子檔案的原共用。故沒有停共用或傳送明文，也未改固定連結。每日23:30自動化已讀回仍ACTIVE且時間不變，提示已更新為先讀最新私有加密證據及本次固定專案ACL前置，不再以舊狀態概括。另有已驗的私有加密備份，但不能替代固定專案的每日流程；N14仍待。
3. **N13舊工作站規則用途**：既有固定出口已用於正式與私有服務；另外三條舊工作站規則仍需管理者提供用途／到期後逐一處理。本輪沒有刪除他人的存取；Atlas連接器須重新登入才能補平台讀回。
4. **N11／完整故障與展示**：政策區consumer未讀範圍、真正遠端任意Atlas故障、具名覆核與實體排練依原清單保留；不在正式庫製造全面停機。N07～N10仍屬下一階段，不擴充V5分母。

V5仍為14關中2關已結案。網站在本輪正常回應，且上述觀察範圍無伺服器／資料庫錯誤；仍未取得全部關卡所需本人證據，不宣告全站零缺陷或全部結案。

English: Current production and private services share the pinned source/image and VPC egress. Eight public checks and the complete two-page log window passed; the read-only schema audit also passed. The notification email was sent and verified. Preserve human/device acceptance, Drive ACL limitations and remaining owner-controlled gates as pending.
