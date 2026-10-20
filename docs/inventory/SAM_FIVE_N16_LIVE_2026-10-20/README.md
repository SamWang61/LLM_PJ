# N16 最後採用版本：日期補充素材索引｜2026-10-20

本目錄收錄 Codex 以 IAB 在正式 Firebase 擷取的11張未編修PNG，將 S01～S12 每項對到新原圖或實際同映像API／探針證據。SAM以技術代理身分整理；[REN](mailto:chen2000401@gmail.com)與[JEFF](mailto:jeff841117@gmail.com)本人採用及簽收不預填。此補充索引已填補使用者本輪篩選的N16技術／素材缺口；原20張歷史圖及固定V5 PPTX／PDF保留。

## 當次正式版本與時間

來源 `fc4e7c071c34a43594a50f6d0407952e8f20113b`；正式 `vibecart-web-five-fc4e`、私有 `vibecart-acceptance-pr21-five-fc4e-normal` 各100%，同digest `sha256:5efdd89f40c3119306a1d5f1560a039eeff5d8a1d70667d1dfacb40c81341ea3`。08:52:49～08:52:51控制平面與Hosting路由見[最後原始JSON](../SAM_FIVE_FINAL_CONTROL_2026-10-20.json)；Hosting release `1792363722745000`／version `a33b77d8155885b8`沿用，rewrite仍指向`vibecart-web`。此批圖在新Run修訂承接正式路由後取得，不是PPTX重新生成或另一次Hosting發布。

下表為原檔寫入時間（Asia/Taipei），不是瀏覽器請求起始時間；實際PNG尺寸、位元組、SHA-256、URL與版本均在[manifest](manifest.json)。08:51～08:52第一輪的02／04只取到頁首，保留其限制；後續10／11補出搜尋結果。SAM管理登入後只讀，正常CSRF登出並reset尺寸；未送出模型或建立正式訂單。

| 原檔 | 寫入時間 UTC+8 | PNG尺寸 | 畫面與證明範圍 |
|---|---|---|---|
| [01-home.png](01-home.png) | 08:51:18.757 | 1265×711 | 首頁教學聲明與6＋4標題；未完整顯示推薦商品清單。 |
| [02-search.png](02-search.png) | 08:51:35.735 | 1265×711 | 搜尋「刷樂」後停留頁首；不作結果區證明。 |
| [03-product.png](03-product.png) | 08:51:44.032 | 1265×711 | 刷樂醫生牙刷79元、庫存95、預設4.0／0筆；尚未選SKU規格。 |
| [04-no-results.png](04-no-results.png) | 08:51:48.289 | 1265×711 | 不存在字串搜尋後停留頁首；不作0件證明。 |
| [05-role-login.png](05-role-login.png) | 08:51:58.054 | 1265×711 | 匿名登入入口與同Email依密碼選角色說明；不是登入成功圖。 |
| [06-admin.png](06-admin.png) | 08:52:02.660 | 1265×711 | SAM管理者營運總覽；預設最近100筆／包含示範訂單，有效63／全部100、營收110205.20。 |
| [07-ai-compare.png](07-ai-compare.png) | 08:52:12.024 | 1265×711 | Local／Cloud比較狀態仍為尚未量測，不宣稱模型輸出或耗時通過。 |
| [08-monitor.png](08-monitor.png) | 08:52:13.602 | 1265×711 | 規則權重4/3/2/1；BGE旗標未啟用、Claude摘要旗標啟用。 |
| [09-admin-390.png](09-admin-390.png) | 08:52:13.745 | 375×844 | 實際頁面是推薦監控；390×844桌面瀏覽器尺寸，非真手機。 |
| [10-search-results.png](10-search-results.png) | 08:56:38.001 | 1265×711 | 刷樂商品卡；前四張與第五張開頭可見，實際AX讀回共5項。 |
| [11-no-results-detail.png](11-no-results-detail.png) | 08:56:48.561 | 1265×711 | 0件空結果提示及三人頁尾可見；實際AX讀回共0項。 |

02／04初輪完整URL未另存，只保留已知查詢字串。10／11的實際完整URL分別為：

- `https://vibecart-llmai.web.app/?q=%E5%88%B7%E6%A8%82&major=&category=#products`
- `https://vibecart-llmai.web.app/?q=sam-no-result-20261020&major=&category=#products`

## S01～S12 最後採用對照

