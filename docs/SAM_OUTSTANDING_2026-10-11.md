# SAM 尚未完成工作總表｜2026-10-11

合併來源：[10/7 具名殘留清單](PROJECT_BLOCKERS_2026-10-07.md)、[10/11 JEFF 回覆核對](JEFF_REPLY_SAM_PLAN_2026-10-11.md)及本聊天完成狀態。10/11 已重新核對 GitHub 與 Atlas；今日證據見 [完成紀錄](SAM_TODAY_COMPLETED_2026-10-11.md)。每列主責均為 SAM；JEFF／HEN 的功能交付列為前置，不計入 SAM 成果。歷史 R 編號保留，新增 R18 追蹤本輪發布。

「本機完成」「已推送」「已合併」「Atlas 已部署」「整合已驗收」分別判定，不能互相替代。

**本輪今日完成更新（R03-b／R05）**：使用者選擇先部署隔離再匯入。SAM已補後台監控、v4／legacy 前台推薦、規則與BGE服務隔離及7項回歸測試；正式部署與Atlas匯入仍未完成。部署目標已確認Firebase vibecart-llmai；Hosting尚無release，Cloud Run／排程API未啟用，評分／歸因外部消費者待JEFF核對。詳見 [隔離修正](SYNTHETIC_ISOLATION_2026-10-11.md)。下表先前「JEFF先交隔離」現改為SAM已補程式、JEFF配合消費者核對。

