# SAM 整合基線與交付版本｜2026-10-16

本頁記錄同一工作樹可審查的程式來源與驗證。最終展示版仍須完成跨角色、遠端資料與畫面驗收；本頁不是簽收紀錄。

## 來源與順序

| 來源 | 版本 | 本輪處理 |
|---|---|---|
| GitHub `main` | `0d04dd8`（PR #20 已合併） | 作為整合起點；保留文件同步、Git LFS PDF 政策、SAM 交易測試紀錄。該 SHA 的 GitHub push CI [成功](https://github.com/SamWang61/LLM_PJ/actions/runs/38656840917)。 |
| SAM PR #11 → #16 → #17 | `e80d251` → `a418d08` → `a0fcad0` | 依原相依鏈取得資料層、synthetic 隔離、JEFF 功能整合及雲端展示程式；這些 PR 仍未合併至 `main`。 |
| HEN PR #18 | `5053993` | 其基底包含 SAM #17，提供多裝置 session、購物及事件接口；PR 仍為草稿。 |
| 商品導覽分支 | `1caf854` | 在 HEN `5053993` 之上增加前後商品導覽；本輪以此為功能分支來源。 |
| 簡報 PR #19 | `33e70c8` | 仍為草稿，素材與本整合分支分開審查；最終 PPTX 與 S01～S12 證據未完成。 |

本輪從 `main` 建立 `codex/sam-final-baseline-20261016`，整合 `1caf854`。衝突集中在文件及清冊；保留 `main` 的較新文件與原始位元組，並在 `.gitattributes` 同時保留 PDF LFS 與 schema overlay 的換行規則。功能程式沿用導覽分支；原始髒工作目錄未修改。

## 本輪驗證與剩餘門檻

- `python scripts/check_repository.py`：279 files、261 UTF-8 texts、0 errors。
- `git diff --cached --check`：通過。
- 在 `MuscleCore分析資料/website` 執行 `python -m pytest tests -q -p no:cacheprovider`：164 passed、3 skipped。三項真 MongoDB 交易測試須使用隔離 localhost replica set；[10/15 已在 HEN `5053993` 取得 166 passed、0 skipped](SAM_CI_TRANSACTION_ACCEPTANCE_2026-10-15.md)，但本輪新整合 SHA 尚未重跑該環境。
- 本輪尚未驗證新 SHA 的 Docker boot、遠端 CI、Cloud Run 部署、Atlas 正式交易、真模型或人工瀏覽器／手機流程。不得把舊部署 revision 當成本分支。

## 接續順序

1. 取得本整合 SHA 的遠端 CI 成功及容器 build／boot 結果，確認 README、setup、環境範例與實際部署來源一致。
2. 依 PR 相依鏈審查功能與文件差異，確認 HEN／JEFF 功能主責的接口；再決定合併順序。此分支供審查，不替代各主責簽收。
3. 以同一展示 revision 完成角色權限、購物交易與庫存、商品資料對帳、RWD、S01～S12 證據；D4 必須先完成全部 consumer 的遠端 synthetic 隔離驗證。
