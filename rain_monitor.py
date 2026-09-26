#!/usr/bin/env python3

"""
桃園每日雨量監測系統
========================================

資料來源：
    中央氣象署 CWA O-A0002-001
    雨量觀測站－雨量資料

主要功能：
    1. 取得 CWA 即時雨量資料
    2. 篩選桃園指定測站
    3. 取得「今日 0 時至目前」累積雨量
    4. 取得 10 分鐘、1 小時、24 小時雨量
    5. 依四組 Repository Secrets 判斷雨量警戒
    6. 四項全部未達門檻 → 不輸出該測站
    7. 任一項達到門檻 → 輸出該測站
    8. Telegram 推送每日監測報告
    9. 達任一雨量警戒門檻時發送警報
    10. GitHub Actions 可直接執行

必要環境變數：
    CWA_API_KEY
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

雨量警戒環境變數 / GitHub Repository Secrets：
    RAIN_THRESHOLD_MM
        → 今日 0 時至目前累積雨量 Precipitation

    Past10Min_THRESHOLD_MM
        → 10 分鐘雨量 Past10Min

    Past1hr_THRESHOLD_MM
        → 1 小時雨量 Past1hr

    Past24hr_THRESHOLD_MM
        → 24 小時雨量 Past24hr

可選環境變數：
    DEBUG_CWA

警戒判斷邏輯：

    Precipitation >= RAIN_THRESHOLD_MM
        OR
    Past10Min >= Past10Min_THRESHOLD_MM
        OR
    Past1hr >= Past1hr_THRESHOLD_MM
        OR
    Past24hr >= Past24hr_THRESHOLD_MM

    任一項達到門檻：
        → 輸出測站

    四項全部低於門檻：
        → 不輸出測站
"""

import json
import os
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ============================================================
# 基本設定
# ============================================================

CWA_DATASET_ID = "O-A0002-001"

CWA_API_URL = (
    "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"
    f"{CWA_DATASET_ID}"
)


# ============================================================
# 桃園監測測站
# ============================================================

TARGET_STATIONS = [
    "大溪永福",
    "中大臨海站",
    "觀音工業區",
    "八德蔬果",
    "新興坑尾",
    "國二E009K",
    "國一高架N063K",
    "國三N072K",
    "國三N063K",
    "國一S072K",
    "西濱S032K",
    "中央大學",
    "茶改場",
    "東眼山",
    "蘆竹",
    "新屋",
    "復興",
    "八德",
    "大溪",
    "平鎮",
    "楊梅",
    "龍潭",
    "龜山",
    "竹圍",
    "中德",
    "水尾",
    "四稜",
    "桃園",
    "觀音",
    "中壢",
]


# ============================================================
# Telegram 每日回報測站
# ============================================================

DEFAULT_REPORT_STATIONS = [
    "新屋",
    "八德",
    "蘆竹",
    "龜山",
    "中壢",
]


# ============================================================
# 環境變數
# ============================================================

def get_env(
    name: str,
    required: bool = True,
) -> str:
    """
    取得環境變數。
    """

    value = os.getenv(
        name,
        "",
    ).strip()

    if required and not value:

        raise RuntimeError(
            f"缺少必要環境變數：{name}"
        )

    return value


def get_rain_thresholds() -> dict[str, float]:
    """
    取得四項雨量警戒門檻。

    GitHub Repository Secrets：

        RAIN_THRESHOLD_MM
            → Precipitation

        Past10Min_THRESHOLD_MM
            → Past10Min

        Past1hr_THRESHOLD_MM
            → Past1hr

        Past24hr_THRESHOLD_MM
            → Past24hr

    回傳：

        {
            "RAIN": float,
            "Past10Min": float,
            "Past1hr": float,
            "Past24hr": float,
        }
    """

    env_names = {
        "RAIN": "RAIN_THRESHOLD_MM",
        "Past10Min": "Past10Min_THRESHOLD_MM",
        "Past1hr": "Past1hr_THRESHOLD_MM",
        "Past24hr": "Past24hr_THRESHOLD_MM",
    }

    thresholds = {}

    for rain_type, env_name in env_names.items():

        value = os.getenv(
            env_name,
            "",
        ).strip()

        if not value:

            raise RuntimeError(
                "缺少雨量警戒門檻環境變數："
                f"{env_name}"
            )

        try:

            threshold = float(
                value
            )

        except ValueError:

            raise RuntimeError(
                f"{env_name} 必須是數字，"
                f"目前值：{value}"
            )

        if threshold < 0:

            raise RuntimeError(
                f"{env_name} 不可以小於 0"
            )

        thresholds[
            rain_type
        ] = threshold

    return thresholds


