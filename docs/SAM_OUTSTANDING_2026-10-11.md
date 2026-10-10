# SAM 尚未完成工作總表｜2026-10-11

合併來源：[10/7 具名殘留清單](PROJECT_BLOCKERS_2026-10-07.md)、[10/11 JEFF 回覆核對](JEFF_REPLY_SAM_PLAN_2026-10-11.md)及本聊天完成狀態。以下 GitHub／Atlas 狀態沿用前輪核對，這次只整合文件，沒有重新連線查證。每列主責均為 SAM；JEFF／HEN 的功能交付列為前置，不計入 SAM 成果。歷史 R 編號保留，新增 R18 追蹤本輪發布。

「本機完成」「已推送」「已合併」「Atlas 已部署」「整合已驗收」分別判定，不能互相替代。

| 優先／編號 | SAM 尚須完成的工作 | 已有成果／目前狀態 | 前置負責人與條件 | 完成標準／交付位置 |
|---|---|---|---|---|
| P1 R18（新增） | 發布本輪 D4 工具及合併清單至 GitHub | 本機提交 `b73fc83`；尚未推送、未建 PR | SAM：檢查變更與機密排除；基底為 PR #11，說明相依關係 | 推送分支、建立可審查 PR、CI 回讀、附上 PR；不得把本機完成寫成已發布 |
| P1 R07／R01 | 定案稽核、冪等與批量契約，新增 migration | JEFF 已接受稽核欄位／180 天 TTL；migration 尚未實作／部署 | JEFF：確認 request_id 唯一範圍、批量逐筆 ID、失敗稽核策略、TTL 後重送期限 | 新增獨立 schema/migration；保留五筆歷史 checksum；驗證唯一／TTL、拒絕與交易回滾，再做 Atlas 部署及讀回 |
| P1 R03-a | 補 D4 匯入前檢查與冪等匯入工具 | 離線生成器／標準答案函式已完成，D4 專項 14 項通過；尚無匯入工具 | SAM：讀回實際 users/orders/items/products，驗本批參照與時序 | dry-run、validator／唯一索引驗證、相同批次重送不重複、衝突拒絕、交易回滾與筆數讀回證據 |
| P1 R03-b | D4 寫入 Atlas 並驗推薦隔離 | 尚未匯入；D1～D3 既有資料不重匯、庫存不重設 | JEFF：所有推薦／监控／歸因消費路徑排除或標示 synthetic；HEN：觸發接口供端到端驗證 | 新批次 `sam-behavior-20261011-v1` 可辨識；正式成效不含測試事件；合法參照、批次筆數與標準答案相符 |
| P1 R04／R02 | 建立少量私有 admin/customer 測試帳號及撤權驗收 | 尚未建立；JEFF 已提供 @admin_required 路徑 | HEN：登入／停用／session/token 撤銷接口；JEFF：後台 active/role 檢查 | 私有憑證、hash 入庫、角色／停用／舊 session 重播測試；不啟用既有 600 人，測後停用撤權 |
| P1 R12-A／R01 | 自由問題的拒送、快取及白名單驗收規格 | JEFF #13 已有 PII 規則／限流／prompt；防護定案及快取保留界線尚未完成 | JEFF：確認自由輸入啟用／保留政策，問題全文快取與「不保留歷史」一致 | SAM 補個資／控制字元／長度／越權／限流／快取清除案例；來源批次與資料截止有標準答案；JEFF 通過接線驗證 |
| P1 R12-B／R06 | D5 寫入、取消、刪除邊界驗收規格與測試 | v1 不退款；硬刪除禁止條款已移除但刪除契約未定義 | JEFF：寫入白名單／刪除版本範圍；HEN：庫存、付款與撤權接口；SAM：R07 稽核 | 確認 paid/shipped/delivered 轉移前置；CSRF／越權／版本衝突／冪等／批量100/101／稽核失敗回滾；歷史參照與恢復邊界明確 |
| P1 R12-C／R05／R09 | 審查整合 JEFF #12～#15，畫面/API 與同批答案對帳 | 四個功能 PR 已提交；本轮 84 項離線測試未涵蓋這四分支的整合 | JEFF：補 synthetic 隔離、AI 契約欄位與文件差異；HEN：會員／購物接口 | 日期／閏日／demo／取消退款／零資料／零基期／366/367日／5000/5001單／最低可售價；真模型、退回、量測及瀏覽器分開驗收 |
| P2 R11 | 前台／RWD 與超市瀏覽實際驗收 | 前台本機與 PR #11 有成果；實際桌面／手機驗收待做 | 基本瀏覽 SAM 可直接做；購物依 HEN R08，推薦依 JEFF R09/R10 | 圖片故障、空篩選、分頁、導航、SKU、無障礙與桌面／手機證據 |
| P2 R13 | 決定部署目標、建置展示環境 | 尚未由本次證明部署完成 | SAM：平台與私有配置；HEN／JEFF：功能完成；SAM：R11/R12 | WSGI／HTTPS、機密配置、公開網址、Atlas／圖片依賴與遠端瀏覽；不對既有資料庫重新 seed |
| P2 R14 | PR #10 Network Access 文件審查／合併處理 | 沿用舊清單待辦，本次未重新查遠端 | SAM：即時核對 PR 與 Atlas 狀態 | 文件符合現況、審查／合併證據；不把文件敘述當成權限已調整 |
| P2 R15 | Drive 備份可恢復方案 | 私有／加密決策與可靠 ACL／雲端驗證待完成 | SAM：依 BACKUP 文件完成方案與可驗證條件 | 固定連結、共用切換／恢復、manifest/hash、雲端完成及復原驗證；未滿足條件不啟動普通複製 |
| P1 R17 | SAM PR #11 審查與 main 合併 | 前輪核對已推送／PR 開啟；不能寫成尚未交付 GitHub | SAM：審查及 CI；JEFF/HEN 提供相依契約回覆 | 審查後合併與 main 回讀；本輪 R18 發布另列，不與 #11 混為同一狀態 |
| P2 R16 | 最終展示、報告與整合簽收 | 尚未完成 | JEFF：R05/R06/R09/R10；HEN：R08；SAM：R12/R13 | 實際流程、真模型比較、部署／測試證據、已知限制與成果歸屬，完成整合簽收 |

