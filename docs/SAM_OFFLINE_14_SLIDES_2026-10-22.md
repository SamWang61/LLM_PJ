# SAM 14頁簡報備援修正 / Presentation fallback alignment

開始：約2026/10/22 00:36（Asia/Taipei）；實際執行者Codex，SAM代理整合／N16～N18技術補件。本輪只處理簡報閱讀與離線備援，不改網站程式、Atlas或部署，也不預填組員本人重做。

## 問題與結果

PR #165已將使用者指定PPTX更新成14頁；舊PDF及離線閱讀圖仍13頁，工具仍鎖定舊PPTX雜湊，因而拒絕目前主檔。此次新增[14頁閱讀與備援](../簡報文件/超市AI版_2026-10-22_閱讀與備援/README.md)，以PowerPoint 16.0原生`SaveAs(ppSaveAsPDF)`從唯讀原稿匯出PDF，逐頁渲染為14張1600×900 PNG。原稿PPTX、舊PDF、舊預覽及歷史講稿均保留。

| 物件 | 本輪核對 |
| --- | --- |
| 使用者指定PPTX | 14頁、3,262,322 bytes；SHA-256 `4aa9b13286fe98574d3dd648889545ad196d92cea9aebb9a143c794ad392d193`，匯出前後未變 |
| 新PDF | 14頁、933,269 bytes；SHA-256 `79e4883a70fc38df2cd94cdb0b74685228b1763481753a55584945c4779186f5` |
| 逐頁PNG | 14張，共3,461,194 bytes；逐頁清冊見[pages.json](../簡報文件/超市AI版_2026-10-22_閱讀與備援/投影片/pages.json) |
| 原稿觀察 | 第12、13頁內容相同，頁尾均標12；忠實保留，以實際順序1～14導覽，未擅改使用者主檔 |

## 工具與安全界線

`scripts/v5_offline_bundle.py`預設使用明確`v5-14-20261022`契約，同時保留`--profile legacy-13`供相符歷史commit重建。新契約固定PPTX／PDF SHA-256、14頁及PNG清冊；只讀指定Git提交白名單內22份內容檔，另產生manifest。未下載的Git LFS實體內容仍拒絕封裝，不把pointer當PDF。

沿用既有路徑／檔案數／大小限制、逐檔雜湊、符號連結與Windows名稱防護、先驗證再建新目錄及磁碟寫入後讀回。包內HTML不需外部CDN，原稿閱讀與更新卡分開，未收錄文件的引用固定到Git commit並明示需連線。ZIP只留本機交付，不進GitHub，不包含帳號、環境檔或金鑰。清冊不是數位簽章。

## 驗證與操作紀錄

- 約00:37：本機來源hash guard發現腳本預期值抄寫多1字元，停止；修正腳本值，實際PPTX未更動。
- 約00:38：PowerShell COM呼叫`ExportAsFixedFormat`發生參數轉換錯誤，無輸出；改用PowerPoint原生`SaveAs`之PDF格式，匯出成功。只開關本輪唯讀簡報及新建立PowerPoint實例，無既有使用者PowerPoint工作階段。
- 約00:39～00:42：PDF頁數14、原稿hash不變；完成14張逐頁渲染及全頁目視檢查。文字、表格、圖片完整可讀，保留原稿歷史數字及第12／13頁重複內容。
- 離線備援契約測試22 passed，驗證14頁完整白名單、同來源確定性建包／復原，並拒絕PPTX、PDF、PNG或頁序清冊被改動；既有路徑穿越／竄改／超限等防護測試持續使用。

## 固定提交建包與復原結果

2026/10/22 **00:45:58開始、00:46:52驗證完成**（Asia/Taipei），固定來源`872b1b7b91995f835d4d1a442d6eb51adf319602`。兩次ZIP皆7,310,018 bytes，SHA-256皆`6a8ca650c8ed78f35e0908d98ce4bd3785cebf6dce8d66e3902d51bc6ef00719`；新目錄復原22份內容檔及manifest，逐檔磁碟讀回相符。最終契約測試22 passed，HTML相對連結全部存在，無JavaScript或外部網路素材。第一次本機HTTP檢查的多餘favicon 404已由HTML內聯空圖示宣告消除，最終本機請求全部200。

Codex內嵌瀏覽器透過**本機loopback HTTP**確認索引、14頁導覽、14張1600×900圖片全部完成載入及第14頁跳轉；[原圖](inventory/sam_offline_20261022/offline-14-browser.png)與[去敏機器紀錄](inventory/SAM_OFFLINE_14_SLIDES_2026-10-22.json)可核對。這是同機瀏覽器技術檢查，未斷開整台裝置網路、未使用第二台或投影。瀏覽器政策拒絕`file:`直接開檔，只允許HTTP/HTTPS；該步驟未通過、未換瀏覽器或繞過限制，故不稱已驗直接開檔。

PDF的Git LFS物件已從遠端重新下載，933,269 bytes及SHA-256與本機相符。交付PR為[#170](https://github.com/SamWang61/LLM_PJ/pull/170)，最終HEAD的CI與合併結果以GitHub實際讀回為準；ZIP固定來源為上列提交，後續新增的驗證文件與操作原圖不冒稱已收入同一ZIP。

每日固定Drive備份仍受可恢復ACL能力所限，本輪未複製或改共用。完整USB同機復原已接受的子項不重開；本人獨立重做、真手機、異機及投影若未操作，仍不寫成實體完成。代理管理判定依[現行規則](../專題進度/SAM代理操作簽收與組員獨立重做_2026-10-20.md)記錄，正式V5清單目前仍3/14。

English: The supplied master now has 14 slides, but the previous offline contract referenced 13-slide assets. A native PDF and page renders now match the exact master without altering it. The new explicit profile preserves strict hash, whitelist and fresh-restore checks; the historical profile remains available. Static fallback validation is distinct from live operation or personal/device acceptance.