# ============================================================
# 台灣時間
# ============================================================

def get_taipei_now() -> datetime:
    """
    取得 Asia/Taipei 時間。
    """

    try:

        from zoneinfo import ZoneInfo

        return datetime.now(
            ZoneInfo("Asia/Taipei")
        )

    except Exception:

        # GitHub Actions 通常使用 UTC，
        # 因此這裡僅作為 fallback。
        return datetime.now()


def get_today() -> str:
    """
    回傳 YYYY-MM-DD。
    """

    return get_taipei_now().strftime(
        "%Y-%m-%d"
    )


# ============================================================
# 數值處理
# ============================================================

def parse_precipitation(
    raw,
) -> float:
    """
    將 CWA 雨量欄位轉換成 float。

    CWA 常見值：

        T       雨跡
        -       無資料
        --      無資料
        -98     特殊值
        -99     特殊值

    對於警報判斷：

        T / 空值 / 非數字
            → 0
    """

    if raw is None:
        return 0.0

    value = str(
        raw
    ).strip()

    if value == "":
        return 0.0

    # 雨跡
    if value.upper() == "T":
        return 0.0

    # 特殊缺值
    if value in (
        "-",
        "--",
    ):
        return 0.0

    # CWA 特殊缺值
    if value in (
        "-98",
        "-99",
    ):
        return 0.0

    try:

        number = float(
            value
        )

        # NaN
        if not number == number:
            return 0.0

        return number

    except (
        TypeError,
        ValueError,
    ):

        return 0.0


# ============================================================
# HTTP JSON
# ============================================================

def fetch_json(
    url: str,
    headers: dict | None = None,
    timeout: int = 30,
) -> dict:
    """
    GET JSON API。
    """

    request = Request(
        url,
        headers=headers or {},
        method="GET",
    )

    try:

        with urlopen(
            request,
            timeout=timeout,
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            return json.loads(
                body
            )

    except HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {exc.code}: "
            f"{body[:2000]}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            "API 連線失敗："
            f"{exc.reason}"
        ) from exc

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "API 回傳內容不是有效 JSON"
        ) from exc


# ============================================================
# CWA API
# ============================================================

def fetch_cwa_data(
    api_key: str,
) -> dict:
    """
    取得 CWA O-A0002-001。
    """

    params = {
        "format": "JSON",
    }

    url = (
        f"{CWA_API_URL}?"
        f"{urlencode(params)}"
    )

    headers = {
        "Authorization": api_key,
        "Accept": "application/json",
        "User-Agent": (
            "taoyuan-rain-monitor/"
            "github-actions"
        ),
    }

    print("")
    print("CWA API:")
    print(url)

    payload = fetch_json(
        url=url,
        headers=headers,
        timeout=30,
    )

    return payload


# ============================================================
# CWA JSON 結構 Debug
# ============================================================

def debug_cwa_structure(
    payload: dict,
) -> None:
    """
    API 沒有解析到資料時，
    印出最重要的 JSON 結構。
    """

    records = payload.get(
        "records",
        {},
    )

    print("")
    print("========== CWA DEBUG ==========")

    print(
        "records keys:",
        list(records.keys())
        if isinstance(records, dict)
        else type(records),
    )

    stations = []

    if isinstance(
        records,
        dict,
    ):

        stations = (
            records.get("Station")
            or records.get("station")
            or []
        )

    if isinstance(
        stations,
        dict,
    ):

        stations = [
            stations
        ]

    print(
        "CWA Station count:",
        len(stations),
    )

    for station in stations[:5]:

        if not isinstance(
            station,
            dict,
        ):
            continue

        print(
            "StationName:",
            station.get(
                "StationName"
            ),
        )

        print(
            "StationId:",
            station.get(
                "StationId"
            ),
        )

        print(
            "ObsTime:",
            station.get(
                "ObsTime"
            ),
        )

        rainfall = station.get(
            "RainfallElement"
        )

        if isinstance(
            rainfall,
            dict,
        ):

            print(
                "RainfallElement keys:",
                list(
                    rainfall.keys()
                ),
            )

            now_data = (
                rainfall.get(
                    "Now"
                )
                or {}
            )

            print(
                "Now:",
                now_data,
            )

    print(
        "================================"
    )

    print("")


