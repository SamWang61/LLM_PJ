# SAM PR #74 最終技術覆核與整合｜2026-10-18

執行：[SAM](mailto:cashsam@gmail.com)。使用者授權：完成必要測試／驗收，無問題直接合併 main。[PR #74](https://github.com/SamWang61/LLM_PJ/pull/74)的實際合併 SHA／時間以 GitHub merge 記錄為準；本報告與進度更新隨該 PR 交付。覆核起點 `4102fb4141386133385303b9af91da9f577ecabf`，新增工具安全修正 `6d9dc6f56dce829be24e9d114c2c49a5416f529a`。

## 審查與本輪修正

結帳寫入末端對會員及裝置 session 建立同交易寫入衝突保護；角色／密碼／停用或 session 撤銷與交易競爭時，整筆寫入回滾並在重試時拒絕。session 到期時間、指紋與建立時間不因鎖定延長。展示帳號保留20:30台灣時間的到期檢查；不新增公開故障測試端點。

既有 P1（故障 runner 誤把帳號模式送進故障探針）已改為只接受 read-only 或 `--run-isolated`，在取憑證／IAM前拒絕帳號及任意模式。本輪另修正展示驗證工具：原「登入前後 session 差集刪除」可能誤刪同時登入的真實持有人，改走本次瀏覽器的 CSRF 單裝置登出並驗證後續拒絕，不刪別人的 session；新增4項回歸涵蓋兩角色、並行裝置與登入／登出失敗。

## 測試與當前部署讀回

- 本輪重新跑一次性 localhost MongoDB replica set：**208 passed／0 skipped／0 failures／0 errors**。fixture庫全清、容器移除；執行來源為覆核起點，後續僅改維運工具／文件，網站執行程式未再變。
- 既有 Python 探針安全23項、並行展示session修正4項、Node runner3項皆通過。最新提交另以GitHub push／PR CI作合併門檻；不沿用舊head綠燈。
- PR網站執行白名單 **51檔**與已部署來源 `e000d952d22a64b568903641893f4ffdc71accd3` Git物件一致，差異0。
- 08:03台灣時間獨立讀回正式 `vibecart-web-00019-phf` 100%、私有 `vibecart-acceptance-pr21-00010-9zg` 100%，同digest `7199fa08c711917a80e5f54dbfd580ed96f3ef632bda7337b4aa2bde2325c992`。兩者皆為正常容器command，臨時barrier已移除。兩筆故障／正常驗收IAM condition讀回0；公開ready200、私有匿名403。本輪未重新部署、切流量或更動Hosting。

## 遠端故障證據、公開帳號與清理

[既有故障報告](inventory/REN_REMOTE_FAULT_FIXED_2026-10-18.json)的實際時間為06:36～06:38：唯一索引寫入錯誤409、受控AutoReconnect503，皆業務快照不變、故障解除後同checkout ID恢復及冪等重送；PURCHASE途中撤session或停用會員均400、回滾、後續302。本輪核對同runtime、同wrapper雜湊及清理結果；因臨時barrier已退休，**沒有宣稱08:00重新注入故障**。受控AutoReconnect不等於真Atlas網路中斷，也不涵蓋全部outage。

本輪以修正後維運函式在公開Hosting對既有customer／admin做真HTTPS登入、cart讀取及角色驗證：登入302、cart200；customer後台302、admin後台200。兩者皆正常單裝置登出302、之後cart302；獨立Atlas讀回兩帳號session合計0。沒有做正式庫checkout、後台業務寫入、重新啟用或重建帳號；帳密只在記憶體／原DPAPI私有位置。

獨立Atlas另查五個fixture marker的users／products／SKU、兩個checkout ID前綴訂單、fault control：皆0；orders暫時索引0。九類關聯清理與before/after詳細值仍引用原runner，沒有把根標記0冒稱獨立九集合逐筆重驗。完整去敏機器證據與程式雜湊見[本輪JSON](inventory/SAM_PR74_MERGE_REVIEW_2026-10-18.json)。

## V5與後續

本次整合將已部署來源納入main，修復「線上已部署但主線仍缺程式」的交付缺口；N03版本入口改按19／10與source e000d95讀取。N04已有公開自動登入／登出，仍待09:00持有人具名接收與現場操作，並須展示後退休，最晚20:30；N06指定技術故障／中途撤權通過，仍缺更廣outage矩陣與具名接受。N15其餘舊PR不因本次整合自動關閉。

**14關卡仍2完成、12待結案**，不把技術測試改成N18全站簽收；N07～N10仍下一階段。N17離線備援保留，原手動V5簡報／PDF不變。D1～D4不重匯、不重設庫存。同步原專案只更新可辨認Git歷史的限定檔案、備份舊bytes，未知本機YAML／文件僅做必要局部合併，其他未提交修改不發布。
