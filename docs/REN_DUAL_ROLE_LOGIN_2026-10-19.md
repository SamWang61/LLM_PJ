# REN 同 Email／雙角色登入｜2026-10-19

## 本次需求與帳號

依委託人指示，同一Email輸入不同密碼，分別登入一般會員（`customer`）或管理員（`admin`）。本階段密碼固定，僅經指定文件與離線建立工具載入，不提供會員或管理員線上改密功能。

| 使用者 | 登入Email／通知信箱 | 角色 |
|---|---|---|
| [SAM](mailto:cashsam@gmail.com) | [cashsam@gmail.com](mailto:cashsam@gmail.com) | customer、admin |
| [JEFF](mailto:jeff841117@gmail.com) | [jeff841117@gmail.com](mailto:jeff841117@gmail.com) | customer、admin |
| [REN](mailto:chen2000401@gmail.com) | [chen2000401@gmail.com](mailto:chen2000401@gmail.com) | customer、admin |

JEFF依最後更正採`jeff841117@gmail.com`；先前拼寫未建立帳號、未寄通知。三人共六筆登入身分，各有獨立ObjectId、密碼雜湊、session與購物資料；既有管理員ObjectId保留。

## 登入與密碼規則

- 維持同一登入表單，不接受前端指定角色；只有唯一符合密碼的資料才能登入。一般會員進前台，管理員進管理後台；錯誤、停用、過期或同密碼命中兩角色時拒絕登入。
- `users`改採唯一索引`(email, role)`；先建立新索引，再移除舊Email唯一索引，過程持續保護同角色唯一性。舊migration來源保持原bytes；新增第七筆migration。
- 每次請求仍依ObjectId讀回啟用狀態／角色與裝置session；交易提交仍驗角色、密碼指紋及session。切換角色撤銷同瀏覽器前一session，其他裝置獨立。
- `/auth/password`對已登入的兩角色均拒絕（403）；登入表單顯示本階段不開放改密。註冊不能建立管理員，也不能覆寫既有Email。
- Atlas只存加鹽雜湊。GitHub保存程式、[帳號清冊](../config/role_accounts_20261018.json)及說明；不提交明文密碼、密碼雜湊或私有連線檔。通知信依委託人授權寄至上列三個信箱。

## 由文件建立

公開清冊指定三人及兩角色。私有檔放在版本庫外，支援JSON或Windows CurrentUser DPAPI；JSON結構如下，值由委託人指定資料填入：

```json
{
  "mongo_uri": "<既有授權的私有URI>",
  "role_passwords": {"admin": "<指定管理密碼>", "customer": "<指定一般會員密碼>"}
}
```

先執行dry-run，再於已測的新登入程式可用時套用：

```powershell
python scripts/provision_role_accounts.py --manifest config/role_accounts_20261018.json --credentials-file <版本庫外的私有檔>
python scripts/provision_role_accounts.py --manifest config/role_accounts_20261018.json --credentials-file <版本庫外的私有檔> --apply
```

工具限制正式Atlas hostname及`vibecart_ai`，拒絕拼錯的清冊、相同角色密碼、synthetic或非local身分；六筆帳號在同一交易建立／更新。重跑已符合的身分不改雜湊、不撤其session；修改密碼或重新啟用時撤銷該身分舊session。報告不含密碼材料。DDL migration與六筆帳號交易分開記錄；帳號交易失敗可以重跑，不能將DDL成功誤認為帳號成功。

## 實際測試與交付

更新：2026/10/19 05:52（台灣時間）。[機器證據](inventory/REN_DUAL_ROLE_LOGIN_2026-10-19.json)。

- 最新main整合版本：網站 **260 passed／0 skipped**，封裝／來源 **5 passed**；登入實作`2c32fa4`的[CI #496](https://github.com/SamWang61/LLM_PJ/actions/runs/39169052358)成功。正式基線的本次登入增量另跑 **207 passed／0 skipped**，包含真MongoDB六筆帳號原子回滾。
- Atlas：三筆原管理員更新指定密碼並保留ObjectId，新增三筆customer；六筆啟用且雜湊核對正確。28集合／89索引／7筆migration嚴格讀回通過，舊六筆migration checksum及庫存hash不變，D4仍1,240筆。本次沒有重匯D1～D4或執行業務結帳。
- 正式來源 **`576b474822efd7464d650d7af2aa245e07fbc911`**，由原正式`e000d95`加登入增量建立；51檔Git blob封裝、GCS完整讀回一致，runtime只有`app/auth.py`及`app/templates/auth/login.html`兩檔不同。最新main的評價／6＋4增量另依原預覽紀錄處理。
- [Cloud Build](https://console.cloud.google.com/cloud-build/builds;region=asia-east1/9971323c-5772-4273-aec5-ad8dd59d3cf0?project=278483818008)兩步SUCCESS，image digest **`sha256:228862259bd96a69224132e5af73fc4e1c89165a759057470ed467c4ce80617b`**。
- 正式revision **`vibecart-web-role-auth-576b4748`**，05:48切換100%流量；Cloud Run與[Firebase公開入口](https://vibecart-llmai.web.app/auth/login)均使用本次登入版，Hosting rewrite未重發。
- 05:47預覽與05:49正式HTTPS各驗六組：customer登入302至前台、admin路由拒絕302；admin登入302至後台且後台200；兩角色改密403；正常登出302後舊session無法進後台。每次只登出本次瀏覽器，沒有刪除其他裝置session；未執行付款／出貨。
- 已由`cashsam@gmail.com`分別寄出三封通知至表列信箱，寄件服務均回傳SENT；指定密碼只包含於授權通知及版本庫外DPAPI私有檔，未入Git。未使用臨時IAM授權。
- [PR #95](https://github.com/SamWang61/LLM_PJ/pull/95)保存main整合程式與文件；正式執行來源為上述部署分支。PR推送／審查與正式部署來源分開記錄。

本次帳號需求與H08實機／REN具名接收分別記錄，既有V5關卡統計仍2/14。
