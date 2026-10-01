# taoyuan-rain-monitor

🌧️ 桃園每日雨量監測系統
使用中央氣象署（CWA）O-A0002-001 雨量觀測資料，監測桃園指定雨量測站，並依照自訂雨量警戒門檻，透過 Telegram 發送雨量報告與警報。
本專案適合使用 GitHub Actions 定時執行。

📌 功能
本系統主要提供以下功能：
取得中央氣象署 CWA O-A0002-001 即時雨量資料。
篩選桃園指定測站。

取得以下四項雨量資料：
今日 00:00 至目前累積雨量
過去 10 分鐘雨量
過去 1 小時雨量
過去 24 小時雨量

使用 GitHub Repository Secrets 設定雨量警戒門檻。
任一項雨量達到門檻，即判定該測站達到警戒。
所有雨量項目均未達門檻時，不列入 Telegram 報告。
所有測站均未達門檻時，不發送任何 Telegram 訊息。

任一測站達到警戒時：
發送 Telegram 每日雨量報告
發送 Telegram 雨量警報

CWA API 連線失敗時自動 Retry。
Telegram API 連線失敗時自動 Retry。
支援 GitHub Actions 自動排程。
支援 CWA API Debug 模式。

📡 資料來源
資料來源：中央氣象署 CWA
資料集：O-A0002-001
資料名稱：雨量觀測資料
API：https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001

程式使用：format=JSON

📍 桃園監測測站
目前監測以下測站：
大溪永福
中大臨海站
觀音工業區
八德蔬果
新興坑尾
國二E009K
國一高架N063K
國三N072K
國三N063K
國一S072K
西濱S032K
中央大學
茶改場
東眼山
蘆竹
新屋
復興
八德
大溪
平鎮
楊梅
龍潭
龜山
竹圍
中德
水尾
四稜
桃園
觀音
中壢

程式會依照 CWA API 回傳的 StationName 進行比對。

🌧️ 雨量警戒判斷

系統使用四項獨立的雨量警戒門檻。

1. 今日累積雨量
環境變數：RAIN_THRESHOLD_MM
對應 CWA：
RainfallElement
└── Now
    └── Precipitation
代表：今日 00:00 至目前累積雨量

2. 過去 10 分鐘雨量
環境變數：Past10Min_THRESHOLD_MM
對應：
RainfallElement
└── Past10Min
    └── Precipitation

3. 過去 1 小時雨量
環境變數：Past1hr_THRESHOLD_MM
對應：
RainfallElement
└── Past1hr
    └── Precipitation

4. 過去 24 小時雨量
環境變數：Past24hr_THRESHOLD_MM
對應：
RainfallElement
└── Past24hr
    └── Precipitation

🚨 警戒判斷邏輯

任一項達到門檻，即視為該測站達到雨量警戒。
判斷方式：
Precipitation >= RAIN_THRESHOLD_MM
OR
Past10Min >= Past10Min_THRESHOLD_MM
OR
Past1hr >= Past1hr_THRESHOLD_MM
OR
Past24hr >= Past24hr_THRESHOLD_MM

也就是：
四項全部低於門檻
        ↓
    未達警戒

任一項 >= 門檻
        ↓
    達到警戒

📱 Telegram 推播規則
這是目前版本的重要行為。
❌ 所有測站都未達門檻
如果所有指定測站：
今日累積
10分鐘
1小時
24小時

全部都低於門檻：
→ 不發送 Telegram 每日報告
→ 不發送 Telegram 雨量警報


GitHub Actions 會正常完成：
ℹ️ 目前指定測站均未達任何雨量警戒門檻。
ℹ️ 不發送 Telegram 每日報告。
✅ 沒有測站達到任何雨量警戒門檻
✅ Workflow 執行完成

🚨 有測站達到門檻
如果任一測站任一雨量項目達到門檻：

→ 發送 Telegram 每日雨量報告
→ 發送 Telegram 雨量警報

例如：
30 個測站
      ↓
中壢
Past1hr = 50 mm
門檻 = 40 mm
      ↓
達到警戒
      ↓
