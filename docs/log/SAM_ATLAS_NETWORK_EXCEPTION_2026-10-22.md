# VERTCART 學習協作網路例外 / Atlas network exception

決策日期：2026/10/22（Asia/Taipei）。核准人：組長 SAM。適用於本倉庫 VibeCart／LLM_PJ 的 Atlas 專案 `vibecart_ai`；依 SAM 指定，以「**VERTCART 專屬特點／學習協作例外**」作為此項決策標籤，不因此重新命名既有系統或資料庫。

## 已接受的設定 / Accepted setting

SAM 明確要求保留 `0.0.0.0/0`，原因是本專案為共同作品與學習歷程證明，需要讓組員從不同網路環境連線。使用者提供的 Atlas IP Access List 畫面顯示此條目為 Active；本次未透過 API 新增、刪除或修改 Atlas 網路規則。

日後檢查將這一條設定列為 **`accepted_exception`（SAM 已接受的專案例外）**：不以它單獨判定檢查失敗、不重複要求移除、不自動刪除，也不再將同一已知設定列成新的未解缺失。若用途或核准人決策改變，再依新的直接指示更新；本次未指定失效日期。

技術定義保持正確：`0.0.0.0/0` 是所有 IPv4 來源的 CIDR 範圍，並非專案獨有的單一 IP。MongoDB 官方文件亦說明 `/0` 允許任意來源；這項管理例外不等於已證明不會被濫用。[官方 IP Access List 說明](https://www.mongodb.com/docs/atlas/security/ip-access-list/)

## 後續檢查範圍 / Review scope

- 只適用於此 Atlas 專案與此一 IPv4 CIDR；不延伸到其他專案、IPv6 `::/0`、其他規則或未來新增權限。
- 檢查報告保留實際觀察值及 `accepted_exception` 狀態，不將它偽記為「沒有廣域規則」或「已限制來源」。
- 資料庫認證、角色最小權限、TLS、明文憑證、外洩與存取異常仍正常檢查；網路例外不授權公開帳密或讀寫正式資料。
- 原三條工作站 `/32` 的 10/31 管理覆核另依[既有決策](../SAM_ACCEPTANCE_DECISIONS_2026-10-20.md)處理；不將該期限套用到本例外。
- SAM 已同意固定 Drive 專案先停止非擁有者共用至機密修復及雲端驗證完成；本項 Atlas 網路決策不撤回該同意。

[機器可讀決策](../inventory/ATLAS_NETWORK_EXCEPTIONS.json)與[最新上下文](../CURRENT_CONTEXT.md)提供後續檢查入口。歷史報告保留各自當時的真實觀察，不改寫舊數據。

已同步此例外至既有SAM及JEFF／REN兩份進度監控提示，保留原排程與收件設定；本次未另外寄送信件。依SAM要求另保存一份專案外的後續記憶更新，避免下次仍採用舊的廣域規則判定。

English: SAM explicitly accepts the existing `0.0.0.0/0` entry for this collaborative learning project. Future reviews should classify this exact project/CIDR pair as an accepted exception, not repeatedly demand removal or silently delete it. The CIDR permits all IPv4 sources; it is not a unique project address. Authentication, authorization, TLS, credential leakage and actual access checks remain in scope. No Atlas network settings were changed in this task.
