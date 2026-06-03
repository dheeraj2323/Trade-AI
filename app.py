from flask import Flask, jsonify, render_template, request, session, redirect
from flask_cors import CORS
from functools import wraps
import random
try:
    from pysqlite3 import dbapi2 as sqlite3
except ImportError:
    import sqlite3
import datetime
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
import time
import math
import os
import logging
import hashlib

# -- IST timezone --
from datetime import timezone as _tz, timedelta as _td

# -- CNN pattern mapper --
import hashlib as _hs
CNN_PATTERN_NAMES = {
    "BUY":  ["Hammer","Bullish Engulfing","Morning Star","Piercing Line","Bullish Harami","Three White Soldiers","Dragonfly Doji"],
    "SELL": ["Shooting Star","Bearish Engulfing","Evening Star","Dark Cloud Cover","Bearish Harami","Three Black Crows","Gravestone Doji"],
    "HOLD": ["Doji","Spinning Top","Inside Bar","Neutral Harami","Marubozu"]
}
def get_pattern_name(signal='HOLD', symbol='', timeframe='1D'):
    names = CNN_PATTERN_NAMES.get(str(signal).upper(), ['Unknown Pattern'])
    idx = int(_hs.md5(f'{symbol}_{timeframe}'.encode()).hexdigest(), 16) % len(names)
    return 'CNN: ' + names[idx]
IST = _tz(_td(hours=5, minutes=30))
def now_ist():
    from datetime import datetime
    return datetime.now(IST)

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SESSION_SECRET", "tradeai_secret_key_2026")

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tradeai")

VIRTUAL_BALANCE = 100000

DB_PATH = os.path.join(os.path.dirname(__file__), "signals.db")

# ── Stock universe ────────────────────────────────────────────────────────────
FALLBACK_STOCKS = {
    "NIFTY50":    {"base": 22450, "vol_base": 120000000},
    "BANKNIFTY":  {"base": 48200, "vol_base":   8000000},
    "RELIANCE":   {"base":  2870, "vol_base":   5000000},
    "TCS":        {"base":  3890, "vol_base":   2800000},
    "INFOSYS":    {"base":  1560, "vol_base":   8000000},
    "HDFCBANK":   {"base":  1680, "vol_base":   7500000},
    "ICICIBANK":  {"base":  1120, "vol_base":  12000000},
    "WIPRO":      {"base":   480, "vol_base":   9000000},
    "SBIN":       {"base":   810, "vol_base":  18000000},
    "BHARTIARTL": {"base":  1640, "vol_base":   6000000},
    "KOTAKBANK":  {"base":  1780, "vol_base":   4500000},
    "AXISBANK":   {"base":  1120, "vol_base":   9000000},
    "LT":         {"base":  3470, "vol_base":   2200000},
    "MARUTI":     {"base": 12400, "vol_base":    800000},
    "TATAMOTORS": {"base":   960, "vol_base":  14000000},
    "BAJFINANCE": {"base":  7200, "vol_base":   1800000},
    "TITAN":      {"base":  3540, "vol_base":   1200000},
    "SUNPHARMA":  {"base":  1680, "vol_base":   3000000},
    "NESTLEIND":  {"base":  2260, "vol_base":    900000},
    "TECHM":      {"base":  1680, "vol_base":   4000000},
    "ULTRACEMCO": {"base": 10800, "vol_base":    500000},
    "ONGC":       {"base":   270, "vol_base":  22000000},
    "POWERGRID":  {"base":   320, "vol_base":  15000000},
    "NTPC":       {"base":   365, "vol_base":  18000000},
    "HINDALCO":   {"base":   660, "vol_base":  11000000},
    "TATASTEEL":  {"base": 160,   "vol_base": 25000000},
    "DRREDDY":    {"base": 1280,  "vol_base": 2000000},
    "DIVISLAB":   {"base": 4800,  "vol_base": 800000},
    "CIPLA":      {"base": 1580,  "vol_base": 3000000},
    "ADANIPORTS": {"base": 1380,  "vol_base": 5000000},
    "BAJAJFINSV": {"base": 1920,  "vol_base": 1500000},
    "HEROMOTOCO": {"base": 4200,  "vol_base": 1000000},
    "EICHERMOT":  {"base": 5100,  "vol_base": 600000},
    "APOLLOHOSP": {"base": 6800,  "vol_base": 700000},
    "ASIANPAINT": {"base": 2400,  "vol_base": 1200000},
    "BRITANNIA":  {"base": 5200,  "vol_base": 500000},
    "COALINDIA":  {"base": 430,   "vol_base": 12000000},
    "GRASIM":     {"base": 2700,  "vol_base": 1000000},
    "INDUSINDBK": {"base": 820,   "vol_base": 5000000},
    "JSWSTEEL":   {"base": 970,   "vol_base": 8000000},
    "MAHINDRA":   {"base": 2900,  "vol_base": 4000000},
    "BAJAJAUTO":  {"base": 8500,  "vol_base": 600000},
    "HCLTECH":    {"base": 1680,  "vol_base": 4000000},
    "TATACONSUM": {"base": 1020,  "vol_base": 3000000},
    "VEDL":       {"base": 460,   "vol_base": 14000000},
    "PIDILITIND": {"base": 2800,  "vol_base": 800000},
    "SIEMENS":    {"base": 6200,  "vol_base": 400000},
    "HAVELLS":    {"base": 1680,  "vol_base": 1500000},
    "MUTHOOTFIN": {"base": 1950,  "vol_base": 1200000},
    "PERSISTENT": {"base": 5800,  "vol_base": 500000},
}

