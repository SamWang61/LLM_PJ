# 14頁簡報閱讀與離線備援 / Reviewed 14-slide fallback

更新：2026/10/22（Asia/Taipei）。此目錄對應[使用者指定的原始PPTX](../超市AI版_2026-10-18/VibeCart_AI_超市網購與AI系統_2026-10-18_v5.pptx)，不另改原稿內容。請先讀[展示內容更新卡](展示內容更新卡.md)，再講解原稿中較早的畫面及狀態。

- [14頁PDF](VibeCart_AI_14頁閱讀版_2026-10-22.pdf)：由Microsoft PowerPoint 16.0原生匯出，933,269 bytes。
- [14頁渲染清冊](投影片/pages.json)：PDF逐頁渲染為1600×900 PNG，逐頁大小與SHA-256均在清冊。
- [專案最新上下文](../../docs/CURRENT_CONTEXT.md)及[本輪交付紀錄](../../docs/SAM_OFFLINE_14_SLIDES_2026-10-22.md)。

原始PPTX為14頁、3,262,322 bytes，SHA-256 `4aa9b13286fe98574d3dd648889545ad196d92cea9aebb9a143c794ad392d193`。本PDF SHA-256為 `79e4883a70fc38df2cd94cdb0b74685228b1763481753a55584945c4779186f5`。原稿第12、13頁內容相同、頁尾均標12；本閱讀版完整保留，導覽使用實際順序1至14，不自行刪頁或重新編原稿頁碼。原稿部分待辦敘述已非最新狀態，口述以更新卡與當次證據為準。

## 建包與復原

連線時先下載Git/LFS物件，確認PDF實體內容已在本機，再離線建包。Python工具只讀指定提交白名單內的簡報與文件，不讀環境檔、密鑰、帳號或資料庫；建包過程不連網。所有輸出檔名及復原目錄均須尚未存在。

```powershell
git lfs pull
python scripts/v5_offline_bundle.py build --commit HEAD --profile v5-14-20261022 --output "$env:TEMP/VibeCart_14slides_20261022.zip"
python scripts/v5_offline_bundle.py restore --archive "$env:TEMP/VibeCart_14slides_20261022.zip" --destination "$env:TEMP/VibeCart_14slides_restored_new"
```

成功建包後先核對輸出ZIP的SHA-256，再放到展示電腦及離線儲存裝置。ZIP不進GitHub；本目錄的PDF經Git LFS、PNG與流程經Git版控。包內有22份內容檔案加1份manifest，含PPTX、PDF、14張PNG、HTML索引與逐頁入口、渲染清冊、流程、更新卡及專案上下文。

復原工具先驗完整檔案集合、路徑、大小與SHA-256，通過後才建立新目錄，寫入後再讀回；拒絕舊目錄、路徑穿越、大小超限、重複或符號連結。雜湊用於核對交付及傳輸完整性，不是數位簽章；仍須從已核對提交或可信交付者取得ZIP。

## 現場替代流程

1. 網路或網站失效時，停止送出交易，開復原目錄的`index.html`。
2. 優先開`slides.html`看14頁圖片，不依賴網路、外部字型、CDN或PDF外掛；PDF與PPTX為另外的閱讀方式。
3. 先按`updates/current-scope.md`說明歷史畫面與現況界線，再依實際頁序展示。不要把離線圖片稱作即時網站操作。
4. 帳號被拒、模型逾時或資料庫異常時，改用已錄存畫面說明，記下時間及錯誤；不在正式庫造單、重匯D1～D4或改權限來補展示。
5. 如需計時排練，逐頁記錄講者、設備、開始／結束與故障切換。第12、13頁重複內容是否只講一次由講者決定，原稿及備援檔案仍保留全部14頁。

本機建包、復原與桌面離線瀏覽的技術結果，不自動表示曾使用另一台電腦、真手機或投影，也不預填三人本人已重做；SAM代理管理判定按專案最新規則另記。

English: This fallback preserves the user-supplied 14-slide master, including duplicate content on slides 12 and 13. Build from a pinned Git commit with local LFS payloads, restore to a fresh directory, then open `index.html` without network access. This is a static presentation fallback, not a live system or personal/device acceptance record. Historical 13-slide materials remain unchanged.
