# 貢獻指南 / Contributing

先閱讀 [README](README.md) 與 [文件管理政策](docs/REPOSITORY_GUIDE.md)。Read the project overview and repository policy before changing code.

1. 從 `main` 建立 `feature/名稱`、`fix/名稱` 或 `docs/名稱` 分支。Create a focused branch from main.
2. 保留既有模組路徑；Schema 修改以新版本遷移處理，勿改動已執行 migration 的 checksum。Preserve module paths and immutable migration history.
3. 提交訊息使用 `feat:`、`fix:`、`docs:`、`test:`、`db:`，中文說明為主，可補英文。Use descriptive conventional commit prefixes.
4. 文件用 UTF-8，先中文、後英文摘要；API 名稱、命令和檔案路徑保持原樣。Chinese is authoritative; keep identifiers unchanged.
5. 執行 `python scripts/check_repository.py` 與網站的離線 pytest。Run repository checks and offline demo tests.
6. PR 描述問題、最終行為、驗證結果與限制，再由組員審查。Explain the problem, behavior, validation and limits in the PR.

不要提交 `.env`、憑證、真實客戶資料、套件快取或大型媒體。Atlas 整合測試會寫入測試資料，不是文件更新的例行檢查；需使用明確授權的測試環境。

Never commit credentials, real customer data, dependency caches, or large media. Atlas integration tests write data and require an authorized test environment.

新檔案加入後，以 `python scripts/inventory.py` 更新清冊；此清冊刻意略過依賴環境、快取與機密內容。Regenerate the inventory after file changes; dependencies, caches and secret contents are outside its inspection scope.

四人功能分工與既有遠端分支使用方式見 [分支規劃與協作機制](docs/%E5%88%86%E6%94%AF%28Branch%29%E8%A6%8F%E5%8A%83%E8%88%87%E5%8D%94%E4%BD%9C%E6%A9%9F%E5%88%B6.md)。See the branch guide for ownership and remote branch setup.
