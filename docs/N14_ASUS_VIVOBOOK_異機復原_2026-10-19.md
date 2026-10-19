# N14 ASUS VivoBook 異機復原操作卡｜2026/10/19

SAM 與 REN 預計今日 14:00 在 REN 的 ASUS VivoBook（Windows）實測。此操作卡準備的是 **2026/10/18 16:10 快照鏈**：05:28 基底密文與最新差異／Atlas 密文，非 10/19 工作目錄即時備份。工具只在全新 localhost 目標還原，不連正式 Atlas。

## 事前核對

- 在 SAM 電腦的私有資料夾 `C:\Users\USER\AppData\Local\CodexPrivateBackups\N14_ASUS_HANDOFF_20261019` 有 `tools/` 與 `wheels/`，不含金鑰、Mongo URI 或任何帳號密碼。複製到**資料媒體**時，同時帶以下兩個密文：`LLM_PJ_N14_20261018_0850/cloud-reassembled.vcbak` 與 `LLM_PJ_N14_CURRENT_20261018_1530/cloud-recheck-readback.vcbak`。來源都位於 SAM 電腦的 `C:\Users\USER\AppData\Local\CodexPrivateBackups` 之下。
- 32-byte `recovery.key` 位於 SAM 電腦的 `C:\Users\USER\AppData\Local\CodexPrivateKeys\LLM_PJ_N14_20261018`，**只放第二個獨立受控媒體**，不放資料媒體、GitHub、聊天、共用 Drive 或截圖。兩份密文只有同一把既有金鑰才能認證解密。若無法分開傳遞，停在準備階段。
- ASUS VivoBook 需 Windows x64、Python 3.12 x64、C: 至少約 8 GiB 可用空間。現場核 REN 的 Windows 帳號與裝置名稱，選其使用者設定檔下全新、未共用的復原目錄。先檢查 `icacls` 不允許非授權人讀取明文；不要把還原目的地放回資料 USB。
- 複製密文到資料媒體後，以 SHA-256 比對：基底 `328b9aa8194589d53d8f18e7d41b0e96809335a1329bd23ed3ba95d992fe51d5`；最新 `5ff28ee49341fa6070ab6b1e418106ed8623901071b3d4e3d54c7c97092aa885`。工具會在解密前重做完整比對；任一不符即停。

## ASUS VivoBook 執行

以下 `E:` 是**資料媒體**、`F:` 是**金鑰媒體**的範例，現場以實際磁碟代號替換。請先建立 REN 帳號專用的私有根目錄與 Python venv；套件由資料媒體的 `wheels` 離線安裝，不需上網下載依賴。

```powershell
$private = Join-Path $env:LOCALAPPDATA 'VibeCartRecovery'
New-Item -ItemType Directory -Path $private -ErrorAction Stop
py -3.12 -m venv (Join-Path $private 'venv')
& (Join-Path $private 'venv\Scripts\python.exe') -m pip install --no-index --find-links 'E:\wheels' -r 'E:\tools\requirements-backup.txt'
& (Join-Path $private 'venv\Scripts\python.exe') 'E:\tools\verify_offdevice_recovery.py' `
  --base-ciphertext 'E:\cloud-reassembled.vcbak' `
  --latest-ciphertext 'E:\cloud-recheck-readback.vcbak' `
  --key-file 'F:\recovery.key' `
  --destination (Join-Path $private 'restore-20261019-1400') `
  --mongod 'E:\tools\mongod.exe'
```

不要把金鑰 bytes、解密 ZIP、Atlas BSON、`.env`、登入畫面或完整私有清冊傳回聊天／GitHub。工具的 `recovery-report.json` 留在 ASUS 私有目的地；可公開的摘要只包含結果、機器不同於 SAM、時間、檔案／集合／索引／TTL 數量、hash 差異和清理狀態。結果應為：`status=passed`、來源 **13,976** 檔差異 0、Atlas **28** 集合／**14,691** 筆／**89** 索引／**3** TTL、BSON 差異 0、測試資料庫已移除、mongod 已停止、`source_database_contacted=false`。若值不同，記實際結果與錯誤，不能標通過。

REN 在[具名接收表](../專題進度/2026-10-19_具名接收與異機復原表.md)填本人姓名、台灣時間、ASUS 裝置識別、Windows／Python／mongod 版本、操作範圍、結果和無機密的證據連結。**同機預演不算異機復原。** 復原後的明文與隔離 source 仍在 REN 私有目錄，由 REN 確認所需留存後依既定資料處理流程清理；不刪正式 Atlas 或來源快照鏈。

## SAM 同機工具預演

2026/10/19 08:05 前後，在 SAM 電腦 `ASUS-VIVO-SAM` 已用兩個既有密文及外部金鑰跑 `verify_offdevice_recovery.py`：AES-GCM 認證成功，13,976 檔完整重建 hash 差異 0，28 集合／14,691 筆／89 索引／3 TTL 於新 localhost 還原差異 0，測試資料庫及進程已清理。完整結果在本機私有 `N14_OFFDEVICE_DRYRUN_20261019_0800/recovery-report.json`，未放 GitHub。這只證明 ASUS 執行前工具可用，不替代 REN 的第二台電腦實測。
