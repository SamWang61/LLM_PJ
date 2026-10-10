# SAM 驗收矩陣與稽核草案｜2026-10-11

主責 SAM；功能實作 JEFF（AI／後台）、HEN（會員／購物）。本文件交付測試規格，不把未接線案例標成已通過。

## R07 稽核 schema 草案

草案檔：`VibeCart_AI/MongoDB/schema_admin_audit_draft.py`。未加入 `schema_active_v4`、未執行 migration、未建立 Atlas 集合。保留所有五筆歷史 schema／migration 原始位元。

- 提議 migration：`20261011_06_admin_audit_v1`，集合 `admin_audit_logs`。既有欄位 actor_id/request_id/resource_type/resource_id/before/after/reason/result/created_at，採 UTC 日期。
- before/after 依 product/sku/order/customer 列白名單，拒絕額外欄位；不接受 password_hash、token、URI、角色或任意 MongoDB operator。理由需由服務層拒絕個資／秘密，JSON schema 不能完成文字去識別化。
- created_at TTL 180 天，另有 resource 與 actor/request 查詢索引。**沒有 request_id 唯一索引**：等 JEFF 確認 actor／批量逐筆範圍再定案，不能盲目限制多資源交易。
- 草案只存 succeeded 的同交易業務稽核；rollback 後如何另存拒絕／失敗紀錄待定。TTL 稽核不是永久冪等紀錄；需另定 ledger／重送有效期限。
- customer before 可為 active/inactive；after 的 inactive/is_active=false、sku 的兩位金額／可售量推導與保留庫存、訂單前置條件由服務驗證。草案尚未執行 MongoDB validator 拒絕測試，不能標部署就緒。

可先完成的草案已交付；部署依賴 JEFF 確認批量、失敗紀錄與重送期限，SAM 再做 migration runner／current checker 更新、validator 拒絕案例與交易測試。

## R12-A／R12-B／R12-C 驗收矩陣