| ID | 選用原圖或實際證據 | 可說內容及版本界線 |
|---|---|---|
| S01 | 01首頁、11空結果頁尾 | 新正式首頁教學聲明及三人頁尾；未另拍三人hover動作。 |
| S02 | 10搜尋結果、11空結果 | 「刷樂」5項與不存在字串0項；02／04保留為初輪頁首圖。10未將全部5張卡拍在單一視窗。 |
| S03 | 03商品；[N06正常](../SAM_FIVE_N06_NORMAL_2026-10-20.json) | 新正式牙刷79元／庫存95／預設4.0／0筆。詳情圖未選規格；同映像私有SKU契約另有探針，不冒充正式Atlas同SKU讀回。 |
| S04 | 05角色入口、06管理者頁；[N06正常](../SAM_FIVE_N06_NORMAL_2026-10-20.json) | 新正式角色提示及SAM管理者成功頁；同digest私有兩裝置、customer拒絕admin與單裝置登出通過。05本身僅是匿名入口。 |
| S05 | [N06正常](../SAM_FIVE_N06_NORMAL_2026-10-20.json)、[故障](../SAM_FIVE_N06_FAULT_2026-10-20.json)、[獨立清理](../SAM_FIVE_N06_CLEANUP_2026-10-20.json) | 同digest私有cart改量／持久化、同ID同單、409、庫存競爭、故障回滾／恢復與清理。沒有新增正式下單或訂單UI圖；舊S05維持10/18隔離標示。 |
| S06 | 06管理總覽；[N06正常](../SAM_FIVE_N06_NORMAL_2026-10-20.json)；[N12](../../SAM_FIVE_N12_2026-10-20.md) | 正式預設最近100筆；同digest私有12組固定問題／demo範圍KPI有獨立數字對帳。正式圖與私有61.25等數字各屬自己的資料範圍。 |
| S07 | 01的6＋4標題、08旗標；[N06正常D4](../SAM_FIVE_N06_NORMAL_2026-10-20.json)；[原排序證據](../reviews_ai_formal_ui_20261020.json) | 新digest私有一般事件可影響推薦、1001筆synthetic後計數仍14；6＋4高星排序舊證據保留03d01cb5日期／digest。[N15](../../SAM_FIVE_N15_2026-10-20.md)確認新版本僅cart清理改動；沒有假造高星或新拍完整10件列表。 |
| S08 | 07比較、08監控；[N06正常](../SAM_FIVE_N06_NORMAL_2026-10-20.json) | 新正式比較頁尚未量測；BGE旗標未啟用、Claude摘要旗標啟用；私有固定問題為rules-only。未送模型，旗標不代表模型成功呼叫、耗時或品質驗收。 |
| S09 | [N15來源與CI](../../SAM_FIVE_N15_2026-10-20.md)、[來源fc4e7c0 Actions](https://github.com/SamWang61/LLM_PJ/actions/runs/39338040151) | 執行來源同SHA CI成功；最後文件交付以該PR／main CI紀錄為準。原S09仍為10/18歷史，不偽造新Actions圖。 |
| S10 | [正常事件契約](../SAM_FIVE_N06_NORMAL_2026-10-20.json)、[故障快照](../SAM_FIVE_N06_FAULT_2026-10-20.json)、[12集合三marker清理](../SAM_FIVE_N06_CLEANUP_2026-10-20.json)、[N11清冊](../SAM_FIVE_N11_2026-10-20.json) | 真實去敏API／探針資料及consumer清冊，不是Atlas Console；清理僅涵蓋當次marker。 |
| S11 | [最後控制平面](../SAM_FIVE_FINAL_CONTROL_2026-10-20.json)、[N06發布](../SAM_FIVE_N06_RELEASE_2026-10-20.json) | 新正式／私有同來源與digest各100%、既有Hosting路由由新Run承接、公開五路由200；不稱新Hosting發布或Cloud Console截圖。 |
| S12 | 09新正式推薦監控；[N12五圖與互動](../../SAM_FIVE_N12_2026-10-20.md)；[C05前台](../../SAM_C05_BROWSER_MATRIX_2026-10-20.md) | 新版390×844畫面；N12在08:40～08:44舊03d版驗390／844、焦點、日期錯誤及導覽。新版本只有cart變更，UI byte相同但不改標舊圖digest；C05前台仍為本機mock，均非實機。 |

## 固定V5與離線包

[原20張S01～S12](../../../簡報文件/screenshots/S01-S12_同版取證_2026-10-18.md)仍屬10/18 `ff65eae`／`ba7d347…`，未覆蓋或改日期成新正式圖。固定13頁V5 PPTX SHA-256為 `43374f71c5e42fdc1725f38a8ac69ea0e2ccc696f6238ebb06425e58e00d7203`，PDF為 `c5555c2a54d8a4200fd79fb8073d0fa5af691b40b13a4e031ddf9f8f6dc4535d`；兩檔未改。

本目錄為新增日期補充，未宣稱嵌入PPTX或原43內容檔離線ZIP。既有ZIP保持歷史V5素材包。最後投影片採用、三人具名、真手機／異機及現場投影按使用者口徑排除於這五項技術缺口，本人仍依共同表自行記錄實際結果。