# ============================================================
# Normalize CWA O-A0002-001
# ============================================================

def normalize_data(
    payload: dict,
) -> list[dict]:
    """
    解析 CWA O-A0002-001。

    正確結構：

        records
        └── Station
             ├── StationName
             ├── StationId
             ├── ObsTime
             │    └── DateTime
             │
             └── RainfallElement
                  ├── Now
                  ├── Past10Min
                  ├── Past1hr
                  ├── Past3hr
                  ├── Past6hr
                  ├── Past12hr
                  └── Past24hr

    Now：
        本日 0 時至目前累積雨量。
    """

    records = (
        payload.get(
            "records",
            {},
        )
        or {}
    )

    if not isinstance(
        records,
        dict,
    ):

        return []

    stations = (
        records.get(
            "Station"
        )
        or records.get(
            "station"
        )
        or []
    )

    if isinstance(
        stations,
        dict,
    ):

        stations = [
            stations
        ]

    if not isinstance(
        stations,
        list,
    ):

        return []

    output = []

    for station in stations:

        if not isinstance(
            station,
            dict,
        ):

            continue

        # ----------------------------------------------------
        # Station Name
        # ----------------------------------------------------

        station_name = str(
            station.get(
                "StationName",
                "",
            )
        ).strip()

        if not station_name:
            continue

        # ----------------------------------------------------
        # 只保留指定測站
        # ----------------------------------------------------

        if station_name not in TARGET_STATIONS:
            continue

        # ----------------------------------------------------
        # Station ID
        # ----------------------------------------------------

        station_id = (
            station.get(
                "StationId"
            )
            or station.get(
                "StationID"
            )
            or ""
        )

        # ----------------------------------------------------
        # Observation Time
        # ----------------------------------------------------

        obs_time = (
            station.get(
                "ObsTime"
            )
            or {}
        )

        if not isinstance(
            obs_time,
            dict,
        ):

            obs_time = {}

        date_time = (
            obs_time.get(
                "DateTime"
            )
            or ""
        )

        # ----------------------------------------------------
        # GeoInfo
        # ----------------------------------------------------

        geo_info = (
            station.get(
                "GeoInfo"
            )
            or {}
        )

        if not isinstance(
            geo_info,
            dict,
        ):

            geo_info = {}

        county_name = (
            geo_info.get(
                "CountyName"
            )
            or ""
        )

        town_name = (
            geo_info.get(
                "TownName"
            )
            or ""
        )

        station_altitude = (
            geo_info.get(
                "StationAltitude"
            )
            or ""
        )

        # ----------------------------------------------------
        # RainfallElement
        # ----------------------------------------------------

        rainfall = (
            station.get(
                "RainfallElement"
            )
            or {}
        )

        if not isinstance(
            rainfall,
            dict,
        ):

            rainfall = {}

        # ----------------------------------------------------
        # Now
        #
        # 本日 0 時至目前累積雨量
        # ----------------------------------------------------

        now_data = (
            rainfall.get(
                "Now"
            )
            or {}
        )

        if not isinstance(
            now_data,
            dict,
        ):

            now_data = {}

        raw_precipitation = (
            now_data.get(
                "Precipitation"
            )
        )

        precipitation = parse_precipitation(
            raw_precipitation
        )

        # ----------------------------------------------------
        # 其他區間雨量
        # ----------------------------------------------------

        def get_period(
            key: str,
        ) -> float:

            period = (
                rainfall.get(
                    key
                )
                or {}
            )

            if not isinstance(
                period,
                dict,
            ):

                return 0.0

            return parse_precipitation(
                period.get(
                    "Precipitation"
                )
            )

        past_10_min = get_period(
            "Past10Min"
        )

        past_1hr = get_period(
            "Past1hr"
        )

        past_3hr = get_period(
            "Past3hr"
        )

        past_6hr = get_period(
            "Past6hr"
        )

        past_12hr = get_period(
            "Past12hr"
        )

        past_24hr = get_period(
            "Past24hr"
        )

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        date_str = ""

        if date_time:

            date_str = str(
                date_time
            )[:10]

        # ----------------------------------------------------
        # Normalize
        # ----------------------------------------------------

        output.append(
            {
                "StationID": str(
                    station_id
                ),

                "StationName": (
                    station_name
                ),

                "StationNameEN": (
                    station.get(
                        "StationNameEN",
                        "",
                    )
                    or ""
                ),

                "StationAttribute": (
                    station.get(
                        "StationAttribute",
                        "",
                    )
                    or "雨量觀測站"
                ),

                "DateTime": (
                    date_time
                ),

                "Date": (
                    date_str
                ),

                # 今日 0 時至目前
                "Precipitation": (
                    precipitation
                ),

                "PrecipitationRaw": (
                    ""
                    if raw_precipitation is None
                    else str(
                        raw_precipitation
                    )
                ),

                "Rain": (
                    precipitation > 0
                ),

                # 其他雨量
                "Past10Min": (
                    past_10_min
                ),

                "Past1hr": (
                    past_1hr
                ),

                "Past3hr": (
                    past_3hr
                ),

                "Past6hr": (
                    past_6hr
                ),

                "Past12hr": (
                    past_12hr
                ),

                "Past24hr": (
                    past_24hr
                ),

                # 地理資訊
                "CountyName": (
                    county_name
                ),

                "TownName": (
                    town_name
                ),

                "StationAltitude": (
                    station_altitude
                ),

                "DataSource": (
                    "CWA O-A0002-001"
                ),
            }
        )

    return output


