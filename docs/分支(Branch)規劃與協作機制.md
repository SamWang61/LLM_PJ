# 現行分支決策 / Current branch decision

2026-10-02：SAM 直接負責 `feature/ai-dashboard` 與 v4 Atlas 連線。後台分支基於 `feature/flask-sku-ai-integration`；PR 先指向此整合分支，再由整合分支合併 main。下方歷史四人分工與一律從 main 建分支的指引，在本功能由此決策取代。詳見 [SAM 交接文件](AI_DASHBOARD.md)。

SAM owns the stacked dashboard feature and private test connection. The original plan below is retained for history.

---

建立 GitHub 儲存庫後，從分支規劃到建立協作機制的標準執行流程與步驟如下：

---

### **一、 準備基礎環境與專案主幹（Main Branch Setup）**

> 在大家各自拉出分支前，請確認 main 分支具備完整的初始骨架與規範檔案：

> 1. **檢查環境設定與忽略檔**：  
   * 確認根目錄已有 .gitignore（確保 .venv/、\_\_pycache\_\_/、.env 等私密與暫存檔不會被版控）。  
   * 確認已有 .env.example（提供組員複製並設定本地環境變數）。  
   * 確認已有最新版的 requirements.txt。  
> 2. **設定 main 分支保護規則（Branch Protection Rules）**：  
   * 進入 GitHub 儲存庫 Settings ➔ Branches ➔ 新增 main 分支保護規則。  
   * 勾選 **Require a pull request before merging**（強制必須透過 PR 合併，禁止直推 main）。  
   * 勾選 **Require approvals**（建議設定至少 1 人審查通過才能 Merge）。

### ---

**二、 依據四人分工建立 Feature 分支**

依據專案命名規範（{類型}/{功能}，例如 feature/...），建議由各負責人在本地拉出對應分支並推送到遠端：

| 負責領域 | 建議分支名稱 | 核心權責與目錄範圍 |
| :---- | :---- | :---- |
| **1\. 前台與 RWD 介面** | feature/store-ui | 前台頁面切板、樣式優化 (templates/store/, static/css/) |
| **2\. 會員與購物流程** | feature/auth-order | 會員註冊/登入、購物車與結帳邏輯 (auth.py, store.py) |
| **3\. 資料庫與測試** | feature/mongodb | MongoDB 連線、初始化腳本與測試 (db.py, seed\_mongodb.py, tests/) |
| **4\. AI 與管理後台** | feature/ai-dashboard | 推薦引擎、營運分析與後台介面 (services/, admin.py, templates/admin/) |

### ---

**三、 各組員本地分支切換與開發指令**

組員在本地開啟終端機（Terminal / PowerShell），執行以下指令開始開發：  
`# 1. 切換至最新 main 分支並拉取最新程式碼`  
`git checkout main`  
`git pull origin main`

`# 2. 建立並切換至個人負責的分支 (以 feature/store-ui 為例)`  
`git checkout -b feature/store-ui`

`# 3. 將新建立的分支推送到 GitHub 遠端`  
`git push -u origin feature/store-ui`

### ---

**四、 建立 GitHub Issues 與看板管理（Task Management）**

> 1. **建立功能 Issues**：將四週跟蹤表中的 MVP 功能項目拆解為 GitHub Issue（例如：\#1 實作會員登入與權限控管）。  
> 2. **指派負責人與標籤**：為每個 Issue 指派 Assignee 與 Assignee 負責對應的卡片。  
> 3. **開啟 GitHub Projects**：選擇 Board (Kanban) 視圖，建立 Todo、In Progress、In Review、Done 四個欄位，以便追蹤進度。

### ---

**五、 Pull Request (PR) 與 Code Review 協作流程**

> 當組員完成階段性功能後，遵循以下流轉規範：

