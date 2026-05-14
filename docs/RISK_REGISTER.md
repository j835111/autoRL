# AutoRL Risk Register

最後更新：2026-03-30

## 1. 用途

這份文件用來追蹤專案執行中的風險、觸發條件與緩解方案。

## 2. 風險清單

| Risk ID | 風險 | 影響 | 可能性 | 觸發訊號 | 緩解策略 | 狀態 |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | 內層 baseline 不穩，外層 researcher 會放大波動 | 高 | 中 | reward 大幅震盪、success rate 無法提升 | 先固定 baseline 與驗證指標，再接 LLM | Open |
| R-002 | metrics 定義不足，researcher 無法做有效判斷 | 高 | 中 | 調參結果無法解釋或效果不一致 | 擴充 phase metrics 並保持 schema 穩定 | Open |
| R-003 | researcher 可調整範圍過大，導致系統不可控 | 高 | 中 | researcher 輸出跨越既定欄位 | 以 schema 限制輸出欄位並加入 fallback | Resolved |
| R-004 | 真實遊戲 wrapper 太晚定義，state / reward contract 需重做 | 中 | 中 | toy env 與真實遊戲 observation 差異過大 | 在 DQN 升級前先定 wrapper 契約草案 | Mitigating |
| R-005 | 本地缺乏可執行 Python 環境，驗證中斷 | 中 | 高 | 無法跑 train / play | 統一改用 `uv` 管理執行環境 | Resolved |
| R-006 | 缺乏 checkpoint / rollback，auto-research 只會單向漂移 | 中 | 中 | 新一輪調參讓表現持續退化 | 在 M3 加入 checkpoint compare 與 rollback | Resolved |
| R-007 | 尚未選定具體真實遊戲 backend，`3.2` 無法真正落地 | 高 | 高 | 只有 wrapper scaffold，沒有實際遊戲 integration | 先決定第一個目標遊戲與 `emulator_capture` 或 `device_local` 路徑 | Active |
| R-008 | emulator 訓練與 phone 驗證之間存在 domain gap | 中 | 中 | emulator 成功但真機失敗 | 共用 observation / action 契約，並保留真機驗證階段 | Open |

## 3. 更新規則

每次專案狀態變更時，至少要檢查：

1. 是否有新風險需要登錄。
2. 現有風險狀態是否應改為 `Mitigating`、`Resolved` 或 `Accepted`。
3. 緩解策略是否需要更新。
