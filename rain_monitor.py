#!/usr/bin/env python3

import json
import os
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ============================================================
# CWA API
# ============================================================

# 雨量觀測站－雨量資料
#
# 更新頻率：10 分鐘
# 包含：
# - 本日 0 時至目前累積雨量
# - 10 分鐘累積雨量
# - 1 小時累積雨量
# - 3 小時累積雨量
# - 6 小時累積雨量
# - 12 小時累積雨量
# - 24 小時累積雨量
#
# CWA 官方資料集：
# O-A0002-001
#
CWA_API_URL = (
    "https://opendata.cwa.gov.tw/api/v1/rest/datastore/"
    "O-A0002-001"
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
# GitHub Actions 自動回報測站
# ============================================================

DEFAULT_REPORT_STATIONS = [
    "新屋",
    "八德",
    "蘆竹",
    "龜山",
    "中壢",
]


# ============================================================
# Environment
# ============================================================

def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()

    if required and not value:
        raise RuntimeError(
            f"缺少環境變數：{name}"
        )

    return value


# ============================================================
# 台灣日期時間
# ============================================================

def get_taipei_now():
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(
            ZoneInfo("Asia/Taipei")
        )

    except Exception:
        return datetime.now()


def get_today() -> str:
    return get_taipei_now().strftime(
        "%Y-%m-%d"
    )


# ============================================================
# CWA API
# ============================================================

def fetch_cwa_data(api_key: str) -> dict:

    params = {
        "format": "JSON",
        "Authorization": api_key,
    }

    url = (
        f"{CWA_API_URL}?"
        f"{urlencode(params)}"
    )

    request = Request(
        url,
        headers={
            "Authorization": api_key,
            "Accept": "application/json",
            "User-Agent": (
                "taoyuan-rain-monitor/"
                "github-actions"
            ),
        },
        method="GET",
    )

    print("CWA API:")
    print(CWA_API_URL)

    try:

        with urlopen(
            request,
            timeout=30
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            return json.loads(body)

    except HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"CWA API HTTP {exc.code}: "
            f"{body[:1000]}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            f"CWA API 連線失敗："
            f"{exc.reason}"
        ) from exc


# ============================================================
# 雨量資料解析
# ============================================================

def parse_precipitation(raw):

    if raw is None:
        return 0.0

    value = str(raw).strip()

    # T = 雨跡
    if value == "T":
        return 0.0

    # 空值
    if value == "":
        return 0.0

    # X = 儀器故障
    if value.upper() == "X":
        return 0.0

    try:

        number = float(value)

        if number != number:
            return 0.0

        return number

    except (
        TypeError,
        ValueError
    ):

        return 0.0


# ============================================================
# Normalize CWA O-A0002-001
# ============================================================

def normalize_data(payload: dict) -> list[dict]:

    records = payload.get(
        "records",
        {}
    )

    # --------------------------------------------------------
    # O-A0002-001 常見結構
    #
    # records.locations.station
    #
    # 同時支援 locations / location
    # --------------------------------------------------------

    locations = (
        records.get("locations")
        or records.get("location")
        or []
    )

    if isinstance(locations, dict):
        locations = [locations]

    output = []

    for location in locations:

        station = (
            location.get(
                "station",
                {}
            )
            or {}
        )

        station_name = (
            station.get(
                "StationName"
            )
            or location.get(
                "StationName"
            )
            or ""
        )

        if (
            station_name
            not in TARGET_STATIONS
        ):
            continue

        station_id = (
            station.get(
                "StationId"
            )
            or station.get(
                "StationID"
            )
            or location.get(
                "StationId"
            )
            or ""
        )

        station_name_en = (
            station.get(
                "StationNameEN"
            )
            or ""
        )

        station_attribute = (
            station.get(
                "StationAttribute"
            )
            or ""
        )

        # ----------------------------------------------------
        # O-A0002-001
        #
        # 可能直接把資料放在：
        #
        # location.StationObsTimes
        #
        # 或：
        #
        # location.stationObsTimes
        # ----------------------------------------------------

        observations = (
            location.get(
                "stationObsTimes"
            )
            or location.get(
                "StationObsTimes"
            )
            or []
        )

        if isinstance(
            observations,
            dict
        ):

            observations = (
                observations.get(
                    "stationObsTime"
                )
                or observations.get(
                    "StationObsTime"
                )
                or []
            )

        if isinstance(
            observations,
            dict
        ):
            observations = [
                observations
            ]

        # ----------------------------------------------------
        # 如果 API 直接將測站資料放在 location
        # ----------------------------------------------------

        if not observations:

            date_time = (
                location.get(
                    "DateTime"
                )
                or location.get(
                    "Date"
                )
                or ""
            )

            raw_precipitation = (
                location.get(
                    "Precipitation"
                )
            )

            if (
                date_time
                or raw_precipitation
                is not None
            ):

                precipitation = (
                    parse_precipitation(
                        raw_precipitation
                    )
                )

                output.append(
                    {
                        "StationID": station_id,
                        "StationName": station_name,
                        "StationNameEN": station_name_en,
                        "StationAttribute": station_attribute,
                        "DateTime": date_time,
                        "Date": (
                            str(date_time)[:10]
                            if date_time
                            else ""
                        ),
                        "Precipitation": precipitation,
                        "PrecipitationRaw": (
                            ""
                            if raw_precipitation
                            is None
                            else str(
                                raw_precipitation
                            )
                        ),
                        "Rain": precipitation > 0,
                        "DataSource": "CWA O-A0002-001",
                    }
                )

            continue

        # ----------------------------------------------------
        # 解析 stationObsTime
        # ----------------------------------------------------

        for obs in observations:

            weather_elements = (
                obs.get(
                    "weatherElements",
                    {}
                )
                or {}
            )

            raw_precipitation = (
                weather_elements.get(
                    "Precipitation"
                )
            )

            # 某些資料格式可能直接放在 obs
            if (
                raw_precipitation
                is None
            ):
                raw_precipitation = (
                    obs.get(
                        "Precipitation"
                    )
                )

            date_time = (
                obs.get(
                    "DateTime"
                )
                or obs.get(
                    "Date"
                )
                or ""
            )

            precipitation = (
                parse_precipitation(
                    raw_precipitation
                )
            )

            output.append(
                {
                    "StationID": station_id,
                    "StationName": station_name,
                    "StationNameEN": station_name_en,
                    "StationAttribute": station_attribute,
                    "DateTime": date_time,
                    "Date": (
                        str(date_time)[:10]
                        if date_time
                        else ""
                    ),
                    "Precipitation": precipitation,
                    "PrecipitationRaw": (
                        ""
                        if raw_precipitation
                        is None
                        else str(
                            raw_precipitation
                        )
                    ),
                    "Rain": precipitation > 0,
                    "DataSource": "CWA O-A0002-001",
                }
            )

    return output


# ============================================================
# 取每個測站最新資料
# ============================================================

def latest_station_rows(
    rows: list[dict]
) -> dict[str, dict]:

    result = {}

    for row in rows:

        name = row.get(
            "StationName"
        )

        if not name:
            continue

        if name not in result:

            result[name] = row

            continue

        old_time = str(
            result[name].get(
                "DateTime",
                ""
            )
        )

        new_time = str(
            row.get(
                "DateTime",
                ""
            )
        )

        if new_time >= old_time:

            result[name] = row

    return result


# ============================================================
# 建立 Telegram 每日報告
# ============================================================

def build_report(
    station_map: dict[str, dict],
    requested_stations: list[str],
    date_str: str,
) -> str:

    lines = [
        "🌧️ 桃園每日雨量監測",
        "━━━━━━━━━━━━━━━━",
        f"📅 資料日期：{date_str}",
        (
            "🕐 更新時間："
            f"{get_taipei_now().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        (
            "📍 查詢測站："
            f"{'、'.join(requested_stations)}"
        ),
        "",
    ]

    found_count = 0

    not_found = []

    for station_name in requested_stations:

        data = station_map.get(
            station_name
        )

        if not data:

            not_found.append(
                station_name
            )

            continue

        found_count += 1

        rain = float(
            data.get(
                "Precipitation",
                0
            )
        )

        rain_icon = (
            "🌧️"
            if rain > 0
            else "☀️"
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
                    f"   {rain_icon} "
                    "今日累積雨量："
                    f"{rain:g} mm"
                ),
                (
                    "   測站類型："
                    f"{data.get('StationAttribute') or '雨量觀測站'}"
                ),
                "────────────────",
            ]
        )

    if not_found:

        lines.extend(
            [
                (
                    "⚠️ 無資料："
                    f"{'、'.join(not_found)}"
                ),
                "",
            ]
        )

    lines.extend(
        [
            (
                f"📊 已取得 {found_count} "
                "筆測站資料"
            ),
            (
                "🔎 資料來源："
                "中央氣象署 O-A0002-001"
            ),
        ]
    )

    return "\n".join(lines)


