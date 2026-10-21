# LLM_PJ｜VibeCart AI 智慧購物與營運分析

**2026/10/20 PR #5離線快照接續**：[偏好快照操作](docs/PREFERENCE_SCORING.md)提供現行6＋4請求時計分之外的opt-in離線持久快照，JEFF主責計分契約、SAM整合。預設dry-run，apply需明確會員、資料庫確認與服務層唯一索引；本輪不連Atlas、不接前台、不啟排程。10/2測試與Atlas紀錄保留歷史日期，新驗證及GitHub交付另記。

**下一輪工作入口（2026-10-18）**：[依全部PR整理的未完成工作清單](專題進度/專案未完成工作清單_2026-10-18.md)，先做N01；[60筆PR完整核對清冊](docs/PR_AUDIT_2026-10-18.md)。驗收里程碑估算未完成度約38%，計算與範圍見清單。

中文為主，英文為輔。Chinese is authoritative; English summaries support collaboration.

VibeCart AI 承接 MuscleCore 運動用品電商，研究個人化購物推薦與營運洞察。本倉庫集中管理新版 MongoDB 結構與服務、舊 Flask 展示網站，以及規格、進度與驗證文件。

VibeCart AI builds on the MuscleCore sports store to explore personalized shopping and business intelligence. This repository contains MongoDB schemas and services, a legacy Flask demo, and project documentation.

## 目前狀態 / Current status

截至 2026-10-18 01:58，PR #21 與商品標題 RWD [PR #56](https://github.com/SamWang61/LLM_PJ/pull/56) 均已合併。正式網站的部署來源標籤為 `1d2abf2`，Cloud Run `vibecart-web-00015-nlk` 承接 100% 流量，Firebase Hosting 可瀏覽；[建置、同映像 D4 隔離探針、流量、公開路由與限制](docs/SAM_RELEASE_2026-10-18.md)分別留證。部署標籤是封裝來源，後續文件合併使 `main` SHA 較新，不能把文件提交視為新映像。D4 批次 1,240 筆已完成 apply、verify 與重送讀回，詳見 [D4 驗收](docs/D4_IMPORT_ACCEPTANCE_2026-10-18.md)。

- **新版資料層**：Complete Schema v4，含 SKU 購物車、訂單明細與評價服務；[10/17 Atlas 唯讀核對](docs/SAM_SCHEMA_AUDIT_2026-10-17.md)為 28 集合、89 索引、六筆 migration checksum 一致、12 項參照孤兒 0。D1～D3 原資料保留，不重新匯入。
- **正式網站**：`MuscleCore分析資料/website` 的 Flask + Jinja2 + MongoDB 程式已由 Cloud Run 提供服務、Hosting rewrite 導流；公開頁面檢查通過。早期隔離 Atlas 的會員／交易驗收與目前正式修訂的同版登入、跨裝置、交易簽收仍須區分。
- **尚待驗收**：正式修訂的完整角色與交易流程、真 BGE／Claude 與自由提問、D5 後台寫入及稽核、跨裝置 RWD／無障礙、S01～S12 素材與最終簽收。依[22 項工作清單](專題進度/專案工作清單_2026-10-17.md)逐項核對。

The Flask storefront is live through Cloud Run and Firebase Hosting. Public route checks and the D4 batch have recorded evidence; authenticated acceptance on the current revision, live AI models, and D5 administration remain open.

## 閱讀入口 / Start here

| 入口 / Entry | 用途 / Purpose |
|---|---|
| [Flask／SKU／AI 串接](docs/FLASK_SKU_AI_INTEGRATION.md) | 啟用方式、LangGraph 架構與待驗收項目 / Integration and UAT |
| [文件中心](docs/README.md) | 按主題閱讀 / Topic-based navigation |
| [優化系統](docs/優化系統.md) | 操作優化、Debug 與登出流程調整 / UX improvements and logout behavior |
| [目錄與管理政策](docs/REPOSITORY_GUIDE.md) | 路徑、版本與附件政策 / Layout and lifecycle |
| [全部文件索引](docs/DOCUMENT_INDEX.md) | 逐份文件的中英文定位 / Bilingual document catalog |
| [MongoDB 文件](VibeCart_AI/MongoDB/README.md) | 現行與歷史 Schema / Current and historical schemas |
| [展示網站](MuscleCore分析資料/website/README.md) | 本機啟動 / Local demo setup |
| [部署紀錄](docs/SAM_RELEASE_2026-10-18.md) | 已驗 revision、digest、公開檢查與驗收界線 / Release evidence |
| [主線／映像來源核對](docs/SAM_SOURCE_RECONCILIATION_2026-10-18.md) | 47 檔 Git blob 與部署 manifest 的雜湊比較 / Source equality |
| [備份作業規範](docs/BACKUP.md) | 每日 23:30 需求與設定狀態 / Backup requirements and status |
| [檔案清冊](docs/inventory/files.csv) | 路徑、大小、雜湊與讀取範圍 / Files, sizes, hashes and inspection scope |
| [貢獻指南](CONTRIBUTING.md) | 分支、提交、雙語文件 / Contribution workflow |

## 本機展示 / Run the demo

需求：Python 3.11+、Docker Desktop 或本機 MongoDB。以下初始化只應用於獨立的展示資料庫。

Prerequisites: Python 3.11+ and Docker Desktop or a local MongoDB. Seed only an isolated demo database.

```powershell
git clone https://github.com/SamWang61/LLM_PJ.git
cd LLM_PJ\MuscleCore分析資料\website
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
.venv\Scripts\python.exe seed_mongodb.py
.venv\Scripts\python.exe run.py
```

開啟 `http://127.0.0.1:5000`。示範帳號見網站 README，部署前必須替換。新版 Atlas 遷移應另依 MongoDB 文件操作，不能以展示網站 seed 取代。

Open `http://127.0.0.1:5000`. Replace demo credentials before deployment. Atlas migrations are a separate workflow.

## 驗證 / Validation

```powershell
python scripts/check_repository.py
cd MuscleCore分析資料\website
.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

CI 僅執行離線檢查與網站單元測試，不連接或寫入 Atlas。GitHub 不保存 `.env`、本機環境或大型附件；完整備份與公開原始碼的範圍不同，詳見備份規範。

CI runs offline checks and demo unit tests without contacting Atlas. Secrets, environments, and large artifacts are excluded from Git.

## 授權 / Licensing

本倉庫尚未選定開源授權；公開可見不等同授予再散布或商業使用權。既有圖片、報告與第三方素材仍須遵守原權利人的條款。No open-source license has been selected. Public visibility does not grant a redistribution license; third-party assets retain their original terms.
