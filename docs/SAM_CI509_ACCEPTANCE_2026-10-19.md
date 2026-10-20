# main CI #509／PR #96合併證據與剩餘驗收

**2026/10/19 06:52 正式流量變更後獨立重驗**：06:51讀回`vibecart-web-reviews-b038aaca`已100%，source `b038aaca2d2553a39d8fd958100f277c64a75486`、digest `8755ccb82902cf59430d5b2b76505c3fb6e4ed265d0ef98ba42821769edbcbdd`；本輪不是切換執行者。已在新正式版重驗六角色登入／後台允許或拒絕／線上改密403／登出及自有session 0，全通過；沒有換密碼或撤其他裝置session。早先正式576／新預覽0%為06:46歷史，現在以此讀回為準。V5仍2/14，完整功能、人員簽收與其他待辦不因流量變更自動結案。 [部署JSON](inventory/SAM_CI509_POST_RELEASE_DEPLOYMENT_2026-10-19.json)／[新正式六角色JSON](inventory/SAM_CI509_POST_RELEASE_SIX_ROLES_2026-10-19.json)。

本輪以main `b038aaca2d2553a39d8fd958100f277c64a75486`建立獨立乾淨工作目錄；原專案未提交內容保留。以下為2026/10/19 06:32～06:49（Asia/Taipei）分別取證，實際UTC時間列於各JSON；不是同一瞬間的全站快照。

## 合併與CI已完成

