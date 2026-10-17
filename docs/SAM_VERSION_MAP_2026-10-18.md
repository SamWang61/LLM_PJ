# N03｜版本對應與交付核對｜2026-10-18 03:00

主責：[SAM](mailto:cashsam@gmail.com)。來源核對與控制平面讀回的結果分列如下；N03 仍有遠端證據缺口。

## 本輪已驗證

| 核對範圍 | 實際結果 |
|---|---|
| main／CI | `f53d39c5fed91ba5b3815f9b92165e8d33d5325e`；[CI #39059948386](https://github.com/SamWang61/LLM_PJ/actions/runs/39059948386) success。PR #59 已合併，其來源封裝 P2 已修正；PR #60 與 N01 後續更新亦在此 main。 |
| 文件與程式 | 相較上次兩小時交付基線 `24920d5`，60 個變更後的現存檔案逐項核對工作樹／提交／不可變 GitHub 內容，位元組與 SHA-256 差異 0。完整相對路徑、大小、雜湊與 ref SHA 在[交付清冊](inventory/sam-delivery-reconciliation-20261018-0300.json)。原髒工作目錄保留。 |
| LFS | 四個本機物件與指標 fsck 通過；遠端各讀取 4,096 bytes，PDF 標記及遠端總長度與指標大小一致。兩個大型 PDF 約各 444 MB，本輪沒有完整重下載，也沒有將範圍讀取寫成完整遠端 SHA-256 重算。 |
| 封裝回歸 | `scripts/test_prepare_cloud_source.py` **1 passed／0 skipped**，驗證 CRLF 工作樹與未追蹤檔不污染提交來源。 |
| 真實封裝 | 以本次 main 封裝兩次，47 檔逐一與 Git blob 相同，兩個 archive 位元組相同，SHA-256 `ec1e82bae525a7120e74810b1350a51d3d003bdeb483169b2a9f774bbd042cfc`。47 個 Git blob 亦與先前映像來源 `1d2abf2cfa7465636e49474062e11f6aca571dda` 相同；沒有因此重新部署。 |
| 本機交付修正 | 新交易執行器 `.cjs` 的 checkout 是 CRLF、提交是 LF；已在本乾淨工作樹對齊，新增 `*.cjs text eol=lf`。既有 D4 執行器的精確原始位元組例外仍保留。 |
| 公開健康狀態 | Hosting／Run 的首頁、live、ready 共六項 GET 均 200；私有服務匿名 live 為 403。見[本輪公開讀回及驗證缺口](inventory/sam-delivery-cloud-20261018-0300.json)。 |

## 部署與資料庫對應：歷史讀回及本輪缺口

最近已提交的[同映像私有交易報告](inventory/sam-remote-transaction-20261018.json)時間為 **2026-10-17 18:08:35 UTC（台北 10/18 02:08:35）**：

| 項目 | 既有證據／來源規則 | 本輪狀態 |
|---|---|---|
| 正式服務 | `vibecart-web-00015-nlk` 100%，來源 `1d2abf2`、digest `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b`。 | 沒有新控制平面讀回，不將舊比例當作本輪確認。 |
| 私有服務 | `vibecart-acceptance-pr21-00005-5j5`，同來源／digest，獨立隔離驗收庫。 | 匿名 403 已讀；本輪 IAM／runtime flags／revision 尚未重讀。 |
| Hosting | [倉庫配置](../deploy/firebase/firebase.json)：`**` → `asia-east1/vibecart-web`。 | 網站可讀；最新 release／version／rewrite 尚未從控制平面取得。 |
| 資料庫 | `cloud_runtime.py` 固定正式庫為 `vibecart_ai`；僅受控驗收服務與明確旗標可選 `vibecart_acceptance_pr21`。 | 這是程式配置規則；本輪未讀 runtime 環境或 Atlas，未聲稱持久化／權限再驗通過。 |
| 回退 | [01:58 發布紀錄](SAM_RELEASE_2026-10-18.md)保存 `00013-ds5` 與 `release-80513a9` 回退標籤。 | 本輪沒有重讀標籤／流量，不執行回退。 |

本機 Firebase CLI 的預期帳號是 `cashsam@gmail.com`；03:00 查無預設或其他登入帳號，因此沒有向 Google 控制平面送出請求。已確認最新 CLI 為 15.34.0，並請使用者依登入流程執行 `npx -y firebase-tools@latest login`；憑證與授權碼不放入文件。

N03 待補：重新登入後讀取正式／私有 revision、digest、流量、IAM 與非秘密旗標，讀 Hosting release／rewrite，核對配置的資料庫映射及回退，再結案。公開 HTTP 200、來源相同及先前交易報告沒有取代這些讀回。

English: Sixty changed files match immutable GitHub content, four LFS objects are remotely readable, and the 47-file committed-source archive is reproducible. Current control-plane verification is incomplete because the CLI has no authenticated account; historical deployment evidence remains explicitly dated.
