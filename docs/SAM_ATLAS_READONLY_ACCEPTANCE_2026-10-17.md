# SAM Atlas 唯讀資料對帳｜2026-10-17

核對時間：2026-10-17 約 11:22（Asia/Taipei）。透過 MongoDB Atlas 連接器對專案 `vibecart_ai` 的 `vibecart-ai-free`／資料庫 `vibecart_ai` 執行唯讀查詢；本頁不記錄連線字串、帳密、私人 ID 或完整 Network Access IP。**沒有寫入、重匯、清理或建立測試帳號。**

| 項目 | 唯讀讀回 | 驗收界線 |
|---|---|---|
| 集合 | 28 個 | 只確認集合清單，未核對全部 validator。 |
| `schema_migrations` | 6 筆，全為 `succeeded` | 6 筆 checksum 逐一與 PR #21 當前 Git 提交的對應 migration／schema 原始位元組重算結果相同：`20260916_01`、`20260916_02`、`20260918_03`、`20260918_04`、`20261005_05`、`20261014_06`。不代表已在新環境重跑 migration。 |
| 商品／SKU | active v4 商品 336、active SKU 336 | `product_skus.product_id` 對 `products._id` 的唯讀 `$lookup` 查得孤兒 SKU 0；尚未逐筆核對價格、庫存與畫面。 |
| D1～D3 | 原批次訂單 3,000、明細 8,969 | 全部訂單 3,002、全部明細 8,971；`order_items.order_id` 對 `orders._id` 的唯讀 `$lookup` 查得孤兒明細 0。額外兩筆 `is_demo=true` 訂單保留，不重匯 D1～D3。 |
| D4 | 指定 `metadata.synthetic_batch_id=sam-behavior-20261011-v1` 事件 0 | consumer 遠端隔離尚未證明，**不得 apply D4**。 |
| Session | `auth_sessions` 0 | 只是當下筆數，不能代替登入／跨裝置／撤權遠端驗收。 |
| 索引抽查 | users 4、auth_sessions 3、products 5、product_skus 3、carts 5、orders 6 | 索引名稱已讀回；`behavior_events` 索引查詢工具回內部錯誤，未把該集合列為驗過。未宣稱全部 28 集合或 validator 完整。 |
| Atlas Network Access | 4 筆規則，其中 1 筆為 `0.0.0.0/0` | 全網段規則屬上線前安全缺口；本次未變更，以免影響現行 Cloud Run 連線。須核對規則來源、有效期限及服務固定出口或其他可行替代方案後，另行收斂並驗證連線。 |

上述數字是唯讀快照；雲端資料庫可連線，不代表 PR #21 的角色、交易、付款、consumer 或正式上線已簽收。[同版零流量預覽](SAM_PR21_REMOTE_PREVIEW_2026-10-17.md)仍拒絕登入與寫入。下一步先建立受限、可清理的遠端交易驗收環境，再取得會員、管理員、checkout 重送／庫存／明細的同版讀回；所有 consumer 遠端 synthetic 隔離完成前維持 [D4 閘門](D4_REMOTE_GATE_2026-10-17.md)。