Telegram 每日報告
      ↓
Telegram 雨量警報

每日報告與雨量警報只會列出達到警戒的測站。

🔐 GitHub Repository Secrets

前往：
GitHub Repository
→ Settings
→ Secrets and variables
→ Actions
→ New repository secret


需要設定以下 Secrets。
CWA API Key
Name：
CWA_API_KEY
Value：

你的中央氣象署 API 授權碼

Telegram Bot Token
Name：
TELEGRAM_BOT_TOKEN
Value：
你的 Telegram Bot Token

例如格式：
123456789:XXXXXXXXXXXXXXXXXXXXXXXXXXXX

Telegram Chat ID
Name：
TELEGRAM_CHAT_ID
Value：
你的 Telegram Chat ID

🌧️ 雨量門檻 Secrets
今日累積雨量
Name：RAIN_THRESHOLD_MM
例如：80
代表：今日累積雨量 >= 80 mm
即達警戒。

10 分鐘雨量
Name：Past10Min_THRESHOLD_MM
例如：20

1 小時雨量
Name：Past1hr_THRESHOLD_MM
例如：40

24 小時雨量
Name：Past24hr_THRESHOLD_MM
例如：100

🔐 Secrets 完整清單

GitHub Actions 至少需要：
CWA_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

RAIN_THRESHOLD_MM
Past10Min_THRESHOLD_MM
Past1hr_THRESHOLD_MM
Past24hr_THRESHOLD_MM

⚙️ 可選環境變數
DEBUG_CWA
可以設定：DEBUG_CWA=true

啟用 CWA JSON 結構 Debug。

程式會額外輸出：
records keys
CWA Station count
StationName
StationId
ObsTime
RainfallElement keys
Now


如果 API 有回應，但程式沒有找到桃園測站，可以開啟這個功能協助排查。

🔄 API Retry 機制

目前版本針對 CWA API 與 Telegram API 都加入 Retry。

預設：
HTTP_RETRIES = 4
HTTP_TIMEOUT = 30 秒

CWA API Retry
遇到以下情況會自動重試：
ConnectionResetError
ConnectionError
TimeoutError
URLError
HTTP 429
HTTP 5xx


例如：
🌐 API 連線嘗試 1/4
⚠️ API 連線暫時失敗：[Errno 104] Connection reset by peer
⏳ 2 秒後重試...

🌐 API 連線嘗試 2/4

⏳ Retry 間隔

使用 Exponential Backoff。

大致為：
第一次失敗
    ↓
等待 2 秒

第二次失敗
    ↓
等待 4 秒

第三次失敗
    ↓
等待 8 秒

第四次失敗
    ↓
停止並回報錯誤


最大等待時間限制為：10 秒

📱 Telegram Retry

Telegram API 同樣具有 Retry 機制。

可以處理：
ConnectionResetError
ConnectionError
TimeoutError
URLError
HTTP 429
HTTP 5xx

因此即使 GitHub Actions 與 Telegram API 暫時連線不穩，也不會第一次失敗就直接中止。

🔌 Connection: close

HTTP Request 使用：Connection: close

主要目的是降低 GitHub Actions Runner 重用已被遠端關閉 HTTP/TLS 連線所造成的：

Connection reset by peer

問題。

🧹 雨量特殊值

CWA 雨量資料可能出現：
T
-
--
-98
-99
程式會將這些值視為：0 mm


例如：
T → 0
-  → 0
-- → 0
-98 → 0
-99 → 0
避免特殊值直接造成程式錯誤。

🕐 台灣時間

程式使用：Asia/Taipei
取得目前時間。
例如：2026-10-01 09:30:00
因此：
查詢日期
更新時間
每日累積雨量日期
均以台灣時間為基準。

🧮 測站資料處理

如果 CWA API 同一測站回傳多筆資料，程式會依：
DateTime
比較，最後只保留最新的一筆。

流程：
CWA API
   ↓
桃園指定測站
   ↓
StationName
   ↓
同測站多筆資料
   ↓
比較 DateTime
   ↓
保留最新資料

