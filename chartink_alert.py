# ============================================================
# chartink_alert.py
# ============================================================
# 6 Chartink scanners periodically run karto (GitHub Actions
# dwara, dar 10 minitanni). Prत्येक scanner madhe naveen
# stock disla (आधीच्या run madhe nasलेला) tar Telegram var
# alert pathavto. state.json madhe maglya run che results
# save karto, jyamule duplicate alerts yenar nahit.
# ============================================================

import json
import os
import time
import requests

STATE_FILE = "state.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# -----------------------------
# 6 Scanners (Chartink)
# -----------------------------
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
    """Chartink scanner run karto ani stock symbols cha set return karto."""
    if not scan_clause.strip():
        return set()
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
    data = resp.json().get("data", [])
    symbols = set()
    for row in data:
        sym = row.get("nsecode") or row.get("symbol") or row.get("name")
        if sym:
            symbols.add(str(sym))
    return symbols


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            raw = json.load(f)
        # sets JSON madhe list mhanun save hotात, parat set karto
        return {name: set(syms) for name, syms in raw.items()}
    return {}


def save_state(state):
    serializable = {name: sorted(syms) for name, syms in state.items()}
    with open(STATE_FILE, "w") as f:
        json.dump(serializable, f, indent=2)


def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID set nahi aahet, message pathavता ala nahi.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    })
    if not resp.ok:
        print(f"⚠️ Telegram send failed: {resp.status_code} {resp.text}")


def main():
    old_state = load_state()
    new_state = {}
    alert_lines = []

    for name, info in SCANNERS.items():
        try:
            current_symbols = run_scanner(name, info["url"], info["scan_clause"])
        except Exception as e:
            print(f"  ⚠️ Error running scanner '{name}': {e}")
            # error zala tar juna state tasach thevaycha, empty ne overwrite nahi karaycha
            current_symbols = old_state.get(name, set())

        previous_symbols = old_state.get(name, set())
        new_symbols = current_symbols - previous_symbols

        if new_symbols:
            alert_lines.append(f"\n<b>{name}</b>")
            alert_lines.append(", ".join(sorted(new_symbols)))

        new_state[name] = current_symbols
        time.sleep(0.5)  # Chartink server var jasti load टाळण्यासाठी

    if alert_lines:
        message = "🔔 <b>Chartink Alert - Naveen Stocks</b>" + "".join(alert_lines)
        send_telegram_message(message)
        print("✅ Naveen stocks sापडले, Telegram var alert pathavला.")
    else:
        print("ℹ️ Konतीही naveen stock सापडला nahi, alert pathavला nahi.")

    save_state(new_state)


if __name__ == "__main__":
    main()
