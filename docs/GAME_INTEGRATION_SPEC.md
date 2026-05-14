# Game Integration Specification

## 1. 目的

本文件專門描述目標 Android 遊戲的 RL 串接方案。

這份文件的定位是子規格，不取代專案總體 [SPEC.md](/mnt/d/project/autoRL/docs/SPEC.md)。總體規格仍描述整個 AutoRL 架構；本文件只處理單一遊戲整合。

裝置內部控制協定另見 [GAME_DEVICE_PROTOCOL.md](/mnt/d/project/autoRL/docs/GAME_DEVICE_PROTOCOL.md)。

## 2. 架構決策

本次遊戲串接不再採用「模擬器 wrapper 一套、手機 wrapper 一套」的雙路徑設計，而是統一為手機端單一路徑：

- 手機上有一個 `device control app`
- `device control app` 統一負責觸控注入、截圖、reset / recovery、artifact 管理
- RL runtime 也在手機上執行
- RL runtime 不直接操作 Android input API，而是透過 `device control app` 溝通
- 外層 researcher / orchestrator 只在 phase 邊界透過 `adb` 或等價 transport 與手機互動
- 若之後要支援模擬器，也應盡量跑同一套手機端協定，而不是再做第二套 wrapper

## 3. 已知前提

- 目標遊戲無法提供 API、記憶體狀態或其他結構化資料
- observation 只能來自螢幕截圖
- action 只能透過觸控操作
- 遊戲主要執行環境是 Android 手機
- 外層調參或 artifact 收集由桌面端透過 `adb` 類通道處理
- 模擬器若使用，定位是同協定 target，而不是獨立 backend

## 4. 目標

1. 建立 screenshot-to-action 的 RL 訓練閉環。
2. 把 step-level 遊戲控制統一收斂到手機端 `device control app`。
3. 讓 RL runtime 也在手機上執行，避免桌面端直接控制遊戲。
4. 讓外層 researcher 只做 config / artifact / lifecycle orchestration。
5. 保留未來讓模擬器跑同一套協定的空間。

## 5. 系統分層

### 5.1 Device Control App

執行位置：

- Android 手機

責任：

- 擷取畫面
- 執行觸控或 gesture
- 管理 episode reset / app restart / recovery
- 保存 frames、replay、metrics、debug logs
- 對 RL runtime 暴露本地控制協定

不負責：

- 不直接實作 RL 演算法
- 不承擔外層 researcher 判斷

### 5.2 RL Runtime

執行位置：

- Android 手機

責任：

- 載入 policy 與 training config
- 向 `device control app` 請求 observation
- 輸出 action
- 執行訓練 update
- 保存 checkpoint、summary、phase metrics

不負責：

- 不直接呼叫 Android 觸控 API
- 不直接處理桌面端 adb 溝通細節

### 5.3 Desktop Orchestrator / Researcher

執行位置：

- 桌面端

責任：

- 透過 `adb` 或等價 transport 啟動 / 停止手機端訓練
- 推送 config / policy
- 拉取 metrics / replay / checkpoints
- 在 phase 邊界執行 researcher 與調參

不負責：

- 不介入 step-level action
- 不直接抓圖或注入遊戲觸控

## 6. 通訊模型

### 6.1 手機內部協定

`RL runtime <-> device control app` 之間需有明確協定。

最小命令集合：

- `get_observation`
- `perform_action`
- `reset_episode`
- `get_status`
- `save_artifacts`
- `load_policy`
- `load_training_config`

可接受實作：

- app 內 service / binder
- localhost HTTP
- localhost WebSocket
- file-based command queue

原則：

- 協定要固定，避免 RL runtime 與控制 app 強耦合
- 先求可審計、可偵錯，再求最低延遲

### 6.2 桌面到手機協定

`Desktop orchestrator <-> phone` 之間主要透過 `adb` 類通道。

最小操作集合：

- `start_training`
- `stop_training`
- `resume_training`
- `push_config`
- `push_policy`
- `pull_metrics`
- `pull_replay`
- `pull_checkpoints`

## 7. 契約

### 7.1 Action Contract

第一版採固定離散 action。

原則：

- 使用語意標籤，例如 `move_left`、`move_right`、`jump`、`attack`、`idle`
- 每個 action 對應固定觸控區域、按壓時間或 macro
- 不讓 agent 直接輸出任意連續座標
- 若模擬器也支援，必須共用同一份 action labels

### 7.2 Observation Contract

第一版採 screenshot preprocessing。

原則：

- observation 一律由 `device control app` 或其附屬模組取得
- 固定輸入解析度或固定比例縮放
- 優先採 ROI 裁切
- 視需要做灰階化、降採樣、frame stack
- preprocessing 規則需版本化

### 7.3 Outcome Contract

每一步都需產出：

- `reward`
- `success`
- `failure`
- `stuck`
- `done`

判定來源：

- 過關畫面
- 死亡 / 失敗畫面
- 進度變化
- 長時間無變化

### 7.4 Replay Contract

每筆 transition 至少包含：

- `timestamp`
- `episode_id`
- `step_index`
- `device_id` 或 `device_type`
- `policy_version`
- `action`
- `reward`
- `done`
- `success`
- `failure`
- `stuck`
- `frame_path` 或等價 observation 引用
- `next_frame_path` 或等價 observation 引用

### 7.5 Artifact Contract

手機端需能寫出：

- policy checkpoints
- episode summaries
- replay logs
- phase metrics
- debug screenshots / logs

桌面端需能安全拉取這些 artifact，供 researcher、分析或續跑使用。

## 8. 推薦技術方向

### 8.1 優先方案

建議架構：

- 自製 `Android controller app`
- 使用 Android `AccessibilityService`
- 透過 `dispatchGesture()` 執行觸控
- 透過 `takeScreenshot()` 或等價機制擷取畫面
- RL runtime 放在手機端執行
- 桌面端透過 `adb` 協調 lifecycle 與 artifact

原因：

- 最符合單一路徑架構
- 權責清楚
- 不依賴桌面端 step-level 控制
- 後續仍可讓模擬器跑同協定

### 8.2 可用現成方案

可參考或快速原型的方案：

- `OpenAutojs / Auto.js`：適合快速驗證手機端腳本控制與 action mapping
- `Termux + Termux:API`：適合承載手機端 RL runtime 與 script execution
- `uiautomator2`：適合作為協定與 device-side service 架構參考
- `Shizuku`：適合作為某些權限與系統能力補強

### 8.3 不採用為主架構的方案

- `scrcpy`：適合 debug 與人工觀察，不適合作為手機端常駐 RL wrapper
- `Appium`：較偏桌面測試框架，不符合手機端單一路徑設計

## 9. 實作順序

1. 凍結 action labels、ROI、過關 / 失敗條件。
2. 定義 `device control app <-> RL runtime` 協定。
3. 實作手機端 `device control app`。
4. 實作手機端 RL runtime。
5. 串接 adb transport 與 artifact pull / push。
6. 再考慮模擬器是否要跑同協定 target。
7. 純 RL 閉環穩定後，再接 researcher。

## 10. 待補資訊

下列內容需要依目標遊戲截圖補齊：

- 戰鬥中完整畫面
- 過關畫面
- 失敗畫面
- 關卡起始或重開畫面
- 可點擊區域與功能說明