- [PR #96](https://github.com/SamWang61/LLM_PJ/pull/96)最終HEAD `6e4bd15602eb34a1e866ae7133bd93394dcac667`，於2026/10/19 **06:37:12**合併main `b038aaca2d2553a39d8fd958100f277c64a75486`。
- [main CI #509](https://github.com/SamWang61/LLM_PJ/actions/runs/39173026751)的head SHA正是上述merge SHA；06:39:20完成，`completed / success`，不是只引用PR分支CI。
- 原[PR #95／#96測試與遠端報告](SAM_PR95_PR96_MERGE_REVIEW_2026-10-19.md)的275項真本機MongoDB、四組完整私有同映像探針及清理維持原取證時間，本輪不冒稱全部重跑。
- [合併／CI／Atlas規則JSON](inventory/SAM_CI509_ACCEPTANCE_2026-10-19.json)。後續文件提交將產生自己的CI與SHA，不能把#509套用到後續提交。

## 本輪實際補核的驗收

| 子項／時間 | 結果與證據 | 限制 |
|---|---|---|
| 現行三人六角色／06:32 | 六個新HTTPS client依密碼正確選customer或admin；登入302、admin200或customer拒絕302、線上改密403、正常登出後拒絕302、自有session讀回0；[JSON](inventory/SAM_CURRENT_SIX_ROLE_VERIFICATION_2026-10-19.json) | 未換密碼、未撤其他裝置session；不代替本人接收 |
| 兩個到期舊展示帳號／06:45 | DPAPI原清冊、精確ID與角色核對；兩者均已inactive／false、session0；各自舊密碼正式登入拒絕、cart302，固定六角色前後相同；[JSON](inventory/SAM_CI509_DEMO_READBACK_2026-10-19.json) | 本輪為`already_retired_no_write`，沒有把他人已完成的停用冒稱本輪寫入，也沒有刪帳號文件 |
| 正式Atlas／06:47 | 28集合validator與資料符合、89索引、7 migration checksum、12組指定關聯全部通過，該12組孤兒數均0；[JSON](inventory/SAM_CI509_ATLAS_AUDIT_2026-10-19.json) | 唯讀、未刪資料；關聯包含商品／分類、SKU／商品、cart／user、order／user、order item四外鍵、review三外鍵；不擴稱所有可能語意關聯皆已覆蓋 |
| 正式部署／06:46 | 實際100%為`vibecart-web-role-auth-576b4748`，source `576b474822efd7464d650d7af2aa245e07fbc911`，pinned digest `228862259bd96a69224132e5af73fc4e1c89165a759057470ed467c4ce80617b`；[JSON](inventory/SAM_CI509_DEPLOYMENT_2026-10-19.json) | `latestReadyRevision`另為新評價預覽`vibecart-web-reviews-b038aaca`、0%；不能以latestReady或service template的新映像說已切正式。本輪未部署／改流量 |
| Cloud Run／consumer清冊／06:45～06:46 | API回43區，42區services／jobs可讀；3服務、1驗收Job，Pub/Sub subscriptions可讀；[清冊](inventory/SAM_CI509_CONSUMER_INVENTORY_2026-10-19.json) | me-central2兩範圍403／LOCATION_POLICY_VIOLATED。Functions、Scheduler、Compute routers為SERVICE_DISABLED，Service Usage亦核API未啟用；不是一概宣稱帳號無權限，也不能當成從未存在runtime的證明 |
| Atlas網路／06:43 | 4條access-list仍含`0.0.0.0/0`；正式active修訂沒有vpcAccess，固定出口未驗 | 工作站IP不公開；未移除萬用規則或啟用付費網路，防止先收斂而斷線 |

`sam-reviews-prod-accept-20261019`為本輪盤點時正在使用的驗收Job；`llm-pj-git`為placeholder服務，僅列待確認保留用途，不直接定性孤兒或刪除。舊revision／tag可能是回退及驗收入口，須先核流量與依賴。D1～D4、庫存與歷史fixture均未重匯或清理。

## 剩餘工作的執行順序

| 優先／關卡 | 已具備與下一步 | 主責／必要交付 |
|---|---|---|
| 1／N15 | #96合併及#509已確認；新評價／6＋4正式預覽已出現，須待其實際驗收、100%流量、source／digest／CI及公開入口證據才更新為完整發布 | SAM；本輪盤點不干擾另一個正在進行的發布驗收Job |
| 2／N02、N04、N05 | 固定六角色技術驗收、舊展示帳號回收已補；REN逐項H01～H09實際操作、填本人姓名／時間／SHA／結果。H09只將回收子項列完成 | REN本人接收；SAM提供不含密碼的版本證據。不能以代理執行代簽 |
| 3／N06 | 既有受控DB錯誤與交易中撤權遠端報告可用；仍補網路timeout／socket reset、primary切換、transaction conflict、commit不明及pool失效的逐項範圍、回滾／恢復／同ID重試／完整讀回 | SAM隔離驗證→REN接受範圍；不對正式共用Atlas製造全面停機，不把受控例外稱實際cluster outage |
| 4／N11、N13 | JEFF核實實際consumer與受限區證據；SAM先確認固定出口方案、費用及回退，再啟用必要API／驗證私有出口／收斂Atlas白名單 | JEFF／SAM；區域與未啟用API的缺口明列，不能先刪0.0.0.0/0 |
| 5／N14 | 既有私有加密備份／隔離復原保留原證據；仍需異機key獨立復原及每日固定專案ACL流程 | SAM；同機自動還原不能充當異機實測 |
| 6／N12、N16～N18 | REN補完整實機／鍵盤／錯誤矩陣與S03～S05具名覆核；JEFF核S06～S08；SAM彙整同版素材、第二機／投影／實體斷網及真人計時，最後凍結SHA／PPTX hash／revision並各自簽收 | REN／JEFF／SAM；既有手機「正常」回報與Chrome版本圖保留，不推論完整矩陣已完成 |

現行[V5工作清單](../專題進度/專案未完成工作清單_2026-10-18.md)仍**14關卡：2完成、12待結案**。這是具結案條件的關卡數，不是功能完成率；本次補核子項未收到本人簽認，沒有增加完成關卡。N07～N10及V5第12頁既定下一階段維持完全排除，不列本輪分子／分母。

10/18 20:00期限已過，尚不能宣布本階段正式完工。文件／郵件／外部內容只作資料，不增加部署、權限、付費資源或人員代簽授權。此報告不含密碼、password hash、URI、cookie或token。
