> 2026-09-27 整理註記：本文件保留歷史介紹。現行倉庫以 LLM_PJ 為根目錄，閱讀入口見 [README](README.md) 與 [文件中心](docs/README.md)。以下舊推送建議及測試數字依原日期解讀。
> Organization note: this historical overview is retained. The repository root is now LLM_PJ; use the root README and documentation hub for navigation. Historical test counts were not rerun for this update.

# VibeCart AI 專案總覽與 GitHub 推送整理

## 2026-09-19 完整 Schema 更新（現行）

指定 Atlas 資料庫已依完整規格更新為 19 個核心集合加 8 個保留集合，共 27 個集合、59 個自訂索引。商品與 SKU、訂單與明細分離，新增評價、行為計分、回購統計、關聯規則及推薦記錄結構；66 項新版整合測試通過。

現行程式為 [SKU 購物車服務](VibeCart_AI/services/sku_cart_service.py) 與 [評價服務](VibeCart_AI/services/review_service.py)。完整欄位、遷移與測試證據集中在 [MongoDB 文件入口](VibeCart_AI/MongoDB/README.md)。舊 Flask 網站尚未切換至新資料結構；推薦生成、計分與統計排程尚未部署。

## 2026-09-17 購物車架構更新（歷史）

Atlas `vibecart_ai` 已採用 `carts` 目前狀態＋`cart_events` 歷史事件的雙層模型，合計 14 集合、31 個自訂索引。購物車與事件使用 schema v3，其餘集合維持 v2；同會員僅限一份 active Cart，converted／abandoned 歷史保留。結帳以交易同步扣庫存、建立訂單、寫事件及轉換購物車。

新交易式服務位於 [VibeCart_AI/services/cart_service.py](VibeCart_AI/services/cart_service.py)，已通過 15 項 Atlas 整合測試。最新資料庫與 API 接線設計見 [購物車架構文件](VibeCart_AI/MongoDB/09_購物車架構與API整合.md)，實際結果見 [驗證報告](VibeCart_AI/MongoDB/10_購物車更新驗證結果.md)。下方原 `MuscleCore分析資料/website` 為舊站參考，仍採 Session 購物車；本次未切換其資料库連線或註冊新路由。

## 專案介紹

VibeCart AI 是將 MuscleCore(運動用品電商網站)平台，改由以 Python Flask 建置，連接 MongoDB 儲存會員、商品、訂單與使用者行為事件，並提供基本的商品瀏覽、登入註冊、購物車、結帳，採用雲端與本地雙管道AI，落實：前台主動推薦商品、後台智能分析管理營運。

目前這個根目錄同時包含：
- Flask + MongoDB 主程式 (C:\LLM\LLM_PJ\MuscleCore分析資料\website)
- 專題進度文件 (C:\LLM\LLM_PJ\專題進度)
- 討論紀錄 (C:\LLM\LLM_PJ\討論的相關記錄)
- 資料表設計圖 (VibeCart_AI_專案整合規格_v1.1.md)
- 舊網站展示影片、報告 PDF、壓縮備份檔 (C:\LLM\LLM_PJ\MuscleCore運動用品電商網站)

如果日後要推送到 GitHub，建議以 `C:\LLM\LLM_PJ\VibeCart_AI` 作為主專案根目錄，或把它整理成 repository 的根目錄；大型影片、超大 PDF、zip 備份與 `.env` 不應直接推到 GitHub。

## 技術棧

- 後端框架：Flask 3.1.2
- 資料庫：MongoDB，透過 PyMongo 連線 / MongoDB Compass的Connect
- 模板：Jinja2
- 樣式：CSS (from CodePen)
- 測試：pytest
- 本機資料庫啟動：Docker Compose

## 主要功能

- 商品列表與商品詳情
- 會員註冊、登入、登出
- 購物車與結帳流程
- MongoDB 種子資料匯入
- 使用者行為紀錄：瀏覽、加入購物車、購買
- 基礎推薦邏輯
- 管理員後台儀表板與推薦統計

## 目前目錄整理

