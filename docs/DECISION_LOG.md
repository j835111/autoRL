# AutoRL Decision Log

## 1. 用途

記錄會影響架構、流程或後續實作方向的重要決策，避免之後只記得結論、不記得理由。

## 2. 使用方式

每條決策建議至少包含：

- `Decision ID`
- `Date`
- `Status`
- `Context`
- `Decision`
- `Consequence`

## 3. 決策紀錄

### D-001

- Date: 2026-03-30
- Status: Accepted
- Context: 專案的目標是「外層調參、內層獨立部署」，不是讓 LLM 即時操控遊戲。
- Decision: 外層 researcher 只在訓練階段參與，不直接控制遊戲執行。
- Consequence: 推論時只需要載入內層 policy artifact，不需要 researcher。

### D-002

- Date: 2026-03-30
- Status: Accepted
- Context: 若先接 LLM，再回頭修接口，成本會很高。
- Decision: 先凍結 phase metrics 與 researcher output 的資料契約，再升級內層或接 LLM。
- Consequence: 後續 DQN、LLM researcher、真實遊戲 wrapper 都必須遵守既有 schema。

### D-003

- Date: 2026-03-30
- Status: Accepted
- Context: baseline 尚未穩定時，LLM 調參容易放大不穩定性。
- Decision: 先用 heuristic researcher 驗證 outer loop，再導入 LLM。
- Consequence: LLM integration 不是當前第一優先，而是 M4 任務。

### D-004

- Date: 2026-03-30
- Status: Accepted
- Context: 內層最終必須脫離外層獨立執行。
- Decision: 所有可部署 policy artifact 都必須攜帶推論所需配置與權重，不依賴 researcher。
- Consequence: save/load 介面在後續 DQN 版本也必須保留。

### D-005

- Date: 2026-03-30
- Status: Accepted
- Context: 執行追蹤若只靠聊天紀錄，後續接手的人很難知道目前狀態。
- Decision: 補上 Project Tracker、Decision Log、Risk Register、Execution Log 四類追蹤文件。
- Consequence: 後續每次重要變更都應同步更新這些文件。

### D-006

- Date: 2026-03-30
- Status: Accepted
- Context: 專案需要可重現的執行與測試流程，直接用 `python` 容易讓命令與環境狀態脫節。
- Decision: 專案統一改用 `uv` 管理環境、CLI 與測試執行。
- Consequence: 後續 README、驗證流程與交付命令一律以 `uv run ...` 為準。

### D-007

- Date: 2026-03-30
- Status: Accepted
- Context: 真實遊戲 wrapper 同時存在「手機端直接執行」與「模擬器畫面抓取」兩條路徑，若不先抽象 backend，之後很容易重做 observation / action / reward 契約。
- Decision: 先定義 backend-neutral wrapper contract，再把 `device_local` 與 `emulator_capture` 視為兩種 runtime backend。
- Consequence: 後續真實遊戲接入時，優先替換 backend 與 session controller，而不是重寫 orchestrator 或 agent API。

### D-008

- Date: 2026-03-30
- Status: Accepted
- Context: toy env 需要一條可實際成功的 DQN baseline，否則 M2 只算功能存在，不算可交付。
- Decision: 保留 Q-learning 作為相容 baseline，同時將預設 baseline config 切到已驗證成功的 DQN 參數。
- Consequence: 預設 `configs/baseline.json` 現在以 DQN 為主，`play` / save / load 都需兼容兩種 agent。

### D-009

- Date: 2026-03-31
- Status: Accepted
- Context: `play` 一度回退成依賴 `configs/baseline.json`，且 `resolved_config.json`、phase log、DQN rollback checkpoint 的語意不夠嚴謹。
- Decision: `play` 必須可只靠 policy artifact 獨立執行；`resolved_config.json` 必須對齊 `final_policy.json`；重跑同一個 `output_dir` 時要清理舊 managed artifacts；DQN checkpoint 必須保存 replay state 以支援 rollback 後延續學習。
- Consequence: CLI、orchestrator、DQN snapshot 與文件語意都必須以可部署性與可重現性為優先。

### D-010

- Date: 2026-03-31
- Status: Accepted
- Context: `pi-autoresearch` 這類專案對 AutoRL 有參考價值，但重點在 autonomous experiment management，不在 RL agent 或遊戲 wrapper 本身。
- Decision: 將其可移植能力吸收到 AutoRL 的 orchestration / observability 層，優先考慮 experiment journal、session doc、checks split、confidence scoring 與 budget controls。
- Consequence: 後續若要借鑑外部 autoresearch 專案，應先映射到實驗管理層，而不是直接改寫 inner RL 或真實遊戲 backend。

### D-011

- Date: 2026-03-31
- Status: Accepted
- Context: 若 experiment journal、session doc 與 checks gate 只在 run 結束時產生，實驗一旦中途中斷，就無法只靠 artifact 恢復上下文，也無法嚴格區分「benchmark 變好」與「結果可部署」。
- Decision: 將 `experiment_journal.jsonl`、`experiment_session.md` 與 `benchmark/checks split` 視為第一級 artifact；session doc 必須從 run 開始就建立並在每 phase 後刷新；benchmark 改善只有在 checks 通過時才可被接受為 deployable 結果。
- Consequence: `summary`、`phase_log`、phase metrics 與 journal 必須攜帶足夠的 run/phase 對齊資訊，且 append-only journal 不能因重跑同一路徑而被清空。