📊 GitHub Actions 執行流程

完整流程如下：
GitHub Actions 啟動
        ↓
讀取 GitHub Secrets
        ↓
取得台灣日期
        ↓
呼叫 CWA API
        ↓
CWA API 連線失敗？
        │
        ├── 是 → Retry
        │
        └── 否
             ↓
       解析 JSON
             ↓
       篩選桃園測站
             ↓
       保留最新資料
             ↓
       判斷四項雨量
             ↓
      ┌──────┴──────┐
      │             │
    無達標          有達標
      │             │
      ▼             ▼
不發 Telegram    Telegram 每日報告
      │             │
      │             ▼
      │          Telegram 警報
      │             │
      └──────┬──────┘
             ▼
      Workflow 完成

📁 建議專案結構
taoyuan-rain-monitor/
│
├── rain_monitor.py
│
├── README.md
│
└── .github/
    └── workflows/
        └── rain-monitor.yml

▶️ 本機執行
需要 Python：Python 3.10+
推薦：Python 3.12

設定環境變數後：python rain_monitor.py

🧪 本機測試
Linux / macOS：
export CWA_API_KEY="你的CWA_API_KEY"
export TELEGRAM_BOT_TOKEN="你的TelegramBotToken"
export TELEGRAM_CHAT_ID="你的ChatID"

export RAIN_THRESHOLD_MM="80"
export Past10Min_THRESHOLD_MM="20"
export Past1hr_THRESHOLD_MM="40"
export Past24hr_THRESHOLD_MM="100"

python rain_monitor.py


如果需要 Debug：
export DEBUG_CWA="true"
python rain_monitor.py

🐙 GitHub Actions

Workflow 可以透過 GitHub Actions 定時執行。

例如：
name: Taoyuan Rain Monitor

on:
  workflow_dispatch:

  schedule:
    - cron: "*/10 * * * *"