```text
C:\LLM\LLM_PJ
├─ VibeCart_AI/ (主專案根目錄)
├─ MuscleCore分析資料/ (以 Python Flask CSS 改寫舊網站的模擬結構)
│  ├─ MuscleCore_Python_MongoDB_v1.0.zip
│  └─ website/
│     ├─ .env
│     ├─ .env.example
│     ├─ .gitignore
│     ├─ README.md
│     ├─ docker-compose.yml
│     ├─ requirements.txt
│     ├─ run.py
│     ├─ seed_mongodb.py
│     ├─ start_windows.bat
│     ├─ app/
│     │  ├─ __init__.py
│     │  ├─ admin.py
│     │  ├─ auth.py
│     │  ├─ db.py
│     │  ├─ store.py
│     │  ├─ services/
│     │  │  ├─ __init__.py
│     │  │  ├─ analytics.py
│     │  │  └─ recommendation.py
│     │  ├─ static/
│     │  │  ├─ css/main.css
│     │  │  └─ img/hero.png
│     │  └─ templates/
│     │     ├─ base.html
│     │     ├─ admin/
│     │     ├─ auth/
│     │     └─ store/
│     └─ tests/
│        └─ test_services.py
├─ MuscleCore運動用品電商網站/
│  ├─ [第3組]運動用品電商網站_報告(...).pdf
│  ├─ 13頁展示影片.mp4
│  ├─ 14頁展示影片.mp4
│  ├─ 15頁展示影片.mp4
│  └─ 16頁展示影片.mp4
├─ 專題進度/
│  ├─ LLM購物網站專題_2026-09-09_今日總結與下一步規劃_v1.0.md
│  ├─ LLM購物網站專題_四週進度跟蹤表.md
│  ├─ LLM購物網站專題_四週進度跟蹤表_v2.0.md
│  └─ 第六組_專題製作方向和進度_2026-09-14.md
└─ 討論的相關記錄/
   ├─ CONVENTIONS.md
   ├─ CONVENTIONS.pdf
   ├─ mermaid-diagram.png
   ├─ VibeCart_AI_專案整合規格_v1.1.md
   ├─ 分工清單.jpg
   ├─ 資料表欄位清單.jpg
   └─ 錄製內容 2026-09-09.mp4
```

## 檔案用途說明

### `MuscleCore分析資料/website`

這是 以 Python Flask CSS 改寫舊網站的功能結構，也是未來 VibeCart_AI 推送到 GitHub 的參考程式資料夾。

- `run.py`：Flask 啟動入口。
- `app/__init__.py`：建立 Flask app，註冊 auth、store、admin blueprint。
- `app/db.py`：MongoDB 連線、關閉連線、時間工具。
- `app/auth.py`：會員登入、註冊、登出、登入檢查、管理員檢查。
- `app/store.py`：首頁、商品詳情、購物車、結帳流程。
- `app/admin.py`：管理後台首頁與推薦統計。
- `app/services/analytics.py`：營收、訂單、低庫存、熱銷商品等後台洞察。
- `app/services/recommendation.py`：基礎推薦排序邏輯。
- `app/templates/`：Jinja2 頁面模板。
- `app/static/css/main.css`：網站樣式。
- `app/static/img/hero.png`：首頁主視覺圖。
- `seed_mongodb.py`：建立 demo 會員、管理員、商品等初始資料。
- `docker-compose.yml`：啟動 MongoDB 容器。
- `requirements.txt`：Python 套件需求。
- `tests/test_services.py`：服務層測試。
- `.env.example`：環境變數範例，可推送。
- `.env`：本機密鑰與資料庫設定，不可推送。
- `.venv/`、`__pycache__/`：本機環境與快取，不可推送。

### `MuscleCore分析資料/MuscleCore_Python_MongoDB_v1.0.zip`

是模擬功能結構程式的壓縮備份。GitHub repository 通常不放 zip 備份，建議改放在雲端硬碟或 GitHub Release。

### `MuscleCore運動用品電商網站`

包含展示影片與報告 PDF。其中報告 PDF 約 444 MB，影片也屬大型二進位檔；不適合直接推送 GitHub。建議：

- 小型簡報或壓縮版 PDF 可放 `docs/`
- 大影片與超大 PDF 放 Google Drive、OneDrive、YouTube 不公開連結，或 GitHub Release

### `專題進度`

這些是 Markdown 專題進度文件，適合保留在 repository，例如整理到 `docs/progress/`。

### `討論的相關記錄`

包含開發慣例、流程圖、分工圖、資料表欄位圖與會議錄影。建議：

- `CONVENTIONS.md` 可整理到 `docs/CONVENTIONS.md`
- 圖片可放 `docs/assets/`
- 會議錄影 MP4 不建議推 GitHub

## GitHub 推送建議結構

建議之後整理成：

```text
VibeCart_AI/
├─ app/
├─ tests/
├─ docs/
│  ├─ CONVENTIONS.md
│  ├─ progress/
│  └─ assets/
├─ .env.example
├─ .gitignore
├─ docker-compose.yml
├─ README.md
├─ requirements.txt
├─ run.py
├─ seed_mongodb.py
└─ start_windows.bat
```

## 推送前檢查清單

- 不推送 `.env`
- 不推送 `.venv/`
- 不推送 `__pycache__/` 與 `*.pyc`
- 不推送大型 `.mp4`
- 不推送大型 `.zip`
- 超過 100 MB 的 PDF 不要直接推到 GitHub
- README 建議確認在 GitHub 頁面上顯示中文正常
- 使用專案 `.venv` 跑測試：`.venv\Scripts\python.exe -m pytest`

## 目前驗證結果

在 `MuscleCore分析資料/website` 使用專案虛擬環境執行：

```powershell
.venv\Scripts\python.exe -m pytest
```

結果：2 個測試通過。
