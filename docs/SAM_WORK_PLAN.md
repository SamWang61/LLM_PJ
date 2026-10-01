# SAM 執行與接手清單 / SAM delivery plan

2026-10-02：因團隊人力調整，SAM 除組長整合工作外，需承擔額外一份分工。原四組工作保留；尚未確認額外接手的是前台、會員流程或資料庫測試，不擅自變更其他同學的負責範圍。以下先推進已確定由 SAM 負責的 AI／後台與跨模組驗證。

SAM is delivering the confirmed AI/dashboard and integration work first. The additional ownership assignment is pending team confirmation; personal circumstances are not part of this repository record.

## 執行順序 / Execution order

| 順序 | SAM 項目 | 本次狀態 | 驗收與依賴 |
|---|---|---|---|
| 1 | 營運後台、v4 連線及整合 | 已完成並合併 | [PR #3／#2 紀錄](MERGE_RECORD_2026-10-02.md) |
| 2 | v4 行為計分與商品半衰期 | 已實作 | 去重、70／30 上限、事件種類半衰期、未來事件排除 |
| 3 | 可重跑的批次計分工具 | 已實作 | 預設預覽；指定會員、事件上限、明確資料庫確認後寫入；並行更新防護 |
| 4 | 計分整合測試與交接 | 本次交付 | 離線案例與 [Atlas 讀回](SAM_SCORING_VERIFICATION.json)；操作見 [計分說明](PREFERENCE_SCORING.md) |
| 5 | 首次會員推薦池 | 待實作 | 真實評價 ≥4.5、各大類別一項、可推薦與有效 SKU 篩選；禁止把預設 4.0 當成真實評價 |
| 6 | 個人化 6＋破圈 4 推薦 | 待實作 | 串接計分結果；破圈規則必須滿足政策樣本門檻，缺資料不能宣稱已驗證 |
| 7 | 商品回購率與跨類別批次 | 待實作 | 需要有效非示範訂單；定義樣本不足、重算及清理策略 |
| 8 | BGE／Claude 真實模型驗收 | 待環境準備 | BGE 本機權重、Claude 可用模型與私有 API key；離線替代模型不等於真實 provider |
| 9 | 額外一組的工作 | 待確認組別 | 前台 RWD／會員購物／資料庫測試三擇一後補入對應驗收清單 |

本次的「批次工具」可供日後排程呼叫，但尚未建立常駐排程，也未接入每次瀏覽的同步寫入。完整推薦系統不因計分服務完成就視為完成。This delivery adds a runnable scoring job, not a deployed scheduler or a complete recommender.

驗證結果：50 項離線測試通過；真實 Atlas 計分預覽、寫入、重跑與 v4 validator 通過，臨時資料已清理。證據清冊：`docs/inventory/sam-scoring.csv`。

## 工作界線 / Working boundaries

- 從目前 main 建立聚焦分支，通過檢查後走 PR；保留其他組別分支與未提交文件。
- Schema 與既有 migration 不改寫；使用 `behavior_events`、`system_configs`、`user_preference_scores` 的 v4 契約。
- 不新增費用、部署、Atlas 帳號或 Secrets；本機 URI 保持私有。
- 真實驗證只建立唯一識別的臨時測試資料並清理；不把示範付款當正式購買。
- 分工更新不記錄同學的個人健康資訊；只記責任、依賴與交付狀態。

Preserve existing branches and migrations, keep credentials private, and track ownership without personal details.
