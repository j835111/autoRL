# Game Device Protocol

## 1. 目的

本文件定義 `device control app <-> RL runtime` 的第一版本地協定。

這份文件是 [GAME_INTEGRATION_SPEC.md](/mnt/d/project/autoRL/docs/GAME_INTEGRATION_SPEC.md) 的補充文件，目標是讓 Android controller app 與 on-device RL runtime 可以並行實作，而不必先綁死在同一份程式碼裡。

## 2. 設計原則

1. 先固定語意，再決定實際 IPC 技術。
2. 協定以 request / response 為主，必要時再補 event stream。
3. 每個命令都要可記錄、可重播、可偵錯。
4. controller app 負責裝置控制與畫面取得，不負責 RL 邏輯。
5. RL runtime 負責訓練與推論，不直接呼叫 Android input API。

## 3. 傳輸層

第一版不強制指定實作，但需支援下列其中一種：

- app 內 service / binder
- localhost HTTP
- localhost WebSocket
- file-based command queue

無論使用哪種傳輸層，payload 語意都應對齊本文件。

## 4. 通用訊息格式

### 4.1 Request

```json
{
  "request_id": "req-0001",
  "command": "get_observation",
  "timestamp": "2026-04-05T12:00:00Z",
  "payload": {}
}
```

欄位：

- `request_id`: 請求唯一 ID
- `command`: 命令名稱
- `timestamp`: 發送時間
- `payload`: 命令內容

### 4.2 Response

```json
{
  "request_id": "req-0001",
  "ok": true,
  "timestamp": "2026-04-05T12:00:00Z",
  "result": {},
  "error": null
}
```

欄位：

- `request_id`: 對應 request ID
- `ok`: 是否成功
- `timestamp`: 回覆時間
- `result`: 成功結果
- `error`: 失敗資訊

### 4.3 Error

```json
{
  "code": "SCREENSHOT_FAILED",
  "message": "Unable to capture current frame",
  "retryable": true,
  "details": {}
}
```

## 5. 狀態模型

controller app 至少需維護以下狀態：

- `idle`: 尚未進入 episode
- `ready`: 可開始 episode
- `running`: episode 執行中
- `recovering`: 正在 reset / recovery
- `error`: 需人工或上層處理

RL runtime 至少需能辨識：

- 目前裝置是否可接收 action
- 目前是否可取得 observation
- 目前是否可安全 reset episode

## 6. 核心命令

### 6.1 `get_status`

用途：

- 取得 controller app 當前狀態與環境資訊

request payload：

```json
{}
```

result：

```json
{
  "device_state": "ready",
  "game_in_foreground": true,
  "current_episode_id": "ep-0012",
  "last_frame_time": "2026-04-05T12:00:00Z",
  "screen_size": [1080, 2400],
  "preprocess_version": "v1"
}
```

### 6.2 `get_observation`

用途：

- 取得目前 observation 與相關 metadata

request payload：

```json
{
  "include_frame_path": true,
  "include_debug_info": false
}
```

result：

```json
{
  "episode_id": "ep-0012",
  "step_index": 14,
  "observation_ref": "obs://ep-0012/step-0014",
  "frame_path": "/data/user/0/.../frames/ep-0012_step-0014.png",
  "frame_shape": [256, 144, 1],
  "preprocess_version": "v1",
  "timestamp": "2026-04-05T12:00:00Z"
}
```

說明：

- `observation_ref` 可指向記憶體、檔案或快取鍵
- controller app 不必理解 RL state，只需保證 observation 可被 runtime 消費

### 6.3 `perform_action`

用途：

- 執行單一步 action

request payload：

```json
{
  "episode_id": "ep-0012",
  "step_index": 14,
  "action_label": "jump",
  "action_args": {
    "repeat": 1,
    "hold_ms": 120
  },
  "wait_mode": "fixed_delay",
  "wait_ms": 250
}
```

result：

```json
{
  "accepted": true,
  "executed_at": "2026-04-05T12:00:01Z",
  "device_state": "running"
}
```

約束：