# ============================================================
# 取得每個測站最新資料
# ============================================================

def latest_station_rows(
    rows: list[dict],
) -> dict[str, dict]:
    """
    如果同一測站出現多筆資料，
    取 DateTime 最新的一筆。
    """

    result = {}

    for row in rows:

        station_name = row.get(
            "StationName"
        )

        if not station_name:
            continue

        if station_name not in result:

            result[
                station_name
            ] = row

            continue

        old_time = str(
            result[
                station_name
            ].get(
                "DateTime",
                "",
            )
        )

        new_time = str(
            row.get(
                "DateTime",
                "",
            )
        )

        if new_time >= old_time:

            result[
                station_name
            ] = row

    return result


# ============================================================
# 判斷測站是否達到雨量警戒
# ============================================================

def station_reaches_threshold(
    data: dict,
    thresholds: dict[str, float],
) -> bool:
    """
    判斷測站是否至少有一項雨量達到警戒門檻。

    任一項達到門檻：
        True

    四項全部低於門檻：
        False
    """

    rain = float(
        data.get(
            "Precipitation",
            0,
        )
    )

    past_10_min = float(
        data.get(
            "Past10Min",
            0,
        )
    )

    past_1hr = float(
        data.get(
            "Past1hr",
            0,
        )
    )

    past_24hr = float(
        data.get(
            "Past24hr",
            0,
        )
    )

    return (
        rain >= thresholds["RAIN"]
        or
        past_10_min >= thresholds["Past10Min"]
        or
        past_1hr >= thresholds["Past1hr"]
        or
        past_24hr >= thresholds["Past24hr"]
    )


# ============================================================
# 找出達警戒的雨量項目
# ============================================================

def get_triggered_items(
    data: dict,
    thresholds: dict[str, float],
) -> list[str]:
    """
    回傳測站目前達到警戒門檻的項目。
    """

    triggered = []

    rain = float(
        data.get(
            "Precipitation",
            0,
        )
    )

    past_10_min = float(
        data.get(
            "Past10Min",
            0,
        )
    )

    past_1hr = float(
        data.get(
            "Past1hr",
            0,
        )
    )

    past_24hr = float(
        data.get(
            "Past24hr",
            0,
        )
    )

    if rain >= thresholds["RAIN"]:

        triggered.append(
            (
                "今日累積雨量 "
                f"{rain:g} mm "
                "≥ "
                f"{thresholds['RAIN']:g} mm"
            )
        )

    if past_10_min >= thresholds["Past10Min"]:

        triggered.append(
            (
                "10分鐘雨量 "
                f"{past_10_min:g} mm "
                "≥ "
                f"{thresholds['Past10Min']:g} mm"
            )
        )

    if past_1hr >= thresholds["Past1hr"]:

        triggered.append(
            (
                "1小時雨量 "
                f"{past_1hr:g} mm "
                "≥ "
                f"{thresholds['Past1hr']:g} mm"
            )
        )

    if past_24hr >= thresholds["Past24hr"]:

        triggered.append(
            (
                "24小時雨量 "
                f"{past_24hr:g} mm "
                "≥ "
                f"{thresholds['Past24hr']:g} mm"
            )
        )

    return triggered


