# 目錄與文件管理 / Repository and document management

採單一倉庫集中管理，保留功能目錄，透過文件中心整併閱讀入口。Use a single repository with stable component paths and consolidated documentation navigation.

| 路徑 / Path | 職責 / Responsibility | 管理方式 / Policy |
|---|---|---|
| `VibeCart_AI/services/` | SKU 購物車與評價 / SKU cart and reviews | 現行資料服務 / Current services |
| `VibeCart_AI/MongoDB/` | Schema、遷移、稽核與證據 / Schemas, migrations and evidence | 15–17 號文件為 v4 導覽 / v4 guides in 15–17 |
| `MuscleCore分析資料/website/` | 舊 Flask MVP / Legacy Flask demo | 保留啟動與 import 路徑 / Stable runtime paths |
| `專題進度/` | 有日期的進度與計畫 / Dated plans | 歷史資料不改寫為完成狀態 / Preserve historical status |
| `討論的相關記錄/` | 原始規格與圖像 / Specifications and diagrams | 由索引標明版本 / Explicit versions |
| `MuscleCore運動用品電商網站/` | 舊報告與影片 / Legacy reports and videos | 本機與 Drive 附件，Git 不追蹤 / External artifacts |
| `docs/` | 文件中心、清冊與作業規範 / Documentation hub | 新管理文件集中此處 / New administration docs |
| `scripts/` | 清冊與發佈檢查 / Inventory and publication checks | 可重複執行 / Reproducible utilities |
| `.github/` | Issue、PR、CI / Collaboration automation | 離線測試 / Offline validation |

## 版本與重複檔 / Versions and duplicates

MongoDB 02、07、13 號來源快照分別與討論目錄的整合、購物車、完整 Schema 規格一致；這些副本是稽核證據，刻意保留。其 SHA-256 分組見清冊摘要。其他近似名稱（如壓縮／未壓縮 PDF）不能僅憑名稱判定為重複。

Source snapshots 02, 07 and 13 intentionally duplicate the corresponding specifications. Hash groups are recorded in the inventory. Similar PDF names alone do not establish duplication.

## Git 與附件 / Git and artifacts

Git 追蹤原始碼、UTF-8 Markdown、設定範例、小型圖片及歷史驗證報告。現有政策排除所有 PDF、影片、ZIP、虛擬環境、快取與機密；排除不是刪除，本機原檔保留。Drive 備份必須另行處理機密與同步完成驗證。

Git tracks code, Markdown, configuration examples, small images and historical test reports. PDFs, video, ZIP archives, environments, caches and secrets remain outside Git without deleting local originals.

GitHub 建議提供 README 與貢獻規範；一般 Git 檔案超過 100 MiB 會被阻擋。授權尚待權利人決定，不能擅自套用 MIT 等授權。

References: [GitHub repository best practices](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories), [large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## 清冊範圍 / Inventory scope

`python scripts/inventory.py` 會讀取專案文字、對非機密附件計算 SHA-256；機密只記名稱與大小。依賴環境與快取列為略過目錄；PDF、影片與圖片僅做二進位完整性盤點，不代表逐頁視覺審閱或逐秒轉錄。清冊排除自身，避免循環雜湊。

The inventory reads text and hashes non-secret artifacts. It excludes its own output, dependencies and caches. Binary hashing is not page-by-page review or media transcription.
