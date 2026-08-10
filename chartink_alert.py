# ============================================================
# Chartink 6-Scanner -> Telegram Real-time Alert (GitHub Actions)
# ============================================================
# Hे script GitHub Actions var schedule nusar (cron) chalte.
# Prत्येक run madhe: 6hi scanners live run hotात, aadhichya
# run peksha NAVEEN aslेले stocks Telegram var pathавले jaतात,
# ani jar to stock ekaच vेळी 2+ scanners madhe dिsला tar tyachi
# note pan message madhe yeते.
#
# State (magच्या run madhे koनते stocks dिसले hote) state.json
# file madhe save hote, ani workflow prत्येक run nंतर te file
# git commit karto — tyamuळे pudhchya run la "previous" mahit
# rahте (GitHub Actions runner statelesss aslyaमुळे हे गरजेचे).

import requests
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import pytz

STATE_FILE = Path(__file__).parent / "state.json"
IST = pytz.timezone("Asia/Kolkata")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SCANNERS = {
    "No Loss Only Profit Swing Trading (Fut)": {
        "url": "https://chartink.com/screener/no-loss-only-profit-swing-trading-no-1-screenar-for-big-profit-fut",
        "scan_clause": "( {33489} (  weekly min ( 52 ,  weekly low ) =  daily low and  daily low <  1 day ago open and  daily low <  30 days ago open and  daily volume >  45000 and  daily open <  45 days ago close and  daily close <  90 days ago close and  daily close >=  45 ) ) "
    },
    "Bearish Super New Futures": {
        "url": "https://chartink.com/screener/bearish-super-new-futures",
        "scan_clause": "( {cash} (  daily close >  15 and  daily volume >  500000 and  daily rsi ( 14 ) <=  35 and  daily ^7106('source'=' daily close','max_bars'='80','min_bars'='22','pattern_json'='[29,46,77,111,145,179,201,213,179,146,119,167,245,278,286]','match_threshold'='0.15','resample_points'='15','output'='flag_match')^ =  1 ) ) "
    },
    "Varad Bullish": {
        "url": "https://chartink.com/screener/varad-bullish",
        "scan_clause": "( {cash} ( ( {cash} ( ( {cash} ( ( {cash} (  daily close >  1 day ago close *  1.04 and  daily volume >  daily sma ( volume,10 ) *  0 ) ) or ( {cash} (  weekly close >  1 week ago close *  1.04 and  weekly volume >  weekly sma ( volume,10 ) *  0 ) ) ) ) and  daily ^7106('source'=' daily close','max_bars'='80','min_bars'='22','pattern_json'='[29,46,77,111,145,179,201,213,179,146,119,167,245,278,286]','match_threshold'='0.15','resample_points'='15','output'='flag_match')^ =  1 ) ) ) ) "
    },
    "Stocks in Downtrend 237": {
        "url": "https://chartink.com/screener/stocks-in-downtrend-237",
        "scan_clause": "( {57960} (  daily adx di negative ( 14 ) >  daily adx di positive ( 14 ) *  1.5 and  daily adx ( 14 ) >  25 and  daily close >  20 and  daily volume >  500000 and  1 day ago macd histogram ( 26,12,9 ) >  2 days ago macd histogram ( 26,12,9 ) and  daily macd histogram ( 26,12,9 ) >  1 day ago macd histogram ( 26,12,9 ) and  daily ^7106('source'=' daily close','max_bars'='80','min_bars'='22','pattern_json'='[29,46,77,111,145,179,201,213,179,146,119,167,245,278,286]','match_threshold'='0.15','resample_points'='15','output'='flag_match')^ =  1 ) ) "
    },
    "Downtrend with Good Volume Futures": {
        "url": "https://chartink.com/screener/downtrend-with-good-volume-futures",
        "scan_clause": "( {cash} (  3 days ago close <  3 days ago open *  0.99 and  2 days ago close <  2 days ago open *  0.99 and  1 day ago close <  1 day ago open *  0.99 and  daily volume >  daily sma ( volume,10 ) *  1.3 and  daily open >  10 and  daily ^7106('source'=' daily close','max_bars'='80','min_bars'='22','pattern_json'='[29,46,77,111,145,179,201,213,179,146,119,167,245,278,286]','match_threshold'='0.15','resample_points'='15','output'='flag_match')^ =  1 ) ) "
    },
    "Perfect Bearish Varad 2": {
        "url": "https://chartink.com/screener/perfect-bearish-varad-2",
        "scan_clause": "( {cash} (  daily high >  2 days ago high and  1 day ago high >  2 days ago high and  daily high <  1 day ago high and  daily close >  50 and  daily ^7106('source'=' daily close','max_bars'='80','min_bars'='22','pattern_json'='[29,46,77,111,145,179,201,213,179,146,119,167,245,278,286]','match_threshold'='0.15','resample_points'='15','output'='flag_match')^ =  1 ) ) "
    },
}


