#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/C-B0025-001"

# 預設監測測站
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

# GitHub Actions 自動回報的五站
DEFAULT_REPORT_STATIONS = [
    "新屋",
    "八德",
    "蘆竹",
    "龜山",
    "中壢",
]


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()

    if required and not value:
        raise RuntimeError(f"缺少環境變數：{name}")

    return value


def get_today() -> str:
    """
    GitHub Runner 使用 UTC，但雨量資料以台灣日期為主。
    使用 ZoneInfo 取得 Asia/Taipei 今日日期。
    """
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def fetch_cwa_data(api_key: str, date_str: str) -> dict:
    params = {
        "format": "JSON",
        "DataType": "stationObsTimes",
        "timeFrom": date_str,
    }

    url = f"{CWA_API_URL}?{urlencode(params)}"

    request = Request(
        url,
        headers={
            "Authorization": api_key,
            "Accept": "application/json",
            "User-Agent": "taoyuan-rain-monitor/github-actions",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"CWA API HTTP {exc.code}: {body[:1000]}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"CWA API 連線失敗：{exc.reason}"
        ) from exc


def parse_precipitation(raw):
    """
    CWA 的 T 視為微量雨。
    原 n8n 流程將 T 轉成 0 mm，這裡保持相同邏輯。
    """
    if raw is None:
        return 0.0

    raw_str = str(raw).strip()

    if raw_str in ("", "T"):
        return 0.0

    try:
        value = float(raw_str)

        if value != value:  # NaN
            return 0.0

        return value

    except (TypeError, ValueError):
        return 0.0


def normalize_data(payload: dict) -> list[dict]:
    records = payload.get("records", {})

    locations = records.get("location", [])

    if not isinstance(locations, list):
        locations = [locations]

    output = []

    for location in locations:
        station = location.get("station", {}) or {}

        station_name = station.get("StationName", "")

        if station_name not in TARGET_STATIONS:
            continue

        observations = (
            location
            .get("stationObsTimes", {})
            .get("stationObsTime", [])
        )

        if not isinstance(observations, list):
            observations = [observations]

        for obs in observations:
            weather_elements = obs.get("weatherElements", {}) or {}

            raw = weather_elements.get("Precipitation")

            precipitation = parse_precipitation(raw)

            date_value = obs.get("Date", "")

            output.append(
                {
                    "StationID": station.get("StationID", ""),
                    "StationName": station_name,
                    "StationNameEN": station.get(
                        "StationNameEN", ""
                    ),
                    "StationAttribute": station.get(
                        "StationAttribute", ""
                    ),
                    "Date": date_value,
                    "Precipitation": precipitation,
                    "PrecipitationRaw": (
                        "" if raw is None else str(raw)
                    ),
                    "Rain": precipitation > 0,
                    "YearMonth": (
                        str(date_value)[:7]
                        if date_value
                        else ""
                    ),
                    "DataSource": "CWA C-B0025-001",
                }
            )

    return output


def latest_station_rows(rows: list[dict]) -> dict[str, dict]:
    """
    同一測站若 API 回傳多筆資料，只保留日期最新的一筆。
    """
    result = {}

    for row in rows:
        name = row["StationName"]

        if name not in result:
            result[name] = row
            continue

        old_date = str(result[name].get("Date", ""))
        new_date = str(row.get("Date", ""))

        if new_date >= old_date:
            result[name] = row

    return result


def build_report(
    station_map: dict[str, dict],
    requested_stations: list[str],
    date_str: str,
) -> str:
    lines = [
        "🌧️ 桃園每日雨量監測",
        "━━━━━━━━━━━━━━━━",
        f"📅 資料日期：{date_str}",
        f"📍 查詢測站：{'、'.join(requested_stations)}",
        "",
    ]

    found_count = 0
    not_found = []

    for station_name in requested_stations:
        data = station_map.get(station_name)

        if not data:
            not_found.append(station_name)
            continue

        found_count += 1

        rain = data["Precipitation"]

        rain_icon = "🌧️" if rain > 0 else "☀️"

        lines.extend(
            [
                f"📍 {station_name}",
                f"   測站編號：{data.get('StationID') or '無資料'}",
                f"   日期：{data.get('Date') or '無資料'}",
                f"   {rain_icon} 今日累積雨量：{rain:g} mm",
                f"   測站類型：{data.get('StationAttribute') or '無資料'}",
                "────────────────",
            ]
        )

    if not_found:
        lines.extend(
            [
                f"⚠️ 無資料：{'、'.join(not_found)}",
                "",
            ]
        )

    lines.extend(
        [
            f"📊 已取得 {found_count} 筆測站資料",
            "🔎 資料來源：中央氣象署 C-B0025-001",
        ]
    )

    return "\n".join(lines)


def find_alerts(
    station_map: dict[str, dict],
    threshold: float,
) -> list[dict]:
    triggered = []

    for station_name in TARGET_STATIONS:
        data = station_map.get(station_name)

        if not data:
            continue

        if data["Precipitation"] >= threshold:
            triggered.append(data)

    return triggered


def build_alert(
    triggered: list[dict],
    threshold: float,
) -> str:
    lines = [
        "🚨 桃園今日雨量警報",
        "━━━━━━━━━━━━━━━━",
        f"⚠️ 今日累積雨量達 {threshold:g} mm 以上",
        "",
    ]

    for station in triggered:
        lines.extend(
            [
                f"📍 測站：{station['StationName']}",
                f"📅 日期：{station.get('Date') or '無資料'}",
                (
                    "🌧️ 今日累積雨量："
                    f"{station['Precipitation']:g} mm"
                ),
                (
                    "🆔 測站編號："
                    f"{station.get('StationID') or '無資料'}"
                ),
                "",
            ]
        )

    lines.append("🔎 資料來源：中央氣象署 C-B0025-001")

    return "\n".join(lines)


def send_telegram(
    bot_token: str,
    chat_id: str,
    text: str,
) -> None:
    url = (
        f"https://api.telegram.org/bot"
        f"{bot_token}/sendMessage"
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
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
            "User-Agent": "taoyuan-rain-monitor/github-actions",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body)

            if not result.get("ok"):
                raise RuntimeError(
                    f"Telegram API 回傳失敗：{result}"
                )

    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        raise RuntimeError(
            f"Telegram HTTP {exc.code}: {body[:1000]}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Telegram 連線失敗：{exc.reason}"
        ) from exc


def main() -> int:
    api_key = get_env("CWA_API_KEY")
    bot_token = get_env("TELEGRAM_BOT_TOKEN")
    chat_id = get_env("TELEGRAM_CHAT_ID")

    # 原 n8n Rain Alert Engine 實際使用 100。
    # 可在 GitHub Actions Variables 改成 350。
    threshold = float(
        os.getenv("RAIN_THRESHOLD_MM", "100")
    )

    date_str = get_today()

    print(f"查詢日期：{date_str}")
    print(f"雨量警戒門檻：{threshold:g} mm")

    payload = fetch_cwa_data(
        api_key=api_key,
        date_str=date_str,
    )

    rows = normalize_data(payload)

    if not rows:
        raise RuntimeError(
            "CWA API 未取得桃園指定測站今日資料"
        )

    station_map = latest_station_rows(rows)

    # --------------------------------------------
    # 自動回報五站
    # --------------------------------------------
    report = build_report(
        station_map=station_map,
        requested_stations=DEFAULT_REPORT_STATIONS,
        date_str=date_str,
    )

    print("")
    print(report)

    send_telegram(
        bot_token=bot_token,
        chat_id=chat_id,
        text=report,
    )

    # --------------------------------------------
    # 高雨量警報
    # --------------------------------------------
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
            f"\n沒有測站達到 {threshold:g} mm 警戒門檻。"
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"❌ Workflow 執行失敗：{exc}", file=sys.stderr)
        raise
