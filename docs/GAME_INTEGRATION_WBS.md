# Game Integration WBS

## 1. 目的

本文件拆解目標 Android 遊戲的實作工作，作為 [GAME_INTEGRATION_SPEC.md](/mnt/d/project/autoRL/docs/GAME_INTEGRATION_SPEC.md) 的執行對應。

## 2. Work Breakdown Structure

### 1. 遊戲契約凍結

#### 1.1 Action 定義

- 定義 action labels
- 定義點擊區域與觸控 macro
- 定義 action duration / repeat 規則

狀態：

- 待做

#### 1.2 Observation 定義

- 定義截圖解析度
- 定義 ROI
- 定義 preprocessing 與 frame stack
- 定義 preprocessing version

狀態：

- 待做

#### 1.3 Outcome 定義

- 定義過關畫面條件
- 定義失敗畫面條件
- 定義 stuck / timeout 規則
- 定義 reset 起點

狀態：

- 待做

### 2. 手機端控制層

#### 2.1 Device Control Protocol

- 定義 `get_observation`
- 定義 `perform_action`
- 定義 `reset_episode`
- 定義 `get_status`
- 定義 artifact 與 config 命令

交付物：

- [GAME_DEVICE_PROTOCOL.md](/mnt/d/project/autoRL/docs/GAME_DEVICE_PROTOCOL.md)

依賴：

- 1.1
- 1.2
- 1.3

狀態：

- 待做

#### 2.2 Android Controller App

- 實作截圖能力
- 實作觸控 / gesture 注入
- 實作 reset / recovery
- 實作本地 service 或 IPC

依賴：

- 2.1

狀態：

- 待做

#### 2.3 Artifact 管理

- 保存 frames
- 保存 replay
- 保存 metrics
- 保存 debug logs

依賴：

- 2.2

狀態：

- 待做

### 3. 手機端 RL Runtime

#### 3.1 Runtime 選型

- 決定使用 Python / Termux / 內嵌 runtime / 其他方案
- 評估與 controller app 的整合方式
- 凍結 deployment 方式

依賴：

- 2.1

狀態：

- 待做

#### 3.2 On-Device RL Loop

- 載入 policy 與 config
- 呼叫 controller protocol 取得 observation
- 輸出 action
- 執行 update
- 保存 checkpoint

依賴：

- 2.2
- 3.1

狀態：

- 待做

#### 3.3 Replay Logger

- 寫出 transition logs
- 寫出 episode summary
- 記錄 `policy_version`
- 對齊 artifact 目錄結構

依賴：

- 2.3
- 3.2

狀態：

- 待做

### 4. 桌面端 Orchestration

#### 4.1 ADB Transport

- 啟動 / 停止手機端訓練
- 推送 config
- 推送 policy
- 拉取 metrics / replay / checkpoints

依賴：

- 2.3
- 3.2

狀態：

- 待做

#### 4.2 Desktop Integration

- 將手機 artifact 接回現有專案輸出流
- 決定 summary / phase metrics 對齊方式
- 串接現有 orchestrator 或新增 mobile runner

依賴：

- 4.1

狀態：

- 待做

### 5. 研究層

#### 5.1 Researcher Boundary

- 限制 researcher 只在 phase 邊界介入
- researcher 不碰 step-level control
- researcher 只讀 artifact、寫 config / policy

依賴：

- 4.2

狀態：

- 待做

#### 5.2 LLM 調參流程

- 拉取手機 phase metrics
- 產生下一輪 config
- 推送回手機
- 重新啟動或續跑訓練

依賴：

- 5.1

狀態：

- 待做

### 6. 可選模擬器支援

#### 6.1 Same-Protocol Emulator Target

- 評估模擬器是否可跑相同 controller protocol
- 避免再做第二套 wrapper
- 只在有明確收益時實作

依賴：

- 2.1
- 2.2
- 4.1

狀態：

- 待做

## 3. 建議執行順序

1. `1.1`、`1.2`、`1.3`
2. `2.1`、`2.2`、`2.3`
3. `3.1`、`3.2`、`3.3`
4. `4.1`、`4.2`
5. `5.1`、`5.2`
6. `6.1`
