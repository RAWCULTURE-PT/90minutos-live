#!/usr/bin/env python3
"""
Scraper diario Sport TV -> channels.json
Corre via GitHub Actions duas vezes por dia (08h e 14h hora de Lisboa).
"""
import json
import sys
import urllib.request
import urllib.parse
from datetime import date, timedelta, datetime

CHANNEL_ID_MAP = {
    "727":  "Sport TV 1",
    "5418": "Sport TV 1",
    "5419": "Sport TV 2",
    "5420": "Sport TV 3",
    "5421": "Sport TV 4",
    "5422": "Sport TV 5",
    "5423": "Sport TV 6",
}

ISO_TO_CODE = {
    "MEX": "MEX", "KOR": "KOR", "CZE": "CZE", "CAN": "CAN",
    "BIH": "BIH", "QAT": "QAT", "USA": "USA", "AUS": "AUS",
    "TUR": "TUR", "BRA": "BRA", "MAR": "MAR", "SCO": "SCO",
    "CUW": "CUW", "CIV": "CIV", "ECU": "ECU", "JPN": "JPN",
    "SWE": "SWE", "TUN": "TUN", "ESP": "ESP", "CPV": "CPV",
    "BEL": "BEL", "EGY": "EGY", "IRN": "IRN", "NZL": "NZL",
    "FRA": "FRA", "SEN": "SEN", "IRQ": "IRQ", "NOR": "NOR",
    "ARG": "ARG", "AUT": "AUT", "JOR": "JOR", "COD": "COD",
    "UZB": "UZB", "COL": "COL", "ENG": "ENG", "GHA": "GHA",
    "PAN": "PAN",
    # ISO -> codigo FIFA/app
    "ZAF": "RSA", "CHE": "SUI", "PRY": "PAR", "HTI": "HAI",
    "DEU": "GER", "NLD": "NED", "SAU": "KSA", "URY": "URU",
    "DZA": "ALG", "PRT": "POR", "HRV": "CRO",
    # Abreviaturas portuguesas usadas pela Sport TV em isoCountryCode
    "EUA": "USA", "ING": "ENG", "ALE": "GER", "ESC": "SCO",
}

WC_TEAMS = set(ISO_TO_CODE.values())

# Stage ID da fase de grupos do Mundial 2026 na API Sport TV.
# Quando as eliminatorias comecar, aparece um novo ID — o script alerta.
WC_STAGE_IDS = {
    "mg:stage:55z571cno4oj",   # fase de grupos
    "mg:stage:boic86sby4nb",   # eliminatórias (placeholder/TBD)
    "mg:stage:jqjmib2me4y0",   # eliminatórias (quartos/meias/final)
    "mg:stage:ak3kmjuam700",   # eliminatórias (match host USA/CAN)
    "mg:stage:j47c80l4ni32",   # eliminatórias (terceiro lugar / outro sub-quadro)
}

# Canais corretos para jogos em destaque (fonte: Record.pt / guia TV).
# A API Sport TV devolve 5422 (Sport TV 5) para quase tudo, mas estes jogos
# passam em Sport TV 1 (e alguns em canais generalistas).
CHANNEL_OVERRIDE = {
    "GER-CUW": ["Sport TV 1"],
    "FRA-SEN": ["RTP 1", "Sport TV 1"],
    "POR-COD": ["SIC", "Sport TV 1"],
    "CZE-RSA": ["Sport TV 1"],
    "SUI-BIH": ["RTP 1", "Sport TV 1"],
    "BRA-HAI": ["Sport TV 1"],
    "GER-CIV": ["TVI", "Sport TV 1"],
    "ESP-KSA": ["Sport TV 1"],
    "ARG-AUT": ["Sport TV 1"],
    "FRA-IRQ": ["Sport TV 1"],
    "NOR-SEN": ["Sport TV 1"],
    "JOR-ALG": ["Sport TV 1"],
    "POR-UZB": ["TVI", "Sport TV 1"],
    "ENG-GHA": ["Sport TV 1"],
    "COL-POR": ["RTP 1", "Sport TV 1"],
    "ECU-GER": ["SIC", "Sport TV 1"],
    "NOR-FRA": ["TVI", "Sport TV 1"],
    "SCO-BRA": ["Sport TV 1"],
}

# Canais generalistas para jogos de Portugal (fallback se não estiver em CHANNEL_OVERRIDE).
FREE_TO_AIR = {
    "POR-COD": ["SIC"],
    "POR-UZB": ["TVI"],
    "COL-POR": ["RTP 1"],
}

API_URL    = "https://www.sporttv.pt/api/sports/soccer/v1/event/daily?day={day}"
DAYS_AHEAD = 40


def get_channel_name(channel_id):
    if not channel_id:
        return "Sport TV 5"
    name = CHANNEL_ID_MAP.get(str(channel_id))
    if name:
        return name
    sys.stderr.write(f"  [!] ID de canal desconhecido: {channel_id}\n")
    return "Sport TV"


def fetch_day(d):
    day_str = d.strftime("%Y-%m-%dT00:00:00+0100")
    url = API_URL.format(day=urllib.parse.quote(day_str))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        sys.stderr.write(f"  [!] Erro ao buscar {d}: {e}\n")
        return []


def main():
    channels = {}
    today = date.today()
    sys.stderr.write(f"Sport TV scraper — {today} (+{DAYS_AHEAD} dias)\n\n")

    for i in range(DAYS_AHEAD):
        d = today + timedelta(days=i)
        day_matches = 0

        for event in fetch_day(d):
            stage_id    = (event.get("stage")       or {}).get("id", "")
            local_iso   = (event.get("localTeam")   or {}).get("isoCountryCode", "")
            visitor_iso = (event.get("visitorTeam") or {}).get("isoCountryCode", "")
            channel_id  = str(event.get("tvChannelId") or "")

            lc = ISO_TO_CODE.get(local_iso,   local_iso)
            vc = ISO_TO_CODE.get(visitor_iso, visit