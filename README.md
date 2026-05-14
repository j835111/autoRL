# AutoRL

AutoRL 是一個以「內層強化學習 agent + 外層自動研究者」為核心的實驗框架。內層 agent 負責和環境互動、訓練與保存 policy；外層 researcher 只在訓練階段讀取 phase metrics，並依結果調整下一輪超參數。

訓練完成後，最終產物是一個可以獨立載入與執行的 policy，不需要 researcher 或原始訓練設定檔參與推論。

## 功能特色

- 支援 phase-based 訓練流程，每個 phase 都會訓練、評估並輸出結構化指標。
- 內層 agent 目前支援 `DQN` 與 `Q-learning`，baseline 預設使用 `DQN`。
- 外層 researcher 支援 heuristic mode，並保留 LLM researcher 的 prompt / JSON bridge。
- 訓練 artifact 可保存、審計、重播，包含 best policy、final policy、summary、phase log 與 experiment journal。
- benchmark metrics 與 correctness checks 分離，避免把不可部署的結果誤判為改善。
- 內建 confidence scoring、rollback、early stop 與 budget controls，降低長時間自動調參失控的風險。
- 使用 `uv` 統一管理環境、CLI 與測試工作流。

## 專案結構

```text
auto_rl/
  cli.py                    # CLI 入口：train / play
  config.py                 # 實驗設定載入與資料結構
  experiment_management.py  # journal、session doc 與 metadata 管理
  orchestrator.py           # 訓練、評估、調參與 artifact 輸出主流程
  schema.py                 # metrics / researcher output schema 輔助
  envs/
    base.py                 # Environment API
    grid_game.py            # toy grid environment
    real_game.py            # 真實遊戲 wrapper 預留介面
  training/
    base.py                 # Agent API
    dqn.py                  # DQN agent
    factory.py              # algorithm factory
    metrics.py              # 訓練與評估指標
    q_learning.py           # tabular Q-learning agent
  researcher/
    base.py                 # Researcher API
    heuristic.py            # 規則式 researcher
    llm.py                  # LLM researcher 預留實作
    llm_bridge.py           # metrics -> prompt / JSON extraction
    validation.py           # researcher output validation
configs/
  baseline.json             # 預設實驗設定
docs/                       # 規格、WBS、追蹤與決策文件
schemas/                    # JSON schema
tests/                      # 單元測試
outputs/                    # 訓練輸出目錄
```

## 環境需求

- Python 3.10+
- uv

安裝 `uv` 後，在專案根目錄同步環境：

```bash
uv sync
```

## 快速開始

執行 baseline 訓練：

```bash
uv run auto-rl train --config configs/baseline.json
```

訓練完成後，預設 artifact 會輸出到：

```text
outputs/demo_run/
```

執行已保存的 policy：

```bash
uv run auto-rl play --policy outputs/demo_run/best_policy.json --episodes 5
```

若只想看每回合摘要，不輸出逐步 render：

```bash
uv run auto-rl play --policy outputs/demo_run/best_policy.json --episodes 5 --quiet
```

`play` 模式不需要原始訓練設定檔存在。若想沿用 config 裡的 seed，可以額外傳入：

```bash
uv run auto-rl play --policy outputs/demo_run/best_policy.json --config configs/baseline.json
```

## CLI 指令

### `train`

```bash
uv run auto-rl train --config configs/baseline.json
```

讀取實驗設定，建立 environment、inner agent 與 researcher，執行 phase-based training loop，最後輸出 policy 與實驗報表。

### `play`

```bash
uv run auto-rl play --policy outputs/demo_run/best_policy.json --episodes 3 --quiet
```

載入已保存的 policy，直接在環境中執行推論。這個流程不會啟動 researcher，也不依賴原本的 training config。

可用參數：

- `--policy`: 必填，policy JSON 路徑。
- `--episodes`: 執行回合數，預設為 `3`。
- `--quiet`: 隱藏逐格畫面輸出。
- `--seed`: 指定推論 seed。
- `--config`: 選填，只用來在未指定 `--seed` 時讀取預設 seed。

## 設定檔

預設設定位於 `configs/baseline.json`，主要分成四段：

- `env`: grid world 的寬高、起點、終點、陷阱、牆、reward shaping 與最大步數。
- `agent`: algorithm、learning rate、gamma、epsilon schedule、DQN hidden size、replay buffer 等 agent 參數。
- `training`: phase 數量、每個 phase 的 episode 數、evaluation episodes、seed、輸出目錄與 objective。
- `research`: researcher 啟用狀態、調參門檻、rollback 條件、early stop 條件與 budget controls。

可以複製 `configs/baseline.json` 成新的設定檔後調整實驗：

```bash
uv run auto-rl train --config configs/my_experiment.json
```

## 訓練輸出

一次訓練完成後，輸出目錄會包含下列主要檔案：

- `best_policy.json`: 以 evaluation success rate 與 reward 選出的最佳可部署 policy。
- `final_policy.json`: 最後一個 phase 完成時的 policy。
- `summary.json`: 本次訓練摘要，包含最佳 phase、最佳指標、停止原因與建議下一輪設定。
- `resolved_config.json`: 和 `final_policy.json` 對應的實際訓練設定。
- `experiment_metadata.json`: 本次 run 的 metadata。
- `phase_log.jsonl`: 本次 run 的 phase ledger。
- `experiment_journal.jsonl`: 跨 run append-only 實驗歷史。
- `experiment_session.md`: 給人或 agent 續跑時閱讀的 session 文件。
- `phase_XX_metrics.json`: 每個 phase 的詳細 metrics。

重複使用同一個 `output_dir` 時，AutoRL 會清理自己管理的舊 phase artifact 與 phase log，再寫入本輪輸出。`experiment_journal.jsonl` 會保留為 append-only 歷史。

## 測試

執行單元測試：

```bash
uv run python -m unittest
```

測試涵蓋 config 載入、CLI play、policy I/O、orchestrator、metrics schema、researcher validation 與 experiment management。

## 重要文件

- `docs/SPEC.md`: 系統規格與架構契約。
- `docs/WBS.md`: 工作拆解。
- `docs/PROJECT_TRACKER.md`: 專案狀態追蹤。
- `docs/DECISION_LOG.md`: 決策紀錄。
- `docs/RISK_REGISTER.md`: 風險清單。
- `docs/EXECUTION_LOG.md`: 執行紀錄。
- `schemas/phase_metrics.schema.json`: phase metrics schema。
- `schemas/researcher_adjustments.schema.json`: researcher output schema。

## 架構重點

AutoRL 的核心流程如下：

```text
Experiment Config
   |
   v
Orchestrator
   |----> Environment
   |----> Inner RL Agent
   |----> Evaluator
   |----> Metrics Reporter
   |
   v
Outer Researcher
   |
   v
Next Phase Config
```

外層 researcher 只負責根據 phase metrics 建議下一輪超參數，例如 `learning_rate`、`gamma`、`epsilon_start`、`epsilon_decay` 與 `episodes_per_phase`。它不直接控制環境、不輸出任意程式碼，也不參與最終 policy 推論。

## 後續方向

- 接入真實遊戲 wrapper，讓 toy grid environment 之外的環境也能使用同一套訓練流程。
- 完成手機端 controller app / on-device runtime / adb orchestration 的實作。
- 將 LLM researcher 接到實際 provider，並沿用目前的 JSON output validation 與 fallback 機制。
- 補上更完整的 resume CLI 與長時間自動化訓練工作流。