| 優先／編號 | SAM 尚須完成的工作 | 已有成果／目前狀態 | 前置負責人與條件 | 完成標準／交付位置 |
|---|---|---|---|---|
| P1 R18（新增） | 發布本輪 D4 工具及合併清單至 GitHub | **今日完成推送／建立 [PR #16](https://github.com/SamWang61/LLM_PJ/pull/16)**，功能提交2c3b482；最終文件head的CI以即時回讀為準 | SAM：發布檢查通過；base為PR #11分支，先審本輪增量 | 最終CI通過與審查後合併仍分開；沒有自動合併 |
| P1 R07／R01 | 定案稽核、冪等與批量契約，新增 migration | **今日完成schema／TTL索引草案**；migration runner與部署仍未完成 | JEFF：確認 request_id 唯一範圍、批量逐筆 ID、失敗稽核策略、TTL 後重送期限 | 草案未加入active schema；定案後新增migration與validator拒絕／交易測試，保留五筆歷史checksum |
| P1 R03-a | 補 D4 匯入前檢查與冪等匯入工具 | **今日完成工具及Atlas preflight／交易回滾**；計畫1,240筆，正式新增0；26項test_data通過 | SAM：已讀回實際參照，validator與唯一索引一致；apply前尚需部署隔離證據 | 同內容／衝突離線案例通過，交易內逐文件讀回後abort；正式apply及apply後重送驗證仍待R03-b |
| P1 R03-b | D4 寫入 Atlas 並驗推薦隔離 | **今日完成隔離程式及7項測試；已推送PR #16、CI通過**。Atlas正式新增0／預期1,240；D1～D3不重匯、庫存不重設 | SAM：部署隔離並驗證；JEFF：核對評分／歸因外部消費者；HEN：觸發接口供端到端驗證 | 新批次 `sam-behavior-20261011-v1` 可辨識；正式成效不含測試事件；合法參照、批次筆數與標準答案相符 |
| P1 R04／R02 | 建立少量私有 admin/customer 測試帳號及撤權驗收 | 尚未建立；JEFF 已提供 @admin_required 路徑 | HEN：登入／停用／session/token 撤銷接口；JEFF：後台 active/role 檢查 | 私有憑證、hash 入庫、角色／停用／舊 session 重播測試；不啟用既有 600 人，測後停用撤權 |
| P1 R12-A／R01 | 自由問題的拒送、快取及白名單驗收規格 | **今日完成A01～A06規格**；JEFF功能分支測試另記，防護／保留定案與接線仍待驗 | JEFF：確認自由輸入啟用／保留政策，問題全文快取與「不保留歷史」一致 | 個資／控制字元／長度／越權／限流／快取清除、來源批次／資料截止接線驗收 |
| P1 R12-B／R06 | D5 寫入、取消、刪除邊界驗收規格與測試 | **今日完成B01～B08規格**；v1不退款，刪除契約與功能仍待交付 | JEFF：寫入白名單／刪除版本範圍；HEN：庫存、付款與撤權接口；SAM：R07 稽核 | paid/shipped/delivered前置、CSRF／越權／衝突／冪等／100/101／稽核失敗回滾；不可用規格代替通過 |
| P1 R12-C／R05／R09 | 審查整合 JEFF #12～#15，畫面/API 與同批答案對帳 | **今日完成C01～C05與D01～D02規格；JEFF #15獨立115項離線通過**；SAM分支87項通過，兩者不相加為整合總數 | JEFF：補 synthetic 隔離、AI 契約欄位與文件差異；HEN：會員／購物接口 | SAM／JEFF整合、日期/demo/零值/上限/最低價畫面對帳，真模型／瀏覽器仍待驗 |
| P2 R11 | 前台／RWD 與超市瀏覽實際驗收 | **今日完成Chrome分頁／空搜尋／SKU瀏覽並修正390px手機溢出**；部分完成 | 購物依 HEN R08，推薦依 JEFF R09/R10；基礎瀏覽已完成 | 圖片故障注入、完整無障礙及登入購物／推薦仍待驗；修正後截圖擷取逾時，保留DOM尺寸紀錄 |
| P2 R13 | 建置Firebase展示環境 | **今日確認目標vibecart-llmai及Blaze；Hosting無發布紀錄，Cloud Run／排程API未啟用**。尚未部署 | SAM：建立Flask後端與Hosting接線、私有配置；HEN／JEFF：功能驗收；SAM：R11/R12 | WSGI／HTTPS、機密配置、公開網址、Atlas／圖片依賴與遠端瀏覽；不對既有資料庫重新 seed |
| P2 R14 | PR #10 Network Access 文件審查／合併處理 | **今日完成open狀態及文件差異核對**；Atlas管理外掛需重新登入，CIDR Active／到期尚未讀回 | SAM：管理連線恢復後核對Access List；PyMongo可連線不證明0.0.0.0/0已啟用 | 文件區分owner回報與未讀回狀態；審查合併仍待處理 |
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

原安排中的 R18 發布、R07 草案、R03-a 匯入前檢查與 R12 規格已有今日成果，下一批依下方剩餘工作接續。

## 今日完成標記與下一步

**今日已完成**：R18推送與PR、R03-a工具／preflight／Atlas回滾、R07草案、R12驗收矩陣／JEFF獨立離線測試、R11基礎Chrome瀏覽與手機溢出修正、R14文件差異核對。上表仍保留每項剩餘工作；不代表整列全部完成。

下一批：SAM部署已補的synthetic隔離；JEFF核對評分／歸因消費者與D5語義，HEN交撤權／購物接口；SAM接續稽核migration、D4正式入庫、私有帳號與整合對帳。SAM可另補圖片故障／無障礙、部署方案及PR審查；備份依BACKUP前置處理。本輪Atlas正式持久新增／schema更新為0。

English: Consolidated SAM backlog with original R identifiers, explicit local/GitHub/Atlas/acceptance states, and single-owner prerequisites. Completed fixture work is separated from publishing, importing and integration acceptance. This document update performs no remote publication or database write.

## 本輪 Firebase 與通知更新

- **今日完成**：隔離程式0f6fc27、完整94項離線回歸、7項最後隔離回歸、GitHub最終head f16799f 的push／PR CI皆success；PR #16仍未合併。
- **今日完成**：Firebase CLI成功讀回Hosting site `vibecart-llmai`；管理API讀回Hosting releases為空。Cloud Run與asia-east1排程查詢返回SERVICE_DISABLED；不能推定所有其他專案／地區消費者不存在。
- Firebase成員依使用者提供截圖：SAM cashsam@gmail.com、JEFF jeff841117@gmail.com、HEN chen2000401@gmail.com均為擁有者。此次未變更IAM，亦未逐一以API重新核對成員。
- 尚未完成：啟用／配置Cloud Run後端、Hosting rewrite、私有秘密配置、遠端隔離與各consumer驗證，然後才apply／verify／重送D4。
- 證據：[Firebase preflight](inventory/FIREBASE_PREFLIGHT_2026-10-11.json)、[D4 preflight](inventory/D4_FORMAL_PREFLIGHT_2026-10-11.json)、[隔離修正](SYNTHETIC_ISOLATION_2026-10-11.md)。
- 郵件依使用者授權寄給上述三人；寄送結果以Gmail SENT及聊天回報為準。文件更新不自行宣稱郵件已送出。
