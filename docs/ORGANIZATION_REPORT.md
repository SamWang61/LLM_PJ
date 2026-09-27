# 整理與驗證紀錄 / Organization and validation report

日期：2026-09-27，Asia/Taipei。Date: September 27, 2026.

## 已完成 / Completed

- 將原始碼、Schema、歷史規格、進度與媒體納入可稽核清冊，保留原路徑與檔案。Inventoried code, schemas, specifications, progress notes and media without deleting originals.
- 建立根目錄 README、文件中心、逐份中英文索引與子目錄 README，統一閱讀入口。Added unified documentation navigation and English summaries.
- 補齊 CONTRIBUTING、SECURITY、CODE_OF_CONDUCT、CHANGELOG、Issue／PR 範本、格式設定與 CI。Added collaboration, security and validation documents.
- 原始中文文件保留；英文以首頁、管理文件與逐份摘要為主，未聲稱完成全部歷史文件逐句翻譯。English coverage is provided through guides and document summaries, not a full translation of every historical source.
- 三組完全相同的規格快照屬刻意保留的歷史證據，未刪除。Three duplicate source-snapshot pairs were retained intentionally.

## 本次驗證 / Validation performed

- `python scripts/check_repository.py`：檔案政策、UTF-8、Python 語法與 Markdown 本機連結檢查通過。Repository checks passed.
- 網站 `.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider`：**2 passed**。Two offline demo tests passed.
- 本機機密值比對沒有發現 Atlas 真實密碼被納入提交；命中項目為舊網站的 localhost URI／示範設定，Atlas 文件使用密碼占位符。Credential review found demo defaults and placeholders, not actual Atlas passwords, in publication candidates.
- 未執行 Atlas 遷移、線上寫入或歷史整合測試；文件中的 66 passed 保持原日期。No live Atlas migration or integration tests were run.
- PDF、圖片與影片的讀取範圍是檔案雜湊與清冊，並非全面內容審閱。Binary artifacts were hashed and cataloged, not exhaustively reviewed.

## 尚待完成 / Pending

每日備份已設定喚醒時間，但仍需確認機密保存方案與可靠共用切換／雲端驗證方式；尚無一次成功全量備份可供宣稱。固定 Drive 專案與共用連結未更動。詳見 [備份規範](BACKUP.md)。

Daily backup scheduling is configured, but secret handling and a reliable sharing/verification mechanism remain prerequisites. No successful full backup is claimed; the fixed Drive project link remains unchanged.
