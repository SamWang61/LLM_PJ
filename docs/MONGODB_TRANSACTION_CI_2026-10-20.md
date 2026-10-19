# 一次性 MongoDB 交易 CI 啟動診斷

2026-10-20（Asia/Taipei）。本機同步 main 時，發現提交 `1b2fdcd`、`d341829` 的 CI 在一次性 localhost MongoDB 交易步驟回報 `cleanup-failed`／`RuntimeError`。`1b2fdcd` 第二次執行成功；`d341829` 兩次執行失敗。其他離線檢查均成功，原 PR #120 合併提交 `0e8ed567` 的檢查亦已成功。現有證據未能判定容器啟動失敗的根因。

原測試容器使用 Docker `--rm`，程序若提前退出，容器會在 finally 讀取狀態前被刪除，啟動錯誤及 exit code 因此無法留證。測試程式改由 finally 依生成的唯一名稱驗證容器身分後刪除；失敗時先記錄狀態、exit code、OOM 標記及最多 30 行／12,000 字元的容器日誌。診斷讀取失敗不阻止後續清理。報告不含 Atlas 憑證，目標仍為一次性、無帳密的 localhost replica set。

啟動或交易失敗仍回非零；清理失敗仍明列 `cleanup-failed`，沒有以重試、跳過或降低驗收條件改成成功。新增兩項啟動退出回歸，分別驗證清理成功與清理失敗時，原測試均維持失敗且保留診斷；CI 在真交易驗收前執行這兩項回歸。真實交易仍要求零 failure/error/skipped 及 fixture／容器清理。

## English summary

Keep the disposable MongoDB container until explicit cleanup so an early exit does not erase startup evidence. Failed runs record bounded state and logs before removal. Startup, transaction and cleanup failures still fail validation. Two regression cases cover startup exit with successful and failed cleanup. Atlas and deployed services are not accessed or changed.
