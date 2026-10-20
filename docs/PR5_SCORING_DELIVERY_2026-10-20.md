# PR #5 比對與離線持久快照交付｜2026-10-20

本輪依使用者「若新版取代就關閉，否則完成修正、推送、檢查後合併」執行。原候選 `dc3114de7de0cd72b370610a1bdd6e2a707d8940` 與 main `9273e40acae2f5ef34624ef2bbad420da3457a2e` 比對後，結論為 **未被完整取代，完成缺少的持久快照工具**。推薦契約主責 JEFF；Codex 執行 SAM 的資料庫、測試與整合工作，不改歷史作者。

## 比對結論

| 原候選內容 | 現行 main 與本輪處理 |
|---|---|
| 偏好權重、半衰期、70／30 | 前台 `storefront_ranking.py` 已有請求時計分及 6＋4；保留現行路徑。 |
| 明確會員的持久分數快照、預覽／重建 CLI | main 沒有 `preference_service.py`／`rebuild_preference_scores.py`；本輪完成獨立 opt-in 工具。 |
| 同事件去重／衝突、較舊時間與並行快照覆蓋防護 | 補完整輸入驗證、先去重再判購買資格、完整前像 CAS 與服務層唯一索引檢查。 |
| 舊 non-demo-only 計分 | 採現行 personalization：雙 synthetic 標記在排序／limit 前排除，真人有效 demo 購買可影響本人；不改 production 歸因。 |
| 舊文件、舊 50 項／Atlas 結果 | 保留 10/2 歷史標示，六處衝突保留最新 main；本輪新結果獨立記錄。 |

需求依據是[10/18對話決議第五、七節](../討論的相關記錄/商品評價與猜你喜歡6加4推薦_對話決議_2026-10-18.md)：請求時計分不是全部歷史資料的持久化排程。不能用前台 6＋4 成功宣稱舊批次工具已全部交付，也不能把這個工具合併當排程已啟用。

## 本輪實作

[操作與完整契約](PREFERENCE_SCORING.md)記錄 CLI 與快照語義。保留 snapshot version1 的分類 raw 權重 cap70／30、商品逐事件衰減及明確 ObjectId 搜尋；現行前台分類也會衰減、可按搜尋文字找商品，兩者不宣稱數值相等。

- 預設 dry-run、明確 1～100 會員、每人 1～100000 事件；apply 要精確 database-confirm。CLI 參數錯誤不回印任意原字串，輸出僅彙總。
- synthetic 先排除再排序／限量；純計算入口也驗證。相同 event_id 的任何計分輸入衝突，於無效購買被排除前拒絕，防止漏驗。
- apply 在服務層要求完整、非 sparse／partial 的唯一 user_id 索引及 acknowledged write；保留 cross-category 分數，較舊 as_of 拒絕、BSON 毫秒精度、完整前像 CAS，首次建立由唯一索引防重。
- 重讀有效會員及唯一有效政策；政策／會員在最後檢查後的跨集合變動仍需維護時段及下一次重建收斂，沒有宣稱跨集合交易或完整撤權競爭保證。
- 原 `verify_v4_test.py` 保持 main，舊 P2 的臨時匯入不再混入既有 smoke；新 CLI 從倉庫根目錄獨立執行並驗證入口。

## 實際驗證

[去敏機器報告](inventory/PR5_SCORING_DELIVERY_2026-10-20.json)保存起訖、原候選／main、74 項唯一測試、54 檔執行來源對帳及清理。

| 範圍 | 本輪結果 |
|---|---|
| 單元／CLI | 54＋13＝67 passed。涵蓋雙標記、無效型別／版本、事件身份衝突、政策更動、會員失效、上限／索引／BSON 及參數去敏。 |
| 真 localhost MongoDB 8.0.20 | 10:35:09～10:35:18，54 單元＋7 真持久化＝61 passed／0 skipped。實際 strict validator、唯一索引、重跑、完整前像 CAS／首次建立競爭、同 timestamp 新欄位防覆蓋、validator 拒寫保留整份原快照。 |
| 去重後總數 | **74 項**＝54 單元＋13 CLI＋7 真持久化；不把兩輪重疊單元重複加總。 |
| 清理 | 新建無憑證 127.0.0.1 replica set；所有隨機 ren_acceptance 測試庫讀回 0，該輪 mongod 程序已停止。 |
| 先前本機嘗試 | 首次未初始化 replica 選取、單檔 schema 匯入及啟動 socket timeout 造成三次前置失敗，各輪程序均停；修正後以上完整重跑通過，未抹除失敗紀錄。 |

GitHub workflow 加入 CLI 隔離測試；原真 MongoDB harness 會執行新持久化測試，要求無失敗／錯誤／skipped。新 HEAD 的 PR／push 檢查及合併結果以 [PR #5](https://github.com/SamWang61/LLM_PJ/pull/5) 實際紀錄為準。

## 交付界線

本輪 54 個網站執行檔逐 byte 等於整合 main，既有前台與線上來源未改；新服務／CLI 為倉庫內明確執行的工具，未加入網站雲端封裝白名單。沒有連線或寫入 Atlas、重新匯入 D1～D4、部署 Cloud Run／Firebase 或建立常駐排程。持久快照的正式資料 apply、前台採用及每日／週／月排程仍各自需要後續實際證據；V5 本人實機／異機與具名驗收不因本 PR 自動改計數。