def is_market_hours():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    open_t = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return open_t <= now <= close_t


def get_csrf_token(session, screener_url):
    resp = session.get(screener_url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    start = resp.text.find('name="csrf-token" content="')
    if start == -1:
        raise ValueError(f"CSRF token सापडला नाही: {screener_url}")
    start += len('name="csrf-token" content="')
    end = resp.text.find('"', start)
    return resp.text[start:end]


def run_scanner(name, url, scan_clause):
    session = requests.Session()
    csrf_token = get_csrf_token(session, url)
    headers = {
        "x-csrf-token": csrf_token,
        "User-Agent": "Mozilla/5.0",
        "Referer": url,
    }
    resp = session.post(
        "https://chartink.com/screener/process",
        headers=headers,
        data={"scan_clause": scan_clause},
    )
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data", [])
    symbols = set()
    for r in rows:
        sym = r.get("nsecode") or r.get("symbol") or r.get("name")
        if sym:
            symbols.add(str(sym))
    return symbols


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {name: [] for name in SCANNERS}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID set नाहीत — message पाठवता आला नाही.")
        return
    # TELEGRAM_CHAT_ID madhe comma ne veगळे kelele multiple ids asू शकतात
    # (उदा. "889495513,123456789") — pratyekala vेगळा message jaईल.
    chat_ids = [c.strip() for c in TELEGRAM_CHAT_ID.split(",") if c.strip()]
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in chat_ids:
        resp = requests.post(url, data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        })
        if not resp.ok:
            print(f"⚠️  Telegram send failed (chat_id {chat_id}): {resp.text}")


def main():
    test_mode = os.environ.get("TEST_MODE", "false").lower() == "true"
    if not test_mode and not is_market_hours():
        print("Market hours नाहीत (9:15-15:30 IST, Mon-Fri) — skip करत आहे.")
        return
    if test_mode:
        print("🧪 TEST MODE चालू आहे — market hours ची अट bypass केली आहे.")

    old_state = load_state()
    new_state = {}
    current_symbols_by_scanner = {}

    for name, info in SCANNERS.items():
        try:
            symbols = run_scanner(name, info["url"], info["scan_clause"])
        except Exception as e:
            print(f"⚠️ Error fetching '{name}': {e}")
            symbols = set(old_state.get(name, []))
        current_symbols_by_scanner[name] = symbols
        new_state[name] = sorted(symbols)

    now_str = datetime.now(IST).strftime("%H:%M:%S")
    alerts = []

    for name, symbols in current_symbols_by_scanner.items():
        prev = set(old_state.get(name, []))
        new_syms = symbols - prev
        for sym in sorted(new_syms):
            other_scanners = [n for n, s in current_symbols_by_scanner.items() if n != name and sym in s]
            line = f"🔔 <b>{sym}</b> — new in <i>{name}</i>"
            if other_scanners:
                line += f"\n   ↳ आधीच यात पण आहे: {', '.join(other_scanners)}"
            alerts.append(line)

    if alerts:
        message = f"<b>Chartink Alert ({now_str} IST)</b>\n\n" + "\n\n".join(alerts)
        send_telegram(message)
        print(f"✅ {len(alerts)} नवीन स्टॉक्ससाठी alert पाठवला.")
    else:
        print("नवीन स्टॉक नाही या cycle मध्ये.")

    save_state(new_state)


if __name__ == "__main__":
    main()
