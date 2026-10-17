# SAM 新推送驗證｜2026-10-18 02:05（Asia/Taipei）

主責：[SAM](mailto:cashsam@gmail.com)。本輪依 22 項工作順序核對新推送，保留原 `C:\LLM\LLM_PJ` 的未提交修改；在獨立乾淨工作樹驗證及交付。

## 來源與驗證結果

| 範圍 | 結果與證據 |
|---|---|
| GitHub 版本 | 上次 `24920d538cfe2cd4f9674bacb340cdc6b933ef56`；本次核對 `85cb40a78949003a56255ae48369968c1c501f36`，已包含 PR #52～#58。[main CI #39056238813](https://github.com/SamWang61/LLM_PJ/actions/runs/39056238813) success。各 ref 完整 SHA、差異及逐檔清冊在[驗證報告](inventory/sam-push-audit-20261018.json)。 |
| 新交付內容 | 44 個新增／變更後的現存檔案，工作樹／Git blob／不可變 GitHub URL 的位元組一致，SHA-256 差異 0；rename 的舊路徑由 Git 歷史保留。本輪沒有新增 LFS 物件；既有 LFS fsck 通過。 |
| 部署來源 | 47 個部署白名單 Git blob 全部與實際映像來源 `1d2abf2cfa7465636e49474062e11f6aca571dda` 相同；相較上一映像來源 `80513a9`，只改商品標題的 `main.css`。較新的文件提交不當作重新部署。 |
| 網站完整回歸 | 在 `7affe59b23582940a2b83085c023c4b3b8b7d1e9` 執行 **186 passed／0 skipped（37.18 秒）**；到本次 main 的程式與測試檔案差異 0。[原始 JUnit](inventory/sam-push-audit-regression-20261018.xml)及[執行與清理紀錄](inventory/sam-push-audit-regression-20261018.json)可核對。 |
| 真交易測試條件 | 使用隨機連接埠、無憑證的 localhost `mongo:8` replica set，設定 `REN_TEST_MONGO_URI`；涵蓋冪等重送、rollback、最後庫存併發及撤權 rollback。測後僅剩三個系統庫，一次性容器已移除；未使用 `.env` 或 Atlas。 |
| 遠端部署讀回 | 01:58 UTC+8 的[獨立唯讀紀錄](inventory/sam-push-audit-cloud-20261018.json)確認正式 `vibecart-web-00015-nlk` **100%**、私有 `vibecart-acceptance-pr21-00005-5j5` Ready，兩者 digest 同為 `sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b`。Run／Hosting／標籤 URL 的 12 項公開 GET 均 200；這沒有驗證登入成功或交易。 |
| 新映像 D4 隔離 | [PR #58 的部署紀錄](SAM_RELEASE_2026-10-18.md)已保存同映像管理計數 13→14→14、1,001 synthetic 排除、測後清理及撤權證據；本輪比對其 revision／digest 與獨立控制平面讀回一致，未重跑探針或匯入 D4。 |

## 修正 Windows 來源位元組差異

首次雜湊比對發現 Windows 工作樹的 CSS 是 CRLF，而 Git blob／GitHub 是 LF；差異僅為換行。已將本乾淨工作樹的 CSS 對齊 Git blob，並在 `.gitattributes` 明定 `*.css text eol=lf`，避免後續 Windows checkout 再改變建置來源雜湊。44 檔位元組比對於修正後通過；原工作目錄未被覆寫。

## 簡報檢查與後續順序

既有 12 頁進度 PPTX 的 SHA-256 與[交付說明](../簡報文件/交付/README.md)相同；封裝與幾何檢查 0 findings／0 warnings，已使用 Artifact Tool 渲染並逐頁檢視，未見非預期遮擋或截字。這不是 PowerPoint 原生操作驗收。第 5 頁圖片與第 10 頁修訂仍是製作基線的歷史快照；PPTX 沒有人名 `mailto:` 關聯，下一版需補齊聯絡連結與最新素材後再作最終稿。

依順序，#01 最終功能凍結／簽收尚缺；#02～#03 有本機與 CI 證據，#06 的部署來源及公開 RWD 證據已補，但手機實機與具名確認仍待驗。下一項可執行的 SAM／REN 代班驗收為 #07～#09：以既有私有隔離環境對**目前映像**重做角色、雙裝置、demo checkout 與寫後讀回，測後撤權清理。較早映像的成功結果不轉列為新映像通過。

真 BGE／Claude、自由提問、D5／稽核服務、Atlas Network Access 的替代來源、私有加密備份復原、全套素材與排練／具名簽收仍待各自證據。D1～D3 不重匯；已完成的 D4 批次不重新匯入。

English: New pushes were checked against immutable GitHub bytes, the deployed source allowlist, a credential-free local replica-set regression, and read-only Cloud Run state. The CSS checkout line-ending mismatch is fixed. Public responses and local tests do not establish current-image authenticated transactions, models, physical-device acceptance, or final signoff.
