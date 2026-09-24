# taoyuan-rain-monitor
taoyuan-rain-monitor

🌧️ 桃園每日雨量監測系統

使用 GitHub Actions + Python + 中央氣象署 CWA API + Telegram Bot 建立桃園地區每日雨量自動監測與高雨量警報系統。

本專案將原本的 n8n Workflow 改為 GitHub Actions 執行，不需要自行維護 n8n Server。

✨ 功能

每日自動查詢中央氣象署地面測站雨量資料

使用台灣時區 Asia/Taipei

每日自動執行 8 次：

08:00

10:00

12:00

14:00

16:00

18:00

20:00

22:00

自動取得桃園指定測站資料

Telegram 自動推播每日雨量

高雨量自動警報

雨量警戒門檻可調整

API Key 與 Telegram Token 使用 GitHub Secrets 管理

支援 GitHub Actions 手動執行

CWA 回傳 T、空值或非數字資料時進行安全處理

同一測站有多筆資料時取最新日期資料

🏗️ 系統架構
GitHub Actions
      │
      ▼
 Python rain_monitor.py
      │
      ├───────────────► CWA API
      │                    │
      │                    ▼
      │              C-B0025-001
      │                    │
      │                    ▼
      │              桃園測站雨量
      │
      ├───────────────► Telegram Bot
      │                    │
      │                    ▼
      │              每日雨量報告
      │
      └───────────────► 雨量警報判斷
                           │
                           ▼
                    Telegram Alert

📁 專案結構
taoyuan-rain-monitor/
│
├── .github/
│   └── workflows/
│       └── rain-monitor.yml
│
├── rain_monitor.py
│
└── README.md

🔌 資料來源

本專案使用中央氣象署 Open Data：

資料集：C-B0025-001

地面測站每日雨量資料

API：

https://opendata.cwa.gov.tw/api/v1/rest/datastore/C-B0025-001


主要使用資料：

StationID
StationName
StationNameEN
StationAttribute
Date
Precipitation


資料來源：

中央氣象署 Open Data。

📍 監測測站

目前程式監測以下測站：

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

📊 Telegram 預設回報測站

GitHub Actions 每次執行時，預設回報：

新屋
八德
蘆竹
龜山
中壢


例如：

🌧️ 桃園每日雨量監測
━━━━━━━━━━━━━━━━
📅 資料日期：2026-09-25
📍 查詢測站：新屋、八德、蘆竹、龜山、中壢

📍 新屋
   測站編號：C0C480
   日期：2026-09-25
   🌧️ 今日累積雨量：32 mm
   測站類型：一般氣象站
────────────────

📍 八德
   測站編號：C0C590
   日期：2026-09-25
   ☀️ 今日累積雨量：0 mm
   測站類型：一般氣象站
────────────────

📊 已取得 5 筆測站資料
🔎 資料來源：中央氣象署 C-B0025-001


實際測站編號、雨量與測站類型以 CWA API 當次回傳資料為準。

🚨 高雨量警報

系統會對監測測站進行高雨量判斷。

目前預設：

RAIN_THRESHOLD_MM=100


判斷條件：

Precipitation >= threshold


例如某測站：

今日累積雨量：125 mm


則會觸發 Telegram 警報：

🚨 桃園今日雨量警報
━━━━━━━━━━━━━━━━
⚠️ 今日累積雨量達 100 mm 以上

📍 測站：新屋
📅 日期：2026-09-25
🌧️ 今日累積雨量：125 mm
🆔 測站編號：C0C480

🔎 資料來源：中央氣象署 C-B0025-001

⚙️ 調整警戒門檻

在：

.github/workflows/rain-monitor.yml


修改：

RAIN_THRESHOLD_MM: "100"


例如改成 350 mm：

RAIN_THRESHOLD_MM: "350"


即可變成：

Precipitation >= 350 mm


才觸發警報。

⏰ GitHub Actions 排程

Workflow 使用：

schedule:
  - cron: "0 8,10,12,14,16,18,20,22 * * *"
    timezone: "Asia/Taipei"


