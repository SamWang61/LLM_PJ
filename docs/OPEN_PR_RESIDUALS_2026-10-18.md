# 舊開啟PR：main涵蓋與差異核對｜2026-10-18

main `c1ce5cc38727a7077013e0a6452d561ee10ecd67`；核對時間 `2026-10-17T19:22:33.279977+00:00`。本輪open共11，#61為目前執行PR另列。[逐檔blob證據](inventory/N15_OPEN_PR_RESIDUALS_2026-10-18.json)。

| PR | main是否含完整head歷史 | head獨有提交改動路徑 | 與main不同路徑 | 處理建議 |
|---|---|---:|---:|---|
| [#5](https://github.com/SamWang61/LLM_PJ/pull/5) | 否 | 14 | 14 | 下一階段候選；採用前修CLI P2與隔離回歸 |
| [#10](https://github.com/SamWang61/LLM_PJ/pull/10) | 否 | 6 | 6 | 網路現況已另讀；固定出口／收斂仍缺，不合併舊回報當現況 |
| [#13](https://github.com/SamWang61/LLM_PJ/pull/13) | 是 | 0 | 0 | 程式提交全已進main；供原主責確認關閉／封存，不重做 |
| [#14](https://github.com/SamWang61/LLM_PJ/pull/14) | 是 | 0 | 0 | 程式提交全已進main；供原主責確認關閉／封存，不重做 |
| [#15](https://github.com/SamWang61/LLM_PJ/pull/15) | 是 | 0 | 0 | 程式提交全已進main；供原主責確認關閉／封存，不重做 |
| [#16](https://github.com/SamWang61/LLM_PJ/pull/16) | 是 | 0 | 0 | 程式提交全已進main；供原主責確認關閉／封存，不重做 |
| [#17](https://github.com/SamWang61/LLM_PJ/pull/17) | 是 | 0 | 0 | 程式提交全已進main；供原主責確認關閉／封存，不重做 |
| [#18](https://github.com/SamWang61/LLM_PJ/pull/18) | 是 | 0 | 0 | 程式提交全已進main；供原主責確認關閉／封存，不重做 |
| [#19](https://github.com/SamWang61/LLM_PJ/pull/19) | 否 | 7 | 7 | 保留有用原始素材；按同版來源挑選，不整包回退文件 |
| [#65](https://github.com/SamWang61/LLM_PJ/pull/65) | 否 | 11 | 11 | 新範圍／簡報交付另行審查；本分支已整合main c1ce5cc階段決定 |

對#13～#18先驗`git merge-base --is-ancestor <head> <main>`成功，故完整head歷史均包含，沒有遺漏提交。其餘從merge-base..head列變更路徑，比對head與main的Git blob；不同可能是後續更新或衝突，不能單憑不同檔數推論缺功能。

本輪沒有merge或close這些PR，也沒有用PR數增加功能完成分。N15的技術盤點已完成，原主責的結案決策與剩餘素材／網路條件仍待交。
