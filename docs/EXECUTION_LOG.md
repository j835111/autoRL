# AutoRL Execution Log

## 1. 用途

這份文件記錄專案的執行歷程，讓後續接手的人可以快速看懂：

- 做過哪些事
- 為什麼做
- 目前停在哪裡
- 下一步是什麼

## 2. 建議格式

每次更新建議記錄：

- 日期
- 本次完成內容
- 變更檔案
- 產出 artifact
- 下一步

## 3. 紀錄

### 2026-03-30

完成內容：

- 建立最小可運作的 AutoRL 專案骨架
- 建立 toy environment、tabular Q-learning inner agent、heuristic researcher、orchestrator、CLI
- 建立 baseline config 與 README

變更檔案：

- `auto_rl/`
- `configs/baseline.json`
- `README.md`
- `pyproject.toml`

產出 artifact：

- 原型程式碼骨架

下一步：

- 鎖定專案規格與資料契約

### 2026-03-30

完成內容：

- 補上 Spec、WBS、phase metrics schema、researcher adjustments schema
- 將專案從原型提升到有契約的基線

變更檔案：

- `docs/SPEC.md`
- `docs/WBS.md`
- `schemas/phase_metrics.schema.json`
- `schemas/researcher_adjustments.schema.json`

產出 artifact：

- 規格文件
- 可驗證的 JSON schema

下一步：

- 讓文件更便於後續追蹤執行狀態

### 2026-03-30

完成內容：

- 新增專案追蹤文件：Project Tracker、Decision Log、Risk Register、Execution Log
- 同步 WBS 狀態與 README 文件入口

變更檔案：

- `docs/PROJECT_TRACKER.md`
- `docs/DECISION_LOG.md`
- `docs/RISK_REGISTER.md`
- `docs/EXECUTION_LOG.md`
- `docs/WBS.md`
- `README.md`

產出 artifact：

- 可持續維護的專案追蹤層

下一步：

- 進入 `2.2 Agent 抽象化`

### 2026-03-30

完成內容：

- 將專案工作流改成 `uv`
- 修正 `pyproject.toml` package discovery，讓 `uv run` 可正常執行
- 將真實遊戲 wrapper 的雙 backend 策略與採用順序補進 spec

變更檔案：

- `pyproject.toml`
- `uv.lock`
- `README.md`
- `docs/SPEC.md`

產出 artifact：

- 可重現的 `uv` 執行工作流
- wrapper backend 規格文件

下一步：

- 完成 agent 抽象、DQN、researcher hardening 與測試

### 2026-03-30

完成內容：

- 完成 inner agent 抽象、DQN agent、agent factory、real-game wrapper scaffold
- 完成 researcher schema validation、LLM parse/validate/fallback、checkpoint/compare/rollback、early stop、phase log
- 補上單元測試並以 `uv` 驗證
- 調整 baseline DQN config，確認 toy env 可達到 `success_rate = 1.0`

變更檔案：

- `auto_rl/`
- `configs/baseline.json`
- `tests/`
- `docs/WBS.md`
- `docs/PROJECT_TRACKER.md`

產出 artifact：

- DQN baseline policy
- phase checkpoints / compare / log artifacts
- `uv` 測試與訓練驗證結果

下一步：

- 進入 `3.2 真實遊戲 wrapper` 的具體 backend 落地

### 2026-03-31

完成內容：

- 修正 `play` 對 config 的硬依賴，恢復 standalone policy 執行能力
- 修正 `resolved_config.json` 與 `summary.final_*`，使其對齊 `final_policy.json`
- 重跑同一個 `output_dir` 時先清掉舊 managed artifacts，避免 phase log 與 phase 檔案混寫
- DQN checkpoint 補上 replay buffer 等 state，讓 rollback 後可延續學習
- 補上對應 regression tests

變更檔案：

- `auto_rl/cli.py`
- `auto_rl/orchestrator.py`
- `auto_rl/training/dqn.py`
- `tests/`
- `README.md`
- `docs/SPEC.md`
- `docs/DECISION_LOG.md`
- `docs/EXECUTION_LOG.md`

產出 artifact：

- 可獨立執行的 `play` 路徑
- 對齊 `final_policy` 的 `resolved_config`
- 更完整的 DQN rollback checkpoint

下一步：

- 回到 `3.2 真實遊戲 wrapper` 的具體 backend 落地

### 2026-03-31

完成內容：

- 參考 `pi-autoresearch`，整理出 AutoRL 可移植的 experiment-management 能力清單
- 將該清單寫入 spec，並在 WBS 中新增 `5.4 Experiment Journal / Confidence / Checks`

變更檔案：

- `docs/SPEC.md`
- `docs/WBS.md`
- `docs/PROJECT_TRACKER.md`
- `docs/DECISION_LOG.md`
- `docs/EXECUTION_LOG.md`

產出 artifact：

- AutoRL 的 autoresearch 管理層規格清單

下一步：

- 在真實遊戲 wrapper 之外，規劃 `5.4` 的實作順序

### 2026-03-31

完成內容：

- 調整 WBS，把 `3.2 真實遊戲 wrapper` 與 `5.4 Experiment Journal / Confidence / Checks` 拆成更可執行的工作包
- 更新近期建議執行順序，改成先補實驗管理層，再推進真實遊戲 backend

變更檔案：

- `docs/WBS.md`
- `docs/PROJECT_TRACKER.md`
- `docs/EXECUTION_LOG.md`

產出 artifact：

- 更可執行的近期工作拆分與排序

下一步：

- 從 `5.4.1 Experiment Journal / Session Doc` 開始落地

### 2026-03-31

完成內容：

- 完成 `5.4 Experiment Journal / Confidence / Checks`
- 新增 append-only `experiment_journal.jsonl` 與可續跑的 `experiment_session.md`
- 將 benchmark metric 與 correctness checks 分離，並把 confidence scoring 接進 researcher 判斷
- 加入 runtime / rollback / failed-check budget controls
- 讓 session doc 在 run 開始就建立，並在每個 phase 後刷新
- 補上對應單元測試，並重新驗證 train / play artifact

變更檔案：

- `auto_rl/orchestrator.py`
- `auto_rl/experiment_management.py`
- `auto_rl/training/metrics.py`
- `auto_rl/researcher/heuristic.py`
- `auto_rl/config.py`
- `schemas/phase_metrics.schema.json`
- `configs/baseline.json`
- `tests/`
- `README.md`
- `docs/SPEC.md`
- `docs/WBS.md`
- `docs/PROJECT_TRACKER.md`
- `docs/DECISION_LOG.md`
- `docs/EXECUTION_LOG.md`

產出 artifact：

- `experiment_journal.jsonl`
- `experiment_session.md`
- 含 `benchmark` / `checks` / `journal_event_id` 的 phase metrics
- 含 `run_id` / `objective` 的 summary 與 phase log

下一步：

- 專注落地 `3.2.2 emulator_capture` backend
