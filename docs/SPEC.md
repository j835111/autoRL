# AutoRL Specification

## 1. 目的

本專案要建立一個雙層架構的自主學習系統：

- 內層：負責與遊戲環境互動並學習控制策略的 RL agent
- 外層：負責根據訓練結果自動調整超參數的 auto-researcher

核心要求是：

- 外層只在訓練階段參與
- 訓練完成後，內層 agent 必須可以獨立執行
- 外層 researcher 不直接控制遊戲

## 2. 產品目標

### 2.1 主要目標

1. 提供一個可反覆實驗的 RL 訓練框架。
2. 將調參邏輯從內層控制器中分離。
3. 讓外層 researcher 可由規則式邏輯逐步升級到 LLM。
4. 讓訓練產物可保存、可重播、可部署。

### 2.2 非目標

1. 本階段不追求通用 AGI 式自我改寫。
2. 本階段不讓 LLM 直接在遊戲幀級別決策。
3. 本階段不處理大規模分散式訓練。

## 3. 當前範圍

### 3.1 已有原型

- 可訓練的 toy game environment
- 可獨立保存與載入的 tabular Q-learning agent
- phase-based auto-research loop
- CLI train/play 入口
- phase metrics 與 summary 輸出

### 3.2 下一階段範圍

- 鎖定資料介面與 JSON schema
- 將內層從 Q-learning 升級到適合遊戲控制的 DQN
- 保留外層 researcher 的輸入輸出契約不變
- 定義真實遊戲 wrapper 的雙路徑接入方式

### 3.3 真實遊戲 Wrapper 策略

真實遊戲 wrapper 預設有兩種可並存的 backend，兩者共用同一組 `Environment API` 與 action / reward 契約：

#### 路徑 A：直接在手機端執行

定義：

- 內層 policy 直接部署在手機端或與手機端 automation runtime 緊耦合執行
- observation 由手機端直接取得
- action 由手機端直接注入遊戲

適合場景：

- 目標遊戲依賴真機硬體、感測器、網路條件或 anti-emulator 機制
- 最終部署目標本來就是手機端常駐執行
- 需要驗證真機延遲、解析度、觸控行為與 app lifecycle

優點：

- 與真實執行環境最接近
- 可避免 emulator domain gap
- 最終部署路徑最短

缺點：

- 訓練吞吐量低
- 偵錯、重置、快照回復、批次實驗都較困難
- 必須處理權限、前背景切換、熱節流、電量、通知干擾等裝置問題

必要能力：

- 手機端 observation capture
- 手機端 action injection
- app lifecycle recovery
- 安全停機與前景檢查
- 訓練或推論紀錄回傳機制

#### 路徑 B：抓取模擬器畫面來執行

定義：

- 遊戲跑在模擬器
- wrapper 從桌面端抓取模擬器畫面、OCR / UI 特徵或狀態訊號
- wrapper 從桌面端注入點擊、滑動、按鍵等動作

適合場景：

- 需要快速迭代 reward shaping、action mapping、DQN 架構與 researcher 策略
- 需要可重現、可快照、可回退的訓練環境
- 需要大量 phase / config compare

優點：

- 便於自動化、快照、重置與批量實驗
- 訓練吞吐量與可觀測性通常優於真機
- 比較容易做 fail recovery、畫面錄製與 phase replay

缺點：

- 與真機存在 domain gap
- 可能遇到 emulator 專屬效能問題或遊戲偵測限制
- observation latency 與 input timing 未必等於真機

必要能力：

- 穩定的畫面抓取管線
- 模擬器控制介面或桌面輸入注入
- 快照重置 / crash recovery
- 視窗焦點與解析度一致性保證

#### 建議採用順序

1. 先以「模擬器畫面抓取」完成訓練閉環、reward shaping、DQN 調參與 researcher 驗證。
2. 再以「手機端直接執行」做真機驗證、長時間穩定性測試與最終部署。
3. 若目標遊戲明確封鎖模擬器，或核心訊號只有真機可取得，則改成手機端優先，但仍保留桌面側資料回傳與分析能力。

結論：

- 本專案 architecture 應先抽出 backend-neutral wrapper 契約。
- M3 以前優先推進模擬器 backend，因為它更利於 DQN 訓練與 rollback。
- 手機端 backend 作為 M5 的真實部署路徑與 acceptance path，而不是一開始就承擔所有研究成本。

### 3.4 AutoResearch 可移植清單

