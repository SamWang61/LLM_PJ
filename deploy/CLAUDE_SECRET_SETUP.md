# Claude 密鑰設定與無流量驗收｜2026-10-18

適用專案：Google Cloud `vibecart-llmai`（編號 `278483818008`），不是 Atlas 的 `vibecart_ai`。主責：[SAM](mailto:cashsam@gmail.com)。Key由有權擁有人在Console輸入，Cloud Run使用Secret Manager引用；聊天與Git只記版本號。

## 本次完成狀態

使用者已新增版本**1**；SAM讀版本metadata為**ENABLED**，並已於`vibecart-acceptance-pr21-main20ee-claude1-180s`明確引用版本1。四固定問題／快取／token與停用退回結果見[驗收紀錄](../docs/SAM_MAIN_PREVIEW_2026-10-18.md)。正式流量與自由提問仍未開放，SAM未讀密鑰內容；下列步驟保留作設定與輪替手冊。

## 已準備的部分

2026/10/18 16:40（台北）已建立空的 `ANTHROPIC_API_KEY` secret，當時沒有任何版本。已讀回此secret上的 `roles/secretmanager.secretAccessor`，成員為 `vibecart-pr21-acceptance@vibecart-llmai.iam.gserviceaccount.com`；只供私有驗收服務使用。本輪沒有替正式runtime新增此權限，也沒有存取Claude密鑰內容。

## 你需要操作的步驟

1. 若已有有權使用、尚未失效且有API額度的Anthropic Key，直接進入下一步。否則到[Claude Console](https://platform.claude.com/)的 **Settings → API keys → Create key**，選定本專案可使用的workspace及適當期限，建立並複製Key；多人共用的服務使用service account key。這是Claude API金鑰，不是Google登入憑證、MongoDB密碼或ChatGPT訂閱。[Anthropic官方說明](https://platform.claude.com/docs/en/get-api-key)。
2. 開啟[本專案的密鑰版本頁](https://console.cloud.google.com/security/secret-manager/secret/ANTHROPIC_API_KEY/versions?project=vibecart-llmai)，確認頂端專案為 `vibecart-llmai`，密鑰名稱為 `ANTHROPIC_API_KEY`。
3. 按 **新增版本／Add new version**，在 **Secret value** 貼入完整Key；不要加引號、`ANTHROPIC_API_KEY=`、Markdown或其他文字。按 **新增／Add** 完成儲存。操作依[Google新增版本說明](https://docs.cloud.google.com/secret-manager/docs/add-secret-version)。
4. 確認新版本狀態為 **Enabled／已啟用**，記下數字版本。首次通常為 `1`；若之前建過版本，以實際數字為準。完成後只回覆「版本1已啟用」或實際版本號，勿貼Key、Console顯示密鑰值或含Key的截圖。

若無法按新增版本，先確認Google帳號與專案；管理者可在這個secret授予輸入者 `roles/secretmanager.secretVersionAdder`。這與Cloud Run執行身分的secretAccessor是不同用途。不要為此把secret或服務設為公開。

## 輸入後的驗收順序

1. SAM只讀版本metadata確認該數字版本Enabled及私有runtime IAM；再在同版映像的新私有、0%流量修訂引用 `ANTHROPIC_API_KEY:<數字版本>`，不使用`latest`冒稱可重現。
2. 私有修訂保持獨立 `vibecart_acceptance_pr21`、`CLOUD_ACCEPTANCE_MODE=true`、2Gi／1CPU、min0／max1。啟用 `AI_SUMMARY_ENABLED=true`，模型 `claude-sonnet-5`；`AI_FREE_QUESTION_ENABLED=false`。
3. 使用少量隔離fixture驗admin／customer角色、BGE首次／快取、四個固定intent、Claude實際token／耗時、相同請求快取、受控自由提問403與錯誤fallback；清理fixture與臨時測試存取權限。無Key、額度不足、供應商錯誤或回覆不符合契約時保留未通過。
4. 保存同版SHA、digest、revision、secret版本號與結果；不保存Key。取得完整證據前，正式流量與Hosting入口維持原版本。新增secret版本本身不會更新現有修訂或自動切流量。[Cloud Run秘密注入](https://docs.cloud.google.com/run/docs/configuring/services/secrets)、[無流量tag驗證](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)。

Claude真實呼叫會使用該Key所屬組織的API額度。若不提供Key，本輪仍可完成無流量部署、商品唯讀、隔離交易與真BGE；Claude保留待驗收，不改成完成。