# ── NSE Index membership ──────────────────────────────────────────────────────
NIFTY50 = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR",
    "ITC","SBIN","BHARTIARTL","KOTAKBANK","LT","AXISBANK","ASIANPAINT",
    "MARUTI","TITAN","SUNPHARMA","WIPRO","ULTRACEMCO","NESTLEIND","TECHM",
    "BAJFINANCE","BAJAJFINSV","HCLTECH","ADANIPORTS","ONGC","NTPC",
    "POWERGRID","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA",
    "GRASIM","INDUSINDBK","DRREDDY","DIVISLAB","CIPLA","APOLLOHOSP",
    "EICHERMOT","HEROMOTOCO","BAJAJAUTO","BRITANNIA","TATACONSUM",
    "HAVELLS","PIDILITIND","SIEMENS","VEDL","MUTHOOTFIN","PERSISTENT","MAHINDRA",
]

NIFTY_NEXT50 = [
    "DMART","BAJAJHLDNG","SBILIFE","HDFCLIFE","ICICIPRULI","SHREECEM",
    "TORNTPHARM","COLPAL","GODREJCP","BERGEPAINT","MARICO","DABUR",
    "EMAMILTD","LUPIN","BIOCON","AUROPHARMA","ALKEM","IPCALAB",
    "NATCOPHARM","GLENMARK","LAURUSLABS","BANDHANBNK","FEDERALBNK",
    "IDFCFIRSTB","RBLBANK","NHPC","SJVN","RECLTD","PFC","IRCTC",
    "CONCOR","ZOMATO","NYKAA","SBICARD","POLICYBZR","DELHIVERY",
    "PAYTM","CARTRADE","LATENTVIEW","CUB","DCBBANK","MFSL","GICRE",
    "NIACL","SUNDRMFAST","TATAELXSI","MPHASIS","COFORGE","LTTS","OFSS",
]

NIFTY_BANK = [
    "HDFCBANK","ICICIBANK","KOTAKBANK","SBIN","AXISBANK","INDUSINDBK",
    "BANDHANBNK","FEDERALBNK","IDFCFIRSTB","RBLBANK","AUBANK","PNB",
    "BANKBARODA","CANBK","UNIONBANK",
]

NIFTY_IT = [
    "TCS","INFOSYS","WIPRO","HCLTECH","TECHM","LTIM","MPHASIS",
    "COFORGE","PERSISTENT","LTTS","OFSS","KPITTECH","TATAELXSI","HEXAWARE",
]

NIFTY_PHARMA = [
    "SUNPHARMA","DRREDDY","CIPLA","DIVISLAB","BIOCON","AUROPHARMA",
    "LUPIN","ALKEM","TORNTPHARM","IPCALAB","GLENMARK","LAURUSLABS",
    "NATCOPHARM","ABBOTINDIA","PFIZER","GLAXO","SANOFI",
]

INDEX_MAP = {
    "n50":    NIFTY50,
    "nn50":   NIFTY_NEXT50,
    "bank":   NIFTY_BANK,
    "it":     NIFTY_IT,
    "pharma": NIFTY_PHARMA,
}


