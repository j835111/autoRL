# AutoRL Project Tracker

最後更新：2026-04-05

## 1. 用途

這份文件是專案執行追蹤的單一入口，目的不是取代 spec 或 WBS，而是回答下面幾個執行問題：

- 專案現在做到哪裡
- 目前正在推進什麼
- 下一步要做什麼
- 有哪些風險、阻塞、決策需要同步

規格來源：

- [SPEC.md](/D:/project/autoRL/docs/SPEC.md)
- [WBS.md](/D:/project/autoRL/docs/WBS.md)
- [GAME_INTEGRATION_SPEC.md](/mnt/d/project/autoRL/docs/GAME_INTEGRATION_SPEC.md)
- [GAME_INTEGRATION_WBS.md](/mnt/d/project/autoRL/docs/GAME_INTEGRATION_WBS.md)

## 2. 當前狀態快照

### 專案整體

- 專案狀態：Active
- 當前階段：M2、M3、M4 與非-wrapper 的 M5 前置能力完成，進入真實遊戲接入
- 當前焦點：手機端單一路徑 wrapper 與 device control protocol
- 下一個主要里程碑：Emulator RL Loop

### 已完成

- 最小原型骨架完成
- toy environment 完成
- inner baseline agent 完成
- inner agent 抽象完成
- DQN baseline 完成並通過 toy env 驗證
- heuristic auto-researcher 完成
- researcher schema validation / fallback 完成
- checkpoint / compare / rollback 完成
- early stop / stop criteria 完成
- experiment journal / session doc 完成
- benchmark / correctness checks split 完成
- confidence scoring 完成
- budget / resume / finalization semantics 完成
- CLI train / play 入口完成
- `uv` 工作流完成
- 單元測試完成
- spec / WBS / schema 文件完成

### 正在推進

- 手機端單一路徑架構已定稿，準備落地 `device control app`
- 目標遊戲子規格與子 WBS 已改為 controller app / on-device runtime / adb orchestration

### 下一步

1. 依 [GAME_INTEGRATION_SPEC.md](/mnt/d/project/autoRL/docs/GAME_INTEGRATION_SPEC.md) 凍結目標遊戲契約。
2. 定義 `device control app <-> RL runtime` 協定。
3. 實作手機端 controller app 與 on-device RL runtime。

## 3. 里程碑追蹤

| 里程碑 | 名稱 | 狀態 | 出口條件 | 備註 |
| --- | --- | --- | --- | --- |
| M1 | Prototype Contract Freeze | Done | spec、WBS、schema 完成 | 已完成 |
| M2 | Inner RL Upgrade | Done | DQN 可訓練、可存檔、可獨立推論 | 已完成 |
| M3 | Researcher Hardening | Done | schema validation、fallback、best/rollback 規則固定 | 已完成 |
| M4 | LLM Researcher Integration | Done | LLM JSON output 可驗證且可回退 | 已完成安全 parse/validate/fallback 路徑 |
| M5 | Real Game Integration | Active | 手機端單一路徑 wrapper 接入成功 | 具體遊戲細節另見 game integration 文件 |

## 4. Workstream 追蹤

| Workstream | 當前狀態 | 下一步 | 主要檔案 |
| --- | --- | --- | --- |
| 專案結構 | Stable | 維持 | `auto_rl/`, `configs/`, `docs/`, `schemas/` |
| 規格契約 | Stable | 總體規格維持，遊戲串接改更新子規格 | `docs/SPEC.md`, `docs/GAME_INTEGRATION_SPEC.md`, `schemas/` |
| 內層 RL | DQN ready | 維持並視需要再調參 | `auto_rl/training/` |
| 環境層 | Toy env ready | 接手機端 controller protocol 與 game env | `auto_rl/envs/` |
| 外層 Researcher | Hardened | 接入實際 LLM provider 或 response source | `auto_rl/researcher/` |
| 調度與輸出 | Hardened | 維持 | `auto_rl/orchestrator.py` |
| 可觀測性 | Hardened | 維持，後續接入真實遊戲 signal 與 replay artifact | `docs/`, `outputs/` |

## 5. 近期執行清單

### Active

- `3.2 真實遊戲 wrapper`

### Ready Next

- `device control protocol` 與 action / outcome / replay 契約凍結
- 手機端 controller app 原型

### Later

- on-device RL runtime
- adb artifact transport 與 phase 邊界 researcher 接入

## 6. 阻塞與依賴

### 當前阻塞

- 尚未凍結第一個具體遊戲的 action、ROI、過關/失敗畫面規則。

### 主要依賴

- 真實遊戲 screenshot RL 依賴已完成的 `2.3 DQN 升級`
- 手機端依賴裝置截圖、觸控 automation 與本地 runtime 能力
- 桌面端依賴 adb 類 transport 可穩定拉取 / 推送 artifact

## 7. 執行節奏

每次開工或交付後，建議同步更新四個地方：

1. 本文件的「當前狀態快照」。
2. [EXECUTION_LOG.md](/D:/project/autoRL/docs/EXECUTION_LOG.md) 的最新紀錄。
3. [DECISION_LOG.md](/D:/project/autoRL/docs/DECISION_LOG.md) 中新增的重要決策。
4. [RISK_REGISTER.md](/D:/project/autoRL/docs/RISK_REGISTER.md) 中風險狀態與緩解策略。

## 8. 完成定義

一項工作要算完成，至少要滿足：

1. 對應程式碼或文件已落地。
2. 有對應 artifact 或可檢查輸出。
3. Tracker 與 Log 已更新。
4. 若介面有變動，Spec / Schema 已同步。
