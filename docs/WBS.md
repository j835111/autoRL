# AutoRL WBS

## 1. WBS 目的

本 WBS 用來把 `plan -> spec -> implementation` 拆成可交付、可驗收、可排序的工作項目。

## 2. Work Breakdown Structure

### 1. 專案基礎

#### 1.1 專案結構整理

- 建立 `auto_rl/` 模組結構
- 建立 `configs/`、`outputs/`、`docs/`、`schemas/`
- 建立 CLI 入口

交付物：

- 可執行的專案骨架

狀態：

- 已完成

#### 1.2 規格與契約凍結

- 撰寫 spec
- 撰寫 WBS
- 定義 metrics schema
- 定義 researcher schema

交付物：

- [docs/SPEC.md](/mnt/d/project/autoRL/docs/SPEC.md)
- [docs/WBS.md](/mnt/d/project/autoRL/docs/WBS.md)
- [schemas/phase_metrics.schema.json](/mnt/d/project/autoRL/schemas/phase_metrics.schema.json)
- [schemas/researcher_adjustments.schema.json](/mnt/d/project/autoRL/schemas/researcher_adjustments.schema.json)

依賴：

- 1.1

完成條件：

- researcher 與 orchestrator 的輸入輸出語意固定

狀態：

- 已完成

### 2. 內層 RL 系統

#### 2.1 Baseline 內層 agent

- 實作 tabular Q-learning baseline
- 實作 policy 保存與載入
- 實作 `play` 模式

交付物：

- 可獨立執行的 baseline policy

狀態：

- 已完成

#### 2.2 Agent 抽象化

- 抽出統一的 inner agent 介面
- 將現有 Q-learning 對齊同一個抽象
- 為 DQN 預留相同儲存 / 載入介面

依賴：

- 1.2

完成條件：

- orchestrator 不必依賴特定演算法細節

狀態：

- 已完成

#### 2.3 DQN 升級

- 引入神經網路版本 inner agent
- 支援 epsilon-greedy 探索
- 支援 target network / replay buffer
- 可保存 deployable 權重

依賴：

- 2.2

完成條件：

- 遊戲控制場景不再依賴表格式 state

狀態：

- 已完成

### 3. 環境與任務層

#### 3.1 Toy Environment

- 建立 grid game 環境
- 定義成功、失敗、牆、陷阱、距離 shaping reward

交付物：

- 可穩定測試 auto-research 閉環的最小環境

狀態：

- 已完成

#### 3.2 真實遊戲 wrapper

- 定義 observation 格式
- 定義 action mapping
- 定義 reward shaping
- 定義 success / fail 條件

依賴：

- 2.3

完成條件：

- 實際遊戲可被 inner RL 訓練與推論

狀態：

- 部分完成

#### 3.2.1 Backend-neutral wrapper 契約

- 固定 `device_local` 與 `emulator_capture` 共用的 `Environment API`
- 定義 runtime backend、observation extractor、action dispatcher、reward evaluator、session controller 分層
- 保持 orchestrator 與 inner agent 不依賴具體 backend

依賴：

- 2.3

完成條件：

- 真實遊戲接入時只需替換 backend 與 wrapper 細節，不需重寫 RL 主流程

狀態：

- 已完成

#### 3.2.2 `emulator_capture` backend

- 接入模擬器畫面抓取
- 接入桌面端 action injection
- 實作 snapshot reset / crash recovery
- 定義第一版 observation extractor 與 reward evaluator

依賴：

- 3.2.1

完成條件：

- 可在模擬器上穩定跑完整 train / evaluate / play 閉環

狀態：

- 待做

#### 3.2.3 `device_local` backend

- 接入手機端 observation capture
- 接入手機端 action injection
- 處理前背景切換、權限、恢復與安全停機
- 驗證與 emulator backend 的 observation / action 契約對齊

依賴：

- 3.2.1
- 3.2.2

完成條件：

- 可在真機上穩定回放已訓練 policy，並支援驗證流程

狀態：

- 待做

#### 3.2.4 Observation / Reward 對齊

- 對齊 emulator 與 phone backend 的 observation 語意
- 定義 domain-specific feature 差異
- 校正 reward shaping、success / fail / stuck 條件

依賴：

- 3.2.2
- 3.2.3

完成條件：

- 同一份 researcher 與 inner agent 契約可跨兩種 backend 使用

狀態：

- 待做

### 4. 外層 Researcher

#### 4.1 Heuristic Researcher

- 根據 reward、success rate、epsilon、td error 調整超參數
- 控制 learning rate / gamma / epsilon / phase 長度

交付物：

- 第一版可控、可追蹤的 auto-researcher

狀態：

- 已完成

#### 4.2 Researcher 輸出驗證

- 對 researcher 輸出做 schema 驗證
- 限制可調整欄位
- 對不合法輸出做 fallback

依賴：

- 1.2

完成條件：

