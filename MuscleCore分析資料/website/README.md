# MuscleCore｜Python + MongoDB 智慧運動商城

本專案把原運動商品購物網站重構成可展示的 Python MVP，採 Flask Blueprint 分層、MongoDB 文件資料庫與角色權限。前台為 `VibeCart AI` 個人化推薦；後台為 `VibeInsight AI` 營運洞察。

## 已完成

- 商品首頁、分類篩選、商品詳情、購物車與示範結帳
- 會員註冊／登入／登出，以及 customer、admin 角色權限
- MongoDB 4 個核心集合：users、products、orders、behavior_events
- 一鍵建立集合驗證規則、索引、測試帳號與示範商品
- 可解釋推薦引擎：依瀏覽、收藏、加購、購買加權
- 管理後台 KPI、低庫存提示、熱銷排行與推薦事件監控
- 響應式深色運動品牌介面

## Windows 快速啟動

最簡單的方式：安裝 Python 3.11+ 與 Docker Desktop，確認 Docker Desktop 已啟動後，直接雙擊 `start_windows.bat`。腳本會建立虛擬環境、安裝套件、啟動 MongoDB、建立全部集合與測試資料，再開啟網站服務。

若要逐步執行，可在本目錄開啟 PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
python seed_mongodb.py
python run.py
```

完成後瀏覽 `http://127.0.0.1:5000`。

若本機已有 MongoDB，可省略 `docker compose up -d`。

## 示範帳號

| 角色 | 帳號 | 密碼 |
|---|---|---|
| 會員 | demo@musclecore.tw | Demo123! |
| 管理員 | admin@musclecore.tw | Admin123! |

正式展示前，請務必更換示範密碼與 `.env` 的 `SECRET_KEY`。

## 專題架構

```text
MuscleCore/
├─ app/
│  ├─ auth.py              # 身分驗證與角色權限
│  ├─ store.py             # 商城、購物車、結帳
│  ├─ admin.py             # 管理後台
│  ├─ db.py                # MongoDB 連線
│  ├─ services/            # 推薦與營運分析
│  ├─ templates/           # Jinja2 頁面
│  └─ static/              # CSS 與圖像
├─ seed_mongodb.py         # MongoDB 一鍵初始化
├─ docker-compose.yml      # MongoDB 容器
├─ run.py                  # 啟動入口
└─ tests/                  # 核心邏輯測試
```

## 雙模型專題呈現方式

目前推薦與洞察採本機可解釋規則模型，因此不用 GPU、沒有 API 成本，四週內能穩定完成。第二階段可保留相同介面，接入 Hugging Face Inference API 或 OpenAI-compatible API，將「規則基準組」和「LLM 實驗組」做 A/B 比較，評估準確度、回應時間、成本與解釋品質。

## 建議四人 Git 分工

1. 前台與 RWD：templates/store、static/css
2. 會員／購物流程：auth.py、store.py
3. MongoDB 與測試：db.py、seed_mongodb.py、tests
4. AI 與後台：services、admin.py、templates/admin

分支可使用 `feature/store-ui`、`feature/auth-order`、`feature/mongodb`、`feature/ai-dashboard`，經 Pull Request 互相檢查後合併到 main。

## English summary

This is the legacy Flask + MongoDB demonstration store. Create a virtual environment, install requirements, copy the example environment file, start local MongoDB, seed an isolated demo database, and run run.py. The two service tests run offline with pytest. Demo accounts are for local use only. The new v4 services in VibeCart_AI are not wired into this application.