# ============================================================
# 建立每日 Telegram 報告
# ============================================================

def build_report(
    station_map: dict[str, dict],
    requested_stations: list[str],
    date_str: str,
    thresholds: dict[str, float],
) -> str:
    """
    建立每日 Telegram 報告。

    規則：

        四項雨量全部未達門檻
            → 不輸出該測站

        任一項達到門檻
            → 輸出該測站
    """

    now = get_taipei_now()

    lines = [
        "🌧️ 桃園每日雨量監測",
        "━━━━━━━━━━━━━━━━",
        f"📅 資料日期：{date_str}",
        (
            "🕐 更新時間："
            f"{now.strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        (
            "📍 查詢測站："
            f"{'、'.join(requested_stations)}"
        ),
        "",
        "🚨 雨量警戒門檻",
        (
            "   今日累積："
            f"{thresholds['RAIN']:g} mm"
        ),
        (
            "   10分鐘："
            f"{thresholds['Past10Min']:g} mm"
        ),
        (
            "   1小時："
            f"{thresholds['Past1hr']:g} mm"
        ),
        (
            "   24小時："
            f"{thresholds['Past24hr']:g} mm"
        ),
        "",
    ]

    found_count = 0

    for station_name in requested_stations:

        data = station_map.get(
            station_name
        )

        if not data:
            continue

        # ----------------------------------------------------
        # 四項全部未達門檻
        # → 完全不輸出該測站
        # ----------------------------------------------------

        if not station_reaches_threshold(
            data,
            thresholds,
        ):

            continue

        found_count += 1

        rain = float(
            data.get(
                "Precipitation",
                0,
            )
        )

        past_10_min = float(
            data.get(
                "Past10Min",
                0,
            )
        )

        past_1hr = float(
            data.get(
                "Past1hr",
                0,
            )
        )

        past_24hr = float(
            data.get(
                "Past24hr",
                0,
            )
        )

        triggered_items = get_triggered_items(
            data,
            thresholds,
        )

        lines.extend(
            [
                f"📍 {station_name}",

                (
                    "   測站編號："
                    f"{data.get('StationID') or '無資料'}"
                ),

                (
                    "   觀測時間："
                    f"{data.get('DateTime') or '無資料'}"
                ),

                (
                    "   🌧️ 今日累積雨量："
                    f"{rain:g} mm"
                ),

                (
                    "   🌧️ 10分鐘雨量："
                    f"{past_10_min:g} mm"
                ),

                (
                    "   🌧️ 1小時雨量："
                    f"{past_1hr:g} mm"
                ),

                (
                    "   🌧️ 24小時雨量："
                    f"{past_24hr:g} mm"
                ),

                "   🚨 達警戒：",
            ]
        )

        for item in triggered_items:

            lines.append(
                f"      • {item}"
            )

        lines.append(
            "────────────────"
        )

    # --------------------------------------------------------
    # 沒有任何測站達到門檻
    # --------------------------------------------------------

    if found_count == 0:

        lines.extend(
            [
                "✅ 目前指定測站均未達任何雨量警戒門檻。",
                "",
            ]
        )

    lines.extend(
        [
            (
                f"📊 達警戒測站："
                f"{found_count} 筆"
            ),
            (
                "🔎 資料來源："
                "中央氣象署 O-A0002-001"
            ),
        ]
    )

    return "\n".join(
        lines
    )


# ============================================================
# 找出所有達警戒測站
# ============================================================

def find_alerts(
    station_map: dict[str, dict],
    thresholds: dict[str, float],
) -> list[dict]:
    """
    找出至少一項雨量達到警戒門檻的測站。

    這裡檢查 TARGET_STATIONS 的全部測站。
    """

    triggered = []

    for station_name in TARGET_STATIONS:

        data = station_map.get(
            station_name
        )

        if not data:
            continue

        if station_reaches_threshold(
            data,
            thresholds,
        ):

            triggered.append(
                data
            )

    return triggered


# ============================================================
# 建立高雨量警報
# ============================================================