因此台灣時間每天：

08:00
10:00
12:00
14:00
16:00
18:00
20:00
22:00


執行一次。

另外提供：

workflow_dispatch:


因此可以從 GitHub Actions 頁面手動執行。

🔐 GitHub Secrets

請至：

Repository
→ Settings
→ Secrets and variables
→ Actions
→ New repository secret


建立以下三個 Secrets。

CWA_API_KEY

中央氣象署 API Key。

CWA_API_KEY

TELEGRAM_BOT_TOKEN

Telegram Bot Token。

TELEGRAM_BOT_TOKEN

TELEGRAM_CHAT_ID

Telegram 接收通知的 Chat ID。

TELEGRAM_CHAT_ID


完成後應該有：

CWA_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

🔒 安全性

請不要將以下資訊直接寫入 Git Repository：

CWA API Key
Telegram Bot Token
Telegram Chat ID


不要在：

rain_monitor.py


直接寫：

CWA_API_KEY = "xxxxxxxx"


也不要在：

rain-monitor.yml


直接寫：

TELEGRAM_BOT_TOKEN: "123456:ABC..."


本專案使用 GitHub Secrets：

CWA_API_KEY: ${{ secrets.CWA_API_KEY }}
TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

🚀 安裝方式
1. 建立 GitHub Repository

例如：

taoyuan-rain-monitor

2. 建立目錄
taoyuan-rain-monitor/
├── .github/
│   └── workflows/
│       └── rain-monitor.yml
├── rain_monitor.py
└── README.md

3. 上傳 Python 程式

將：

rain_monitor.py


放在 Repository 根目錄。

4. 建立 GitHub Actions

建立：

.github/workflows/rain-monitor.yml


放入 Workflow 設定。

5. 設定 Secrets

建立：

CWA_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

6. 啟用 Actions

進入：

Actions


確認：

桃園每日雨量監測


Workflow 已出現。

🧪 手動測試

進入：

GitHub
→ Actions
→ 桃園每日雨量監測
→ Run workflow
→ Run workflow


GitHub Runner 將執行：

Checkout
↓
Setup Python
↓
Verify configuration
↓
Run Taoyuan Rain Monitor
↓
CWA API
↓
雨量資料處理
↓
Telegram

🐍 Python 版本

目前 Workflow 使用：

Python 3.12


程式只使用 Python Standard Library，因此不需要：

requirements.txt


也不需要額外安裝：

requests
pandas
numpy
python-telegram-bot

🧮 雨量資料處理

CWA 回傳：

T


代表微量雨。

本專案沿用原 n8n Workflow 的處理方式：

T → 0 mm


空值：

"" → 0 mm


無法轉換的資料：

invalid → 0 mm


因此不會因為：

NaN
null
T
空字串


導致警報判斷失敗。

📅 今日日期

程式使用：

Asia/Taipei


取得目前台灣日期。

因此 GitHub Runner 即使使用 UTC，也不會直接拿 UTC 日期當作雨量查詢日期。

例如台灣：

2026-09-25 07:30


程式會使用：

2026-09-25


作為 CWA API 的：

timeFrom

📡 CWA API 流程

程式會呼叫：

C-B0025-001


並傳入：

format=JSON
DataType=stationObsTimes
timeFrom=YYYY-MM-DD


例如：

format=JSON
DataType=stationObsTimes
timeFrom=2026-09-25


取得資料後：

records
  ↓
location
  ↓
station
  ↓
stationObsTimes
  ↓
stationObsTime
  ↓
weatherElements
  ↓
Precipitation

📍 測站篩選

Python 會先取得 CWA API 回傳的所有測站。

接著只保留：

TARGET_STATIONS


裡面的測站。

因此即使 API 回傳其他縣市測站，也不會進入桃園監測結果。

🔎 同測站多筆資料

如果 API 回傳相同測站多筆資料，程式會依：

Date


比較並保留日期最新的一筆。

這可以避免同一測站重複出現在 Telegram 報告。

📤 Telegram API

Telegram 使用：

