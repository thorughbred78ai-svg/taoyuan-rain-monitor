# taoyuan-rain-monitor
taoyuan-rain-monitor

🌧️ 桃園每日雨量監測系統

使用中央氣象署（CWA）開放資料 API O-A0002-001，取得桃園指定雨量觀測站資料，並透過 Telegram Bot 自動發送雨量監測報告與雨量警報。

本系統設計給 GitHub Actions 使用，可依排程自動執行。

📋 功能

本系統提供以下功能：

取得中央氣象署 O-A0002-001 雨量資料

篩選桃園指定雨量測站

取得今日 0 時至目前累積雨量

取得 10 分鐘雨量

取得 1 小時雨量

取得 24 小時雨量

每個測站使用獨立雨量警戒門檻

雨量未達任何門檻的測站不輸出

任一雨量項目達到門檻時輸出測站

任一雨量項目達到門檻時發送 Telegram 警報

GitHub Actions 自動執行

支援 CWA API Debug 模式

📁 專案結構

建議專案結構：

.
├── rain_monitor.py
├── README.md
└── .github/
    └── workflows/
        └── rain_monitor.yml

🌦️ 雨量警戒判斷邏輯

本系統不再使用單一雨量門檻判斷。

目前使用四個 Repository Secrets：

RAIN_THRESHOLD_MM
Past10Min_THRESHOLD_MM
Past1hr_THRESHOLD_MM
Past24hr_THRESHOLD_MM


分別對應：

Repository Secret	CWA 資料欄位	說明
RAIN_THRESHOLD_MM	Precipitation	今日 0 時至目前累積雨量
Past10Min_THRESHOLD_MM	Past10Min	10 分鐘雨量
Past1hr_THRESHOLD_MM	Past1hr	1 小時雨量
Past24hr_THRESHOLD_MM	Past24hr	24 小時雨量
🚨 測站輸出規則

每一個測站會獨立判斷四項雨量。

判斷公式：

Precipitation >= RAIN_THRESHOLD_MM
OR
Past10Min >= Past10Min_THRESHOLD_MM
OR
Past1hr >= Past1hr_THRESHOLD_MM
OR
Past24hr >= Past24hr_THRESHOLD_MM

任一項達到門檻
→ 輸出該測站

四項全部未達門檻
→ 不輸出該測站


例如設定：

RAIN_THRESHOLD_MM        = 50
Past10Min_THRESHOLD_MM   = 10
Past1hr_THRESHOLD_MM     = 20
Past24hr_THRESHOLD_MM    = 50


測站資料：

今日累積：20 mm
10分鐘：5 mm
1小時：10 mm
24小時：30 mm


四項全部未達門檻：

20 < 50
5  < 10
10 < 20
30 < 50


因此：

→ 不輸出


如果測站資料為：

今日累積：20 mm
10分鐘：12 mm
1小時：10 mm
24小時：30 mm


因為：

12 >= 10


所以：

→ 輸出該測站
→ 觸發雨量警報

🔐 GitHub Repository Secrets

進入：

GitHub Repository
    ↓
Settings
    ↓
Secrets and variables
    ↓
Actions
    ↓
Repository secrets


建立以下 Secrets。

CWA API
CWA_API_KEY


用於存放中央氣象署 API Key。

Telegram
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID


分別用於：

Telegram Bot Token

Telegram 接收訊息的 Chat ID

雨量警戒門檻

建立：

RAIN_THRESHOLD_MM
Past10Min_THRESHOLD_MM
Past1hr_THRESHOLD_MM
Past24hr_THRESHOLD_MM


例如：

RAIN_THRESHOLD_MM        = 50
Past10Min_THRESHOLD_MM   = 10
Past1hr_THRESHOLD_MM     = 20
Past24hr_THRESHOLD_MM    = 50


數值單位均為 mm。

⚙️ GitHub Actions

建立：

.github/workflows/rain_monitor.yml


範例：

name: Taoyuan Rain Monitor

on:
  workflow_dispatch:

  schedule:
    # GitHub Actions 使用 UTC
    # 例：台灣時間每天 08:00
    - cron: "0 0 * * *"

jobs:

  rain-monitor:

    runs-on: ubuntu-latest

    env:

      CWA_API_KEY: ${{ secrets.CWA_API_KEY }}

      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}

      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

      RAIN_THRESHOLD_MM: ${{ secrets.RAIN_THRESHOLD_MM }}

      Past10Min_THRESHOLD_MM: ${{ secrets.Past10Min_THRESHOLD_MM }}

      Past1hr_THRESHOLD_MM: ${{ secrets.Past1hr_THRESHOLD_MM }}

      Past24hr_THRESHOLD_MM: ${{ secrets.Past24hr_THRESHOLD_MM }}

    steps:

      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Run rain monitor
        run: python rain_monitor.py

