# REN PR #95合併覆核與H09期限後回收

更新：2026/10/19 06:42（Asia/Taipei）。執行角色REN；[陳仁千](mailto:chen2000401@gmail.com)本人接收欄仍待實際簽認。

## PR #95審查結論

- [PR #95](https://github.com/SamWang61/LLM_PJ/pull/95)於本輪開始前已合併；實際時間2026/10/19 **06:26:40**，main merge `8a29f5fbbb05deb09c2e23324f1769c5bf86c0b3`，審查HEAD `e5788ce12339370a8afb5e2c824a6ecd24e5f602`。merge tree與HEAD完全相同，沒有重複合併。
- 以最新main `b038aaca2d2553a39d8fd958100f277c64a75486`為乾淨工作基線，11份PR程式／測試／清冊與審查HEAD的Git blob相同；正式登入的兩個執行檔亦與runtime `576b474822efd7464d650d7af2aa245e07fbc911`相同。
- 審查密碼唯一命中決定角色、拒絕偽造role／停用／過期／密碼歧義、角色切換只撤前裝置、live角色及密碼重查、先建(email,role)唯一索引再移除舊索引、六帳號transaction／回滾／冪等及指定私有文件建帳，**未發現阻擋問題**。註冊以email拒絕既有帳號，不使用任一角色資料作登入判定；線上改密GET／POST維持403。
- GitHub inline thread讀回0；本輪已提交對HEAD的COMMENT覆核，review ID `5565383890`，並修正PR本文過期的「尚未合併」描述。

## 測試與CI

| 來源／時間 | 結果 |
|---|---|
| PR HEAD e5788ce [CI #503](https://github.com/SamWang61/LLM_PJ/actions/runs/39169873088) | success；含真MongoDB交易步驟 |
| 合併main 8a29f5f [CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39172246284) | success |
| 接續PR #96合併main b038aac [CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39173026751) | success |
| 本輪b038aac本機選定回歸 | **64 passed／0 skipped**；test_dual_role_login、test_ren_auth_order、test_database_readiness，使用隔離fixture |
| 06:30既有SAM完整驗收 | [原報告](SAM_PR95_PR96_MERGE_REVIEW_2026-10-19.md)275項真localhost MongoDB／0 skipped、完整PR95私有0%預覽4組探針及正式6角色驗收。本輪核來源與既有報告，不把它標成本輪重跑 |

## 依清單下一項：H09／N04回收子項

H01～H07已有技術證據；H08仍缺網站操作證據、完整實機錯誤／鍵盤矩陣及REN本人接收。依現行清單接續可執行的H09期限後回收：

1. 精確核對版本庫外DPAPI原展示清冊、原ObjectId、角色、雜湊與到期時間 **2026/10/18 20:30**。06:39處理前兩帳號仍active；原始`before_accounts`記錄REN/customer有 **2** 個session、JEFF/admin有 **0** 個。本次回收撤銷REN的兩筆session，處理後兩帳號均為0；不能只因程式拒絕過期登入就當作已停用。
2. 以既有`provision_handover_demo.run(mode=retire)`只停用兩個指定舊展示帳號並刪除其全部session；未刪除帳號文件，未延長期限或重建副本。
3. 06:39讀回REN/customer與JEFF/admin均`status=inactive`、`is_active=false`、session **0**；各用新的正常HTTPS client以其舊憑證登入，HTTP200顯示通用錯誤，cart HTTP302轉登入，沒有建立session。
4. MongoDB Atlas connector另依兩個精確ObjectId獨立讀回inactive／false與session0，時間見[JSON](inventory/REN_H09_RETIREMENT_2026-10-19.json)。
5. 28集合逐一比較：排除本輪兩份users文件及其session後，其餘資料的count／SHA-256前後完全相同，包含固定六角色、SKU庫存、訂單、事件、索引migration紀錄。未重匯D1～D4或改固定密碼。

| 舊展示帳號 | ObjectId | 結果 |
|---|---|---|
| REN／customer | 6ad3f7849888fd7c5f8c4a47 | inactive／false；session0；正式登入拒絕 |
| JEFF／admin | 6ad3f7859888fd7c5f8c4a48 | inactive／false；session0；正式登入拒絕 |

這兩個到期展示帳號與目前三人六角色清冊是不同身分。原私有資料維持DPAPI保管，文件／Git／截圖不包含密碼、URI或token。

## 部署與待辦

- 本輪唯讀確認正式`vibecart-web-role-auth-576b4748`仍100%，source `576b474822efd7464d650d7af2aa245e07fbc911`，image `sha256:228862259bd96a69224132e5af73fc4e1c89165a759057470ed467c4ce80617b`。本輪沒有新部署或Hosting切換；完整main評價／6＋4仍按私有0%預覽處理。
- H09**回收子項完成**；REN本人私下接收／現場登入、H08網址／交付版／網站操作證據與完整實機矩陣仍待真實紀錄。原先SAM設備及正常回報保留，不代填REN本人簽認。
- N06仍待界定廣義網路／primary切換／commit不明等故障矩陣及具名接受；既有受控例外不提升成真實Atlas outage。V5仍**2/14完成**。
- 已更新專案入口、原雙角色交付與H09／V5清單；原歷史證據及05:52發布manifest不改。原專案其他未提交修改保留，這次交付檔以原目錄／Git／GitHub immutable raw SHA-256另核對。

[審查JSON](inventory/REN_PR95_MERGE_REVIEW_2026-10-19.json)／[回收JSON](inventory/REN_H09_RETIREMENT_2026-10-19.json)／[現行清單](../專題進度/專案未完成工作清單_2026-10-18.md)。

**PR #97審查勘誤**：原文字誤載回收前兩帳號各0個session，已依原始JSON修正為REN 2、JEFF 0；原始證據及回收操作沒有改寫或重跑。`REN_PR95_PUBLICATION_2026-10-19.json`保留提交`1d85f1cb822bd636b31b5a8fd4b8501dd8f49f43`的原發布快照，修正後檔案hash另見[本次勘誤核對](inventory/REN_PR97_REVIEW_CORRECTION_2026-10-19.json)。
