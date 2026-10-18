# REN 同 Email／雙角色登入｜2026-10-19

## 本次需求與帳號

依委託人指示，同一Email輸入不同密碼，分別登入一般會員（`customer`）或管理員（`admin`）。本階段密碼固定，僅經指定文件與離線建立工具載入，不提供會員或管理員線上改密功能。

| 使用者 | 登入Email／通知信箱 | 角色 |
|---|---|---|
| SAM | [cashsam@gmail.com](mailto:cashsam@gmail.com) | customer、admin |
| JEFF | [jeff841117@gmail.com](mailto:jeff841117@gmail.com) | customer、admin |
| REN | [chen2000401@gmail.com](mailto:chen2000401@gmail.com) | customer、admin |

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

## 測試與交付進度

- 本機目前main整合來源`6fbaa0c`：完整網站測試 **260 passed／0 skipped**；其中同Email雙角色、禁止改密、錯誤／停用／歧義拒絕、session獨立、唯一索引／冪等與真MongoDB六筆原子回滾均有檢查。
- 新登入部署將以正式來源`e000d95`加本次登入修改建立獨立版本；部署來源與最新main分開記錄，實測後補revision、image digest與六組公開登入結果。
- Atlas正式套用、公開驗收與三人通知信：尚未執行；完成後以本報告及機器清冊更新。

本次帳號需求與H08實機／REN具名接收分別記錄；不變更既有V5關卡統計，不重匯D1～D4、不重設庫存。