| 編號 | 測試刺激 | 預期與必要證據 | 前置負責人 | 目前狀態 |
|---|---|---|---|---|
| A01 | Email／電話／身分證及分隔／控制字元變形輸入 | 明確個資拒送，fake provider 呼叫數為0；無全文日志。規則無法涵蓋的輸入要明列限制 | JEFF | 規格今日完成，接線待驗 |
| A02 | 300／301字、空白、非法 intent、控制字元 | 300字可接受，301與空問題拒絕；清理規則明確，預設 intent 不送文字框 | JEFF | 規格今日完成，接線待驗 |
| A03 | 問題要求覆写 system／查會員／執行命令 | 僅依白名單；不查 users、不執行操作；供應商輸出 HTML escape；prompt 不足以證明全防護 | JEFF | 規格今日完成，接線待驗 |
| A04 | 同管理員第6／7次，多 worker／不同帳號 | 預設6次／分鐘，超限429；明訂 process-local 限制與跨 worker 行為，不宣稱全部署統一限流 | JEFF | 規格今日完成，接線待驗 |
| A05 | 問題含敏感文字、相同問題重送、300秒到期 | 檢查問題全文／回答是否留 cache；定案保留與刪除行為；logs 僅 intent/長度/耗時/token | JEFF | 快取政策未定案 |
| A06 | 瀏覽器竄改數值／超額欄位 | 伺服器重新聚合，預覽與該次傳送物件一致；來源批次、demo、截止時間有明確意義 | JEFF | 欄位差異待修正 |
| B01 | 未登入/customer/停用admin/失效session/CSRF錯誤 | 401/403（或明訂頁面redirect契約），不得更新與成功稽核；驗API與頁面一致 | JEFF/HEN | 功能／接口待交付 |
| B02 | 相同request ID同內容、不同內容、雙人版本衝突 | 同內容原結果，異內容409；expected_updated_at不符409，不覆蓋 | JEFF | 批量／ledger契約待定 |
| B03 | 100／101批量、逐筆與原子模式、稽核故障 | 上限明確；原子失敗全部回滾，逐筆模式回傳各結果；稽核故障不可留下成功更新 | JEFF，SAM稽核 | R07尚未部署 |
| B04 | stock<reserved、負值／非整数、價格第三位小數 | 422；available=stock-reserved；stock_status依現行規則；不重算歷史demo庫存 | JEFF/HEN | 接線待驗 |
| B05 | pending跳completed、未paid轉confirmed、未shipped轉shipping、未delivered轉completed | 非法跳躍拒絕；合法條件才能轉移，終態不可任意回退 | JEFF/HEN | 接線待驗 |
| B06 | paid訂單取消、退款請求、金額／快照／is_demo改寫 | v1不退款，不假裝付款商已退款；取消庫存責任明訂；保護欄位拒寫 | JEFF/HEN | 功能／付款契約待交付 |
| B07 | 停用customer後重播舊cookie/token，停用admin/自己 | 舊會員不能繼續操作；admin後台停用403；管理員直接資料庫維護另有稽核流程 | HEN/JEFF | 撤權接口待驗 |
| B08 | 有歷史訂單商品／會員的硬刪除 | v1沒有授權刪除接口，測404或明訂拒絕；後續先定參照、稽核及恢復 | JEFF | 刪除契約待定 |
| C01 | 台北午夜、跨年、2024閏日，366／367日 | UTC半開區間；每日補零；同口徑相鄰等長比較期；超上限拒絕 | JEFF | 分支離線測試另記，不算畫面對帳 |
| C02 | 全狀態分母／paid非cancelled分子，demo only/exclude/all | 訂單分子分母及Decimal營收吻合標準答案；排除既有demo後為零 | JEFF | live畫面/API待驗 |
| C03 | 零有效單／零基期，5000／5001單 | 客單／成長率null；5001回range_too_large，禁止靜默截斷營收 | JEFF | live畫面/API待驗 |
| C04 | 最低價下架／無庫存SKU、無可售SKU商品 | 僅active且available>0的SKU決定最低可售價與候選；基準商品排除 | JEFF | 分支離線測試另記 |
| C05 | 100／101商品、促銷成本未知、營收因果提問 | 排序截斷有標示；promotion_eligible=null；資料不足不捏造因果 | JEFF | live模型待驗 |
| D01 | synthetic本批與真實事件混合、計分排程／正式歸因 | 分別篩選／標示；production歸因、計分與推薦不混入synthetic | JEFF | 已查明目前consumer不隔離，正式入庫阻擋 |
| D02 | D4相同批次重送、變更payload、唯一碰撞、交易插入故障 | 完全相同零新增；不同內容拒覆寫；故障rollback；只寫behavior_events | SAM | 冪等／衝突離線測試與Atlas rollback今日通過；正式重送待apply後驗 |

## R03 操作方式與 evidence

工具：`VibeCart_AI/MongoDB/test_data/behavior_import.py`。明確 `--env-file` 固定目標 `vibecart-ai-free.odqe25w.mongodb.net/vibecart_ai`，不複製環境憑證。預設100筆訂單，僅投影必要參照，不讀會員密碼／Email，不在報告輸出ID或文件。

```powershell
python VibeCart_AI/MongoDB/test_data/behavior_import.py preflight --env-file <私有設定路徑> --report <新報告路徑>
python VibeCart_AI/MongoDB/test_data/behavior_import.py dry-run --env-file <私有設定路徑> --report <新報告路徑>
```

preflight完全唯讀；dry-run在snapshot/majority交易試插入、逐文件讀回後abort，報告committed=false/inserted=0。apply需另傳 `--isolation-evidence`，包含database/batch/deployment_ref/checked_at及admin_monitor/storefront_recommendation/scoring_scheduler/production_attribution四項passed，並由SAM實際核對部署證據；旗標文件不能取代live驗收。本輪没有提供虚构隔離證據，不執行apply。

今日實際結果：[Atlas唯讀](inventory/SAM_DATABASE_CURRENT_2026-10-11.json)、[D4 preflight](inventory/D4_PREFLIGHT_2026-10-11.json)、[D4交易回滾](inventory/D4_ROLLBACK_2026-10-11.json)。1,240事件、四種類各310、檢查和3,100；正式插入0。UTC時間依報告，台北日期為10/11。沒有新增migration或測試帳號。

English: Delivers an undeployed audit-schema proposal and an acceptance matrix. D4 live-reference preflight and transaction rollback passed, but production isolation is missing. Drafts, offline tests, rolled-back validation and committed Atlas updates remain separate states.
