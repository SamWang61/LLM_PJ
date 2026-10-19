# SAM 最新main正式部署與獨立驗收

更新：2026/10/19 06:56（Asia/Taipei）；主責[SAM](mailto:cashsam@gmail.com)。依使用者正式部署及驗收授權執行。偵測到另一個已獲授權的商品評價發布流程正在部署同一版本，本輪沿用該發布結果，另做獨立核對，沒有第二次切換流量。

## 正式版本與來源

| 項目 | 讀回結果 |
|---|---|
| 正式網站 | [Firebase正式入口](https://vibecart-llmai.web.app/) |
| Cloud Run | `vibecart-web-reviews-b038aaca`，100%正式流量，Ready成功；06:47:55切換 |
| 執行來源 | `b038aaca2d2553a39d8fd958100f277c64a75486`，56個Git blob；後續文件main 0ab1fa1210b18e5be76751fd3e31abcccc06ff3b的執行來源相同 |
| 映像 | `sha256:8755ccb82902cf59430d5b2b76505c3fb6e4ed265d0ef98ba42821769edbcbdd` |
| Hosting | release `1792363722745000`，06:48:42發布；rewrite `**`→`vibecart-web`／`asia-east1` |
| 回退版本（06:56紀錄） | 當時`vibecart-web-role-auth-576b4748`保留0%；N13固定出口啟用後不可直接切回，見下方更正 |

**2026/10/19 08:40回退更正**：Atlas萬用IP規則已移除。現行`vibecart-web-nat-1019`接專用VPC／固定NAT出口並承接100%流量；舊`vibecart-web-role-auth-576b4748`沒有`vpcAccess`，不能僅切流量回去。評價／6＋4的安全回復步驟與舊碼重建條件，見[正式部署文件「回復與後續」](SAM_REVIEWS_6PLUS4_PRODUCTION_2026-10-19.md#回復與後續)。

獨立下載GCS generation `1792361421014751`的完整2,157,908 bytes來源包，SHA-256為`bd85ba17567bfdcff4b7d633551841df4b02a6dafee0a701fac46d969cf7fb4e`。56檔逐一對照main Git blob，差異0；Cloud Build `4e12f368-f6fd-41a7-9404-86b276e3e66b`的SUCCESS、來源generation與映像digest讀回相符。本輪重用已驗映像，沒有冒稱重新建置。

## 線上與同版驗收

| 範圍 | 實際結果 |
|---|---|
| 候選修訂六角色 | 切換前0%候選，三人各customer/admin共六組；登入302、管理者後台200／會員拒絕302、GET及POST改密403、單裝置登出及Atlas自有session清理0 |
| 正式Firebase六角色 | 上線後以六個新client獨立重驗全部相同契約；server-issued token與Atlas user_id相符，正常登出後自己的session為0；未變更任何密碼 |
| Atlas結構 | 28集合／89索引／7 migration／12項關聯通過；正常登入的last_login及自有session變動另列 |
| 評價正式資料 | 受控缺貨、不可推薦商品的模擬訂單評價4＋4＋5，獨立Atlas讀回sum13／count3／raw4.333…／display4.4，正式HTML同樣顯示4.4星／3筆 |
| 即時畫面 | 已核對另一授權發布流程的Chrome原頁紀錄及兩張結果圖：4.0／2筆→4.4／3筆、原表單仍保留且停用、成功訊息；其JSON記錄withoutReload=true。此處另做的是獨立HTTP／Atlas讀回，未冒稱本輪另開瀏覽器送出 |
| 6＋4足量與排序 | 新一次同digest私有遠端4組探針全passed；6個個人＋4個破圈、10項去重、小類上限3／2、破圈星等5／4.9／4.8／4.7、缺貨／預設排除、1001 synthetic不影響結果及其他會員 |
| 正式候選不足 | 正式ACTUAL且≥4.5的商品為0，匿名冷啟動顯示0／0符合規則；不灌假星數或以預設值湊滿。這與隔離庫足量6／4證據分開 |
| 發布後觀測 | 06:47:55～06:55:58讀回313筆請求，5xx為0；403角色／改密拒絕、清理後商品404為驗收預期。這是有限觀測，未擴稱SLO |

正式產品評價JS SHA-256 `82ef1fb2f5d8281375dfba4496dff4adc6d3c0371a3ac24626656be431219cc0`，與main完整bytes相同。原頁AJAX更新、同來源分頁通知與伺服器跨裝置推播是不同範圍；本輪未宣稱後者。

## 清理、重試與邊界

1. 正式受控會員、商品、SKU、3筆模擬訂單／明細、3筆評價、4筆事件及session已按註冊ID清除。此處又獨立查八集合剩餘全0、商品URL404；既有商品／庫存／訂單／明細／評價／事件及會員身分整體hash等於測前，登入時間欄位明確排除。D4 synthetic仍1,240筆，未重匯。
2. 六角色首次公開測試的核心測項全通過，但額外觀測的1個既有session在並行測試期間消失，原整體結果保留failed；無法僅憑總數歸因撤權。修正驗收工具，公開站只判定本次server-issued token；其他裝置保留由同版隔離雙裝置測試證明。第二次六角色全部通過，當時既有session為0，不把首次嘗試改寫成通過。
3. 初次臨時評價讀回斷言未保留細項；改用固定UTF-8腳本逐項核對後，Atlas13／3／4.4與HTML4.4／3通過；未修改正式程式來迎合驗收。發布流程另有一次原頁取證中斷，只重做本次fixture的第三筆評價，其重試與最終證據保留在發布原始紀錄。
4. BGE、Claude摘要、自由提問維持false；正式上線為規則6＋4。本輪未寄信、重設帳密、執行migration或建立第二套正式部署。

## 專案目錄與V5

原`C:\LLM\LLM_PJ`髒工作樹保留。56個執行檔中55檔與部署來源逐byte一致；`app/templates/base.html`有原先額外的頁尾inline style，已記錄原hash並保留，完整標準部署版本可由乾淨工作樹取得。文件入口採增量同步及備份，不把本機變體當作部署來源。

CURRENT_CONTEXT、文件索引、部署入口、執行紀錄及V5均補本次證據。V5保持**2/14**；N04／N05具名接收、N12完整實機矩陣、N13固定出口、N14異機金鑰／每日流程、N18最終凍結簽認等仍各自待結案。技術驗收不能代填本人簽收。

[完整機器紀錄](inventory/SAM_MAIN_PRODUCTION_ACCEPTANCE_2026-10-19.json)包含56檔相對路徑／SHA-256、雲端版本、六角色、同版探針、畫面摘要與清理證據；GitHub提交／合併／CI與來源／遠端／原目錄對帳另由交付收據核對。
