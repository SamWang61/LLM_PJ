# 安全政策 / Security policy

本專題仍在開發中，不宣稱可直接投入正式商用。This project is under development and is not certified for production use.

## 通報 / Reporting

請透過既有私下聯絡管道聯繫倉庫擁有者 SamWang61。不要在公開 Issue、PR 或日誌張貼密碼、權杖、連線字串或使用者資料。若 GitHub 的私人漏洞通報功能可用，可使用該入口；本文件不代表已啟用。

Contact SamWang61 through an existing private channel. Do not post secrets or personal data publicly. Use GitHub private vulnerability reporting if available; this document does not claim it is enabled.

## 管理原則 / Handling

- 憑證只存本機受保護環境或 Secret Manager；`.env.example` 僅放占位值。Store secrets in protected local configuration or a secret manager.
- 發現外洩時先撤銷／輪替憑證，再處理 Git 歷史與存取紀錄。Rotate exposed credentials before cleaning history.
- 公開 GitHub 與共用 Drive 都不能保存明文機密。Neither public GitHub nor shared Drive is a secret store.
- 備份中斷不得提前恢復共用；先驗證內容，再恢復原權限。Do not restore sharing before backup verification succeeds.