sendMessage


發送文字訊息。

程式會將：

每日雨量報告


與：

高雨量警報


分別發送。

⚠️ GitHub Actions 注意事項

GitHub Actions 的 scheduled workflow 並不是即時排程服務。

在 GitHub Actions 負載較高時，scheduled workflow 可能出現延遲。

因此：

08:00


應理解為：

預定約 08:00 執行


而不是保證精確到秒。

如果是非常嚴格的即時監測需求，建議使用專門的排程服務。

🔧 常見問題
CWA API 沒有資料

先確認：

CWA_API_KEY


是否正確。

也確認 CWA API 是否正常回傳：

records.location

Telegram 沒有收到訊息

確認：

TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID


是否正確。

並確認 Telegram 使用者或群組已經和 Bot 建立有效的聊天關係。

GitHub Actions 沒有自動執行

確認：

Actions
→ 桃園每日雨量監測


是否啟用。

也可以先使用：

Run workflow


進行手動測試。

警報一直沒有出現

確認：

RAIN_THRESHOLD_MM: "100"


門檻是否高於目前測站雨量。

也可以暫時降低，例如：

RAIN_THRESHOLD_MM: "1"


測試 Telegram 警報流程。

測試完成後記得恢復正式門檻。

🛠️ 自訂自動回報測站

修改：

DEFAULT_REPORT_STATIONS = [
    "新屋",
    "八德",
    "蘆竹",
    "龜山",
    "中壢",
]


例如：

DEFAULT_REPORT_STATIONS = [
    "新屋",
    "八德",
    "蘆竹",
    "龜山",
    "中壢",
    "桃園",
    "楊梅",
]


即可增加每日 Telegram 回報測站。

但該測站必須同時存在於：

TARGET_STATIONS

➕ 新增監測測站

在：

TARGET_STATIONS


增加 CWA API 使用的正式測站名稱：

TARGET_STATIONS = [
    ...
    "新測站名稱",
]


測站名稱必須與 CWA API 的：

StationName


完全一致。

📈 未來可以擴充

本專案可以進一步加入：

24 小時累積雨量

48 小時累積雨量

72 小時累積雨量

每小時雨量

桃園雨量排行榜

最大雨量測站

多級警報

100 / 200 / 350 / 500 mm 警戒

重複警報抑制

警報歷史紀錄

GitHub Issues 自動建立

CSV 歷史資料

SQLite / PostgreSQL

Email 通知

LINE 通知

Discord 通知

Telegram 指令查詢

Telegram 指定測站查詢

每日雨量統計圖

GitHub Pages 儀表板

🔄 與原 n8n Workflow 對照
原 n8n	GitHub Actions 版本
Schedule Trigger	GitHub Actions schedule
Request Router	Python 主程式
CWA API HTTP Request	Python urllib
Normalize CWA Data	normalize_data()
Detect Requested Stations	station_map
Build Telegram Report	build_report()
Send Rain Report	send_telegram()
Rain Alert Engine	find_alerts()
Alert Required?	if triggered:
Send Rain Alert	send_telegram()
n8n Credentials	GitHub Secrets
Asia/Taipei	Workflow timezone + Python ZoneInfo
📜 授權與資料來源

本專案程式碼可依專案需求自行修改。

氣象資料來源：

中央氣象署 Open Data
C-B0025-001
地面測站每日雨量資料


實際資料內容、測站狀態與 API 服務狀態以中央氣象署提供資料為準。

📌 快速開始

完成以下三件事即可使用：

1. 上傳 rain_monitor.py
2. 上傳 .github/workflows/rain-monitor.yml
3. 設定 CWA_API_KEY、TELEGRAM_BOT_TOKEN、TELEGRAM_CHAT_ID


然後：

GitHub
→ Actions
→ 桃園每日雨量監測
→ Run workflow


即可進行第一次測試。

之後 GitHub Actions 會依：

Asia/Taipei

08:00
10:00
12:00
14:00
16:00
18:00
20:00
22:00


自動執行桃園雨量監測。
