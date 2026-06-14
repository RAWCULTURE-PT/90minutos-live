#!/usr/bin/env python3
"""
Scraper Sport TV -> channels.json  +  football-data.org -> results.json / standings.json
Corre via GitHub Actions de 2 em 2 horas durante o Mundial 2026.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import date, timedelta, datetime

FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

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
    "ZAF": "RSA", "CHE": "SUI", "PRY": "PAR", "HTI": "HAI",
    "DEU": "GER", "NLD": "NED", "SAU": "KSA", "URY": "URU",
    "DZA": "ALG", "PRT": "POR", "HRV": "CRO",
    "EUA": "USA", "ING": "ENG", "ALE": "GER", "ESC": "SCO",
}

WC_TEAMS = set(ISO_TO_CODE.values())

WC_STAGE_IDS = {
    "mg:stage:55z571cno4oj",
    "mg:stage:boic86sby4nb",
    "mg:stage:jqjmib2me4y0",
    "mg:stage:ak3kmjuam700",
    "mg:stage:j47c80l4ni32",
}

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
    sys.stderr.write("  [!] ID de canal desconhecido: " + str(channel_id) + "\n")
    return "Sport TV"


def fetch_day(d):
    day_str = d.strftime("%Y-%m-%dT00:00:00+0100")
    url = API_URL.format(day=urllib.parse.quote(day_str))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        sys.stderr.write("  [!] Erro ao buscar " + str(d) + ": " + str(e) + "\n")
        return []


def fetch_results_and_standings():
    if not FOOTBALL_DATA_KEY:
        sys.stderr.write("  [!] FOOTBALL_DATA_API_KEY nao definida\n")
        return {}, {}

    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY, "User-Agent": "Mozilla/5.0"}
    results = {}
    standings = {}

    # Resultados
    try:
        req = urllib.request.Request(FOOTBALL_DATA_URL + "/competitions/WC/matches", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        for m in data.get("matches", []):
            if m["status"] == "FINISHED":
                home = m["homeTeam"]["tla"]
                away = m["awayTeam"]["tla"]
                results[home + "-" + away] = {
                    "home": m["score"]["fullTime"]["home"],
                    "away": m["score"]["fullTime"]["away"],
                }
        sys.stderr.write("  -> " + str(len(results)) + " resultados finais\n")
    except Exception as e:
        sys.stderr.write("  [!] Erro resultados: " + str(e) + "\n")

    # Classificacoes
    try:
        req = urllib.request.Request(FOOTBALL_DATA_URL + "/competitions/WC/standings", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        for g in data.get("standings", []):
            letter = g["group"].replace("Group ", "")
            standings[letter] = [
                {
                    "pos": t["position"],
                    "tla": t["team"]["tla"],
                    "nome": t["team"]["shortName"],
                    "pj":  t["playedGames"],
                    "v":   t["won"],
                    "e":   t["draw"],
                    "d":   t["lost"],
                    "gf":  t["goalsFor"],
                    "gc":  t["goalsAgainst"],
                    "dg":  t["goalDifference"],
                    "pts": t["points"],
                }
                for t in g["table"]
            ]
        sys.stderr.write("  -> " + str(len(standings)) + " grupos na classificacao\n")
    except Exception as e:
        sys.stderr.write("  [!] Erro classificacoes: " + str(e) + "\n")

    return results, standings


def main():
    channels = {}
    today = date.today()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sys.stderr.write("Sport TV scraper -- " + str(today) + " (+" + str(DAYS_AHEAD) + " dias)\n\n")

    for i in range(DAYS_AHEAD):
        d = today + timedelta(days=i)
        day_matches = 0

        for event in fetch_day(d):
            stage_id    = (event.get("stage")       or {}).get("id", "")
            local_iso   = (event.get("localTeam")   or {}).get("isoCountryCode", "")
            visitor_iso = (event.get("visitorTeam") or {}).get("isoCountryCode", "")
            channel_id  = str(event.get("tvChannelId") or "")

            lc = ISO_TO_CODE.get(local_iso,   local_iso)
            vc = ISO_TO_CODE.get(visitor_iso, visitor_iso)

            is_wc_stage = stage_id in WC_STAGE_IDS
            is_wc_teams = lc in WC_TEAMS and vc in WC_TEAMS and lc != vc

            if not is_wc_stage and not is_wc_teams:
                continue
            if not lc or not vc or lc == vc:
                continue
            if is_wc_teams and not is_wc_stage:
                sys.stderr.write("  [?] Novo stage_id " + repr(stage_id) + " em " + lc + "-" + vc + "\n")

            ch  = get_channel_name(channel_id)
            key = lc + "-" + vc
            if key in CHANNEL_OVERRIDE:
                channels[key] = CHANNEL_OVERRIDE[key]
            else:
                fta = FREE_TO_AIR.get(key) or FREE_TO_AIR.get(vc + "-" + lc) or []
                channels[key] = fta + [ch]
            day_matches += 1

        if day_matches:
            sys.stderr.write("  -> " + str(day_matches) + " jogo(s) em " + str(d) + "\n\n")

    channels["_"] = ["Sport TV 5"]
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump({"generated": now_str, "channels": channels}, f, indent=2, ensure_ascii=False)
    sys.stderr.write("\nDone. " + str(len(channels)) + " entradas em channels.json\n")

    sys.stderr.write("\nfootball-data.org:\n")
    results, standings = fetch_results_and_standings()
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump({"generated": now_str, "results": results}, f, indent=2, ensure_ascii=False)
    with open("standings.json", "w", encoding="utf-8") as f:
        json.dump({"generated": now_str, "standings": standings}, f, indent=2, ensure_ascii=False)
    sys.stderr.write("Done.\n")


if __name__ == "__main__":
    main()
