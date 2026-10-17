# N03｜版本對應與交付核對｜2026-10-18 03:07

主責：[SAM](mailto:cashsam@gmail.com)。使用者重新登入後，**03:07 的本輪 N03 版本／路由／配置對應已完成讀回**；這個快照供 N04～N06 驗收使用，不是 N18 最終凍結或全站簽收。

## 03:07 控制平面與版本對應

| 項目 | 最新實際讀回 |
|---|---|
| 待驗 Git／CI 基線 | `c1ce5cc38727a7077013e0a6452d561ee10ecd67`，[CI #39061131544](https://github.com/SamWang61/LLM_PJ/actions/runs/39061131544) success；其 47 個部署 Git blob 與來源 `1d2abf2cfa7465636e49474062e11f6aca571dda` 完全相同。 |
| 正式／私有映像 | 正式 `vibecart-web-00015-nlk` **100%**；私有 `vibecart-acceptance-pr21-00005-5j5` 為其服務內 **100%**。兩者 Ready、來源 `1d2abf2`、不可變 digest `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b` 相同。 |
| 配置的資料庫映射 | 正式 `vibecart_ai`；私有旗標 `CLOUD_ACCEPTANCE_MODE=true`、`CLOUD_ACCEPTANCE_DB=vibecart_acceptance_pr21`。兩者非唯讀預覽、checkout 為 true；映射由目前非秘密 runtime flags 與已核對的 `cloud_runtime.py` 決定，本輪未重查 Atlas 使用者權限或資料。 |
| IAM | 正式服務公開 invoker 為 `allUsers`；私有 invoker 僅 `serviceAccount:vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com`，沒有額外條件或公開成員；runtime 身分已記錄。 |
| Hosting | release `sites/vibecart-llmai/releases/1791982222797000`、FINALIZED version `c3772dcc7c906211`；`**` → `asia-east1/vibecart-web`，與倉庫配置一致。既有 Hosting release 導向 Cloud Run 服務，本輪沒有重新發布。 |
| 回退 | `vibecart-web-00013-ds5` Ready、0%，保留 `release-80513a9` 標籤及舊 pinned 映像。 |
| 公開 GET | Hosting／Run 的首頁、live、ready 六項 200；私有服務匿名 live 403。這些請求沒有驗證登入成功、寫入或真模型。 |

[版本鎖定報告](inventory/sam-version-lock-20261018-0307.json)保存 main／CI、47 個來源 SHA-256、配置映射與回退；[完整控制平面讀回](inventory/sam-delivery-cloud-20261018-0300.json)保存 revision、IAM、非秘密旗標及 Hosting version／rewrite。換映像、配置或 consumer 後，依 N11 重新驗證。

## 03:00 來源核對與首次登入缺口（歷史）

| 核對範圍 | 實際結果 |
|---|---|
| main／CI | `f53d39c5fed91ba5b3815f9b92165e8d33d5325e`；[CI #39059948386](https://github.com/SamWang61/LLM_PJ/actions/runs/39059948386) success。PR #59 已合併，其來源封裝 P2 已修正；PR #60 與 N01 後續更新亦在此 main。 |
| 文件與程式 | 相較上次兩小時交付基線 `24920d5`，60 個變更後的現存檔案逐項核對工作樹／提交／不可變 GitHub 內容，位元組與 SHA-256 差異 0。完整相對路徑、大小、雜湊與 ref SHA 在[交付清冊](inventory/sam-delivery-reconciliation-20261018-0300.json)。原髒工作目錄保留。 |
| LFS | 四個本機物件與指標 fsck 通過；遠端各讀取 4,096 bytes，PDF 標記及遠端總長度與指標大小一致。兩個大型 PDF 約各 444 MB，本輪沒有完整重下載，也沒有將範圍讀取寫成完整遠端 SHA-256 重算。 |
| 封裝回歸 | `scripts/test_prepare_cloud_source.py` **1 passed／0 skipped**，驗證 CRLF 工作樹與未追蹤檔不污染提交來源。 |
| 真實封裝 | 以本次 main 封裝兩次，47 檔逐一與 Git blob 相同，兩個 archive 位元組相同，SHA-256 `ec1e82bae525a7120e74810b1350a51d3d003bdeb483169b2a9f774bbd042cfc`。47 個 Git blob 亦與先前映像來源 `1d2abf2cfa7465636e49474062e11f6aca571dda` 相同；沒有因此重新部署。 |
| 本機交付修正 | 新交易執行器 `.cjs` 的 checkout 是 CRLF、提交是 LF；已在本乾淨工作樹對齊，新增 `*.cjs text eol=lf`。既有 D4 執行器的精確原始位元組例外仍保留。 |
| 公開健康狀態 | Hosting／Run 的首頁、live、ready 共六項 GET 均 200；私有服務匿名 live 為 403。見[首次公開讀回及驗證缺口](inventory/sam-delivery-cloud-auth-gap-20261018-0300.json)。 |

## 03:00 當時引用的歷史部署證據

最近已提交的[同映像私有交易報告](inventory/sam-remote-transaction-20261018.json)時間為 **2026-10-17 18:08:35 UTC（台北 10/18 02:08:35）**：

| 項目 | 既有證據／來源規則 | 本輪狀態 |
|---|---|---|
| 正式服務 | `vibecart-web-00015-nlk` 100%，來源 `1d2abf2`、digest `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b`。 | 沒有新控制平面讀回，不將舊比例當作本輪確認。 |
| 私有服務 | `vibecart-acceptance-pr21-00005-5j5`，同來源／digest，獨立隔離驗收庫。 | 匿名 403 已讀；本輪 IAM／runtime flags／revision 尚未重讀。 |
| Hosting | [倉庫配置](../deploy/firebase/firebase.json)：`**` → `asia-east1/vibecart-web`。 | 網站可讀；最新 release／version／rewrite 尚未從控制平面取得。 |
| 資料庫 | `cloud_runtime.py` 固定正式庫為 `vibecart_ai`；僅受控驗收服務與明確旗標可選 `vibecart_acceptance_pr21`。 | 這是程式配置規則；本輪未讀 runtime 環境或 Atlas，未聲稱持久化／權限再驗通過。 |
| 回退 | [01:58 發布紀錄](SAM_RELEASE_2026-10-18.md)保存 `00013-ds5` 與 `release-80513a9` 回退標籤。 | 本輪沒有重讀標籤／流量，不執行回退。 |

本機 Firebase CLI 的預期帳號是 `cashsam@gmail.com`；03:00 查無預設或其他登入帳號，因此沒有向 Google 控制平面送出請求。已確認最新 CLI 為 15.34.0，並請使用者依登入流程執行 `npx -y firebase-tools@latest login`；憑證與授權碼不放入文件。

03:00 時待補的 revision、digest、流量、IAM、旗標、Hosting release／rewrite、配置的資料庫映射及回退，已在使用者重新登入後於上方 03:07 逐項取得。首次缺口保存在獨立報告；本輪沒有部署、變更 IAM、寫遠端資料庫或重匯資料。

English: Sixty changed files match immutable GitHub content, four LFS objects are remotely readable, and the 47-file archive is reproducible. Authentication was restored and the 03:07 version/routing/configuration snapshot is verified. Authenticated business flows, database-user permissions, models and final signoff remain separate acceptance work.