參考 `pi-autoresearch` 這類 autonomous experiment loop 專案後，本專案可直接借用的不是 RL 核心，而是「外層實驗管理層」的能力。可移植清單如下：

1. append-only experiment journal

- 將每次 phase / run / compare 的結果持續追加到單一 journal，而不只保留最新 summary
- 適合保存 metric、status、policy 路徑、checkpoint、rollback、stop reason、研究者理由
- 目的不是取代 `summary.json`，而是提供可追溯、可續跑的完整實驗歷史

2. session document

- 除了 machine-readable JSONL，還保留一份 human-readable 的研究文件
- 記錄目標、目前 metric、已嘗試方法、死路、已知有效設定、下一步假設
- 讓新的 agent 或新接手的人可以不靠聊天上下文續跑

3. benchmark 與 correctness checks 分離

- 將「要優化的 metric」與「不得破壞的約束」拆成兩條路徑
- 例如 reward / success rate / throughput 屬於 benchmark
- schema validation、policy load、wrapper smoke test、回放正確性屬於 checks
- researcher 只能在 benchmark 改善且 checks 通過時保留變更

4. noise floor / confidence scoring

- 對 phase 結果加入 noise-aware 解讀，而不是只看單次 improvement
- 可用 MAD、rolling variance 或 repeated evaluation 估計 noise floor
- 外層 researcher 應區分「明顯改善」與「可能只是噪音」

5. experiment budget controls

- 對自主研究循環加入明確的 budget，例如最大 phase 數、最大 wall-clock、最大 rollback 次數、最大無效嘗試次數
- 避免 outer loop 在真實遊戲場景消耗過多時間或裝置資源

6. resume semantics

- 實驗中斷後，系統應可只靠 journal、session doc 與 artifact 恢復狀態
- 不應依賴單一 agent 的短期記憶

7. result finalization

- 將「實驗歷史」與「可交付產物」分開
- 前者保留噪音、失敗與 rollback 過程
- 後者只保留可部署的 policy、對齊的 config 與可審計摘要

採用原則：

- 以上能力屬於 orchestration / observability / experiment management 層
- 不直接替代 inner RL、game wrapper 或 researcher schema
- 本版本已落地 `experiment journal + session doc + checks split + confidence scoring + budget controls`，後續重點回到真實遊戲 wrapper backend

