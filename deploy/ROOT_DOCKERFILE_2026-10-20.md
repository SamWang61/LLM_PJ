# 根目錄 Dockerfile 與 Cloud Build 驗證｜2026-10-20

使用者要求修補儲存庫根目錄缺少的Dockerfile，推送GitHub並實測Cloud Build。原始 `C:/LLM/LLM_PJ` 有其他未提交工作，本輪在乾淨工作樹處理。

## 建置入口與相容性

- [根目錄Dockerfile](../Dockerfile)對應儲存庫目錄：網站來源為 `MuscleCore分析資料/website`，共享服務為根目錄的 `VibeCart_AI/services`，沿用Python3.12、Gunicorn、UID10001、`PORT`、AI選配及Secret Manager執行期注入方式。
- [根目錄.dockerignore](../.dockerignore)預設排除全部，只開放雲端依賴、runtime、指定app來源副檔名與三個共享服務；`.env`、資料檔、cache、node_modules與Git目錄不進context。資料夾例外會連帶放行子檔案，因此此處只使用檔案白名單，並以真Docker export驗證，沒有用自製glob模擬Docker規則。
- [既有網站Dockerfile](../MuscleCore分析資料/website/Dockerfile)保留給舊的flat封裝，既有發布工具預設行為不變。[來源封裝器](../scripts/prepare_cloud_source.py)新增 `--layout repository`，輸出根目錄Dockerfile與原始目錄結構。兩種layout都只讀指定Git commit的regular blobs，拒絕把未提交檔案當作部署來源。
- [GitHub Cloud Build設定](cloudbuild-github-preview.json)先對固定 `COMMIT_SHA`產生repository白名單至 `.cloud-preview`，再於該目錄用根目錄Dockerfile執行Build → 離線boot → Push → 私有候選。沒有直接把完整髒目錄交給Docker，也沒有移動現有app或共享服務。

10/20控制平面核對時，既有觸發器 `d0b39103-7508-451d-b3e6-6c251f82855d` 已使用上述JSON檔、監聽main，目標為 `vibecart-acceptance-pr21`。本輪不用覆寫觸發器、IAM、秘密或正式流量。部署步驟仍強制私有服務、`--no-traffic`、`github-preview` tag，清空暫時command/args，沿用既有VPC與資料庫設定。

## 本機驗證

[原始報告](../docs/inventory/ROOT_DOCKER_LOCAL_2026-10-20.json)的受測來源為 `f71e5aa47d9a7cf0646ffce6d7b42e622e1ee9be`：

- repository archive 56檔，SHA-256 `492d2ed8c78f6614b54f382cd2a215f7b1eb1827a02637143b7e050ab83b2986`。
- 真Docker context export與56檔的完整檔案集合／bytes一致；8種偽造canary均排除，含app內的`.env`／`.key`／CSV／cache與node_modules。最初預檢曾抓到目錄例外過寬，修正後才進入映像與雲端測試。
- 映像54個執行來源逐檔SHA相符；離線factory健康檢查200、UID10001；實際Gunicorn用 `PORT=9099` 啟動，健康檢查200，測試容器已移除。
- 封裝的committed bytes／CRLF／未提交檔排除、未知layout、既有source audit與私有0%管線防護共 **8 passed**。

可重現命令（需要本機Docker與測試依賴）：

```powershell
python scripts/verify_root_docker_build.py --report <新的本機驗證JSON路徑>
python scripts/prepare_cloud_source.py --layout repository --commit <完整SHA> --output <repo外的source.tar.gz>
python -m pytest scripts/test_prepare_cloud_source.py scripts/test_cloudbuild_entrypoint.py scripts/test_audit_delivery_source.py -q
```

`verify_root_docker_build.py`只做本機建置與離線啟動，不連Atlas、不push映像、不部署；報告拒絕覆寫。Docker建置context應使用乾淨工作樹或上述固定commit封裝，不從含私有異動的原目錄建置。

## Cloud Build 實跑

本機預檢通過後，以推送的完整SHA手動執行既有觸發器，先驗私有0%候選。雲端成功／步驟／映像digest／Ready revision與流量讀回在取得實際結果後補入；沒有結果前不宣稱「一次成功」。後續合併main的自動觸發與CI也分別回讀。

本輪驗的是根目錄入口、封裝、建置及私有候選部署；正式發布、真交易／模型與V5簽收依各自範圍處理，不能由Cloud Build綠燈推定全部完成。

## 官方行為依據

- [Docker context與.dockerignore](https://docs.docker.com/build/concepts/context/)：忽略規則在context根目錄生效，最後匹配規則決定包含與排除；檔案例外由實際Docker驗證。
- [Cloud Build step工作目錄](https://docs.cloud.google.com/build/docs/build-config-file-schema#dir)。
- [以固定來源執行既有trigger](https://docs.cloud.google.com/build/docs/api/reference/rest/v1/projects.locations.triggers/run)。
