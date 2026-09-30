# LLM_PJ｜VibeCart AI 智慧購物與營運分析

中文為主，英文為輔。Chinese is authoritative; English summaries support collaboration.

VibeCart AI 承接 MuscleCore 運動用品電商，研究個人化購物推薦與營運洞察。本倉庫集中管理新版 MongoDB 結構與服務、舊 Flask 展示網站，以及規格、進度與驗證文件。

VibeCart AI builds on the MuscleCore sports store to explore personalized shopping and business intelligence. This repository contains MongoDB schemas and services, a legacy Flask demo, and project documentation.

## 目前狀態 / Current status

- **新版資料層**：Complete Schema v4，含 SKU 購物車、訂單明細與評價服務。2026-09-19 保存的證據為 27 集合、59 自訂索引、66 項整合測試通過；這是歷史證據，並非本次重新驗證 Atlas。
- **展示網站**：`MuscleCore分析資料/website` 為 Flask + Jinja2 + MongoDB MVP；已提供可選 v4 路由介接與離線測試；尚未完成真實資料庫整合驗收。
- **尚待完成**：完整 AI 推薦、排程計分、批次統計，以及真實模型與新版資料層整合驗收。規格中的 FastAPI／Firebase 部署是設計內容，不代表已部署。

The Flask demo now has an opt-in v4 adapter and LangGraph workflows; live integration remains unverified. Historical Atlas test reports are retained; AI ranking, scheduled scoring, deployment, and application integration are not represented as complete.

## 閱讀入口 / Start here

| 入口 / Entry | 用途 / Purpose |
|---|---|
| [Flask／SKU／AI 串接](docs/FLASK_SKU_AI_INTEGRATION.md) | 啟用方式、LangGraph 架構與待驗收項目 / Integration and UAT |
| [文件中心](docs/README.md) | 按主題閱讀 / Topic-based navigation |
| [目錄與管理政策](docs/REPOSITORY_GUIDE.md) | 路徑、版本與附件政策 / Layout and lifecycle |
| [全部文件索引](docs/DOCUMENT_INDEX.md) | 逐份文件的中英文定位 / Bilingual document catalog |
| [MongoDB 文件](VibeCart_AI/MongoDB/README.md) | 現行與歷史 Schema / Current and historical schemas |
| [展示網站](MuscleCore分析資料/website/README.md) | 本機啟動 / Local demo setup |
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