🕐 GitHub Actions 時區

GitHub Actions 的 cron 使用 UTC。

台灣時間為：

UTC+8


例如：

台灣時間	UTC Cron
08:00	0 0 * * *
12:00	0 4 * * *
18:00	0 10 * * *
20:00	0 12 * * *

例如每天台灣時間 08:00 執行：

schedule:
  - cron: "0 0 * * *"


如果需要每 10 分鐘執行：

schedule:
  - cron: "*/10 * * * *"

📍 桃園監測測站

目前 rain_monitor.py 的 TARGET_STATIONS：

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


如果需要增加或移除測站，可以修改：

TARGET_STATIONS = [
    ...
]

📊 每日 Telegram 報告測站

每日報告目前只針對以下測站：

DEFAULT_REPORT_STATIONS = [
    "新屋",
    "八德",
    "蘆竹",
    "龜山",
    "中壢",
]


這與 TARGET_STATIONS 不同。

也就是：

每日報告

只檢查：

新屋
八德
蘆竹
龜山
中壢


而且：

四項雨量全部未達門檻
    ↓
不輸出

任一項達門檻
    ↓
輸出

🚨 雨量警報測站

雨量警報則會檢查：

TARGET_STATIONS


也就是目前設定的全部桃園測站。

只要任一測站：

今日累積雨量達標
OR
10分鐘雨量達標
OR
1小時雨量達標
OR
24小時雨量達標


就會發送 Telegram 雨量警報。

📱 Telegram 每日報告範例

如果沒有任何指定每日報告測站達到門檻：

🌧️ 桃園每日雨量監測
━━━━━━━━━━━━━━━━
📅 資料日期：2026-09-26
🕐 更新時間：2026-09-26 08:00:00
📍 查詢測站：新屋、八德、蘆竹、龜山、中壢

🚨 雨量警戒門檻
   今日累積：50 mm
   10分鐘：10 mm
   1小時：20 mm
   24小時：50 mm

✅ 目前指定測站均未達任何雨量警戒門檻。

📊 達警戒測站：0 筆
🔎 資料來源：中央氣象署 O-A0002-001

🌧️ 測站達警戒範例

假設「新屋」：

今日累積：30 mm
10分鐘：12 mm
1小時：15 mm
24小時：40 mm


門檻：

今日累積：50 mm
10分鐘：10 mm
1小時：20 mm
24小時：50 mm


因為：

10分鐘 12 >= 10


所以新屋會被輸出。

Telegram：

📍 新屋
   測站編號：XXXX
   觀測時間：2026-09-26T08:00:00+08:00
   🌧️ 今日累積雨量：30 mm
   🌧️ 10分鐘雨量：12 mm
   🌧️ 1小時雨量：15 mm
   🌧️ 24小時雨量：40 mm
   🚨 達警戒：
      • 10分鐘雨量 12 mm ≥ 10 mm

🚨 Telegram 雨量警報範例
🚨 桃園雨量警報
━━━━━━━━━━━━━━━━
⚠️ 以下測站至少一項雨量達到警戒門檻

📍 測站：新屋
🆔 測站編號：XXXX
🕐 觀測時間：2026-09-26T08:00:00+08:00
🚨 達標項目：
   • 10分鐘 12 mm ≥ 10 mm

🔎 資料來源：中央氣象署 O-A0002-001


如果同一測站同時有多項達標，會全部列出。

例如：

🚨 達標項目：
   • 今日累積 60 mm ≥ 50 mm
   • 1小時 25 mm ≥ 20 mm
   • 24小時 70 mm ≥ 50 mm

🔎 Debug 模式

預設：

DEBUG_CWA=false


如果需要查看 CWA API JSON 結構，可以在 GitHub Actions 增加：

env:
  DEBUG_CWA: "true"


或在本機：

DEBUG_CWA=true python rain_monitor.py


Debug 模式會顯示：

records 結構

CWA Station 數量

StationName

StationId

ObsTime

RainfallElement

目標測站雨量資料

💻 本機執行

需要 Python 3.10 以上。

建議使用 Python 3.12。

設定環境變數：

Linux / macOS
export CWA_API_KEY="你的CWA_API_KEY"

export TELEGRAM_BOT_TOKEN="你的Telegram_Bot_Token"

export TELEGRAM_CHAT_ID="你的Chat_ID"

export RAIN_THRESHOLD_MM="50"

export Past10Min_THRESHOLD_MM="10"

export Past1hr_THRESHOLD_MM="20"

export Past24hr_THRESHOLD_MM="50"


執行：

