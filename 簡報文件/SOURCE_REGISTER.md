# 來源與交付盤點

盤點：2026-10-15；遠端 main 基線 7d10f7e。此次是文件／Git 檔案存在性核對，未重跑整站測試、Atlas 或部署驗收。

| 同學要求 | 來源與版本 | 目前可用素材 | 待補／負責人 |
|---|---|---|---|
| README | [根 README](../README.md)、[網站 README](../MuscleCore分析資料/website/README.md) | 專案定位、入口、legacy setup | SAM 整理最終版本；舊 README 的完成宣稱须以同版驗收補強 |
| 架構圖 | [本目錄架構](ARCHITECTURE.md)、[串接說明](../docs/FLASK_SKU_AI_INTEGRATION.md) | 模組及雲端拓樸草稿 | JEFF／HEN 確認接口，SAM 定稿 |
| setup | 根／網站 README、[網站環境範例](../MuscleCore分析資料/website/.env.example) | Python 3.11、venv、依賴、DB、run.py | SAM 在乾淨環境驗 final SHA；不得對既有 Atlas 重跑 seed |
| screenshots | [操作截圖清單](screenshots/README.md) | S01 本輪實拍；其餘按場景收集 | HEN購物、JEFF後台AI、SAM整合與證據 |
| 測試 | 網站 tests、[CI](../.github/workflows/validate.yml) | main 的離線驗證工作流 | SAM 保存最終 run／SHA／數字與測試範圍 |
| Dockerfile | [整合分支 deploy](https://github.com/SamWang61/LLM_PJ/tree/a0fcad0/deploy) | 分支有部署容器資料；main 無 Dockerfile | SAM 對最終交付版本做 build／boot smoke |
| docker-compose | [compose](../MuscleCore分析資料/website/docker-compose.yml) | mongo:8、持久 volume、healthcheck；僅 DB | SAM 明確列 DB 容器與本機 Flask 分開啟動 |
| CI | .github/workflows/validate.yml | 檔案政策＋Python 3.11 網站離線 pytest | 最新 Actions 結果待附，不推定綠燈 |
| .env.example | 網站及 [MongoDB 範例](../VibeCart_AI/MongoDB/.env.example) | 範例存在；秘密另外設定 | SAM 核對 final 分支的完整配置，不收集真 .env |
| 部署文件 | [10/12 整合交付](https://github.com/SamWang61/LLM_PJ/blob/a0fcad0/docs/SAM_DELIVERY_2026-10-12.md)、deploy README | 歷史 Hosting／Run／HTTP／容器證據 | SAM 重新核對最終 revision 和完整功能開放範圍 |

## 本輪畫面觀察

- Chrome 商城首頁於本輪載入：336 項商品、14 頁、分類、搜尋、登入使用者推薦理由及教學測試聲明。
- 既有後台頁面可讀到日期／示範訂單篩選、KPI、熱銷和低庫存；頁面本身標示資料讀取時間 10/14 21:53。此觀察不是重新載入後台或重新驗收。
- 該後台明確顯示 BGE 未安裝、退回規則，雲端 LLM 未啟用；商品／訂單／會員管理尚未開放。不可寫成全 AI 與後台 CRUD 已完成。

## 安裝展示稿

按根 README 在獨立本機展示庫建立 venv、安裝 requirements、複製環境範例，啟動 MongoDB compose，再啟动 run.py。初始化 seed 僅適用於新隔離展示庫；不得把它列為現有 Atlas 的例行啟動步驟。v4／AI 配置另依串接說明；最終簡報需附可重現的實測指令和版本。

歷史引用均保留日期。10/12 的 163 passed／27 集合／86 索引是交付文件記錄，未在本輪重驗，也不代替購物、交易、模型或權限驗收。