- `action_label` 必須來自固定 action contract
- runtime 不可直接傳任意座標作為常規控制方式

### 6.4 `step_transition`

用途：

- 執行 action 後，回傳下一步 transition 所需資訊

這是 `perform_action + get_observation + outcome evaluation` 的複合命令，可作為高頻互動主路徑。

request payload：

```json
{
  "episode_id": "ep-0012",
  "step_index": 14,
  "action_label": "jump",
  "wait_mode": "fixed_delay",
  "wait_ms": 250
}
```

result：

```json
{
  "episode_id": "ep-0012",
  "step_index": 15,
  "observation_ref": "obs://ep-0012/step-0015",
  "frame_path": "/data/user/0/.../frames/ep-0012_step-0015.png",
  "reward": 0.2,
  "done": false,
  "success": false,
  "failure": false,
  "stuck": false,
  "info": {
    "frame_hash": "abc123",
    "outcome_version": "v1"
  }
}
```

說明：

- 若 controller app 已具備 outcome evaluator，建議 RL runtime 優先走此命令
- 若 outcome evaluator 還未完成，可先拆成 `perform_action` 與 `get_observation`

### 6.5 `reset_episode`

用途：

- 把遊戲帶回可訓練起點

request payload：

```json
{
  "reason": "episode_done",
  "force_restart": false
}
```

result：

```json
{
  "episode_id": "ep-0013",
  "device_state": "ready",
  "reset_strategy": "in_game_restart",
  "completed_at": "2026-04-05T12:01:00Z"
}
```

### 6.6 `save_artifacts`

用途：

- 強制 flush 目前 replay、metrics、logs 或 checkpoints

request payload：

```json
{
  "save_replay": true,
  "save_metrics": true,
  "save_debug_frames": false
}
```

result：

```json
{
  "saved": true,
  "artifacts": {
    "replay_path": "/data/user/0/.../replays/ep-0012.jsonl",
    "metrics_path": "/data/user/0/.../metrics/latest.json"
  }
}
```

### 6.7 `load_policy`

用途：

- 讓 runtime 或 controller 對齊目前 policy version

request payload：

```json
{
  "policy_path": "/data/user/0/.../policies/policy_v3.bin",
  "policy_version": "policy_v3"
}
```

result：

```json
{
  "loaded": true,
  "policy_version": "policy_v3"
}
```

### 6.8 `load_training_config`

用途：

- 載入訓練設定或本輪 phase 設定

request payload：

```json
{
  "config_path": "/data/user/0/.../configs/phase_03.json",
  "config_version": "phase_03"
}
```

result：

```json
{
  "loaded": true,
  "config_version": "phase_03"
}
```

## 7. 事件與記錄

第一版至少要記錄：

- 每筆 request / response
- 每次 action 執行
- 每次 reset
- 每次 recovery
- 每次 artifact flush

建議欄位：

- `request_id`
- `episode_id`
- `step_index`
- `command`
- `latency_ms`
- `ok`
- `error_code`

## 8. 版本管理

協定需要版本欄位：

- `protocol_version`
- `action_version`
- `preprocess_version`
- `outcome_version`

原則：

- 任何會影響 replay 可重放性或模型可用性的變更都要升版

## 9. 失敗處理

常見錯誤碼建議：

- `SCREENSHOT_FAILED`
- `ACTION_REJECTED`
- `GAME_NOT_FOREGROUND`
- `RESET_FAILED`
- `RECOVERY_IN_PROGRESS`
- `INVALID_ACTION_LABEL`
- `POLICY_LOAD_FAILED`
- `CONFIG_LOAD_FAILED`
- `INTERNAL_ERROR`

處理原則：

- 可重試錯誤需標示 `retryable=true`
- 不可重試錯誤需讓上層轉入 recovery 或 stop

## 10. 最小落地範圍

第一版實作至少要完成：

1. `get_status`
2. `get_observation`
3. `perform_action`
4. `reset_episode`
5. `save_artifacts`

第二版再補：

1. `step_transition`
2. `load_policy`
3. `load_training_config`
4. 更完整的 event stream 與 debug telemetry