jobs:
  rain-monitor:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Run rain monitor
        env:
          CWA_API_KEY: ${{ secrets.CWA_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

          RAIN_THRESHOLD_MM: ${{ secrets.RAIN_THRESHOLD_MM }}
          Past10Min_THRESHOLD_MM: ${{ secrets.Past10Min_THRESHOLD_MM }}
          Past1hr_THRESHOLD_MM: ${{ secrets.Past1hr_THRESHOLD_MM }}
          Past24hr_THRESHOLD_MM: ${{ secrets.Past24hr_THRESHOLD_MM }}

        run: |
          python rain_monitor.py

⚠️ GitHub Actions 排程注意事項

GitHub Actions 的：
schedule:使用 UTC 時間。
台灣時間：
UTC+8

因此如果要按照台灣時間設定，需要自行換算。

例如台灣：08:00
對應 UTC：00:00

🔎 常見錯誤
1. Connection reset by peer

錯誤：
ConnectionResetError:
[Errno 104] Connection reset by peer

目前版本會自動 Retry。

正常情況會看到：

🌐 API 連線嘗試 1/4
⚠️ API 連線暫時失敗
⏳ 2 秒後重試...


如果第四次仍失敗，才會：

❌ Workflow 執行失敗

2. CWA API 沒有取得測站

如果看到：

⚠️ CWA API 有回應，
但沒有解析到桃園目標測站。


請設定：

DEBUG_CWA=true


再執行一次。

查看：

records keys
CWA Station count
StationName
StationId
ObsTime
RainfallElement


確認 CWA API 實際回傳格式是否發生變化。

3. 缺少 CWA API Key

如果出現：

缺少必要環境變數：CWA_API_KEY


請確認 GitHub Repository Secrets 有：

CWA_API_KEY

4. Telegram 沒有發送

如果：

所有測站都未達門檻


這是正常行為。

程式會顯示：

ℹ️ 目前指定測站均未達任何雨量警戒門檻。
ℹ️ 不發送 Telegram 每日報告。


這種情況不會呼叫 Telegram API。

5. Telegram API 連線失敗

程式會自動 Retry。

例如：

📨 Telegram 發送嘗試 1/4
⚠️ Telegram 連線暫時失敗
⏳ 2 秒後重試...


如果四次全部失敗，Workflow 才會失敗。

6. Telegram Bot Token 錯誤

如果出現：

Telegram HTTP 401


請確認：

TELEGRAM_BOT_TOKEN


是否正確。

這類錯誤不是暫時性網路問題，因此不會無限 Retry。

7. Telegram Chat ID 錯誤

請確認：

TELEGRAM_CHAT_ID


設定正確。

如果 Bot 沒有加入群組或沒有權限，也可能導致 Telegram API 回傳錯誤。

🛡️ Secrets 安全性

不要將以下資訊直接寫進程式：

CWA_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID


不要將 Secrets commit 到 Git。

錯誤示範：

CWA_API_KEY = "xxxxxxxx"


正確方式：

CWA_API_KEY = os.getenv("CWA_API_KEY")


GitHub Actions 使用：

CWA_API_KEY: ${{ secrets.CWA_API_KEY }}

📋 執行結果範例
情況 A：沒有任何測站達標
查詢日期：2026-10-01
資料來源：CWA O-A0002-001

CWA 回傳桃園目標資料筆數：30

成功辨識測站：...
測站數量：30

達到雨量警戒測站數量：0

ℹ️ 目前指定測站均未達任何雨量警戒門檻。
ℹ️ 不發送 Telegram 每日報告。
✅ 沒有測站達到任何雨量警戒門檻

✅ Workflow 執行完成


Telegram：

不發送

情況 B：有測站達標

例如：

中壢
Past1hr = 50 mm
Past1hr_THRESHOLD_MM = 40 mm


執行結果：

達到雨量警戒測站數量：1

========== Telegram Report ==========

🌧️ 桃園每日雨量監測
...
📍 中壢
...
🚨 達警戒：
   • 1小時雨量 50 mm ≥ 40 mm

======================================

📨 Telegram 發送嘗試 1/4
✅ Telegram 每日雨量報告已發送

========== Rain Alert ==========

🚨 桃園雨量警報
...
📍 測站：中壢
...
🚨 達標項目：
   • 1小時 50 mm ≥ 40 mm

================================

📨 Telegram 發送嘗試 1/4
🚨 高雨量警報已發送

✅ Workflow 執行完成

🔧 目前版本的重要行為
情況	Telegram 每日報告	Telegram 警報	Workflow
全部測站未達門檻	❌	❌	✅ 成功
任一測站達一項門檻	✅	✅	✅ 成功
CWA 暫時連線失敗	Retry	-	Retry
Telegram 暫時連線失敗	Retry	Retry	Retry
CWA 4 次都失敗	-	-	❌ 失敗
Telegram 4 次都失敗	-	-	❌ 失敗
API 回傳 HTTP 401/403	-	-	❌ 失敗
CWA JSON 格式錯誤	-	-	❌ 失敗
📌 程式主要檔案

主要程式：

rain_monitor.py


功能包含：

CWA API
    ↓
JSON 解析
    ↓
桃園測站篩選
    ↓
最新資料判斷
    ↓
雨量門檻判斷
    ↓
Telegram

📜 License

本專案僅供個人監測、研究及自動化使用。

雨量資料來源為中央氣象署公開資料，實際資料內容與服務狀態以中央氣象署公告為準。

本系統的雨量門檻為使用者自行設定，不代表中央氣象署發布之官方警戒標準。

⚠️ 注意事項

本系統屬於：

自動化雨量資料監測工具


資料可能受到以下因素影響：

API 暫時無法連線

測站通訊異常

API 資料延遲

測站資料缺值

GitHub Actions 執行延遲

Telegram API 暫時無法連線

因此不應將本程式視為唯一的防災或緊急警報來源。

如涉及實際防災、交通或人員安全，應同時參考中央氣象署及相關政府單位發布的最新資訊。

:::

這份 README 已經和前面那版 `rain_monitor.py` 的行為一致，尤其是**「未達門檻不發 Telegram」**與 **CWA / Telegram 都有 4 次 Retry** 這兩個變更。
