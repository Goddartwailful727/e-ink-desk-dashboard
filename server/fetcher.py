from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx


OPENWEATHER_API_KEY = ""
BEIJING_LAT = float(os.environ.get('WEATHER_LAT', '39.9042'))
BEIJING_LON = float(os.environ.get('WEATHER_LON', '116.4074'))


async def fetch_weather() -> dict[str, Any] | None:
    if not OPENWEATHER_API_KEY:
        return None

    params = {
        "lat": BEIJING_LAT,
        "lon": BEIJING_LON,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
        "lang": "zh_cn",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            current_resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params=params,
            )
            forecast_resp = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params=params,
            )
            current_resp.raise_for_status()
            forecast_resp.raise_for_status()
            return {
                "current": current_resp.json(),
                "forecast": forecast_resp.json(),
            }
    except (httpx.HTTPError, ValueError):
        return None


POEMS = [
    ("长风破浪会有时，直挂云帆济沧海。", "李白"),
    ("纸上得来终觉浅，绝知此事要躬行。", "陆游"),
    ("会当凌绝顶，一览众山小。", "杜甫"),
    ("沉舟侧畔千帆过，病树前头万木春。", "刘禹锡"),
    ("不畏浮云遮望眼，自缘身在最高层。", "王安石"),
    ("欲穷千里目，更上一层楼。", "王之涣"),
    ("读书不觉已春深，一寸光阴一寸金。", "王贞白"),
    ("黑发不知勤学早，白首方悔读书迟。", "颜真卿"),
    ("千磨万击还坚劲，任尔东西南北风。", "郑燮"),
    ("路漫漫其修远兮，吾将上下而求索。", "屈原"),
    ("少年易老学难成，一寸光阴不可轻。", "朱熹"),
    ("三更灯火五更鸡，正是男儿读书时。", "颜真卿"),
    ("博观而约取，厚积而薄发。", "苏轼"),
    ("非淡泊无以明志，非宁静无以致远。", "诸葛亮"),
    ("业精于勤荒于嬉，行成于思毁于随。", "韩愈"),
    ("天生我材必有用，千金散尽还复来。", "李白"),
    ("莫愁前路无知己，天下谁人不识君。", "高适"),
    ("海内存知己，天涯若比邻。", "王勃"),
    ("山重水复疑无路，柳暗花明又一村。", "陆游"),
    ("春风得意马蹄疾，一日看尽长安花。", "孟郊"),
    ("问渠那得清如许，为有源头活水来。", "朱熹"),
    ("及时当勉励，岁月不待人。", "陶渊明"),
    ("盛年不重来，一日难再晨。", "陶渊明"),
    ("大鹏一日同风起，扶摇直上九万里。", "李白"),
    ("咬定青山不放松，立根原在破岩中。", "郑燮"),
    ("宝剑锋从磨砺出，梅花香自苦寒来。", "佚名"),
    ("功名多向穷中立，祸患常从巧处生。", "陆游"),
    ("古人学问无遗力，少壮工夫老始成。", "陆游"),
    ("苟利国家生死以，岂因祸福避趋之。", "林则徐"),
    ("雄关漫道真如铁，而今迈步从头越。", "毛泽东"),
    ("千淘万漉虽辛苦，吹尽狂沙始到金。", "刘禹锡"),
]


def get_quote(now: datetime) -> dict[str, str]:
    text, author = POEMS[(now.day - 1) % len(POEMS)]
    return {"text": text, "author": author}