python rain_monitor.py

🪟 Windows PowerShell
$env:CWA_API_KEY="你的CWA_API_KEY"

$env:TELEGRAM_BOT_TOKEN="你的Telegram_Bot_Token"

$env:TELEGRAM_CHAT_ID="你的Chat_ID"

$env:RAIN_THRESHOLD_MM="50"

$env:Past10Min_THRESHOLD_MM="10"

$env:Past1hr_THRESHOLD_MM="20"

$env:Past24hr_THRESHOLD_MM="50"


執行：

python rain_monitor.py

🧪 測試警戒門檻

可以暫時使用非常低的門檻測試 Telegram。

例如：

RAIN_THRESHOLD_MM        = 0
Past10Min_THRESHOLD_MM   = 0
Past1hr_THRESHOLD_MM     = 0
Past24hr_THRESHOLD_MM    = 0


這會讓所有有資料的測站都達到門檻。

測試完成後，務必恢復正常門檻。

⚠️ 注意事項
1. API Key 不要寫進程式碼

不要在 rain_monitor.py 裡直接寫：

CWA_API_KEY = "xxxxxxxx"


應使用 GitHub Repository Secrets：

CWA_API_KEY

2. Telegram Token 不要公開

不要將：

TELEGRAM_BOT_TOKEN


提交到 Git。

應使用：

${{ secrets.TELEGRAM_BOT_TOKEN }}

3. 四個雨量門檻都必須設定

以下四個 Secrets 都是必要的：

RAIN_THRESHOLD_MM
Past10Min_THRESHOLD_MM
Past1hr_THRESHOLD_MM
Past24hr_THRESHOLD_MM


缺少其中任何一個，程式會停止並顯示：

缺少雨量警戒門檻環境變數

4. 門檻必須是數字

正確：

50
10
20
50


也可以：

50.0
10.5
20.0
50.5


錯誤：

50mm
十
10分鐘10mm

5. 雨跡 T

CWA 的：

T


代表雨跡。

本程式會將：

T → 0 mm


因此不會因為雨跡而觸發雨量警戒。

📡 資料來源

資料集：

CWA O-A0002-001


資料來源為中央氣象署開放資料平台。

本程式主要使用：

RainfallElement.Now.Precipitation
RainfallElement.Past10Min.Precipitation
RainfallElement.Past1hr.Precipitation
RainfallElement.Past24hr.Precipitation

🔄 系統流程
GitHub Actions
      │
      ▼
執行 rain_monitor.py
      │
      ▼
讀取 Repository Secrets
      │
      ├── CWA_API_KEY
      ├── TELEGRAM_BOT_TOKEN
      ├── TELEGRAM_CHAT_ID
      │
      ├── RAIN_THRESHOLD_MM
      ├── Past10Min_THRESHOLD_MM
      ├── Past1hr_THRESHOLD_MM
      └── Past24hr_THRESHOLD_MM
      │
      ▼
取得 CWA O-A0002-001
      │
      ▼
篩選桃園指定測站
      │
      ▼
取得各測站
      │
      ├── 今日累積雨量
      ├── 10分鐘雨量
      ├── 1小時雨量
      └── 24小時雨量
      │
      ▼
逐測站判斷
      │
      ├── 任一項達門檻
      │       │
      │       ├── 每日報告 → 輸出
      │       └── 警報 → Telegram
      │
      └── 四項全部未達
              │
              └── 不輸出

📌 核心規則總結
條件	每日報告	雨量警報
四項全部未達門檻	❌ 不輸出	❌ 不警報
今日累積達標	✅ 輸出	🚨 警報
10 分鐘達標	✅ 輸出	🚨 警報
1 小時達標	✅ 輸出	🚨 警報
24 小時達標	✅ 輸出	🚨 警報
多項同時達標	✅ 輸出	🚨 警報並列出全部達標項目
📄 主要檔案
檔案	功能
rain_monitor.py	雨量資料取得、判斷與 Telegram 通知
README.md	專案說明
.github/workflows/rain_monitor.yml	GitHub Actions 自動執行設定
✅ 完成設定後

確認 GitHub Repository 已設定：

☑ CWA_API_KEY
☑ TELEGRAM_BOT_TOKEN
☑ TELEGRAM_CHAT_ID
☑ RAIN_THRESHOLD_MM
☑ Past10Min_THRESHOLD_MM
☑ Past1hr_THRESHOLD_MM
☑ Past24hr_THRESHOLD_MM


然後在：

Actions
    ↓
Taoyuan Rain Monitor
    ↓
Run workflow


手動執行一次確認。

執行成功後，GitHub Actions 就會依照 .github/workflows/rain_monitor.yml 的 schedule 自動執行。