def build_alert(
    triggered: list[dict],
    thresholds: dict[str, float],
) -> str:
    """
    建立雨量警報。

    任一雨量項目達到各自門檻即可進入警報。
    """

    lines = [
        "🚨 桃園雨量警報",
        "━━━━━━━━━━━━━━━━",
        "⚠️ 以下測站至少一項雨量達到警戒門檻",
        "",
    ]

    for station in triggered:

        station_name = station.get(
            "StationName",
            "無資料",
        )

        rain = float(
            station.get(
                "Precipitation",
                0,
            )
        )

        past_10_min = float(
            station.get(
                "Past10Min",
                0,
            )
        )

        past_1hr = float(
            station.get(
                "Past1hr",
                0,
            )
        )

        past_24hr = float(
            station.get(
                "Past24hr",
                0,
            )
        )

        alert_items = []

        if rain >= thresholds["RAIN"]:

            alert_items.append(
                (
                    "今日累積 "
                    f"{rain:g} mm"
                    " ≥ "
                    f"{thresholds['RAIN']:g} mm"
                )
            )

        if past_10_min >= thresholds["Past10Min"]:

            alert_items.append(
                (
                    "10分鐘 "
                    f"{past_10_min:g} mm"
                    " ≥ "
                    f"{thresholds['Past10Min']:g} mm"
                )
            )

        if past_1hr >= thresholds["Past1hr"]:

            alert_items.append(
                (
                    "1小時 "
                    f"{past_1hr:g} mm"
                    " ≥ "
                    f"{thresholds['Past1hr']:g} mm"
                )
            )

        if past_24hr >= thresholds["Past24hr"]:

            alert_items.append(
                (
                    "24小時 "
                    f"{past_24hr:g} mm"
                    " ≥ "
                    f"{thresholds['Past24hr']:g} mm"
                )
            )

        lines.extend(
            [
                f"📍 測站：{station_name}",

                (
                    "🆔 測站編號："
                    f"{station.get('StationID') or '無資料'}"
                ),

                (
                    "🕐 觀測時間："
                    f"{station.get('DateTime') or '無資料'}"
                ),

                "🚨 達標項目：",
            ]
        )

        for item in alert_items:

            lines.append(
                f"   • {item}"
            )

        lines.extend(
            [
                "",
            ]
        )

    lines.append(
        "🔎 資料來源："
        "中央氣象署 O-A0002-001"
    )

    return "\n".join(
        lines
    )


# ============================================================
# Telegram API
# ============================================================

def send_telegram(
    bot_token: str,
    chat_id: str,
    text: str,
) -> None:
    """
    使用 Telegram Bot API 發送訊息。
    """

    if not bot_token:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN 未設定"
        )

    if not chat_id:

        raise RuntimeError(
            "TELEGRAM_CHAT_ID 未設定"
        )

    url = (
        "https://api.telegram.org/"
        f"bot{bot_token}/sendMessage"
    )

    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": text,
        }
    ).encode(
        "utf-8"
    )

    request = Request(
        url,
        data=payload,
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",

            "User-Agent":
                "taoyuan-rain-monitor/"
                "github-actions",
        },
        method="POST",
    )

    try:

        with urlopen(
            request,
            timeout=30,
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            result = json.loads(
                body
            )

            if not result.get(
                "ok",
                False,
            ):

                raise RuntimeError(
                    "Telegram API 回傳失敗："
                    f"{result}"
                )

    except HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            "Telegram HTTP "
            f"{exc.code}: "
            f"{body[:2000]}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            "Telegram 連線失敗："
            f"{exc.reason}"
        ) from exc


# ============================================================
# 主程式
# ============================================================