# ============================================================
# 高雨量警報
# ============================================================

def find_alerts(
    station_map: dict[str, dict],
    threshold: float,
) -> list[dict]:

    triggered = []

    for station_name in TARGET_STATIONS:

        data = station_map.get(
            station_name
        )

        if not data:
            continue

        precipitation = float(
            data.get(
                "Precipitation",
                0
            )
        )

        if precipitation >= threshold:

            triggered.append(
                data
            )

    return triggered


def build_alert(
    triggered: list[dict],
    threshold: float,
) -> str:

    lines = [
        "🚨 桃園今日雨量警報",
        "━━━━━━━━━━━━━━━━",
        (
            f"⚠️ 今日累積雨量達 "
            f"{threshold:g} mm 以上"
        ),
        "",
    ]

    for station in triggered:

        lines.extend(
            [
                (
                    "📍 測站："
                    f"{station['StationName']}"
                ),
                (
                    "🕐 觀測時間："
                    f"{station.get('DateTime') or '無資料'}"
                ),
                (
                    "🌧️ 今日累積雨量："
                    f"{float(station['Precipitation']):g} mm"
                ),
                (
                    "🆔 測站編號："
                    f"{station.get('StationID') or '無資料'}"
                ),
                "",
            ]
        )

    lines.append(
        "🔎 資料來源："
        "中央氣象署 O-A0002-001"
    )

    return "\n".join(lines)