def load_nse_stocks():
    """Fetch full NSE equity list; fall back to FALLBACK_STOCKS on error."""
    try:
        import io
        import urllib.request
        import pandas as pd
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {"User-Agent": "Mozilla/5.0 (TradeAI/1.0)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        df = pd.read_csv(io.StringIO(raw))
        stocks = {}
        for _, row in df.iterrows():
            symbol = str(row["SYMBOL"]).strip()
            fb = FALLBACK_STOCKS.get(symbol, {})
            stocks[symbol] = {
                "base":     fb.get("base", 100),
                "vol_base": fb.get("vol_base", 1_000_000),
                "name":     str(row["NAME OF COMPANY"]).strip(),
            }
        logging.getLogger("tradeai").info("NSE stock list loaded: %d symbols", len(stocks))
        return stocks
    except Exception as exc:
        logging.getLogger("tradeai").warning(
            "NSE fetch failed (%s) – using %d fallback stocks", exc, len(FALLBACK_STOCKS)
        )
        return dict(FALLBACK_STOCKS)


STOCKS = load_nse_stocks()

BUY_PATTERNS = [
    "Hammer", "Morning Star", "Bullish Engulfing", "Three White Soldiers",
    "Piercing Line", "Bullish Marubozu", "Dragonfly Doji", "Inverted Hammer",
]
SELL_PATTERNS = [
    "Shooting Star", "Evening Star", "Bearish Engulfing", "Dark Cloud Cover",
    "Bearish Marubozu", "Hanging Man", "Three Black Crows", "Gravestone Doji",
]
HOLD_PATTERNS = ["Doji", "Spinning Top", "High Wave"]

PATTERN_INFO = {
    "Hammer":             ("Bullish reversal with a small body and long lower shadow — buyers regaining control.", 72),
    "Morning Star":       ("Three-candle bullish reversal at the bottom of a downtrend.", 80),
    "Bullish Engulfing":  ("A large green candle engulfs the previous red candle, signaling reversal.", 78),
    "Three White Soldiers":("Three consecutive rising candles indicating strong bullish momentum.", 82),
    "Piercing Line":      ("Bullish reversal where a green candle closes above the previous candle's midpoint.", 73),
    "Bullish Marubozu":   ("Full green body with no shadows — strong uninterrupted buying pressure.", 77),
    "Dragonfly Doji":     ("Doji with long lower shadow at support — potential bullish reversal signal.", 69),
    "Inverted Hammer":    ("Small body with long upper shadow at the bottom — potential bullish reversal.", 68),
    "Shooting Star":      ("Bearish reversal with a small body and long upper shadow at resistance.", 70),
    "Evening Star":       ("Three-candle bearish reversal at the top of an uptrend.", 79),
    "Bearish Engulfing":  ("A large red candle engulfs the previous green candle — bearish signal.", 76),
    "Dark Cloud Cover":   ("Bearish reversal where a red candle opens above and closes below midpoint.", 71),
    "Bearish Marubozu":   ("Full red body with no shadows — strong uninterrupted selling pressure.", 75),
    "Hanging Man":        ("Small body with long lower shadow at the top of an uptrend — bearish warning.", 67),
    "Three Black Crows":  ("Three consecutive falling candles indicating strong bearish momentum.", 81),
    "Gravestone Doji":    ("Doji with long upper shadow at resistance — potential bearish reversal.", 68),
    "Doji":               ("Indecision candle where open and close are nearly equal.", 61),
    "Spinning Top":       ("Small body with equal wicks showing indecision in the market.", 58),
    "High Wave":          ("Long upper and lower shadows with a small body — extreme market indecision.", 55),
}

TIMEFRAMES = ["1m", "5m", "15m", "1h", "1D", "1W"]
ALL_TF     = ["1D", "1W", "1h", "15m", "5m", "1m"]

_signal_cache: dict = {}
_cache_ts: float = 0
CACHE_TTL = 60


# ── Database ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            timeframe   TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            entry       REAL,
            target      REAL,
            sl          REAL,
            pattern     TEXT,
            confidence  REAL,
            timestamp   TEXT,
            status      TEXT DEFAULT 'Active'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT,
            signal_type     TEXT,
            entry_price     REAL,
            target_price    REAL,
            sl_price        REAL,
            quantity        INTEGER,
            invested_amount REAL,
            pattern         TEXT,
            timeframe       TEXT,
            confidence      REAL,
            status          TEXT DEFAULT 'Active',
            pnl             REAL DEFAULT 0,
            entry_time      TEXT,
            exit_time       TEXT,
            exit_price      REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            avatar_color  TEXT DEFAULT '#1D9E75'
        )
    """)
    # ── Migrate stale users table that used name/password columns ────────────
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
        wrong_cols = ("name" in cols and "username" not in cols) or \
                     ("password" in cols and "password_hash" not in cols)
        if wrong_cols:
            c.execute("ALTER TABLE users RENAME TO _users_old")
            c.execute("""
                CREATE TABLE users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT UNIQUE NOT NULL,
                    email         TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    avatar_color  TEXT DEFAULT '#1D9E75'
                )
            """)
            old_name = "name" if "name" in cols else "username"
            old_pass = "password" if "password" in cols else "password_hash"
            old_color = "avatar_color" if "avatar_color" in cols else "'#1D9E75'"
            c.execute(f"""
                INSERT INTO users (id, username, email, password_hash, created_at, avatar_color)
                SELECT id, {old_name}, email, {old_pass},
                       coalesce(created_at, datetime('now')),
                       coalesce({old_color}, '#1D9E75')
                FROM _users_old
            """)
            c.execute("DROP TABLE _users_old")
        elif "avatar_color" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN avatar_color TEXT DEFAULT '#1D9E75'")
    except Exception as e:
        logger.warning("users migration: %s", e)
    conn.commit()
    conn.close()


# ── Signal helpers ────────────────────────────────────────────────────────────
def _jitter(base, pct=0.02):
    return round(base * (1 + random.uniform(-pct, pct)), 2)


def _tf_signal():
    action = random.choices(["BUY", "SELL", "HOLD"], weights=[40, 30, 30], k=1)[0]
    confidence = round(
        random.uniform(65, 95) if action in ("BUY", "SELL") else random.uniform(50, 65), 1
    )
    if confidence < 60:
        action = "HOLD"
        confidence = round(random.uniform(50, 59.9), 1)
    pattern = random.choice(
        BUY_PATTERNS if action == "BUY" else SELL_PATTERNS if action == "SELL" else HOLD_PATTERNS
    )
    return {"signal": action, "pattern": pattern, "confidence": confidence}


def _consensus(tf_signals: dict) -> str:
    counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
    for v in tf_signals.values():
        counts[v["signal"]] += 1
    top_action = max(counts, key=counts.get)
    return f"Strong {top_action}" if counts[top_action] >= 4 else "Mixed Signal"


def generate_signals_fresh():
    now = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    signals = []
    for symbol, info in STOCKS.items():
        base = info["base"]
        tf_signals = {tf: _tf_signal() for tf in ALL_TF}
        primary = tf_signals["1D"]
        action  = primary["signal"]
        entry   = _jitter(base, 0.005)
        if action == "BUY":
            target, sl = round(entry * 1.008, 2), round(entry * 0.996, 2)
        elif action == "SELL":
            target, sl = round(entry * 0.992, 2), round(entry * 1.004, 2)
        else:
            target, sl = round(entry * 1.004, 2), round(entry * 0.998, 2)
        consensus = _consensus(tf_signals)
        signals.append({
            "symbol": symbol, "timeframe": "1D", "action": action,
            "entry": entry, "target": target, "stoploss": sl,
            "confidence": primary["confidence"],
            "pattern_name": "Daily " + primary["pattern"],
            "timestamp": now, "status": "Active",
            "primary_signal": action,
            "primary_pattern": "Daily " + primary["pattern"],
            "primary_confidence": primary["confidence"],
            "timeframe_signals": tf_signals,
            "consensus": consensus,
        })
    return signals


def get_signals():
    global _signal_cache, _cache_ts
    if time.time() - _cache_ts > CACHE_TTL:
        signals = generate_signals_fresh()
        _signal_cache = {s["symbol"]: s for s in signals}
        _cache_ts = time.time()
        _persist_signals(signals)
    return list(_signal_cache.values())


def _persist_signals(signals):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for s in signals:
            c.execute(
                "INSERT INTO signals (symbol,timeframe,signal_type,entry,target,sl,pattern,confidence,timestamp,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (s["symbol"], s["timeframe"], s["action"], s["entry"], s["target"],
                 s["stoploss"], s["pattern_name"], s["confidence"], s["timestamp"], s["status"]),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_watchlist():
    signals = get_signals()
    sig_map = {s["symbol"]: s for s in signals}
    rows = []
    for symbol, info in STOCKS.items():
        base = info["base"]
        ltp  = _jitter(base, 0.015)
        prev = _jitter(base, 0.010)
        chg  = round((ltp - prev) / prev * 100, 2)
        vol  = int(info["vol_base"] * random.uniform(0.7, 1.3))
        sig  = sig_map.get(symbol, {})
        rows.append({
            "symbol": symbol, "ltp": ltp, "change": chg, "volume": vol,
            "signal":     sig.get("action",       "HOLD"),
            "pattern":    sig.get("pattern_name", "—"),
            "confidence": sig.get("confidence",   0),
            "entry":      sig.get("entry",        ltp),
            "target":     sig.get("target",       ltp),
            "stoploss":   sig.get("stoploss",     ltp),
        })
    return rows


def get_ticker_data():
    return [{"symbol": r["symbol"], "ltp": r["ltp"], "change": r["change"]}
            for r in get_watchlist()[:10]]


def get_history(limit=50):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        rows = c.execute(
            "SELECT symbol,timeframe,signal_type,entry,target,sl,pattern,confidence,timestamp,status "
            "FROM signals ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        cols = ["symbol","timeframe","signal_type","entry","target","sl","pattern","confidence","timestamp","status"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def gen_ohlcv(symbol, timeframe, bars=60):
    info = STOCKS.get(symbol, {"base": 1000})
    base = info["base"]
    now  = now_ist()
    tf_minutes = {"1m":1,"5m":5,"15m":15,"1h":60,"1D":1440,"1W":10080,"1d":1440}
    delta_min  = tf_minutes.get(timeframe, 5)
    price = base * random.uniform(0.96, 1.04)
    candles = []
    for i in range(bars, 0, -1):
        t  = now - datetime.timedelta(minutes=delta_min * i)
        o  = price
        chg = random.gauss(0, base * 0.004)
        c   = round(o + chg, 2)
        h   = round(max(o, c) + abs(random.gauss(0, base * 0.002)), 2)
        l   = round(min(o, c) - abs(random.gauss(0, base * 0.002)), 2)
        vol = int(info.get("vol_base", 1000000) * random.uniform(0.5, 1.5) / bars)
        candles.append({"time": int(t.timestamp()), "open": round(o,2), "high": h, "low": l, "close": round(c,2), "volume": vol})
        price = c
    return candles


# ── Page routes ───────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/stock/<symbol>")
def stock_detail(symbol):
    return render_template("stock.html", symbol=symbol.upper())

@app.route("/signals")
def signals_page():
    return render_template("signals.html")

@app.route("/watchlist")
def watchlist_page():
    return render_template("watchlist.html")

@app.route("/history")
def history_page():
    return render_template("history.html")

@app.route("/portfolio")
def portfolio_page():
    return render_template("portfolio.html")

@app.route("/about")
def about_page():
    return render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    return render_template("signup.html")

@app.route("/profile")
def profile_page():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("profile.html")


# ── Data API routes ───────────────────────────────────────────────────────────
@app.route("/data/signals")
def api_signals():
    return jsonify({"status":"ok","signals":get_signals(),"generated_at":datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")})

@app.route("/data/watchlist")
def api_watchlist():
    return jsonify({"status":"ok","watchlist":get_watchlist()})

@app.route("/data/ticker")
def api_ticker():
    return jsonify({"status":"ok","ticker":get_ticker_data()})

@app.route("/data/history")
def api_history():
    return jsonify({"status":"ok","history":get_history(50)})

@app.route("/data/stock/<symbol>")
def api_stock(symbol):
    sym = symbol.upper()
    sigs = get_signals()
    sig  = next((s for s in sigs if s["symbol"] == sym), None)
    wl   = get_watchlist()
    stock_row = next((r for r in wl if r["symbol"] == sym), None)
    history   = [r for r in get_history(100) if r["symbol"] == sym][:20]
    base_pattern = sig["primary_pattern"].replace("Daily ","") if sig else ""
    pat_info = PATTERN_INFO.get(base_pattern, ("Pattern detected by AI model via CNN analysis.", 65))
    tf_signals = sig.get("timeframe_signals", {}) if sig else {}
    return jsonify({
        "status": "ok", "symbol": sym,
        "ltp":    stock_row["ltp"]    if stock_row else 0,
        "change": stock_row["change"] if stock_row else 0,
        "signal": sig,
        "pattern_description": pat_info[0],
        "pattern_accuracy":    pat_info[1],
        "timeframe_signals":   tf_signals,
        "consensus": sig.get("consensus","Mixed Signal") if sig else "Mixed Signal",
        "history": history,
    })

@app.route("/data/chart/<symbol>/<timeframe>")
def api_chart(symbol, timeframe):
    sym = symbol.upper()
    tf  = timeframe if timeframe in TIMEFRAMES else "5m"
    return jsonify({"status":"ok","symbol":sym,"timeframe":tf,"candles":gen_ohlcv(sym,tf)})


# ── Paper trading ─────────────────────────────────────────────────────────────
def _update_active_trades():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM paper_trades WHERE status='Active'")
        rows = c.fetchall()
        cols = [d[0] for d in c.description]
        now  = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        for row in rows:
            t = dict(zip(cols, row))
            base = STOCKS.get(t["symbol"], {}).get("base", t["entry_price"])
            cur  = _jitter(base, 0.018)
            status, exit_price, pnl = "Active", None, 0.0
            if t["signal_type"] == "BUY":
                if cur >= t["target_price"]:   status, exit_price = "Target Hit", t["target_price"]; pnl = (exit_price - t["entry_price"]) * t["quantity"]
                elif cur <= t["sl_price"]:     status, exit_price = "SL Hit",     t["sl_price"];     pnl = (exit_price - t["entry_price"]) * t["quantity"]
            else:
                if cur <= t["target_price"]:   status, exit_price = "Target Hit", t["target_price"]; pnl = (t["entry_price"] - exit_price) * t["quantity"]
                elif cur >= t["sl_price"]:     status, exit_price = "SL Hit",     t["sl_price"];     pnl = (t["entry_price"] - exit_price) * t["quantity"]
            if status != "Active":
                c.execute("UPDATE paper_trades SET status=?,pnl=?,exit_time=?,exit_price=? WHERE id=?",
                          (status, round(pnl,2), now, exit_price, t["id"]))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("update_active_trades error: %s", e)


@app.route("/data/paper-trade", methods=["POST"])
def place_paper_trade():
    t0 = time.time()
    try:
        d = request.get_json(force=True)
        invested = round(float(d["entry_price"]) * int(d["quantity"]), 2)
        now = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO paper_trades (symbol,signal_type,entry_price,target_price,sl_price,quantity,invested_amount,pattern,timeframe,confidence,status,pnl,entry_time) VALUES (?,?,?,?,?,?,?,?,?,?,'Active',0,?)",
            (d["symbol"],d["signal_type"],d["entry_price"],d["target_price"],d["sl_price"],d["quantity"],invested,d.get("pattern",""),d.get("timeframe","1D"),d.get("confidence",0),now),
        )
        tid = c.lastrowid
        conn.commit()
        conn.close()
        logger.info("POST /data/paper-trade %s %s %.3fs", d["symbol"], d["signal_type"], time.time()-t0)
        return jsonify({"status":"ok","trade_id":tid})
    except Exception as e:
        logger.error("place_paper_trade error: %s", e)
        return jsonify({"status":"error","message":str(e)}), 400


@app.route("/data/portfolio")
def get_portfolio():
    t0 = time.time()
    try:
        _update_active_trades()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM paper_trades ORDER BY entry_time DESC")
        rows = c.fetchall()
        cols = [d[0] for d in c.description]
        trades = [dict(zip(cols,r)) for r in rows]
        conn.close()
        active = [t for t in trades if t["status"]=="Active"]
        closed = [t for t in trades if t["status"]!="Active"]
        invested = sum(t["invested_amount"] for t in active)
        realized = sum(t["pnl"] for t in closed)
        unr = 0.0
        for t in active:
            base = STOCKS.get(t["symbol"],{}).get("base", t["entry_price"])
            cur  = _jitter(base, 0.008)
            unr += (cur-t["entry_price"])*t["quantity"] if t["signal_type"]=="BUY" else (t["entry_price"]-cur)*t["quantity"]
        total_pnl = round(realized+unr, 2)
        wins = len([t for t in closed if t["pnl"]>0])
        win_rate = round(wins/len(closed)*100,1) if closed else 0.0
        logger.info("GET /data/portfolio %.3fs", time.time()-t0)
        return jsonify({"status":"ok","stats":{"virtual_balance":VIRTUAL_BALANCE,"invested":round(invested,2),"current_value":round(VIRTUAL_BALANCE+total_pnl,2),"total_pnl":total_pnl,"realized_pnl":round(realized,2),"unrealized_pnl":round(unr,2),"win_rate":win_rate,"total_trades":len(trades),"active_trades":len(active),"closed_trades":len(closed)},"active_trades":active,"closed_trades":closed})
    except Exception as e:
        logger.error("get_portfolio error: %s", e)
        return jsonify({"status":"error","message":str(e)}), 500


@app.route("/data/paper-trade/<int:trade_id>/exit", methods=["POST"])
def exit_paper_trade(trade_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({"status":"error","message":"Trade not found"}), 404
        cols = [d[0] for d in c.description]
        t = dict(zip(cols, row))
        base = STOCKS.get(t["symbol"],{}).get("base", t["entry_price"])
        ep   = _jitter(base, 0.01)
        pnl  = (ep-t["entry_price"])*t["quantity"] if t["signal_type"]=="BUY" else (t["entry_price"]-ep)*t["quantity"]
        now  = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE paper_trades SET status='Exited',pnl=?,exit_time=?,exit_price=? WHERE id=?",
                  (round(pnl,2), now, round(ep,2), trade_id))
        conn.commit()
        conn.close()
        return jsonify({"status":"ok","pnl":round(pnl,2),"exit_price":round(ep,2)})
    except Exception as e:
        logger.error("exit_paper_trade error: %s", e)
        return jsonify({"status":"error","message":str(e)}), 500


@app.route("/data/portfolio/performance")
def portfolio_performance():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT SUM(pnl) FROM paper_trades WHERE status!='Active'")
        realized = c.fetchone()[0] or 0.0
        conn.close()
        history = []
        now = datetime.datetime.now()
        val = VIRTUAL_BALANCE * random.uniform(0.9, 0.97)
        final = VIRTUAL_BALANCE + realized
        for i in range(29, -1, -1):
            d = now - datetime.timedelta(days=i)
            blend = (29-i)/29
            target = VIRTUAL_BALANCE*(1-blend*0.05) + final*blend*0.05
            val = val*0.85 + target*0.15 + random.gauss(0, VIRTUAL_BALANCE*0.004)
            history.append({"date": d.strftime("%Y-%m-%d"), "value": round(max(VIRTUAL_BALANCE*0.7, val), 2)})
        history[-1]["value"] = round(final, 2)
        return jsonify({"status":"ok","history":history})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500


# ── Auth routes ───────────────────────────────────────────────────────────────
@app.route("/auth/signup", methods=["POST"])
def auth_signup():
    username = request.form.get("username","").strip()
    email    = request.form.get("email","").strip().lower()
    password = request.form.get("password","")
    if not username or not email or not password:
        return redirect("/signup?error=All fields are required.")
    hashed = hashlib.sha256(password.encode()).hexdigest()
    colors = ["#1D9E75","#378ADD","#7F77DD","#D85A30","#BA7517"]
    color  = colors[len(email) % len(colors)]
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (username,email,password_hash,avatar_color) VALUES (?,?,?,?)",
                  (username, email, hashed, color))
        conn.commit()
        conn.close()
        return redirect("/login?success=Account created successfully! Please login.", 303)
    except Exception:
        return redirect("/signup?error=Email already registered. Please use a different email.", 303)


@app.route("/auth/login", methods=["POST"])
def auth_login():
    email    = request.form.get("email","").strip().lower()
    password = request.form.get("password","")
    hashed   = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE email=? AND password_hash=?", (email, hashed)).fetchone()
    conn.close()
    if user:
        session["user_id"]    = user[0]
        session["user_name"]  = user[1]   # username column
        session["user_email"] = user[2]   # email column
        session["user_color"] = user[5] if len(user) > 5 else "#1D9E75"  # avatar_color
        return redirect("/", 303)
    return redirect("/login?error=Invalid email or password. Please try again.", 303)


@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return redirect("/login")


@app.route("/data/all-stocks")
def api_all_stocks():
    stocks = [{"symbol": k, "name": v.get("name", k)} for k, v in STOCKS.items()]
    return jsonify({"stocks": stocks, "total": len(stocks)})


@app.route("/data/user/info")
def api_user_info():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in":  True,
        "user_id":    session["user_id"],
        "user_name":  session["user_name"],
        "user_email": session.get("user_email",""),
        "user_color": session.get("user_color","#1D9E75"),
    })


@app.route("/data/user/trades")
def api_user_trades():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM paper_trades ORDER BY entry_time DESC LIMIT 10")
        rows = c.fetchall()
        cols = [d[0] for d in c.description]
        trades = [dict(zip(cols,r)) for r in rows]
        closed = [t for t in trades if t["status"]!="Active"]
        wins   = len([t for t in closed if t["pnl"]>0])
        win_rate = round(wins/len(closed)*100,1) if closed else 0
        best_pnl = max((t["pnl"] for t in closed), default=0)
        conn.close()
        return jsonify({"status":"ok","trades":trades,"total":len(trades),"win_rate":win_rate,"best_pnl":round(best_pnl,2)})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500



# -- logout route --
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -- user_watchlist DB table init --
def _init_watchlist_table():
    try:
        from pysqlite3 import dbapi2 as _sq3
    except ImportError:
        import sqlite3 as _sq3
    conn = _sq3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS user_watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, symbol))""")
    conn.commit()
    conn.close()
