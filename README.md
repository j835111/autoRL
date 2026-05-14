# AutoRL

一個簡單、可擴充的強化學習框架：

- 內層是可獨立執行的 RL agent
- 外層是自動依照訓練結果調參的 auto-researcher
- 訓練完成後，最終只需要載入內層 policy 檔，不需要再接外層 agent

這個版本以 `uv` 作為專案環境與執行入口，方便把實驗、測試與 CLI 都收斂到同一個工作流。之後如果要換成 PyTorch + DQN/PPO，或把外層換成 LLM，都可以沿用目前的介面。

## 架構

```text
auto_rl/
  cli.py
  config.py
  orchestrator.py
  schema.py
  envs/
    base.py
    grid_game.py
    real_game.py
  training/
    base.py
    dqn.py
    factory.py
    metrics.py
    q_learning.py
  researcher/
    base.py
    heuristic.py
    llm.py
    llm_bridge.py
    validation.py
configs/
  baseline.json
outputs/
```

## 執行方式

先安裝 `uv`，再在專案根目錄執行：

```bash
uv sync
uv run auto-rl train --config configs/baseline.json
```

訓練完成後，最終的 `best_policy.json` 可以獨立執行；`play` 不需要 `configs/baseline.json` 存在：

```bash
uv run auto-rl play --policy outputs/demo_run/best_policy.json --episodes 5
```

若你仍想沿用訓練 config 內的 seed，也可以額外傳入：

```bash
uv run auto-rl play --policy outputs/demo_run/best_policy.json --config configs/baseline.json
```

## 設計重點

- 內層 RL 已支援 `DQN` 與 `Q-learning`，預設 baseline 走 `DQN`
- 外層 researcher 依據結構化 phase metrics 自動調整超參數
- 每個 phase 會分開記錄 benchmark 與 correctness checks，避免把不可部署結果誤當成改善
- 內建 confidence scoring 與 budget controls，降低長迴圈只靠單次波動調參的風險
- 未來若要換成 DQN / PPO 或接 LLM，只要保留 `metrics -> researcher -> next config` 這個回圈即可

## 規格文件

- Spec: `docs/SPEC.md`
- WBS: `docs/WBS.md`
- Phase metrics schema: `schemas/phase_metrics.schema.json`
- Researcher output schema: `schemas/researcher_adjustments.schema.json`

## 追蹤文件

- Project tracker: `docs/PROJECT_TRACKER.md`
- Decision log: `docs/DECISION_LOG.md`
- Risk register: `docs/RISK_REGISTER.md`
- Execution log: `docs/EXECUTION_LOG.md`

## 輸出內容

訓練結束後，`outputs/demo_run/` 會產生：

- `best_policy.json`: 先看 success rate、再看 reward 選出的最佳內層 policy
- `final_policy.json`: 最後一個 phase 的內層 policy
- `summary.json`: 完整訓練摘要、`run_id`、`objective`、最後實際訓練設定，以及下一輪建議設定
- `resolved_config.json`: 與 `final_policy.json` 對應的實際訓練設定
- `experiment_metadata.json`: 本輪 run metadata
- `phase_log.jsonl`: 本輪 phase ledger，包含 `run_id` 與 `journal_event_id`
- `experiment_journal.jsonl`: 跨 run append-only 的實驗歷史
- `experiment_session.md`: 供人與 agent 續跑的 session 文件，會在 run 開始時建立，並於每個 phase 後刷新

若重複使用同一個 `output_dir`，AutoRL 會先清掉自己管理的舊 artifact，再寫入本輪輸出，避免舊的 `phase_log` 與 phase 檔案混入新 run。
`experiment_journal.jsonl` 不在這個清理範圍內，會保留跨 run 的 append-only 歷史。

## 如果要改成 LLM 外層

目前 `auto_rl/researcher/llm_bridge.py` 已經提供：

- phase metrics 轉 prompt
- 從模型回覆中抽出 JSON 調參結果

所以你之後只需要把 `HeuristicAutoResearcher` 替換成：

1. 讀取最近幾個 phase 的指標
2. 呼叫你要的模型
3. 要求只回傳 JSON 超參數
4. 套回下一輪訓練

## 備註

目前專案已切到 `uv` 工作流，建議所有訓練、測試、CLI 執行都統一透過 `uv run ...` 進行。