## 4. 系統架構

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
Next Experiment Params
```

### 4.1 模組責任

`auto_rl/config.py`

- 載入實驗設定
- 管理 env、agent、training、research 四類設定

`auto_rl/envs/`

- 提供標準化遊戲環境介面
- 輸出 state、reward、done、success 等訊號
- 隱藏真實遊戲 backend 差異

`auto_rl/training/`

- 內層 agent 訓練與推論
- phase / episode 指標整理
- 保存 deployable policy artifact

`auto_rl/researcher/`

- 根據 phase metrics 產生下一輪超參數
- 支援 heuristic 與 LLM researcher

`auto_rl/orchestrator.py`

- 負責整個 outer loop
- 執行訓練、評估、選 best policy、保存報表
- 管理可續跑的實驗狀態與 artifact 語意

### 4.2 真實遊戲 Wrapper 分層

真實遊戲 wrapper 不應直接把「抓畫面」和「算 reward」寫死在同一層，建議拆成下面五層：

1. `Runtime Backend`

- `device_local`: 手機端直接執行
- `emulator_capture`: 模擬器畫面抓取執行

2. `Observation Extractor`

- 將原始畫面、UI tree、OCR 或 telemetry 轉成 RL state
- 必須保證跨 backend 的 observation 語意一致

3. `Action Dispatcher`

- 將離散 action id 映射成點擊、滑動、按鍵或 macro
- 避免直接讓 agent 輸出任意座標流

4. `Reward / Outcome Evaluator`

- 根據畫面、UI、戰鬥結果或任務進度計算 reward
- 定義 success / fail / stuck 條件

5. `Session Controller`

- 負責啟動、重置、回主畫面、錯誤恢復、超時退出
- 是 rollback、phase compare、實驗重播的基礎

這樣做的原因是：

- backend 可以替換，但 RL 介面不必改
- reward shaping 與 action mapping 可以獨立迭代
- 後續從 emulator 過渡到 device local 時，主要替換的是 backend 與 session controller，而不是整個 agent stack

## 5. 核心流程

### 5.1 訓練流程

1. 讀取 `ExperimentConfig`
2. 初始化 environment、inner RL agent、researcher
3. 執行一個 phase 的訓練 episodes
4. 執行一個 phase 的 evaluation episodes
5. 產生 `phase_metrics.json`
6. 外層 researcher 讀取 phase metrics 並輸出下一輪參數
7. orchestrator 更新 config
8. 重複直到 phase 結束
9. 保存 `best_policy`、`final_policy`、`summary`

### 5.2 推論流程

1. 載入保存好的 policy artifact
2. 建立對應 environment
3. 以 greedy / deterministic policy 執行
4. 不依賴 researcher
5. 不要求 `ExperimentConfig` 或既有輸出目錄存在

### 5.3 Autoresearch 管理流程

在 phase-based RL 之外，實驗管理層目前採用下面流程：

1. 寫入 `run_start` metadata 與 append-only journal
2. 執行 phase 訓練與 evaluation
3. 將 benchmark metric 與 correctness checks 分開計算
4. 只有在 checks 通過時，benchmark 改善才可被接受為 deployable 結果
5. 用 noise floor 與 confidence score 協助 researcher 判斷改善是否顯著
6. 每 phase 寫入 `phase_log.jsonl`、`experiment_journal.jsonl` 與 `experiment_session.md`
7. 套用 wall-clock、rollback、failed-check budget controls
8. 收斂出 `best_policy`、`final_policy`、`summary` 與 `resolved_config`

這一層不是替代 researcher，而是讓 researcher 的決策基礎更可審計。

## 6. 介面規格

### 6.1 Environment API

所有環境都應提供下列能力：

- `reset() -> state`
- `step(action) -> StepResult`
- `render() -> str | frame`
- `action_size`

`StepResult` 最少包含：

- `state`
- `reward`
- `done`
- `success`
- `hit_trap` 或等價失敗標記

說明：

- `state` 可以是 symbolic state、feature vector、影像 embedding，或畫面經過 extractor 後的結構化結果
- 對 toy env 來說可用字串 state
- 對真實遊戲 wrapper 來說，應優先輸出固定長度 feature 或可穩定序列化的 observation

### 6.1.1 Real Game Wrapper Contract

真實遊戲 wrapper 除了滿足 `Environment API`，還必須額外定義：

- `observation format`
- `action mapping`
- `reward shaping`
- `success condition`
- `failure / stuck condition`
- `reset / recovery strategy`

其中 `action mapping` 原則如下：

- 以有限、可審計的離散動作為主
- 可以是 tap region、swipe macro、button macro
- 不建議一開始就用自由座標連續控制

其中 `observation format` 原則如下：

- emulator 與 phone backend 應產出同語意 observation
- 若無法完全一致，必須明確標記 domain-specific features
- observation extractor 應可被單獨測試

### 6.2 Inner Agent API

所有內層 agent 都應提供：

- `select_action(state, explore=True)`
- `update(state, action, reward, next_state, done)`
- `end_episode()`
- `save(path, env_config, action_labels)`
- `load(path)`

### 6.3 Phase Metrics Contract

每個 phase 都必須輸出結構化報表，供 researcher 使用。

必要欄位：

- `phase_index`
- `training.avg_reward`
- `training.success_rate`
- `training.avg_steps`
- `training.mean_td_error`
- `training.final_epsilon`
- `evaluation.avg_reward`
- `evaluation.success_rate`
- `evaluation.avg_steps`
- `learning_rate`
- `gamma`
- `epsilon_start`
- `epsilon_decay`
- `episodes_per_phase`
- `benchmark`
- `checks`
- `adjustments`
- `journal_event_id`

正式 schema 見 [schemas/phase_metrics.schema.json](/mnt/d/project/autoRL/schemas/phase_metrics.schema.json)。

### 6.4 Researcher Output Contract

外層 researcher 只允許調整：

- `learning_rate`
- `gamma`
- `epsilon_start`
- `epsilon_min`
- `epsilon_decay`
- `episodes_per_phase`

可選輔助欄位：

- `rationale`
- `stop_training`
- `rollback_to_best`

不允許 researcher 直接輸出任意程式碼作為訓練主流程的一部分。

正式 schema 見 [schemas/researcher_adjustments.schema.json](/mnt/d/project/autoRL/schemas/researcher_adjustments.schema.json)。

## 7. Artifact 規格

### 7.1 訓練輸出

每次完整訓練至少輸出：

- `best_policy.json`
- `final_policy.json`
- `summary.json`
- `resolved_config.json`
- `experiment_metadata.json`
- `experiment_journal.jsonl`
- `experiment_session.md`
- `phase_XX_metrics.json`
- `phase_log.jsonl`

語意要求：

- `final_policy.json` 與 `resolved_config.json` 必須描述同一個最後實際完成訓練的 agent 狀態
- 若最後一個 phase 產生了「下一輪建議參數」，該建議只能作為 summary 附帶資訊，不能覆蓋 `resolved_config.json`
- `summary.json` 應保留 `run_id`、`objective` 與 `suggested_next_*`，供後續續跑或審計使用
- `experiment_journal.jsonl` 必須是 append-only，保留跨 run 歷史
- `experiment_session.md` 必須在 run 開始時建立，並在每個 phase 後刷新，讓中途中斷仍可恢復上下文
- 若重複使用同一個 `output_dir`，本輪開始前必須清除本系統管理的舊 phase artifact、checkpoint 與 phase log，避免不同 run 混寫
- append-only journal 必須與「本輪 managed artifacts」語意區分清楚，不能因清理輸出目錄而被截斷

### 7.2 Deployable Policy 要求

保存的 policy artifact 必須包含：

- 演算法標記
- environment 配置
- agent 配置
- 推論所需權重或表格
- action labels

要求：

- 載入 policy 後即可直接執行推論
- 不需要 researcher 參與
- 不需要原始 training config 存在
- 若用於 rollback checkpoint，需保留足夠的 agent state 讓訓練可以延續

## 8. 功能需求

### 8.1 必要功能

1. 可執行 phase-based 訓練。
2. 可在 phase 結束後做自動調參。
3. 可保存最佳與最終策略。
4. 可重播已保存策略。
5. 可輸出供 heuristic 或 LLM 使用的結構化報表。
6. 可區分 benchmark metric 與 correctness checks。

### 8.2 預留功能

1. 將內層 agent 換成 DQN / PPO。
2. 接入實際 LLM provider。
3. 將環境換成實際遊戲 wrapper。
4. 補上更完整的 resume CLI / long-running automation orchestration。

### 8.3 真實遊戲 Wrapper 功能要求

1. 至少支援一個 `backend-neutral` 的 wrapper 介面。
2. 支援 `device_local` 與 `emulator_capture` 兩種 backend 的擴充。
3. reward shaping 與 observation extraction 必須可獨立替換。
4. action space 必須離散化並可記錄。
5. wrapper 必須提供 reset / recovery 能力，否則 outer loop 無法穩定運作。

### 8.4 實驗管理層功能要求

1. 支援 append-only experiment journal。
2. 支援 session document，讓中斷後可續跑。
3. 支援 benchmark 與 correctness checks 分離。
4. 支援 noise-aware confidence scoring。
5. 支援實驗預算控制，例如 phase cap、wall-clock cap、rollback cap、failed-check cap。

## 9. 非功能需求

1. 可重現：同 seed 下結果應盡量穩定。
2. 可擴充：researcher 與 inner agent 必須解耦。
3. 可觀測：每個 phase 必須有結構化輸出。
4. 可部署：內層最終產物不得依賴外層。
5. 可約束：researcher 輸出必須可驗證。
6. 可轉移：emulator 與 phone backend 必須盡量共享 observation / action contract。
7. 可恢復：真實遊戲 session 發生 crash、卡死、背景化時，wrapper 必須能恢復或安全退出。
8. 可續跑：自主研究循環中斷後，應能依賴 artifact 恢復上下文。

## 10. 里程碑與驗收

### M1: Prototype Contract Freeze

驗收條件：

- 完成 spec
- 完成 WBS
- 完成 metrics / researcher JSON schema

### M2: Inner RL Upgrade

驗收條件：

- 內層改為 DQN 或等價遊戲控制方法
- 保持可保存與獨立推論
- `play` 模式可用

### M3: Researcher Hardening

驗收條件：

- heuristic researcher 可穩定運作
- researcher 調參有 schema 驗證

### M4: LLM Researcher Integration

驗收條件：

- LLM researcher 有 prompt bridge
- JSON output 可解析、驗證與 fallback

### M5: Real Game Integration

驗收條件：

- 真實遊戲 wrapper 可接到訓練流程
- 至少有一條 backend 路徑可跑 train / play
- 內層最終 policy 仍可獨立部署