_init_watchlist_table()

@app.route("/watchlist/add", methods=["POST"])
def watchlist_add():
    try:
        from pysqlite3 import dbapi2 as _sq3
    except ImportError:
        import sqlite3 as _sq3
    uid = session.get("user_id", "guest")
    symbol = (request.json or {}).get("symbol", "").upper()
    if symbol in STOCKS:
        conn = _sq3.connect(DB_PATH)
        conn.execute("INSERT OR IGNORE INTO user_watchlist (user_id, symbol) VALUES (?,?)", (uid, symbol))
        conn.commit()
        conn.close()
        return jsonify({"status": "added", "symbol": symbol})
    return jsonify({"status": "error", "msg": "Unknown symbol"}), 400

@app.route("/watchlist/remove", methods=["POST"])
def watchlist_remove():
    try:
        from pysqlite3 import dbapi2 as _sq3
    except ImportError:
        import sqlite3 as _sq3
    uid = session.get("user_id", "guest")
    symbol = (request.json or {}).get("symbol", "").upper()
    conn = _sq3.connect(DB_PATH)
    conn.execute("DELETE FROM user_watchlist WHERE user_id=? AND symbol=?", (uid, symbol))
    conn.commit()
    conn.close()
    return jsonify({"status": "removed"})

@app.route("/watchlist/clear", methods=["POST"])
def watchlist_clear():
    try:
        from pysqlite3 import dbapi2 as _sq3
    except ImportError:
        import sqlite3 as _sq3
    uid = session.get("user_id", None)
    if not uid:
        return jsonify({"status": "error", "msg": "Not logged in"}), 401
    conn = _sq3.connect(DB_PATH)
    conn.execute("DELETE FROM user_watchlist WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/data/watchlist/user")
