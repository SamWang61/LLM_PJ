# D5 稽核與冪等收據：本機 migration 演練

**下一階段準備，未啟用正式Atlas或網站。** 依[最新範圍](SAM_N02_V1_SCOPE_HANDOFF_2026-10-18.md)，10/18 v1維持唯讀後台。新增來源提交`4eeebbe`；現有`schema_active_v4.py`的六筆migration及checksum未修改。

| 交付 | 已驗範圍 | 未完成範圍 |
|---|---|---|
| `schema_d5_v1.py` | admin_audit_logs與admin_write_requests；稽核180天TTL、收據expires_at TTL；actor/request唯一；資源快照白名單，拒絕密碼／token／角色提升欄位 | 服務端讀取必須主動判斷到期，不只等待TTL背景清除 |
| `migrate_admin_audit.py` | 預檢只讀、兩集合先驗漂移再DDL、重跑單ledger、strict/error validator、索引／TTL／checksum漂移拒絕 | 第七筆active checker整合、下一階段正式rollout與遠端讀回；本CLI僅允許無憑證localhost的sam_d5_acceptance_隔離庫 |
| 真MongoDB交易 | business＋audit＋receipt同交易commit；invalid audit、重複收據使business及audit回滾 | D5實際API／UI、批量atomic/per_item服務、100/101上限與重送hash衝突、到期查詢、遠端驗收 |

一次性`mongo:8` replica set、隨機127.0.0.1 port、無憑證；每個fixture隨機隔離DB，測後移除，僅admin/config/local保留，容器也移除。[成功報告](inventory/N08_LOCAL_RETRY1_2026-10-18.json)及[JUnit](inventory/N08_LOCAL_RETRY1_2026-10-18.xml)：**15項D5＋186項網站＝201 passed／0 skipped**。不使用Atlas或.env。

首次真MongoDB演練發現`required: []`不被validator接受，造成10 failed／191 passed；已修正快照schema移除空required，重跑201全部通過。[首次失敗摘要](inventory/N08_LOCAL_2026-10-18.json)保留，不覆寫成成功；失敗JUnit留本機私有工作暫存。

重現：先安裝網站requirements-test，再執行`python scripts/run_transaction_acceptance.py --report <新報告.json> --junit <新JUnit.xml>`。需要Docker；報告以exclusive create避免覆蓋舊證據，任何fail/error/skipped或清理失敗皆非通過。CI已加入此真交易步驟，雲端結果以當前PR head檢查為準。
