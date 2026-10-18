# JEFF → SAM｜10/18 AI 交付與線上啟用說明

> 日期：2026-10-18（期限 20:00）；撰寫：JEFF（AI／管理後台）
> 本檔整理今天所有 AI 相關 PR、需要 SAM 協助的 Google Cloud 操作、費用負擔與選項。內容與 PR 說明有重複，方便單獨閱讀。

\---

## 1\. 今天的 PR（都可直接合併、彼此不衝突）

|PR|分支 → base|內容|是否影響線上|
|-|-|-|-|
|[#82](https://github.com/SamWang61/LLM_PJ/pull/82)|`feature/jeff-cloud-ai` → `main`|**A1** 雲端 AI 開關改讀環境變數（預設仍關）；**A2** 可選 AI 映像（`INSTALL\_AI`，預設映像不變）；**D1** 線上 AI 設定文件|合併後**不會**改變線上行為；要建 AI 映像＋設定環境變數才會開|
|[#83](https://github.com/SamWang61/LLM_PJ/pull/83)|`feature/jeff-v4-weights` → `main`|**B1** 規則推薦改用 v4 權重 購買 4／加購 3／搜尋 2／瀏覽 1；讀資料庫政策；搜尋字也會計分|下次部署後生效（前台推薦順序會改變）|
|[#84](https://github.com/SamWang61/LLM_PJ/pull/84)|`feature/jeff-demo-purchase` → `feature/jeff-v4-weights`|**B2** 會員自己的示範結帳會影響自己的推薦；推薦監控／成效統計仍排除|下次部署後生效；**#83 合併後請把 base 改成 main**|

**請 SAM 特別看 #84**：在你的 `app/services/behavior\_scope.py` **新增** `personalization\_\*` 兩個函式，原本的 `production\_\*` 沒有修改；你和 REN 的隔離測試都沒改、全部通過。

驗證（三個分支）：網站測試 202 passed／8 skipped、文件檢查 0 errors。#82 另跑了 test\_data、backup manifest、`prepare\_cloud\_source.py`（52 檔）。

**另外**：#12～#15（T1～T4）內容早已在 main，可以關閉。

> 備註：#83／#84 一開始推上去時 `CHANGELOG.md`、`AI\_DASHBOARD.md` 誤存成 CRLF（GitHub 會顯示整檔變更），已補 commit 改回 LF，現在 diff 只剩實際新增的行數。

\---

## 2\. 線上 AI 為什麼還沒開

1. `cloud\_runtime.py` 把 AI 開關寫死 False → **#82 已修**（改讀環境變數，預設仍關）
2. 雲端映像沒有 AI 套件 → **#82 已加建置選項** `INSTALL\_AI=true`（CPU 版 PyTorch＋建置時內建 BGE 模型）
3. Secret Manager 沒有 `ANTHROPIC\_API\_KEY` → **需要建立**（T5 用的 Key 在 JEFF 本機 `.env.v4-test`，雲端讀不到）

\---

## 3\. 可能需要 SAM 負擔的部分（請先看）

**費用**（記在 `vibecart-llmai` 帳單；實際金額依專案免費額度，JEFF 這邊查不到，不估數字）

|項目|說明|
|-|-|
|Cloud Build|AI 映像要裝 CPU 版 PyTorch＋下載 BGE，預估 15～25 分鐘（現在的映像只要幾分鐘）|
|Artifact Registry|AI 映像預估 1～2 GB，多佔儲存空間|
|Cloud Run|記憶體建議 2Gi（現在 512Mi）；min-instances 維持 0，有人連線才計費|
|Secret Manager|多 1 個 secret，費用很低|
|Claude API|**由 JEFF 的 Key 負擔，不算 SAM 的**|

**時間與風險**

* SAM 操作時間約 30～60 分鐘（含等建置）
* 冷啟動變慢（載入 PyTorch／BGE），第一次開首頁或 Local 推薦可能多等幾秒～十幾秒
* AI 映像**還沒實際建過**（JEFF 本機沒有 Docker／gcloud），第一次建置可能要排錯
* 全程先用「零流量」修訂驗證，舊修訂保留，可隨時退回

\---

## 4\. 四個選項（請 SAM 選一個）

|選項|做法|SAM 負擔|簡報可以怎麼說|
|-|-|-|-|
|**A｜完整上線**|合併 #82 → 建 AI 映像 → 建空 secret＋授權 → 零流量部署（2Gi）→ 驗證後切流量|費用最高、操作 30～60 分鐘|線上 Claude＋BGE 運作中|
|**B｜只開 Claude**|同 A，但 `AI\_RECOMMENDATIONS\_ENABLED=false`，記憶體先試 1Gi|建置／儲存同 A，執行記憶體較低|線上 Claude；BGE 用本機實測數字|
|**C｜JEFF 自己操作**|JEFF（專案擁有者）裝 gcloud 照第 5 節執行；SAM 只同意費用並避開同時間發布|費用同 A 或 B，不花 SAM 時間|同 A 或 B|
|**D｜今天不上線**|線上維持現狀（規則推薦、AI 關閉）|0|用 T5 本機實測＋截圖，寫「線上啟用為下一階段」|

\---

## 5\. 操作步驟（選 A／B／C 時使用）

專案 `vibecart-llmai`、區域 `asia-east1`、服務 `vibecart-web`。沿用 `deploy/README.md` 流程，只多標 ★ 的部分。

1. **合併 #82**，從合併後的 main 打包（白名單 52 檔），解壓到獨立目錄當 build context：

```bash
   python scripts/prepare\_cloud\_source.py --output <repo外暫存>/vibecart-source.tar.gz
   ```

2. ★ **建置 AI 映像**（多一個 substitution；日誌要看到 `container-boot-ok` 與 `ai-image-ok`，記下 digest）：

```bash
   gcloud builds submit <build context> --project vibecart-llmai --region asia-east1 \\
     --config <repo>/deploy/cloudbuild.yaml \\
     --substitutions \_IMAGE=asia-east1-docker.pkg.dev/vibecart-llmai/vibecart/web:ai-<日期時間>,\_INSTALL\_AI=true \\
     --service-account projects/vibecart-llmai/serviceAccounts/278483818008-compute@developer.gserviceaccount.com \\
     --gcs-log-dir gs://vibecart-llmai-sam-build-278483818008/logs
   ```

3. ★ **建立空的 secret 並授權**（不放內容）：

```bash
   gcloud secrets create ANTHROPIC\_API\_KEY --project vibecart-llmai --replication-policy automatic
   gcloud secrets add-iam-policy-binding ANTHROPIC\_API\_KEY --project vibecart-llmai \\
     --member serviceAccount:vibecart-web@vibecart-llmai.iam.gserviceaccount.com \\
     --role roles/secretmanager.secretAccessor
   ```

   → 通知 JEFF；**JEFF 在 Cloud Console 的 Secret Manager 自己「新增版本」貼上 Key**，Key 不經過 SAM 或任何檔案。

4. ★ **部署零流量修訂**（沿用現行正式修訂的其他設定，只增加 AI 相關）：

```bash
   gcloud run deploy vibecart-web --project vibecart-llmai --region asia-east1 \\
     --image <步驟 2 的 digest> --no-traffic --tag ai-preview \\
     --memory 2Gi --cpu 2 \\
     --update-env-vars AI\_SUMMARY\_ENABLED=true,CLAUDE\_MODEL=claude-sonnet-5,AI\_RECOMMENDATIONS\_ENABLED=true,AI\_FREE\_QUESTION\_ENABLED=false \\
     --update-secrets ANTHROPIC\_API\_KEY=ANTHROPIC\_API\_KEY:latest
   ```

   * 選項 B：`AI\_RECOMMENDATIONS\_ENABLED=false`、`--memory 1Gi`
   * 若現行正式修訂是唯讀預覽（`CLOUD\_PREVIEW\_READ\_ONLY=true`），`/admin` 會被擋，後台 AI 無法驗證；請照你現行的正式設定
5. **驗證**（零流量網址 `https://ai-preview---vibecart-web-<hash>.a.run.app`）：`/health/live`、`/health/ready`、首頁推薦；JEFF 登入後台測 Local 推薦、雲端洞察 4 個預設問題各 1 次、AI 比較頁；記錄冷啟動、BGE 首次／快取後耗時、Claude 耗時。
6. **切換流量**（JEFF 與 SAM 都同意後才做）：

```bash
   gcloud run services update-traffic vibecart-web --project vibecart-llmai --region asia-east1 --to-tags ai-preview=100
   ```

   退回：

```bash
   gcloud run services update-traffic vibecart-web --project vibecart-llmai --region asia-east1 --to-revisions <舊修訂>=100
   ```

\---

## 6\. 順便請 SAM 唯讀查一下（B3）

正式修訂有沒有設定 `BEHAVIOR\_SYNTHETIC\_BATCH`？

```bash
gcloud run services describe vibecart-web --project vibecart-llmai --region asia-east1 --format "value(spec.template.spec.containers\[0].env)"
```

有設定的話，真實會員的瀏覽／搜尋事件會被標成 synthetic，推薦學不到東西，建議正式環境移除。

\---

## 7\. 簡報相關（給 SAM 參考，REN 排版）

* JEFF 已把 v5 第 8、10、12 頁的 AI 文字交給 REN，數字都是 **T5 本機實測**（BGE 查詢中位數 26.5 ms、Top5 40/40 同大類；Claude 每次 7.5～8.6 秒、輸入 5,000～10,000 tokens）
* 若選 A／B 並完成部署，JEFF 會改用線上實測數字並補 S07／S08 截圖；選 D 則 S08 用本機截圖並標註「本機執行＋commit SHA」

\---

請回覆選 **A／B／C／D**，JEFF 這邊配合。謝謝！