def api_user_watchlist():
    try:
        from pysqlite3 import dbapi2 as _sq3
    except ImportError:
        import sqlite3 as _sq3
    uid = session.get("user_id", None)
    if not uid:
        return jsonify({"status": "ok", "logged_in": False, "watchlist": []})
    conn = _sq3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT symbol FROM user_watchlist WHERE user_id=? ORDER BY added_at DESC", (uid,)
    ).fetchall()
    conn.close()
    symbols = [r[0] for r in rows]
    sigs = get_signals()
    sig_map = {s["symbol"]: s for s in sigs}
    watchlist = []
    for symbol in symbols:
        info = STOCKS.get(symbol, {"base": 1000, "vol_base": 1000000})
        base = info["base"]
        ltp  = _jitter(base, 0.015)
        prev = _jitter(base, 0.010)
        chg  = round((ltp - prev) / prev * 100, 2)
        sig  = sig_map.get(symbol, {})
        tfs  = sig.get("timeframe_signals", {})
        agree = sum(1 for t in tfs.values() if t.get("signal") == (sig.get("primary_signal") or sig.get("action","HOLD")))
        watchlist.append({
            "symbol":     symbol,
            "name":       info.get("name", symbol),
            "ltp":        ltp,
            "change":     chg,
            "signal":     sig.get("primary_signal") or sig.get("action", "HOLD"),
            "pattern":    sig.get("primary_pattern", "—"),
            "confidence": sig.get("primary_confidence") or sig.get("confidence", 0),
            "agree":      agree,
            "timeframe":  "1D",
        })
    return jsonify({"status": "ok", "logged_in": True, "watchlist": watchlist})

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    logger.info("TradeAI starting on 0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port, debug=False)

@app.route("/admin/fix-users-table")
def fix_users_table():
    try:
        conn = sqlite3.connect(DB_PATH)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "username" not in cols:
            conn.execute("ALTER TABLE users RENAME TO users_old")
            conn.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                avatar_color TEXT DEFAULT '#1D9E75',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
            conn.commit()
            msg = "FIXED: users table recreated with username column"
        else:
            msg = "OK: users table already has username column"
        cols2 = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return f"{msg}<br>Columns: {cols2}<br>Total users: {count}"
    except Exception as e:
        return f"ERROR: {e}"
