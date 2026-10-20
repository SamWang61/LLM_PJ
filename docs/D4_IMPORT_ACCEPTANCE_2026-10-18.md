# D4 合成事件正式庫匯入與驗收｜2026-10-18

驗收窗口：SAM。執行時間約 00:35～00:41（Asia/Taipei）。範圍僅為 `vibecart_ai.behavior_events` 的 `sam-behavior-20261011-v1` 合成批次；D1～D3 不重匯，商品庫存與既有訂單不重設。

## 閘門如何通過

[PR #47](https://github.com/SamWang61/LLM_PJ/pull/47) 已合併為 `f513b32b2774c092b5cee1fb4f35f858a1473c01`，[main CI](https://github.com/SamWang61/LLM_PJ/actions/runs/39049790404) success。其[同版隔離對照](REN_D4_PRIVATE_PROBE_2026-10-17.md)證實管理監控與前台推薦在 sort／limit 前排除 1,001 筆 synthetic，正常事件仍可見；探針資料清理及 IAM 撤權均獨立讀回 0。

00:35 的[全專案盤點](inventory/sam-d4-final-inventory-20261018.json)補核 v1 global services／Jobs／worker pools，無 unreachable 或未讀分頁：只有正式與私有兩服務，Jobs／worker pools 0；Scheduler／Functions／Workflows／Tasks API 未啟用，Pub/Sub topic／subscription 0。先前 `me-central2` 區域政策拒絕仍保留為診斷，沒有拿區域失敗冒充成功；全專案清單本次可完整讀回。Hosting `**` 仍指向 `asia-east1/vibecart-web`。

正式 `vibecart-web-00013-ds5` 100% 與私有 `vibecart-acceptance-pr21-00004-9qr` 都使用來源 `80513a951d0dff67fd47a153a45918522b5ffbb5`、映像 `sha256:57c8fd038d7c231a4e417471a66b9c7996c296efd2d7b1ff70302c46a45f0fab`。已部署的兩 consumer 有同映像遠端證據；未部署的計分／正式歸因則以完整盤點留證。

[正式 isolation evidence](inventory/sam-d4-isolation-evidence-20261018.json)引用不可變 GitHub commit URL，逐檔下載確認 SHA-256；`behavior_import.isolation_evidence()` 已驗格式與範圍。工具使用的 canonical evidence digest 為 `436f14e63661e553009a4dc06208cf27968bfe835f0ef15479637988e8d0be45`。此為通過當時的部署範圍，未來新增 consumer 或換映像須重驗。

## 匯入、讀回與重送

執行 `VibeCart_AI/MongoDB/test_data/behavior_import.py`，受控 v4 環境檔只供程式讀取；報告不含 URI、帳密或個資。先前 [preflight](inventory/sam-d4-formal-preflight-20261018.json)及 [abort dry-run](inventory/sam-d4-formal-dry-run-20261018.json)通過，正式 apply 亦在 snapshot transaction 內重核來源、schema、索引及碰撞，再 commit 並讀回。

| 階段 | 既有／缺少 | 新增 | 結果 |
|---|---|---|---|
| [首次 apply](inventory/sam-d4-formal-apply-20261018.json) | 0／1,240 | 1,240 | committed=true；交易及提交後讀回通過。 |
| [verify](inventory/sam-d4-formal-verify-20261018.json) | 1,240／0 | 0 | 全批次 BSON、event_id 與來源契約一致。 |
| [同批次 apply 重送](inventory/sam-d4-formal-replay-20261018.json) | 1,240／0 | 0 | 冪等通過，沒有重複事件或額外新增。 |

三階段 dataset SHA-256 均為 `da6998425bc80746902b407336489f43bfcc77bc7f092d9ece5e3b02d1d0edea`，與 preflight／dry-run 相同；規劃參數為預設 `--max-orders 100`。

報告的 `expected` 是共用的離線資料集規格，其中 `database_writes=0` 不是本次寫入觀測值；實際結果以頂層 `committed`／`inserted` 為準，首次 apply 實際新增 1,240。

另一 [Atlas 連接器獨立讀回](inventory/sam-d4-final-readback-20261018.json)：SEARCH、PRODUCT_VIEW、ADD_TO_CART、PURCHASE 各 **310**，合計 **1,240**；每筆均 `metadata.synthetic=true`、`metadata.exclude_from_attribution=true`，漏標 **0**。原 D1～D3 仍有 **3,000 訂單／8,969 明細**，額外 demo 訂單 **2** 保留。demo count 介面曾 internal error，改以聚合重試取得 2，未將錯誤改記為成功。

## 判定與下一步

工作清單 #11 的本批次匯入、資料讀回與冪等重送已取得證據；本頁是 D4 範圍驗收。合成 PURCHASE 不代表真付款或正式歸因，權重合計也不是營運 KPI。真 BGE／Claude、自由提問、D5 實作、手機實機、最終簡報與全站具名簽收仍按各自清單推進。報告位元組雜湊另見[交付清冊](inventory/sam-d4-final-sha256-20261018.json)。
