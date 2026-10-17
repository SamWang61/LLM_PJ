# SAM 私有展示帳號與撤權驗收｜2026-10-18

**03:19～03:23（Asia/Taipei）**，SAM 在 REN 24 小時暫代窗口內，完成 N04 的兩角色一次性帳號流程及 N05 的同映像遠端登入／撤權案例。這是私有服務的 HTTP 與 Atlas 讀回；實際展演窗口的帳號、操作畫面與具名簽認仍待安排，沒有留下常駐可登入帳號。

## 版本、角色與範圍

| 項目 | 本輪讀回 |
|---|---|
| 程式來源 | `1d2abf2cfa7465636e49474062e11f6aca571dda`；探針執行前後，正式／私有 serving revision 與映像保持相同。main 文件／工具基線為 `c1ce5cc38727a7077013e0a6452d561ee10ecd67`，本輪沒有更動網站部署來源。 |
| 正式站 | `vibecart-web-00015-nlk`，100% 流量；沒有建立正式業務帳號或交易。 |
| 私有服務 | `vibecart-acceptance-pr21-00005-5j5`；只允許專用 service account invoker，獨立再查無 ID token 的 `/health/live` 為 403。 |
| 共用映像 | `asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web@sha256:1686638380b8cb8dc792423b059918b292e94f095d68c623ea9136da1ff9813b` |
| 資料庫 | 僅 `vibecart_acceptance_pr21`，連線身分實際只有該庫 `readWrite`。沒有新增 Atlas 資料庫使用者。 |
| 應用帳號 | admin、customer 各 1，唯一標記 `sam-accounts-11847cc6c4310272`；測後均停用、撤 session 並刪除。沒有啟用 600 位合成會員。 |

完整無憑證原始結果及獨立清理證據見 [JSON](inventory/sam-account-acceptance-20261018.json)。N03 較完整的 Hosting／回退版本映射另已送 [PR #65](https://github.com/SamWang61/LLM_PJ/pull/65)，本輪沒有重新發布 Hosting 或切換流量。

## 已完成的同映像遠端案例

| 案例 | HTTP／Atlas 結果 |
|---|---|
| 未登入應用會員 | 經私有 IAM 授權但沒有應用 cookie，`/cart`、`/admin/` 均轉登入。這與 Cloud Run 無 ID token 的 403 分開核對。 |
| admin／customer | admin 的 `/admin/`、`/admin/recommendations` 回 200；customer 不能進後台，可讀購物車。沒有呼叫模型或管理寫入。 |
| 兩裝置 | customer 的兩個獨立 cookie jar 可讀購物車，Atlas 為 2 筆 session。這是 HTTP 裝置模擬，非兩台實機。 |
| 同瀏覽器重登入 | 前一 cookie 重播轉登入，新 cookie 與另一裝置仍可用，session 保持 2 筆。 |
| 全裝置撤權 | 操作端清除該 customer 的 2 筆 session，兩個舊 cookie 均轉登入；admin session 仍可讀後台。 |
| 帳號停用 | 兩帳號先停用，再撤銷共 3 筆 session，讀回 0；admin 與兩個 customer cookie 均被拒，兩角色重新輸入憑證亦不能登入。 |
| 重新啟用 | 僅臨時重啟該 customer，舊 cookie 仍無效；新登入成功。finally 再停用、撤除新增的 1 筆 session，刪除兩帳號。 |
| 清理閉環 | runner 讀回帳號／session 殘留 0；**獨立 Atlas 連接器**按 marker／兩個 user ID 再查，兩集合均 0。專用 SA 的本輪臨時 token creator binding 獨立讀回 0。 |

帳號停用、啟用與全 session 撤除由受控驗收操作端直接針對隔離夾具執行；這證明部署中的請求會讀取最新狀態並拒絕舊 cookie，**不是 D5 管理寫入 HTTP 功能已實作或驗收**。

## 重現與撤權計畫

1. 先在乾淨工作樹執行 `node scripts/run_remote_transaction_acceptance_probe.cjs`。預設只讀；必須核對正式／私有同一不可變映像、驗收模式／資料庫、單一私有 invoker 與正確 runtime SA。
2. 需執行時才使用 `--run-accounts-isolated`，並以 `REN_PYTHON` 指向已安裝網站測試依賴的 Python。此旗標允許本輪臨時 IAM 授權及兩個隔離應用帳號；沒有任意服務／資料庫參數。
3. CLI OAuth token、私有 ID token、Mongo URI、一次性密碼及 cookie 僅在程序記憶體與 stdin 傳遞。`users` 暫存密碼雜湊，測後連同帳號刪除；JSON 的 `credentials_persisted=false` 指沒有把明文憑證寫入檔案。不得截取登入欄位、cookie 或密鑰畫面。
4. 正常或失敗都先停用帶本輪 marker 的帳號，再清除其 user ID 的 session，逐項讀回，最後刪除帳號。失敗或讀回不明列為 `cleanup_failed`，不可報通過。
5. 如果程序被強制終止而無法 finally：僅在 `vibecart_acceptance_pr21` 依本輪 `acceptance_run` 和建立時間找出帳號，核對 marker／ID 後停用、清 session、讀回 0，再刪除。不得用空條件、全部會員或正式庫作清理。由清單上的本輪 IAM condition title 精確撤權並再讀回，保留其他人的 binding。
6. 本輪 token creator 授權設 20 分鐘條件且已移除。**移除授權不會使已簽發 ID token 立即失效**；token 不落盤、不分享，程序結束即丟棄，仍依其原到期時間失效。私有服務未新增公開 invoker。
7. 正式展演前再鎖定版本、時段、操作人與終止時間，只建立最少角色帳號；流程驗收不替代實際展演帳號交付、瀏覽器畫面或具名簽收。本輪憑證已丟棄，不能拿本輪帳號直接展演。

## 工具與測試

- [固定範圍 Node 執行器](../scripts/run_remote_transaction_acceptance_probe.cjs)：原交易探針旗標保留，新增明確的帳號探針旗標；預設不寫入。
- [Python 帳號探針](../scripts/remote_account_acceptance_probe.py)：只允許私有服務、指定 URI 帳號／庫及窄權限；角色核對失敗時連 cleanup 也不寫入。
- [帳號安全回歸](../scripts/test_remote_account_acceptance_probe.py)及既有 D4 安全回歸：合計 **15 passed／0 skipped**；Node 兩組安全回歸合計 **5 passed／0 skipped**。
- 既有網站 `tests/test_ren_auth_order.py`：**31 passed／0 skipped**。上述離線測試是回歸，遠端結果另以上表與 JSON 為準。

## 尚未完成與下一步

N04 的一次性兩角色流程與撤權計畫已驗，實際展演窗口帳號仍未交付；N05 的本輪遠端案例已驗，操作畫面及具名簽認仍未補齊。下一可推進的 SAM 技術項為 N06：同映像遠端故障回滾與最後庫存併發；本輪沒有重做結帳或代替 N06。

N02 具名交接、實機、最終素材／PPTX 與 N18 全站簽收仍開放。D5、交付環境真模型與真付款依[現行範圍](SAM_N02_V1_SCOPE_HANDOFF_2026-10-18.md)列下一階段；自由提問維持關閉。D1～D4 沒有重匯，沒有部署、改動正式流量或向他人寄訊息。原 56／88 為全案歷史對照，本輪未重算為縮減後 v1 的完成率。