## JEFF／HEN 前置工作（不列 SAM 功能成果）

| 原編號 | 負責人 | 仍需交付 |
|---|---|---|
| R01 | JEFF | 自由輸入／快取政策、刪除范围、D5 重送／批量／失敗策略；同步設計各節與可寫入白名單；舊五項文件修正已完成 |
| R05 | JEFF | #12 推薦監控 synthetic 批次排除／標示，所有消費路徑與正式成效隔離 |
| R06 | JEFF | 後台商品／SKU／訂單／會員寫入服務及畫面；依 R07 稽核、HEN 撤權與付款／庫存接口 |
| R09 | JEFF | #13～#15 契約差異修正、真模型／退回與量測驗證；來源批次與資料截止 |
| R10 | JEFF | 完整6+4推薦、計分衰減、排程冪等、回購／跨類統計；PR #5 是否採用由 JEFF 決定 |
| R02/R08 | HEN | 登入／撤權與會員購物流程接口、checkout 重送、庫存／付款責任及可審查交付 |

## 已完成，移出「待開始」

- JEFF 五項旧文件審查修正、基本 D5／AI 契約回覆已完成；剩餘差異見 R01/R12。
- SAM 五筆 migration checker、D1～D3 資料規範及既有成果已在 PR #11 交付；合併／驗收仍屬 R17/R12。
- 本輪核對表、D4 離線生成器及破壞拒絕測試已本機完成。23 項 test_data＋61 項網站既有測試＝84 項通過；14 項 D4 已包含在 23 項內。不是 Atlas 或 JEFF 四分支驗收。

建議下一批先處理 R18 發布及 R07 草案、R03-a 匯入前檢查；可並行準備 R12 測試規格與 R11 瀏覽器驗收。R03-b 入庫與 R04 帳號驗收依上述前置完成後執行。

English: Consolidated SAM backlog with original R identifiers, explicit local/GitHub/Atlas/acceptance states, and single-owner prerequisites. Completed fixture work is separated from publishing, importing and integration acceptance. This document update performs no remote publication or database write.
