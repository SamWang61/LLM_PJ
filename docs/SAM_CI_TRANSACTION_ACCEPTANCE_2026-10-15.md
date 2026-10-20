# SAM：CI、文件版本與真交易驗收｜2026-10-15

範圍：以 GitHub `main` 的 `7d10f7e358152ed90a419f40d26e2bca529c568e` 為文件修復起點；交易測試使用 REN `feature/auth-order` 的 `505399313ca4c09b49d77484e98df806b3b30f58`。這兩條分支尚未整合成單一部署版本，驗收結果依來源版本分列。

## CI 與文件

10/15 主分支及簡報 PR #19 的 File policy 均因 35 項錯誤中止，網站測試因此未執行。修復後本機執行 `python scripts/check_repository.py`：**170 files、161 UTF-8 texts、0 errors**；主分支原網站測試：**55 passed**。遠端 CI 結果以修復 PR 的 GitHub Actions 為準。

| 原因 | 修正 |
|---|---|
| 四份已追蹤 PDF 使用 Git LFS，舊規則一律拒絕 PDF，兩份還超過 100 MiB | 檔案政策只放行 `filter=lfs` 的 PDF；其他大型檔與私有格式仍拒絕 |
| 10/5 匯入與超市文件連結到未納入 Git 的本機生成報告 | 已在交付分支公開的六份匯入報告改為固定 commit 連結；未公開的本機封存項目改為明確檔名與「未納入 Git」標示 |
| 10/12 SAM 文件被複製到不同資料夾，相對連結失效 | 兩份副本的部署及查核證據改為固定 `a0fcad0` commit 連結 |
| 歷史 `before` 文件仍用原目錄相對路徑 | 重新指向同一版本庫內的 XML 與規格來源 |

`docs/TEST_DATA_IMPORT_2026-10-05.md` 與 `docs/SAM_DELIVERY_2026-10-12.md` 是歷史交付紀錄；文內 10/5、10/12 的數字及當時的部署限制只描述原日期，不代表目前 Cloud Run 或 Atlas 狀態。最新狀態須重新查詢，不應用舊文件覆蓋新 revision。

`docs/SAM_DELIVERY_2026-10-12.md` 與 `討論的相關記錄/SAM_DELIVERY_2026-10-12.md` 已同步為相同位元組；SHA-256：`c3341cb370ea363f92f1afc3ec13fcf5c2035fb0cecd8ab31d36aa8dd6a1d04d`。

## 本機真交易驗收

SAM 使用 MongoDB Community Server **8.0.20**，在 `127.0.0.1:27029` 啟動單節點 replica set `rsSAM20261015`。測試夾具僅接受無帳密 localhost URI，為每個案例建立隨機 `ren_acceptance_*` 資料庫並於結束刪除；未使用專案 `.env` 或 Atlas。

在 REN commit `5053993` 的 `MuscleCore分析資料/website` 執行 `python -m pytest tests -q -p no:cacheprovider`，帶入 `REN_TEST_MONGO_URI=mongodb://127.0.0.1:27029/?replicaSet=rsSAM20261015`：**166 passed、0 skipped**。其中先前跳過的三項真交易案例：

1. 結帳寫入後故意拋錯，確認訂單、明細、庫存與購物車一併回滾；成功重試及相同 checkout ID 重送只產生一筆訂單與一筆 PURCHASE 事件。
2. 兩個會員同時結帳最後一件庫存，結果一筆成功、一筆被拒；庫存歸零且不超賣。
3. 管理員撤權與停用會員放在同一交易後 abort；兩項改動都回滾。

[JUnit 測試紀錄](inventory/SAM_REN_TRANSACTION_2026-10-15.xml) 保存同一版本完整測試結果。這項驗收覆蓋本機真 MongoDB 交易與並發；測試夾具沒有安裝全套正式 Atlas validators，也沒有做遠端付款、完整後台或正式 D4 匯入。D4 仍須先完成所有 consumer 的部署隔離與遠端讀回。