# ============================================================
# Telegram
# ============================================================

def send_telegram(
    bot_token: str,
    chat_id: str,
    text: str,
) -> None:

    url = (
        "https://api.telegram.org/"
        f"bot{bot_token}/sendMessage"
    )

    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": text,
        }
    ).encode("utf-8")

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
            timeout=30
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            result = json.loads(
                body
            )

            if not result.get("ok"):

                raise RuntimeError(
                    "Telegram API 回傳失敗："
                    f"{result}"
                )

    except HTTPError as exc:

        body = exc.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"Telegram HTTP {exc.code}: "
            f"{body[:1000]}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            f"Telegram 連線失敗："
            f"{exc.reason}"
        ) from exc


# ============================================================
# Main
# ============================================================

def main() -> int:

    api_key = get_env(
        "CWA_API_KEY"
    )

    bot_token = get_env(
        "TELEGRAM_BOT_TOKEN"
    )

    chat_id = get_env(
        "TELEGRAM_CHAT_ID"
    )

    threshold = float(
        os.getenv(
            "RAIN_THRESHOLD_MM",
            "100"
        )
    )

    today = get_today()

    print(
        f"查詢日期：{today}"
    )

    print(
        "資料來源：CWA O-A0002-001"
    )

    print(
        f"雨量警戒門檻："
        f"{threshold:g} mm"
    )

    # --------------------------------------------------------
    # CWA
    # --------------------------------------------------------

    payload = fetch_cwa_data(
        api_key
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    rows = normalize_data(
        payload
    )

    print(
        f"CWA 回傳桃園目標資料筆數："
        f"{len(rows)}"
    )

    if not rows:

        # ----------------------------------------------------
        # 額外輸出 API 結構，方便 GitHub Actions debug
        # ----------------------------------------------------

        print(
            "⚠️ CWA API 有回應，但沒有解析到目標測站。"
        )

        print(
            "records keys：",
            list(
                payload.get(
                    "records",
                    {}
                ).keys()
            )
        )

        raise RuntimeError(
            "CWA API 未取得桃園指定測站資料"
        )

    # --------------------------------------------------------
    # 最新測站資料
    # --------------------------------------------------------

    station_map = latest_station_rows(
        rows
    )

    print(
        "成功辨識測站："
        + "、".join(
            station_map.keys()
        )
    )

    # --------------------------------------------------------
    # 每日報告
    # --------------------------------------------------------

    report = build_report(
        station_map=station_map,
        requested_stations=(
            DEFAULT_REPORT_STATIONS
        ),
        date_str=today,
    )

    print("")
    print(report)

    send_telegram(
        bot_token=bot_token,
        chat_id=chat_id,
        text=report,
    )

    # --------------------------------------------------------
    # 高雨量警報
    # --------------------------------------------------------

    triggered = find_alerts(
        station_map=station_map,
        threshold=threshold,
    )

    if triggered:

        alert = build_alert(
            triggered=triggered,
            threshold=threshold,
        )

        print("")
        print(alert)

        send_telegram(
            bot_token=bot_token,
            chat_id=chat_id,
            text=alert,
        )

    else:

        print(
            f"沒有測站達到 "
            f"{threshold:g} mm 警戒門檻。"
        )

    return 0


if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except Exception as exc:

        print(
            f"❌ Workflow 執行失敗：{exc}"
        )

        raise