def main() -> int:

    # --------------------------------------------------------
    # Environment
    # --------------------------------------------------------

    cwa_api_key = get_env(
        "CWA_API_KEY"
    )

    telegram_bot_token = get_env(
        "TELEGRAM_BOT_TOKEN"
    )

    telegram_chat_id = get_env(
        "TELEGRAM_CHAT_ID"
    )

    # --------------------------------------------------------
    # 四項雨量警戒門檻
    # --------------------------------------------------------

    rain_thresholds = get_rain_thresholds()

    debug_enabled = (
        os.getenv(
            "DEBUG_CWA",
            "false",
        )
        .strip()
        .lower()
        in (
            "1",
            "true",
            "yes",
            "y",
        )
    )

    # --------------------------------------------------------
    # 日期
    # --------------------------------------------------------

    today = get_today()

    print(
        f"查詢日期：{today}"
    )

    print(
        f"資料來源：CWA {CWA_DATASET_ID}"
    )

    print(
        "雨量警戒門檻："
    )

    print(
        "  RAIN_THRESHOLD_MM = "
        f"{rain_thresholds['RAIN']:g} mm"
    )

    print(
        "  Past10Min_THRESHOLD_MM = "
        f"{rain_thresholds['Past10Min']:g} mm"
    )

    print(
        "  Past1hr_THRESHOLD_MM = "
        f"{rain_thresholds['Past1hr']:g} mm"
    )

    print(
        "  Past24hr_THRESHOLD_MM = "
        f"{rain_thresholds['Past24hr']:g} mm"
    )

    # --------------------------------------------------------
    # CWA API
    # --------------------------------------------------------

    payload = fetch_cwa_data(
        cwa_api_key
    )

    # --------------------------------------------------------
    # API 基本檢查
    # --------------------------------------------------------

    if not isinstance(
        payload,
        dict,
    ):

        raise RuntimeError(
            "CWA API 回傳格式錯誤"
        )

    if debug_enabled:

        debug_cwa_structure(
            payload
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    rows = normalize_data(
        payload
    )

    print(
        "CWA 回傳桃園目標資料筆數："
        f"{len(rows)}"
    )

    # --------------------------------------------------------
    # 如果沒有資料
    # --------------------------------------------------------

    if not rows:

        print(
            "⚠️ CWA API 有回應，"
            "但沒有解析到桃園目標測站。"
        )

        debug_cwa_structure(
            payload
        )

        raise RuntimeError(
            "CWA API 未取得桃園指定測站資料"
        )

    # --------------------------------------------------------
    # Debug
    # --------------------------------------------------------

    print("")

    print(
        "========== 測站資料 =========="
    )

    for row in rows[:30]:

        print(
            "DEBUG:",
            row.get(
                "StationName"
            ),
            "| ID:",
            row.get(
                "StationID"
            ),
            "| Time:",
            row.get(
                "DateTime"
            ),
            "| Today:",
            row.get(
                "Precipitation"
            ),
            "mm",
            "| 10min:",
            row.get(
                "Past10Min"
            ),
            "mm",
            "| 1hr:",
            row.get(
                "Past1hr"
            ),
            "mm",
            "| 24h:",
            row.get(
                "Past24hr"
            ),
            "mm",
        )

    print(
        "=============================="
    )

    # --------------------------------------------------------
    # 每測站只保留最新一筆
    # --------------------------------------------------------

    station_map = latest_station_rows(
        rows
    )

    print("")

    print(
        "成功辨識測站："
        + "、".join(
            station_map.keys()
        )
    )

    print(
        "測站數量："
        f"{len(station_map)}"
    )

    # --------------------------------------------------------
    # Telegram 每日報告
    #
    # 注意：
    # 只有至少一項雨量達到門檻的測站才會輸出。
    # --------------------------------------------------------

    report = build_report(
        station_map=station_map,

        requested_stations=(
            DEFAULT_REPORT_STATIONS
        ),

        date_str=today,

        thresholds=rain_thresholds,
    )

    print("")

    print(
        "========== Telegram Report =========="
    )

    print(report)

    print(
        "======================================"
    )

    send_telegram(
        bot_token=telegram_bot_token,
        chat_id=telegram_chat_id,
        text=report,
    )

    print(
        "✅ Telegram 每日雨量報告已發送"
    )

    # --------------------------------------------------------
    # 雨量警報
    #
    # TARGET_STATIONS 全部測站都會檢查。
    # 任一雨量項目達到對應門檻即觸發。
    # --------------------------------------------------------

    triggered = find_alerts(
        station_map=station_map,
        thresholds=rain_thresholds,
    )

    if triggered:

        alert = build_alert(
            triggered=triggered,
            thresholds=rain_thresholds,
        )

        print("")

        print(
            "========== Rain Alert =========="
        )

        print(alert)

        print(
            "================================"
        )

        send_telegram(
            bot_token=telegram_bot_token,
            chat_id=telegram_chat_id,
            text=alert,
        )

        print(
            "🚨 高雨量警報已發送"
        )

    else:

        print(
            "✅ 沒有測站達到任何雨量警戒門檻"
        )

    print("")

    print(
        "✅ Workflow 執行完成"
    )

    return 0


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "⚠️ 使用者中止執行"
        )

        raise SystemExit(130)

    except Exception as exc:

        print(
            "❌ Workflow 執行失敗："
            f"{exc}"
        )

        raise
