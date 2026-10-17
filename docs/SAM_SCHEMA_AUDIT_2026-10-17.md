# SAM v4 schema 與參照唯讀核對｜2026-10-17

查核時間：2026-10-17 18:45:51（Asia/Taipei；報告時間為 10:45:51 UTC）。來源為本 PR 的 `scripts/check_v4_database.py`、六筆既有 migration 原始檔，以及 Atlas `vibecart_ai` 的即時唯讀讀回。查核沒有執行 migration、增刪文件或重匯 D1～D3／D4。

## 結果與可重現證據

| 項目 | 讀回 |
|---|---|
| 契約 | `v4-member-device-sessions-20261014` |
| 集合／索引 | 28／89；逐集合比對 validator、`strict/error`、索引名稱、鍵順序與選項 |
| 文件驗證 | 28 個集合均以目前 validator 計數；文件總數 13,430，沒有不符合契約的計數或查核錯誤 |
| migration | 六筆均 `succeeded`，其 checksum 各自與當初 migration 使用的原始檔位元組重算結果一致；無額外 migration |
| 合法參照 | 12 項 v4 參照逐項 `$lookup`，孤兒數均為 0 |
| 其他 | 額外集合 0；active recommendation policy 1；`status=passed`、`issues=0` |

完整、僅含集合名稱與計數的[唯讀 JSON 報告](inventory/sam-schema-audit-20261017.json) SHA-256 為 `f7f611e614bcf28cab8d54476e9a95966ebf229856e12ff39388a7b30cf2d453`。報告不含 Mongo URI、帳密、文件內容、個人 ID 或電郵。重現方式是在具有正式庫唯讀權限的受控環境設定 `DATA_MODE=v4`，執行 `python scripts/check_v4_database.py --env-file <受控環境檔> --report <新的報告路徑> --relationships`；程式拒絕非指定 Atlas 主機或資料庫，且拒絕覆寫既有報告。

此結果完成工作清單 #04 的**目前版本資料結構、migration checksum 與參照唯讀核對**。它是單一時間的資料庫快照；未重跑 migration、未比對每一商品畫面／價格／庫存，亦不代表正式會員交易、真付款、真模型、D4 consumer 隔離或全站最終簽收。D4 指定批次仍依[遠端閘門](D4_REMOTE_GATE_2026-10-17.md)維持禁止 apply。