- 任何 researcher 輸出都可被安全解析

狀態：

- 已完成

#### 4.3 LLM Researcher

- 建 prompt template
- 建 JSON-only output 約束
- 建 parse / validate / fallback 流程
- 接進 orchestrator

依賴：

- 4.2

完成條件：

- LLM 可在 phase 間安全調參

狀態：

- 已完成

### 5. Orchestration 與實驗管理

#### 5.1 Phase 報表與摘要

- 每 phase 輸出 metrics JSON
- 輸出 final summary
- 保留 best 與 final policy

狀態：

- 已完成

#### 5.2 Checkpoint / Compare / Rollback

- 保存 phase checkpoints
- 提供 best model compare
- 支援回退上一個較佳設定

依賴：

- 5.1

完成條件：

- auto-research 不再只有線性向前，而可回退

狀態：

- 已完成

#### 5.3 Early Stop / Stop Criteria

- 定義收斂與停止條件
- 支援 researcher 建議停止

依賴：

- 5.2

完成條件：

- 訓練資源使用更可控

狀態：

- 已完成

#### 5.4 Experiment Journal / Confidence / Checks

- 建立 append-only experiment journal
- 建立可續跑的 session document
- 分離 benchmark metric 與 correctness checks
- 加入 noise-aware confidence scoring
- 加入實驗預算控制

依賴：

- 5.1, 5.2, 5.3

完成條件：

- 中斷後可依賴 journal 與 session doc 恢復實驗上下文
- researcher 不再只依賴單次 phase 改善，而有 confidence 依據
- keep / rollback 決策有 benchmark 與 checks 雙重依據

狀態：

- 已完成

#### 5.4.1 Experiment Journal / Session Doc

- 建立 append-only experiment journal
- 建立可續跑的 session document
- 定義 run、phase、checkpoint、rollback、stop 的記錄欄位

依賴：

- 5.1

完成條件：

- 實驗中斷後可只靠 artifact 恢復上下文

狀態：

- 已完成

#### 5.4.2 Benchmark / Checks Split

- 分離 benchmark metric 與 correctness checks
- 定義 keep / rollback / reject 的判斷順序
- 將 schema validation、policy load、wrapper smoke test 納入 checks

依賴：

- 5.1
- 5.2

完成條件：

- researcher 不會因單一 metric 改善而保留破壞 correctness 的變更

狀態：

- 已完成

#### 5.4.3 Confidence Scoring

- 加入 noise-aware confidence scoring
- 定義 noise floor 估計方式，例如 MAD、rolling variance 或 repeated evaluation
- 將 confidence 結果暴露給 researcher 與 summary

依賴：

- 5.4.1
- 5.4.2

完成條件：

- researcher 可區分顯著改善與可能噪音

狀態：

- 已完成

#### 5.4.4 Budget / Resume / Finalization

- 加入 experiment budget controls
- 定義 resume semantics
- 區分實驗歷史 artifact 與最終交付 artifact

依賴：

- 5.4.1
- 5.4.2
- 5.4.3

完成條件：

- 長時間 autoresearch 可控、可續跑、可收斂成可交付結果

狀態：

- 已完成

### 6. 可觀測性與品質

#### 6.1 日誌與追蹤

- phase log
- experiment metadata
- 調參原因追蹤

狀態：

- 已完成

#### 6.2 測試

- config 載入測試
- policy 保存 / 載入測試
- metrics schema 測試
- researcher output validation 測試

依賴：

- 1.2, 2.2, 4.2

完成條件：

- 核心介面有最小單元測試保護

狀態：

- 已完成

## 3. 關鍵依賴

1. `1.2 規格與契約凍結` 是後續 DQN、LLM researcher、真實遊戲 wrapper 的前置條件。
2. `2.2 Agent 抽象化` 是 `2.3 DQN 升級` 的前置條件。
3. `4.2 Researcher 輸出驗證` 是 `4.3 LLM Researcher` 的前置條件。
4. `5.2 Checkpoint / Compare / Rollback` 會直接影響外層 researcher 的可控性。
5. `3.2.1 Backend-neutral wrapper 契約` 是 `3.2.2` 與 `3.2.3` 的前置條件。
6. `5.4.*` 已完成，現在作為真實遊戲長迴圈的可觀測性與可控性基礎。
7. `3.2.2 emulator_capture` 建議先於 `3.2.3 device_local` 完成。

## 4. 近期建議執行順序

1. 實作 `3.2.2 emulator_capture` backend
2. 再做 `3.2.3 device_local` backend
3. 最後收斂 `3.2.4 Observation / Reward 對齊`

## 5. 近期交付重點

非遊戲 wrapper 的長迴圈研究能力已補齊，短期重點回到真實遊戲接入：

1. `emulator_capture` backend 的 train / evaluate / play 閉環
2. `device_local` backend 的 replay / validation 路徑
3. emulator 與 phone backend 的 observation / reward 對齊
