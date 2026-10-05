# 仁千 HEN：會員／購物流程（B） / Auth and order handoff

2026-10-05：組長確認 HEN 選擇 B，負責會員／購物流程，對應既有分支 `feature/auth-order`。此決策取代原前台／RWD 暫定安排；前台／RWD 待重新分配，整合驗證責任仍待確認。

HEN owns option B (auth/order). The former provisional frontend assignment is superseded. See [current ownership](TEAM_OWNERSHIP.md).

## 工作範圍 / Scope

| 路徑 | 用途 |
|---|---|
| `MuscleCore分析資料/website/app/auth.py` | 註冊、登入、會員狀態與角色驗證 |
| `MuscleCore分析資料/website/app/store.py` | legacy 購物流程 |
| `MuscleCore分析資料/website/app/store_v4.py` | v4 SKU 購物車、結帳路由 |
| `MuscleCore分析資料/website/app/templates/auth/` | 會員表單 |
| `MuscleCore分析資料/website/app/templates/store/cart_v4.html` | SKU 購物車頁面 |
| `MuscleCore分析資料/website/tests/test_v4_routes.py` | v4 路由契約測試 |

沿用已合併的 v4 SKU 服務，不重建購物車資料結構；資料契約與交易服務變更先與 SAM 協調。AI／後台由 JEFF 負責。結帳仍是示範流程，未接正式金流；不要把會員功能交接當成全站驗收完成。

Reuse the existing v4 transactional services. Coordinate data-contract changes with SAM; AI/admin belongs to JEFF. Checkout remains a demo, not a payment integration.

## 分支與操作 / Branch workflow

`feature/auth-order` 是功能分工分支，PR 合併目標為 `main`。首次使用：

```powershell
git fetch origin
git switch --track origin/feature/auth-order
```

若本機分支已存在，改用 `git switch feature/auth-order`，確認未提交工作已妥善保存後再 `git merge --ff-only origin/feature/auth-order`。有分歧時停止並與 SAM 協調；不使用 reset 或 force push 覆蓋工作。

```powershell
git push origin feature/auth-order
```

提交前執行倉庫檢查及網站離線測試。不要提交 `.env`、Atlas URI 或密碼；GitHub 存取權限不包含 Atlas 帳號。

## GitHub 存取狀態 / Access status

2026-10-05：組長已確認 HEN 的 GitHub 帳號為 [@1dcvgieok4gm](https://github.com/1dcvgieok4gm)。GitHub 已有此帳號的 Write 邀請，目前仍待 HEN 接受；不重複發送邀請，也尚未標記為權限已生效。私人 Email 不寫入公開文件。

本倉庫屬個人帳號，協作者 Write 是倉庫層級，可對倉庫推送；分配 `feature/auth-order` 不會自動限制成「只准修改此分支」。本次不授予管理員權限、不移轉倉庫或改動其他人的權限。正式生效需邀請對象接受，或回讀確認已是協作者。

Collaborator write access is repository-wide; branch ownership is a workflow agreement, not a branch-only ACL. HEN is confirmed as @1dcvgieok4gm. An existing Write invitation is pending acceptance as of 2026-10-05; access is not yet active. [GitHub permissions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository).