> 1. **提交與推送**：小步快跑提交程式碼 (git commit \-m "feat: 新增購物車 API") 並推送至個人分支 (git push)。  
> 2. **發起 Pull Request**：  
   * 在 GitHub 上開啟 PR，方向設定為 base: main ◄ compare: feature/xxx。  
   * 內文中註明關聯的 Issue（例如：Closes \#1），並填寫變更內容摘要與測試方法。  
> 3. **對齊與合併**：  
   * 同組成員進行 Code Review 檢查程式碼。  
   * 確認能正常啟動並通過測試後，審查者按下 Approve。  
   * 採用 Squash and merge 或 Merge pull request 將功能合併回 main 分支。

資料來源：

> * [CONVENTIONS.pdf](https://drive.google.com/file/d/1xfpM0gZAOw9IxpRaNdgpHFr2-2l921pN/view?usp=drive_web)  
> * [README.md](https://drive.google.com/file/d/1HfASb_tS5n-8x1P44J3jGWYkGYY5X1k1/view?usp=drive_web)

---

## LLM_PJ 實際採用方式（2026-09-30）

以上為原始規劃，以下補充本倉庫的實際目錄與分支使用方式。原文中的相對路徑應依本節對照，不需搬動程式碼。

### 分支與目錄對照

四個功能分支皆由包含本文件的 main 起點建立；每個分支保有完整倉庫，下表是主要協作範圍，不是目錄存取限制。負責人的 GitHub 帳號尚未指定。

| 分支 | 主要範圍（相對倉庫根目錄） |
|---|---|
| `main` | 穩定整合版本，功能修改透過 PR 審查與合併 |
| `feature/store-ui` | `MuscleCore分析資料/website/app/templates/store/`、`MuscleCore分析資料/website/app/static/css/` |
| `feature/auth-order` | `MuscleCore分析資料/website/app/auth.py`、`MuscleCore分析資料/website/app/store.py`；整合新版購物車與訂單時與資料庫負責人協調 |
| `feature/mongodb` | `VibeCart_AI/MongoDB/`、`VibeCart_AI/services/`；展示網站的 `app/db.py`、`seed_mongodb.py`、`tests/` 均位於 `MuscleCore分析資料/website/` 下 |
| `feature/ai-dashboard` | `MuscleCore分析資料/website/app/services/`、`MuscleCore分析資料/website/app/admin.py`、`MuscleCore分析資料/website/app/templates/admin/` |

新版資料層與舊 Flask 展示網站仍是不同模組；Schema 變更遵循版本遷移，不改寫既有遷移歷史。跨領域修改先協調共用檔案，PR 以 main 為目標。

### 使用已存在的遠端分支

原文的 `git checkout -b` 適用於尚未建立分支時。遠端分支建立後，組員首次使用以下方式（以 store-ui 為例）：

```powershell
git fetch origin
git switch --track origin/feature/store-ui
```

如果本地已有此分支：

```powershell
git switch feature/store-ui
git pull --ff-only
```

開始新工作前先確認工作目錄已提交或妥善保存，再整合 main：

```powershell
git fetch origin
git merge origin/main
```

完成後推送功能分支，建立指向 main 的 PR，填寫變更與驗證結果，由其他組員審查。合併前執行 [貢獻指南](../CONTRIBUTING.md) 中的離線檢查。若合併後刪除功能分支，下次從最新 main 重新建立同名分支。

### 基礎檔案與後續設定

根目錄已有 `.gitignore`；展示網站的 `.env.example` 與 `requirements.txt` 位於 `MuscleCore分析資料/website/`，依現有多模組架構保留原位置。

本次範圍為分支建立、文件歸位與導覽。原文建議的 main 保護規則（PR + 至少一人核准）、Issues 指派與 Projects 看板，仍屬後續設定，本文件不代表 GitHub 已啟用這些機制。

English summary: Four feature branches share a common main baseline and keep the complete repository. The table maps ownership to actual module paths. Track existing remote branches instead of recreating them. Branch protection, issue assignments and Projects configuration are follow-up work; this document does not assert they are enabled.
