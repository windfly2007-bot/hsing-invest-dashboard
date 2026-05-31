import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime, timedelta

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Hsing 投資儀表板 V7.1", layout="wide")

PORTFOLIO_FILE = "portfolio.csv"
BROKER_FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003

stock_list = {
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "廣達": "2382.TW",
    "大成鋼": "2027.TW",
    "中鋼": "2002.TW",
}

stock_id_map = {
    "台積電": "2330",
    "鴻海": "2317",
    "廣達": "2382",
    "大成鋼": "2027",
    "中鋼": "2002",
}

ai_market_list = {
    "台積電ADR": "TSM",
    "輝達": "NVDA",
    "費城半導體": "^SOX",
    "NASDAQ": "^IXIC",
    "美債10Y": "^TNX",
    "VIX": "^VIX",
    "美元指數": "DX-Y.NYB",
}

commodity_list = {
    "熱軋鋼": "HRC=F",
    "鋁價": "ALI=F",
    "鐵礦砂": "TIO=F",
    "銅價": "HG=F",
}

default_portfolio = {
    "台積電": {"shares": 70, "cost": 2047.76},
    "鴻海": {"shares": 200, "cost": 264.72},
    "廣達": {"shares": 500, "cost": 315.49},
    "大成鋼": {"shares": 1000, "cost": 42.69},
    "中鋼": {"shares": 1000, "cost": 19.02},
}

long_term_rules = {
    "台積電": {"add": 2300, "strong_add": 2200, "reduce": 2500, "type": "AI"},
    "廣達": {"add": 320, "strong_add": 300, "reduce": 380, "type": "AI"},
    "鴻海": {"add": 280, "strong_add": 260, "reduce": 320, "type": "AI"},
    "大成鋼": {"add": 40, "strong_add": 38, "reduce": 48, "type": "STEEL"},
    "中鋼": {"add": 18.5, "strong_add": 17, "reduce": 22, "type": "STEEL"},
}

news_targets = {
    "台積電 ADR": {"ticker": "TSM", "keyword": "台積電 TSMC AI 先進製程"},
    "輝達": {"ticker": "NVDA", "keyword": "NVIDIA 輝達 AI GPU"},
    "廣達": {"ticker": "2382.TW", "keyword": "廣達 2382 AI伺服器"},
    "鴻海": {"ticker": "2317.TW", "keyword": "鴻海 2317 AI伺服器"},
    "中鋼": {"ticker": "2002.TW", "keyword": "中鋼 2002 鋼價"},
    "大成鋼": {"ticker": "2027.TW", "keyword": "大成鋼 2027 鋼鋁 關稅"},
}

st.markdown("""
<style>
html, body, [class*="css"] { font-size: 22px; }
.block-container { padding-top: 3.8rem; padding-left: 2rem; padding-right: 2rem; }
h1 { font-size: 38px !important; font-weight: 900 !important; margin-top: 16px !important; line-height: 1.3 !important; }
h2, h3 { font-size: 30px !important; font-weight: 900 !important; }

table, th, td {
    font-size: 21px !important;
}

[data-testid="stMetricValue"] {
    font-size: 34px !important;
    font-weight: 900 !important;
}

[data-testid="stDataFrame"] {
    font-size: 21px !important;
}

.red-text { color:#ff3333; font-weight:900; }
.green-text { color:#00bb44; font-weight:900; }
.gray-text { color:gray; font-weight:900; }
.big-profit { font-size:32px; font-weight:900; }

.market-card {
    background:#111827;
    border-radius:15px;
    padding:15px;
    text-align:center;
    min-height:130px;
}
.market-title { color:white; font-size:17px; }
.market-value { color:white; font-size:28px; font-weight:bold; }
.market-red { color:#ff3333; font-size:20px; font-weight:900; }
.market-green { color:#00bb44; font-size:20px; font-weight:900; }
.market-gray { color:gray; font-size:20px; font-weight:900; }

.alert-card {
    background:#0f172a;
    border-left:6px solid #60a5fa;
    color:white;
    border-radius:12px;
    padding:14px 18px;
    margin:8px 0;
    line-height:1.5;
}

.section-note { color:#94a3b8; font-size:16px; }

/* V6.4a 顯示修正版 */
[data-testid="stCaptionContainer"] {
    border: none !important;
    text-decoration: none !important;
}

h2, h3 {
    margin-top: 1.2rem !important;
    margin-bottom: 0.9rem !important;
}

[data-testid="stDataFrame"] {
    margin-top: 0.6rem !important;
}

hr {
    margin-top: 1.8rem !important;
    margin-bottom: 1.8rem !important;
}

</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def get_data(ticker, period="1y"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        return df.dropna()
    except Exception:
        return pd.DataFrame()


def create_default_csv():
    df = pd.DataFrame([
        {"股票": k, "股數": v["shares"], "成本": v["cost"]}
        for k, v in default_portfolio.items()
    ])
    df.to_csv(PORTFOLIO_FILE, index=False, encoding="utf-8-sig")


def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        create_default_csv()
    df = pd.read_csv(PORTFOLIO_FILE)
    result = {}
    for _, row in df.iterrows():
        name = row["股票"]
        if name in stock_list:
            result[name] = {"shares": int(row["股數"]), "cost": float(row["成本"])}
    return result


def save_portfolio(portfolio):
    df = pd.DataFrame([
        {"股票": k, "股數": v["shares"], "成本": v["cost"]}
        for k, v in portfolio.items()
    ])
    df.to_csv(PORTFOLIO_FILE, index=False, encoding="utf-8-sig")


def tw_color(v):
    if v > 0:
        return "red"
    if v < 0:
        return "green"
    return "gray"


def colored_text(v, suffix=""):
    color = tw_color(v)
    sign = "+" if v > 0 else ""
    return f'<span class="{color}-text">{sign}{v}{suffix}</span>'


def get_latest_pct(ticker):
    df = get_data(ticker, "5d")
    if df.empty or len(df) < 2:
        return None, None
    latest = df.iloc[-1]["Close"]
    prev = df.iloc[-2]["Close"]
    pct = (latest - prev) / prev * 100
    return latest, pct


def market_card(title, value, pct):
    if pct is None:
        pct = 0
    if pct > 0:
        color = "market-red"
        arrow = "▲"
    elif pct < 0:
        color = "market-green"
        arrow = "▼"
    else:
        color = "market-gray"
        arrow = "－"
    return f"""
    <div class="market-card">
        <div class="market-title">{title}</div>
        <div class="market-value">{value}</div>
        <div class="{color}">{arrow} {pct:+.2f}%</div>
    </div>
    """


def calc_support_resistance(df):
    recent = df.tail(20)
    current = recent.iloc[-1]["Close"]
    support_candidates = recent[recent["Low"] < current]["Low"]
    resistance_candidates = recent[recent["High"] > current]["High"]
    support = support_candidates.max() if not support_candidates.empty else recent["Low"].min()
    resistance = resistance_candidates.min() if not resistance_candidates.empty else recent["High"].max()
    return round(support, 2), round(resistance, 2)


def calc_net_profit(shares, cost_price, current_price, fee_discount):
    buy_amount = shares * cost_price
    sell_amount = shares * current_price
    buy_fee = buy_amount * BROKER_FEE_RATE * fee_discount
    sell_fee = sell_amount * BROKER_FEE_RATE * fee_discount
    sell_tax = sell_amount * SELL_TAX_RATE
    gross_profit = sell_amount - buy_amount
    net_profit = gross_profit - buy_fee - sell_fee - sell_tax
    net_profit_pct = net_profit / buy_amount * 100 if buy_amount else 0
    return buy_amount, sell_amount, net_profit, net_profit_pct


def ai_temperature():
    score = 50
    positive_targets = {"TSM": 10, "NVDA": 10, "^SOX": 10, "^IXIC": 8}
    negative_targets = {"^TNX": 8, "^VIX": 8, "DX-Y.NYB": 6}

    for ticker, weight in positive_targets.items():
        _, pct = get_latest_pct(ticker)
        if pct is not None:
            score += weight if pct > 0 else -weight

    for ticker, weight in negative_targets.items():
        _, pct = get_latest_pct(ticker)
        if pct is not None:
            score += weight if pct < 0 else -weight

    return int(max(0, min(100, score)))


def steel_temperature():
    score = 50
    positive_targets = {"HRC=F": 14, "ALI=F": 12, "HG=F": 8}

    for ticker, weight in positive_targets.items():
        _, pct = get_latest_pct(ticker)
        if pct is not None:
            score += weight if pct > 0 else -weight

    _, iron_pct = get_latest_pct("TIO=F")
    if iron_pct is not None:
        score += 4 if iron_pct > 0 else -4

    return int(max(0, min(100, score)))


def ai_temperature_comment(score):
    if score >= 80:
        return "🟢 AI環境強勢，但高分代表市場偏熱，長線續抱、不追高。"
    if score >= 60:
        return "🔵 AI環境中性偏多，可續抱，拉回再分批。"
    if score >= 40:
        return "🟡 AI環境中性偏弱，停止追價，等支撐。"
    return "🔴 AI環境偏弱，短線保守，暫緩加碼。"


def steel_temperature_comment(score):
    if score >= 75:
        return "🟢 原物料偏強，中鋼與大成鋼可觀察反彈。"
    if score >= 55:
        return "🔵 原物料中性偏多，續抱觀察。"
    if score >= 40:
        return "🟡 原物料中性偏弱，鋼鐵股暫不急著加碼。"
    return "🔴 原物料偏弱，中鋼與大成鋼先保守。"


def risk_distance_from_ma(df):
    if df.empty or len(df) < 120:
        return None, "資料不足"
    close = df.iloc[-1]["Close"]
    ma120 = df["Close"].rolling(120).mean().iloc[-1]
    distance = (close - ma120) / ma120 * 100

    if distance >= 35:
        level = "🔴 過熱，停止加碼，可考慮小幅減碼"
    elif distance >= 25:
        level = "🟡 偏熱，不追高"
    elif distance >= 10:
        level = "🔵 正常偏強，續抱"
    elif distance >= -5:
        level = "🟢 接近合理區，可分批觀察"
    else:
        level = "🟢 拉回區，可優先觀察加碼"
    return distance, level


def stock_long_term_advice(stock_name, current_price):
    rule = long_term_rules[stock_name]
    if current_price <= rule["strong_add"]:
        return "強力加碼區", "🟢"
    if current_price <= rule["add"]:
        return "加碼區", "🟢"
    if current_price >= rule["reduce"]:
        return "接近減碼區", "🟡"
    return "續抱觀察", "🔵"


def score_stock(stock_name, df, ai_score, steel_score, chip_score_20=0):
    if df.empty or len(df) < 120:
        return 50
    close = df.iloc[-1]["Close"]
    ma20 = df["Close"].rolling(20).mean().iloc[-1]
    ma60 = df["Close"].rolling(60).mean().iloc[-1]
    ma120 = df["Close"].rolling(120).mean().iloc[-1]

    score = 50
    score += 12 if close > ma20 else -8
    score += 12 if close > ma60 else -8
    score += 10 if close > ma120 else -10

    if long_term_rules[stock_name]["type"] == "AI":
        score += (ai_score - 50) * 0.35
    else:
        score += (steel_score - 50) * 0.35

    score += chip_score_20 * 3

    distance, _ = risk_distance_from_ma(df)
    if distance is not None:
        if distance >= 35:
            score -= 15
        elif distance >= 25:
            score -= 8
        elif distance <= -5:
            score += 8

    return int(max(0, min(100, score)))


@st.cache_data(ttl=3600)
def get_institutional_data(stock_id, days=45):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days * 2)

    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
        "data_id": stock_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if "data" not in data or len(data["data"]) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(data["data"])
        df["buy"] = pd.to_numeric(df["buy"], errors="coerce")
        df["sell"] = pd.to_numeric(df["sell"], errors="coerce")
        df["net"] = df["buy"] - df["sell"]
        return df

    except Exception:
        return pd.DataFrame()


def summarize_institutional(stock_name):
    stock_id = stock_id_map[stock_name]
    df = get_institutional_data(stock_id)

    if df.empty:
        return {
            "股票": stock_name,
            "外資5日": "N/A",
            "外資20日": "N/A",
            "投信5日": "N/A",
            "投信20日": "N/A",
            "自營商5日": "N/A",
            "籌碼建議": "資料不足",
            "chip_score_20": 0,
        }

    def summarize_days(days):
        recent_dates = sorted(df["date"].unique())[-days:]
        recent = df[df["date"].isin(recent_dates)].copy()

        def net_by_keywords(keywords):
            mask = pd.Series(False, index=recent.index)
            for keyword in keywords:
                mask = mask | recent["name"].astype(str).str.contains(keyword, case=False, na=False)
            sub = recent[mask]
            if sub.empty:
                return 0
            return sub["net"].sum() / 1000

        foreign = net_by_keywords(["外資", "Foreign", "Foreign_Investor", "Foreign_Dealer"])
        investment = net_by_keywords(["投信", "Investment", "Investment_Trust"])
        dealer = net_by_keywords(["自營商", "Dealer", "Dealer_self", "Dealer_Hedging"])
        return foreign, investment, dealer

    foreign_5, investment_5, dealer_5 = summarize_days(5)
    foreign_20, investment_20, dealer_20 = summarize_days(20)

    chip_score_20 = 0
    chip_score_20 += 2 if foreign_20 > 0 else -2
    chip_score_20 += 2 if investment_20 > 0 else -2
    chip_score_20 += 1 if dealer_5 > 0 else -1

    if chip_score_20 >= 3:
        advice = "🟢 20日法人偏多，長線籌碼穩定"
    elif chip_score_20 >= 0:
        advice = "🟡 法人中性，觀察是否連續買超"
    else:
        advice = "🔴 法人偏弱，暫不急著加碼"

    return {
        "股票": stock_name,
        "外資5日": f"{foreign_5:,.0f} 張",
        "外資20日": f"{foreign_20:,.0f} 張",
        "投信5日": f"{investment_5:,.0f} 張",
        "投信20日": f"{investment_20:,.0f} 張",
        "自營商5日": f"{dealer_5:,.0f} 張",
        "籌碼建議": advice,
        "chip_score_20": chip_score_20,
    }


def calc_consecutive_buy_days(stock_name, investor_keywords):
    stock_id = stock_id_map[stock_name]
    df = get_institutional_data(stock_id, days=40)

    if df.empty:
        return 0

    def day_net(day_df):
        mask = pd.Series(False, index=day_df.index)
        for keyword in investor_keywords:
            mask = mask | day_df["name"].astype(str).str.contains(keyword, case=False, na=False)
        sub = day_df[mask]
        if sub.empty:
            return 0
        return sub["net"].sum()

    count = 0
    for date in sorted(df["date"].unique(), reverse=True):
        daily = df[df["date"] == date]
        net = day_net(daily)
        if net > 0:
            count += 1
        else:
            break

    return count


def adr_prediction_text():
    tsm_price, tsm_pct = get_latest_pct("TSM")
    sox_price, sox_pct = get_latest_pct("^SOX")
    nvda_price, nvda_pct = get_latest_pct("NVDA")
    vix_price, vix_pct = get_latest_pct("^VIX")
    tnx_price, tnx_pct = get_latest_pct("^TNX")

    score = 0
    details = []

    if tsm_pct is not None:
        score += 2 if tsm_pct > 1 else 1 if tsm_pct > 0 else -1 if tsm_pct > -1 else -2
        details.append(f"台積電ADR {tsm_pct:+.2f}%")

    if sox_pct is not None:
        score += 2 if sox_pct > 1 else 1 if sox_pct > 0 else -1 if sox_pct > -1 else -2
        details.append(f"費半 {sox_pct:+.2f}%")

    if nvda_pct is not None:
        score += 1 if nvda_pct > 0 else -1
        details.append(f"輝達 {nvda_pct:+.2f}%")

    if vix_pct is not None:
        score += 1 if vix_pct < 0 else -1
        details.append(f"VIX {vix_pct:+.2f}%")

    if tnx_pct is not None:
        score += 1 if tnx_pct < 0 else -1
        details.append(f"美債10Y {tnx_pct:+.2f}%")

    if score >= 4:
        direction = "🟢 明日 AI / 半導體偏多"
        suggestion = "台積電、廣達、鴻海可續抱；若開高太多，仍不建議追高。"
    elif score >= 1:
        direction = "🔵 明日 AI / 半導體中性偏多"
        suggestion = "可續抱，觀察台積電是否站穩短均線。"
    elif score <= -3:
        direction = "🔴 明日 AI / 半導體偏弱"
        suggestion = "停止追價，等待拉回到支撐或加碼區。"
    else:
        direction = "🟡 明日 AI / 半導體中性"
        suggestion = "以個股支撐、法人籌碼與成交量為主。"

    return {
        "判斷": direction,
        "依據": "｜".join(details),
        "建議": suggestion,
    }


def add_reduce_light(stock_name, current_price, score, risk_text):
    rule = long_term_rules[stock_name]

    if current_price <= rule["strong_add"]:
        return "🟢 強力加碼"
    if current_price <= rule["add"]:
        return "🟢 分批加碼"

    if "過熱" in risk_text:
        return "🔴 停止加碼 / 可小幅減碼"

    if current_price >= rule["reduce"]:
        return "🟡 接近減碼區"

    if score >= 80:
        return "🔵 續抱，不追高"
    if score >= 60:
        return "🔵 續抱觀察"
    if score >= 45:
        return "🟡 暫停加碼"
    return "🔴 風險偏高"



@st.cache_data(ttl=3600)
def get_yahoo_news(ticker, limit=3):
    rows = []
    try:
        news = yf.Ticker(ticker).news
        for item in news[:limit]:
            title = item.get("title", "")
            publisher = item.get("publisher", "")
            link = item.get("link", "")
            if title:
                rows.append({"標題": title, "來源": publisher if publisher else "Yahoo Finance", "連結": link})
    except Exception:
        pass

    if rows:
        return rows[:limit]

    try:
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(ticker)}&region=US&lang=en-US"
        response = requests.get(rss_url, timeout=10)
        root = ET.fromstring(response.content)
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            source = item.findtext("source") or "Yahoo Finance RSS"
            if title:
                rows.append({"標題": title, "來源": source, "連結": link})
    except Exception:
        pass

    return rows[:limit]


@st.cache_data(ttl=3600)
def get_google_news(keyword, limit=3):
    rows = []
    try:
        rss_url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        response = requests.get(rss_url, timeout=10)
        root = ET.fromstring(response.content)

        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            source_node = item.find("source")
            source = source_node.text if source_node is not None else "Google News"
            if title:
                rows.append({"標題": title, "來源": source, "連結": link})
    except Exception:
        pass

    return rows[:limit]


def news_sentiment(title):
    positive_words = [
        "AI", "growth", "record", "surge", "beat", "strong", "upgrade",
        "Nvidia", "demand", "profit", "revenue", "rally", "bullish",
        "成長", "創高", "強勁", "調升", "買超", "伺服器", "需求", "擴產"
    ]
    negative_words = [
        "fall", "drop", "cut", "weak", "downgrade", "concern", "risk",
        "slowdown", "miss", "bearish", "warning",
        "下跌", "衰退", "下修", "賣超", "風險", "疲弱", "關稅", "庫存"
    ]

    score = 0
    title_lower = title.lower()

    for word in positive_words:
        if word.lower() in title_lower:
            score += 1

    for word in negative_words:
        if word.lower() in title_lower:
            score -= 1

    if score > 0:
        return "🟢 偏正面"
    if score < 0:
        return "🔴 偏負面"
    return "🟡 中性"


def generate_alerts(ai_score, steel_score, chip_score_map):
    alerts = []

    for stock_name, ticker in stock_list.items():
        df = get_data(ticker, "1y")
        if df.empty or len(df) < 120:
            continue

        current = df.iloc[-1]["Close"]
        ma20 = df["Close"].rolling(20).mean().iloc[-1]
        rule = long_term_rules[stock_name]
        distance, risk_level = risk_distance_from_ma(df)

        if current <= rule["add"]:
            alerts.append(f"🟢 {stock_name} 進入長線加碼觀察區，目前 {current:.2f}")
        elif current >= rule["reduce"]:
            alerts.append(f"🟡 {stock_name} 接近設定減碼區，目前 {current:.2f}")
        elif current < ma20:
            alerts.append(f"🔴 {stock_name} 跌破 MA20，短線偏弱，長線先觀察")
        else:
            gap_add = (current - rule["add"]) / current * 100
            alerts.append(f"🔵 {stock_name} 續抱觀察，距離加碼區約 {gap_add:.2f}%")

        if distance is not None and distance >= 25:
            alerts.append(f"⚠️ {stock_name} 距離半年線約 +{distance:.1f}%，{risk_level}")

        if chip_score_map.get(stock_name, 0) <= -3:
            alerts.append(f"⚠️ {stock_name} 20日法人籌碼偏弱，暫不急著加碼")

    if ai_score >= 80:
        alerts.append("🔥 AI市場溫度偏高，有利台積電、廣達、鴻海續強；但高分時也要避免追高。")
    elif ai_score <= 40:
        alerts.append("⚠️ AI市場溫度偏弱，AI族群短線需保守，等拉回再分批。")

    if steel_score >= 75:
        alerts.append("🔥 鋼鐵原物料偏強，有利中鋼、大成鋼反彈。")
    elif steel_score <= 40:
        alerts.append("⚠️ 鋼鐵原物料偏弱，中鋼、大成鋼暫時保守。")

    return alerts



def calc_add_map(stock_name, current_price):
    add_price = long_term_rules[stock_name]["add"]
    diff_pct = (current_price - add_price) / current_price * 100

    if current_price <= add_price:
        signal = "🟢 已進入加碼區"
    elif diff_pct <= 5:
        signal = "🟡 接近加碼區"
    else:
        signal = "🔴 距離較遠"

    return signal, round(diff_pct, 2)

def steel_stock_score():
    score = steel_temperature()
    if score >= 75:
        return score, "🟢 偏多"
    elif score >= 55:
        return score, "🔵 中性偏多"
    elif score >= 40:
        return score, "🟡 中性"
    return score, "🔴 偏弱"


def buy_point_progress(stock_name, current_price):
    add_price = long_term_rules[stock_name]["add"]
    strong_add = long_term_rules[stock_name]["strong_add"]

    if current_price <= strong_add:
        progress = 100
        text = "🟢 強力加碼區"
    elif current_price <= add_price:
        progress = 95
        text = "🟢 已進入加碼區"
    else:
        gap_pct = (current_price - add_price) / current_price * 100
        progress = max(0, min(90, int(100 - gap_pct * 10)))

        if gap_pct <= 3:
            text = "🟡 非常接近買點"
        elif gap_pct <= 8:
            text = "🟠 等待拉回"
        else:
            text = "🔴 離買點較遠"

    return progress, text


def leader_index_score():
    score = 50
    weights = {
        "NVDA": 18,
        "TSM": 18,
        "^SOX": 16,
        "^IXIC": 10,
        "^VIX": -10,
        "^TNX": -8,
        "DX-Y.NYB": -6,
    }

    for ticker, weight in weights.items():
        _, pct = get_latest_pct(ticker)
        if pct is None:
            continue

        if weight > 0:
            score += weight if pct > 0 else -weight
        else:
            score += abs(weight) if pct < 0 else -abs(weight)

    score = int(max(0, min(100, score)))

    if score >= 75:
        msg = "🟢 AI領先指數偏多"
    elif score >= 55:
        msg = "🔵 AI領先指數中性偏多"
    elif score >= 40:
        msg = "🟡 AI領先指數中性偏弱"
    else:
        msg = "🔴 AI領先指數偏弱"

    return score, msg


def steel_leader_index_score():
    score = 50
    weights = {
        "HRC=F": 18,
        "ALI=F": 14,
        "HG=F": 10,
        "TIO=F": 6,
        "DX-Y.NYB": -8,
        "^TNX": -6,
    }

    for ticker, weight in weights.items():
        _, pct = get_latest_pct(ticker)
        if pct is None:
            continue

        if weight > 0:
            score += weight if pct > 0 else -weight
        else:
            score += abs(weight) if pct < 0 else -abs(weight)

    score = int(max(0, min(100, score)))

    if score >= 75:
        msg = "🟢 鋼鐵領先指數偏多"
    elif score >= 55:
        msg = "🔵 鋼鐵領先指數中性偏多"
    elif score >= 40:
        msg = "🟡 鋼鐵領先指數中性偏弱"
    else:
        msg = "🔴 鋼鐵領先指數偏弱"

    return score, msg


def weekly_strategy(stock_name, current_price, health_score, chip_score, risk_text):
    progress, buy_text = buy_point_progress(stock_name, current_price)
    stock_type = long_term_rules[stock_name]["type"]

    if "過熱" in risk_text:
        return "🔴 停止加碼", "高檔風險偏高，避免追價"

    if current_price <= long_term_rules[stock_name]["add"]:
        return "🟢 分批加碼", "價格進入加碼區"

    if progress >= 80 and health_score >= 65:
        return "🟢 接近買點", "可分批觀察，不一次買滿"

    if health_score >= 80 and chip_score >= 0:
        return "🔵 續抱", "趨勢與籌碼仍可接受"

    if health_score >= 60:
        return "🟡 觀察", "等待更接近加碼價"

    return "🔴 保守", "健康度偏弱，暫緩加碼"


def institutional_strength_rank():
    rows = []
    for stock_name in stock_list:
        row = summarize_institutional(stock_name)
        try:
            foreign20 = float(str(row["外資20日"]).replace(",", "").replace(" 張", ""))
        except Exception:
            foreign20 = 0
        try:
            trust20 = float(str(row["投信20日"]).replace(",", "").replace(" 張", ""))
        except Exception:
            trust20 = 0

        strength = foreign20 + trust20

        rows.append({
            "股票": stock_name,
            "外資20日": row["外資20日"],
            "投信20日": row["投信20日"],
            "法人強度": round(strength),
        })

    return pd.DataFrame(rows).sort_values("法人強度", ascending=False)


def stock_diagnosis(stock_name, ticker, ai_score, steel_score, chip_score_map):
    df = get_data(ticker, "1y")
    if df.empty or len(df) < 120:
        return None

    current = float(df.iloc[-1]["Close"])
    health = score_stock(stock_name, df, ai_score, steel_score, chip_score_map.get(stock_name, 0))
    distance, risk_text = risk_distance_from_ma(df)
    progress, buy_text = buy_point_progress(stock_name, current)

    ma20 = df["Close"].rolling(20).mean().iloc[-1]
    ma60 = df["Close"].rolling(60).mean().iloc[-1]

    trend = "🟢 多頭" if current > ma20 and current > ma60 else "🟡 震盪" if current > ma60 else "🔴 偏弱"
    industry = ai_temperature_comment(ai_score) if long_term_rules[stock_name]["type"] == "AI" else steel_temperature_comment(steel_score)
    strategy, reason = weekly_strategy(stock_name, current, health, chip_score_map.get(stock_name, 0), risk_text)

    return {
        "股票": stock_name,
        "現價": round(current, 2),
        "健康度": health,
        "趨勢": trend,
        "買點狀態": buy_text,
        "高檔風險": risk_text,
        "產業環境": industry,
        "操作建議": strategy,
        "原因": reason,
    }




def health_display(score):
    if score >= 90:
        return f"🟢 {score} 優秀"
    elif score >= 75:
        return f"🔵 {score} 良好"
    elif score >= 60:
        return f"🟡 {score} 普通"
    else:
        return f"🔴 {score} 偏弱"


def medal_label(index, stock_name):
    medals = ["🥇", "🥈", "🥉"]
    if index < len(medals):
        return f"{medals[index]} {stock_name}"
    return stock_name


def technical_signal(stock_name, ticker):
    df = get_data(ticker, "1y")
    if df.empty or len(df) < 120:
        return "資料不足", 50

    close = float(df.iloc[-1]["Close"])
    ma20 = float(df["Close"].rolling(20).mean().iloc[-1])
    ma60 = float(df["Close"].rolling(60).mean().iloc[-1])
    ma120 = float(df["Close"].rolling(120).mean().iloc[-1])

    score = 50
    score += 15 if close > ma20 else -10
    score += 15 if close > ma60 else -10
    score += 15 if close > ma120 else -10
    score += 10 if ma20 > ma60 else -5

    score = int(max(0, min(100, score)))

    if score >= 80:
        signal = "🟢 多頭"
    elif score >= 60:
        signal = "🔵 偏多"
    elif score >= 45:
        signal = "🟡 震盪"
    else:
        signal = "🔴 偏弱"

    return signal, score


def estimate_add_shares(stock_name, cash):
    df = get_data(stock_list[stock_name], "5d")
    if df.empty:
        return 0, 0

    price = float(df.iloc[-1]["Close"])
    if price <= 0:
        return 0, 0

    shares = int(cash // price)
    amount = round(shares * price)
    return shares, amount


def dividend_yield_estimate(stock_name, current_price):
    # 簡易參考值：可自行依實際配息調整
    dividend_map = {
        "台積電": 24.0,
        "鴻海": 5.8,
        "廣達": 9.0,
        "大成鋼": 1.0,
        "中鋼": 0.35,
    }

    dividend = dividend_map.get(stock_name, 0)
    if current_price <= 0:
        return 0

    return round(dividend / current_price * 100, 2)


def portfolio_performance_rows(portfolio, fee_discount):
    rows = []

    for stock_name, info in portfolio.items():
        df = get_data(stock_list[stock_name], "5d")
        if df.empty or len(df) < 2:
            continue

        current = float(df.iloc[-1]["Close"])
        buy_amount, sell_amount, net_profit, net_profit_pct = calc_net_profit(
            info["shares"], info["cost"], current, fee_discount
        )

        rows.append({
            "股票": stock_name,
            "現價": round(current, 2),
            "成本": round(info["cost"], 2),
            "股數": info["shares"],
            "已扣費損益": round(net_profit),
            "報酬率數值": net_profit_pct,
            "狀態": "🟢 賺錢" if net_profit > 0 else "🔴 虧損" if net_profit < 0 else "⚪ 打平",
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("已扣費損益", ascending=False).reset_index(drop=True)
    df["股票"] = [medal_label(i, name) for i, name in enumerate(df["股票"])]
    df["報酬率"] = df["報酬率數值"].map(lambda x: f"{x:.2f}%")
    df = df.drop(columns=["報酬率數值"])
    return df


def cost_warning_rows(portfolio):
    rows = []

    for stock_name, info in portfolio.items():
        df = get_data(stock_list[stock_name], "5d")
        if df.empty:
            continue

        current = float(df.iloc[-1]["Close"])
        cost = float(info["cost"])
        gap_pct = (current - cost) / cost * 100 if cost else 0

        if current < cost:
            warning = "🔴 跌破成本"
        elif gap_pct <= 3:
            warning = "🟡 接近成本"
        else:
            warning = "🟢 高於成本"

        rows.append({
            "股票": stock_name,
            "現價": round(current, 2),
            "成本": round(cost, 2),
            "與成本差距": f"{gap_pct:+.2f}%",
            "警示": warning,
        })

    return pd.DataFrame(rows)


def v64_dashboard_rows(portfolio, cash_input):
    rows = []

    for stock_name, ticker in stock_list.items():
        df = get_data(ticker, "1y")
        if df.empty:
            continue

        current = float(df.iloc[-1]["Close"])
        tech_signal, tech_score = technical_signal(stock_name, ticker)
        add_shares, add_amount = estimate_add_shares(stock_name, cash_input)
        div_yield = dividend_yield_estimate(stock_name, current)

        rows.append({
            "股票": stock_name,
            "現價": round(current, 2),
            "技術面": tech_signal,
            "技術分數": tech_score,
            "本月可買股數": add_shares,
            "試算金額": add_amount,
            "股利殖利率參考": f"{div_yield:.2f}%",
        })

    return pd.DataFrame(rows)



def fear_greed_index(ai_score, steel_score):
    score = 50

    _, vix_pct = get_latest_pct("^VIX")
    _, tnx_pct = get_latest_pct("^TNX")
    _, dxy_pct = get_latest_pct("DX-Y.NYB")
    _, tsm_pct = get_latest_pct("TSM")
    _, sox_pct = get_latest_pct("^SOX")

    if vix_pct is not None:
        score += 15 if vix_pct < 0 else -15
    if tnx_pct is not None:
        score += 10 if tnx_pct < 0 else -10
    if dxy_pct is not None:
        score += 8 if dxy_pct < 0 else -8
    if tsm_pct is not None:
        score += 12 if tsm_pct > 0 else -12
    if sox_pct is not None:
        score += 10 if sox_pct > 0 else -10

    score += (ai_score - 50) * 0.25
    score += (steel_score - 50) * 0.10

    score = int(max(0, min(100, score)))

    if score >= 75:
        text = "🟢 偏貪婪：市場偏熱，續抱但不要追高"
    elif score >= 55:
        text = "🔵 中性偏多：可續抱，拉回分批"
    elif score >= 40:
        text = "🟡 中性偏保守：等支撐，不急買"
    else:
        text = "🔴 偏恐慌：短線保守，適合觀察低接區"

    return score, text


def operation_signal(stock_name, current_price, health_score, chip_score, risk_text):
    progress, buy_text = buy_point_progress(stock_name, current_price)

    if "過熱" in risk_text:
        return "🔴 減碼/停買", "高檔風險偏高"

    if current_price <= long_term_rules[stock_name]["add"] and health_score >= 60:
        return "🟢 可加碼", "進入加碼區且健康度可接受"

    if progress >= 80 and health_score >= 75:
        return "🟢 可分批", "接近買點且健康度良好"

    if health_score >= 75 and chip_score >= 0:
        return "🔵 續抱", "趨勢與籌碼仍穩定"

    if health_score >= 55:
        return "🟡 觀察", "等拉回或等籌碼轉強"

    return "🔴 保守", "健康度偏弱"


def dividend_rows(portfolio):
    rows = []
    dividend_map = {
        "台積電": 24.0,
        "鴻海": 5.8,
        "廣達": 9.0,
        "大成鋼": 1.0,
        "中鋼": 0.35,
    }

    total_dividend = 0
    for stock_name, info in portfolio.items():
        shares = info["shares"]
        dps = dividend_map.get(stock_name, 0)
        expected = shares * dps
        total_dividend += expected

        rows.append({
            "股票": stock_name,
            "預估每股股利": f"{dps:.2f}",
            "股數": shares,
            "預估股息收入": round(expected),
        })

    return pd.DataFrame(rows), round(total_dividend)


def allocation_radar_rows(portfolio):
    rows = []
    total_value = 0
    value_map = {}

    for stock_name, info in portfolio.items():
        df = get_data(stock_list[stock_name], "5d")
        if df.empty:
            continue

        current = float(df.iloc[-1]["Close"])
        value = current * info["shares"]
        value_map[stock_name] = value
        total_value += value

    for stock_name, value in value_map.items():
        stock_type = long_term_rules[stock_name]["type"]
        category = "AI / 半導體" if stock_type == "AI" else "鋼鐵 / 原物料"
        pct = value / total_value * 100 if total_value else 0
        rows.append({
            "股票": stock_name,
            "類別": category,
            "市值": round(value),
            "配置比例": f"{pct:.1f}%",
        })

    return pd.DataFrame(rows)


def asset_allocation_summary(portfolio):
    df = allocation_radar_rows(portfolio)
    if df.empty:
        return pd.DataFrame(), "目前沒有持股資料。"

    tmp = df.copy()
    tmp["配置數值"] = tmp["配置比例"].str.replace("%", "", regex=False).astype(float)
    summary = tmp.groupby("類別", as_index=False)["配置數值"].sum()
    summary["配置比例"] = summary["配置數值"].map(lambda x: f"{x:.1f}%")
    summary = summary.drop(columns=["配置數值"])

    ai_pct = 0
    steel_pct = 0
    for _, row in summary.iterrows():
        if row["類別"] == "AI / 半導體":
            ai_pct = float(row["配置比例"].replace("%", ""))
        elif row["類別"] == "鋼鐵 / 原物料":
            steel_pct = float(row["配置比例"].replace("%", ""))

    if ai_pct >= 85:
        note = "⚠️ AI部位偏高，後續加碼可更謹慎。"
    elif steel_pct >= 35:
        note = "⚠️ 鋼鐵部位偏高，需留意景氣循環。"
    elif ai_pct >= 65:
        note = "🔵 AI為核心配置，符合目前主軸。"
    else:
        note = "🟢 配置相對均衡。"

    return summary, note


def ai_investment_summary(portfolio, ai_score, steel_score, chip_score_map):
    rows = []

    for stock_name, ticker in stock_list.items():
        df = get_data(ticker, "1y")
        if df.empty or len(df) < 120:
            continue

        current = float(df.iloc[-1]["Close"])
        health = score_stock(stock_name, df, ai_score, steel_score, chip_score_map.get(stock_name, 0))
        _, risk_text = risk_distance_from_ma(df)
        signal, reason = operation_signal(
            stock_name,
            current,
            health,
            chip_score_map.get(stock_name, 0),
            risk_text,
        )
        progress, buy_text = buy_point_progress(stock_name, current)

        rows.append({
            "股票": stock_name,
            "操作燈號": signal,
            "主要理由": reason,
            "買點狀態": buy_text,
            "健康度": health_display(health),
        })

    return pd.DataFrame(rows)


def watchlist_today(portfolio, ai_score, steel_score, chip_score_map):
    rows = []

    for stock_name, ticker in stock_list.items():
        df = get_data(ticker, "1y")
        if df.empty or len(df) < 120:
            continue

        current = float(df.iloc[-1]["Close"])
        health = score_stock(stock_name, df, ai_score, steel_score, chip_score_map.get(stock_name, 0))
        _, risk_text = risk_distance_from_ma(df)
        progress, buy_text = buy_point_progress(stock_name, current)

        priority = 0
        if progress >= 80:
            priority += 3
        if health >= 75:
            priority += 2
        if chip_score_map.get(stock_name, 0) >= 0:
            priority += 1
        if "過熱" in risk_text:
            priority -= 3

        rows.append({
            "股票": stock_name,
            "優先度": priority,
            "觀察重點": buy_text,
            "健康度": health_display(health),
            "高檔風險": risk_text,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("優先度", ascending=False).reset_index(drop=True)
    df["排名"] = [medal_label(i, name) for i, name in enumerate(df["股票"])]
    return df[["排名", "觀察重點", "健康度", "高檔風險"]]




def get_secret_value(name, default=""):
    try:
        value = st.secrets.get(name, default)
        if value is None:
            return default
        return str(value).strip()
    except Exception:
        return os.environ.get(name, default).strip()


def line_config_status():
    token = get_secret_value("LINE_CHANNEL_ACCESS_TOKEN")
    to_id = get_secret_value("LINE_USER_ID") or get_secret_value("LINE_TO_ID")

    if token and to_id:
        return True, "🟢 LINE Messaging API 已設定完成"
    return False, "🟡 尚未設定 LINE Token / User ID，系統會顯示預警但不會推播"


def send_line_message(message):
    token = get_secret_value("LINE_CHANNEL_ACCESS_TOKEN")
    to_id = get_secret_value("LINE_USER_ID") or get_secret_value("LINE_TO_ID")

    if not token or not to_id:
        return False, "尚未設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_USER_ID。"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": to_id,
        "messages": [
            {
                "type": "text",
                "text": message[:4500],
            }
        ],
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code in [200, 202]:
            return True, "LINE通知已送出。"
        return False, f"LINE通知失敗：HTTP {response.status_code}｜{response.text[:300]}"
    except Exception as e:
        return False, f"LINE通知失敗：{e}"


def calc_consecutive_sell_days(stock_name, investor_keywords):
    stock_id = stock_id_map[stock_name]
    df = get_institutional_data(stock_id, days=40)

    if df.empty:
        return 0

    def day_net(day_df):
        mask = pd.Series(False, index=day_df.index)
        for keyword in investor_keywords:
            mask = mask | day_df["name"].astype(str).str.contains(keyword, case=False, na=False)
        sub = day_df[mask]
        if sub.empty:
            return 0
        return sub["net"].sum()

    count = 0
    for date in sorted(df["date"].unique(), reverse=True):
        daily = df[df["date"] == date]
        net = day_net(daily)
        if net < 0:
            count += 1
        else:
            break

    return count


def build_auto_alerts(portfolio, ai_score, steel_score, chip_score_map):
    rows = []

    fg_score, fg_text = fear_greed_index(ai_score, steel_score)
    if fg_score >= 78:
        rows.append({"等級": "🟠 市場偏熱", "股票": "整體市場", "訊息": fg_text, "建議": "避免追高，保留現金"})
    elif fg_score <= 35:
        rows.append({"等級": "🔴 市場偏恐慌", "股票": "整體市場", "訊息": fg_text, "建議": "先保守，等支撐或分批低接"})

    for stock_name, ticker in stock_list.items():
        df = get_data(ticker, "1y")
        if df.empty or len(df) < 120:
            continue

        current = float(df.iloc[-1]["Close"])
        rule = long_term_rules[stock_name]
        health = score_stock(stock_name, df, ai_score, steel_score, chip_score_map.get(stock_name, 0))
        distance, risk_text = risk_distance_from_ma(df)
        progress, buy_text = buy_point_progress(stock_name, current)
        add_gap = (current - rule["add"]) / current * 100 if current else 999
        reduce_gap = (rule["reduce"] - current) / current * 100 if current else 999

        if current <= rule["strong_add"]:
            rows.append({"等級": "🟢 強力買點", "股票": stock_name, "訊息": f"現價 {current:.2f} 已低於強力加碼價 {rule['strong_add']}", "建議": "可分批加碼，不一次買滿"})
        elif current <= rule["add"]:
            rows.append({"等級": "🟢 加碼區", "股票": stock_name, "訊息": f"現價 {current:.2f} 已進入加碼價 {rule['add']} 附近", "建議": "可小量分批"})
        elif 0 < add_gap <= 2:
            rows.append({"等級": "🟡 接近買點", "股票": stock_name, "訊息": f"距離加碼價約 {add_gap:.2f}%", "建議": "加入觀察，等待拉回"})

        if current >= rule["reduce"] or "過熱" in risk_text:
            rows.append({"等級": "🔴 高檔風險", "股票": stock_name, "訊息": f"現價 {current:.2f}｜{risk_text}", "建議": "停止追高，必要時小幅減碼"})
        elif 0 < reduce_gap <= 3:
            rows.append({"等級": "🟠 接近減碼區", "股票": stock_name, "訊息": f"距離減碼價約 {reduce_gap:.2f}%", "建議": "續抱但不追價"})

        foreign_buy = calc_consecutive_buy_days(stock_name, ["外資", "Foreign", "Foreign_Investor", "Foreign_Dealer"])
        trust_buy = calc_consecutive_buy_days(stock_name, ["投信", "Investment", "Investment_Trust"])
        foreign_sell = calc_consecutive_sell_days(stock_name, ["外資", "Foreign", "Foreign_Investor", "Foreign_Dealer"])
        trust_sell = calc_consecutive_sell_days(stock_name, ["投信", "Investment", "Investment_Trust"])

        if foreign_buy >= 5 or trust_buy >= 5:
            rows.append({"等級": "🟢 法人轉強", "股票": stock_name, "訊息": f"外資連買 {foreign_buy} 天｜投信連買 {trust_buy} 天", "建議": "籌碼偏多，可列入優先觀察"})
        if foreign_sell >= 5 or trust_sell >= 5:
            rows.append({"等級": "🔴 法人轉弱", "股票": stock_name, "訊息": f"外資連賣 {foreign_sell} 天｜投信連賣 {trust_sell} 天", "建議": "暫緩加碼，觀察是否止賣"})

        if stock_name in portfolio:
            cost = float(portfolio[stock_name]["cost"])
            if cost > 0:
                cost_gap = (current - cost) / cost * 100
                if current < cost:
                    rows.append({"等級": "🔴 跌破成本", "股票": stock_name, "訊息": f"現價 {current:.2f} 低於成本 {cost:.2f}（{cost_gap:.2f}%）", "建議": "不要急攤平，先看趨勢與法人"})
                elif 0 <= cost_gap <= 2:
                    rows.append({"等級": "🟡 接近成本", "股票": stock_name, "訊息": f"現價接近成本，差距 {cost_gap:.2f}%", "建議": "觀察是否守住成本區"})

    if not rows:
        rows.append({"等級": "🔵 無重大預警", "股票": "整體", "訊息": "目前沒有觸發加碼、減碼或法人異常條件", "建議": "依原策略續抱觀察"})

    return pd.DataFrame(rows)


def format_line_alert_message(alert_df, ai_score, steel_score):
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"Hsing 投資儀表板 V7.1 預警｜{now_text}",
        f"AI溫度：{ai_score} 分｜鋼鐵溫度：{steel_score} 分",
        "",
    ]

    for _, row in alert_df.head(12).iterrows():
        lines.append(f"{row['等級']}｜{row['股票']}")
        lines.append(f"{row['訊息']}")
        lines.append(f"建議：{row['建議']}")
        lines.append("")

    lines.append("提醒：此為儀表板輔助判斷，請搭配資金控管。")
    return "\n".join(lines)

def allocation_suggestion(cash, ai_score, steel_score):
    weights = {
        "台積電": 0.45,
        "廣達": 0.25,
        "鴻海": 0.20,
        "大成鋼": 0.05,
        "中鋼": 0.05,
    }

    if ai_score >= 80:
        weights["台積電"] += 0.05
        weights["廣達"] += 0.03
        weights["鴻海"] += 0.02
        weights["大成鋼"] -= 0.05
        weights["中鋼"] -= 0.05
    elif ai_score <= 40:
        weights["台積電"] -= 0.05
        weights["廣達"] -= 0.03
        weights["鴻海"] -= 0.02
        weights["大成鋼"] += 0.05
        weights["中鋼"] += 0.05

    if steel_score >= 75:
        weights["大成鋼"] += 0.05
        weights["中鋼"] += 0.05
        weights["台積電"] -= 0.05
        weights["廣達"] -= 0.03
        weights["鴻海"] -= 0.02

    rows = []
    for stock, w in weights.items():
        w = max(w, 0)
        rows.append({"股票": stock, "配置比例": f"{w * 100:.0f}%", "建議金額": round(cash * w)})
    return pd.DataFrame(rows)


# =====================================================
# 主畫面
# =====================================================

st.title("🚨 Hsing 投資儀表板 V7.1 自動預警版 + LINE通知版")

st.markdown("""
<div class="print-note">
<b>列印建議：</b>
使用瀏覽器列印時，建議選擇「另存為 PDF」、
紙張 A4、邊界選「預設」或「最小」、縮放建議 80%～90%。
若 K 線圖仍被切到，建議先把期間切到 1M 或 2M 再列印。
</div>
""", unsafe_allow_html=True)


st.info("""
V7.1 自動預警版新增功能：
✅ AI投資總結
✅ 操作燈號中心
✅ 資產配置雷達
✅ 台股恐慌貪婪指數
✅ 除權息 / 股息收入估算
✅ 今日重點觀察清單
✅ 超級買點預警
✅ 法人連買 / 連賣警報
✅ 成本價警示整合
✅ LINE Messaging API 推播通知

V6.4a 功能：
✅ 報酬率顯示百分比
✅ 健康度顏色強化
✅ 整體字體放大
✅ 持股績效前三名獎牌
✅ 表格可讀性優化
✅ 修正標題貼頂顯示
✅ 持股績效排名
✅ 跌破成本警示
✅ 加碼股數試算
✅ 技術面燈號
✅ 股利殖利率參考

V6.3 功能：
✅ 本週策略中心
✅ 買點雷達進度條
✅ 法人強度排行榜
✅ AI / 鋼鐵領先指數
✅ 個股診斷中心
✅ 持股健康度2.0

V6.0 新增功能：
✅ 外資/投信連買天數
✅ ADR隔日提示
✅ 加碼紅綠燈
✅ 長線評分
✅ AI/鋼鐵市場溫度
✅ 個人化資金配置建議
""")


saved_portfolio = load_portfolio()

with st.sidebar:
    st.header("⚙️ 持股設定")

    fee_discount = st.number_input("元大手續費折扣", min_value=0.52, max_value=1.0, value=0.52, step=0.01)
    cash_input = st.number_input("本月可投入資金", min_value=0, value=30000, step=1000)

    portfolio = {}

    for stock_name in stock_list.keys():
        st.markdown(f"### {stock_name}")

        default_shares = saved_portfolio.get(stock_name, {"shares": 0})["shares"]
        default_cost = saved_portfolio.get(stock_name, {"cost": 0.0})["cost"]

        shares = st.number_input(f"{stock_name} 股數", min_value=0, value=int(default_shares), step=1)
        cost = st.number_input(f"{stock_name} 成本價", min_value=0.0, value=float(default_cost), step=0.01, format="%.2f")

        if shares > 0 and cost > 0:
            portfolio[stock_name] = {"shares": shares, "cost": cost}

    if st.button("💾 儲存持股"):
        save_portfolio(portfolio)
        st.success("持股資料已儲存")

ai_score = ai_temperature()
steel_score = steel_temperature()

chip_rows = []
chip_score_map = {}

for stock_name in stock_list:
    row = summarize_institutional(stock_name)
    chip_score_map[stock_name] = row.pop("chip_score_20", 0)
    chip_rows.append(row)

# 今日提醒
st.subheader("🔔 今日提醒")
alerts = generate_alerts(ai_score, steel_score, chip_score_map)

for alert in alerts:
    st.markdown(f'<div class="alert-card">{alert}</div>', unsafe_allow_html=True)

st.divider()

st.subheader("🚨 V7.1 自動預警中心")
line_ready, line_status = line_config_status()
st.info(line_status)
st.caption("LINE Notify 已於 2025/03/31 結束服務；本版使用 LINE Messaging API。若未設定 Token，預警仍會在儀表板顯示，不會推播。")

auto_alert_df = build_auto_alerts(portfolio, ai_score, steel_score, chip_score_map)
st.dataframe(auto_alert_df, use_container_width=True, hide_index=True)

line_message = format_line_alert_message(auto_alert_df, ai_score, steel_score)

col_line1, col_line2 = st.columns(2)
with col_line1:
    if st.button("📲 手動發送 LINE 預警", disabled=not line_ready):
        ok, msg = send_line_message(line_message)
        if ok:
            st.success(msg)
        else:
            st.error(msg)

with col_line2:
    today_key = datetime.now().strftime("%Y%m%d")
    if "line_sent_date" not in st.session_state:
        st.session_state["line_sent_date"] = ""

    auto_send = st.checkbox("今天開啟後自動發送一次", value=False, disabled=not line_ready)
    if auto_send and line_ready and st.session_state["line_sent_date"] != today_key:
        ok, msg = send_line_message(line_message)
        if ok:
            st.session_state["line_sent_date"] = today_key
            st.success("今日 LINE 預警已自動發送一次。")
        else:
            st.error(msg)
    elif auto_send and st.session_state["line_sent_date"] == today_key:
        st.info("今日已發送過一次，避免重複推播。")

with st.expander("LINE Messaging API 設定說明"):
    st.markdown("""
    1. 建立 LINE 官方帳號，並啟用 Messaging API。  
    2. 到 LINE Developers 取得 **Channel access token**。  
    3. 取得你的 **User ID** 或群組 ID。  
    4. 在 Streamlit Cloud 的 **Secrets** 加入：

    ```toml
    LINE_CHANNEL_ACCESS_TOKEN = "你的 Channel access token"
    LINE_USER_ID = "你的 userId 或 groupId"
    ```

    儲存後重新部署即可使用 LINE 推播。
    """)

st.divider()


st.subheader("🤖 V7.1 AI投資管家總結")

fg_score, fg_text = fear_greed_index(ai_score, steel_score)
c1, c2, c3 = st.columns(3)
c1.metric("台股恐慌貪婪指數", f"{fg_score} 分")
c2.metric("AI市場溫度", f"{ai_score} 分")
c3.metric("鋼鐵市場溫度", f"{steel_score} 分")
st.info(fg_text)

summary_df = ai_investment_summary(portfolio, ai_score, steel_score, chip_score_map)
if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.subheader("🚦 操作燈號中心")
signal_rows = []
for stock_name, ticker in stock_list.items():
    df_sig = get_data(ticker, "1y")
    if df_sig.empty or len(df_sig) < 120:
        continue

    current_sig = float(df_sig.iloc[-1]["Close"])
    health_sig = score_stock(stock_name, df_sig, ai_score, steel_score, chip_score_map.get(stock_name, 0))
    _, risk_sig = risk_distance_from_ma(df_sig)
    sig, reason = operation_signal(stock_name, current_sig, health_sig, chip_score_map.get(stock_name, 0), risk_sig)

    signal_rows.append({
        "股票": stock_name,
        "燈號": sig,
        "原因": reason,
        "現價": round(current_sig, 2),
        "健康度": health_display(health_sig),
    })

if signal_rows:
    st.dataframe(pd.DataFrame(signal_rows), use_container_width=True, hide_index=True)

st.subheader("🎯 今日重點觀察")
watch_df = watchlist_today(portfolio, ai_score, steel_score, chip_score_map)
if not watch_df.empty:
    st.dataframe(watch_df, use_container_width=True, hide_index=True)

st.subheader("📦 資產配置雷達")
alloc_summary, alloc_note = asset_allocation_summary(portfolio)
if not alloc_summary.empty:
    st.dataframe(alloc_summary, use_container_width=True, hide_index=True)
st.info(alloc_note)

st.subheader("💵 除權息 / 股息收入估算")
div_df, total_div = dividend_rows(portfolio)
if not div_df.empty:
    st.dataframe(div_df, use_container_width=True, hide_index=True)
    st.metric("預估全年股息收入", f"{total_div:,.0f} 元")

st.divider()


st.subheader("🧭 V7.1 本週策略中心")

strategy_rows = []
for stock_name, ticker in stock_list.items():
    df_s = get_data(ticker, "1y")
    if df_s.empty or len(df_s) < 120:
        continue

    current_s = float(df_s.iloc[-1]["Close"])
    health_s = score_stock(stock_name, df_s, ai_score, steel_score, chip_score_map.get(stock_name, 0))
    _, risk_s = risk_distance_from_ma(df_s)
    strategy_s, reason_s = weekly_strategy(
        stock_name,
        current_s,
        health_s,
        chip_score_map.get(stock_name, 0),
        risk_s
    )

    progress_s, buy_text_s = buy_point_progress(stock_name, current_s)

    strategy_rows.append({
        "股票": stock_name,
        "本週建議": strategy_s,
        "理由": reason_s,
        "買點狀態": buy_text_s,
        "健康度": health_display(health_s),
    })

if strategy_rows:
    st.dataframe(pd.DataFrame(strategy_rows), use_container_width=True, hide_index=True)

st.subheader("📊 買點雷達")
for stock_name, ticker in stock_list.items():
    df_b = get_data(ticker, "1y")
    if df_b.empty:
        continue

    current_b = float(df_b.iloc[-1]["Close"])
    progress_b, text_b = buy_point_progress(stock_name, current_b)
    st.write(f"**{stock_name}**｜現價 {current_b:.2f}｜加碼價 {long_term_rules[stock_name]['add']}｜{text_b}")
    st.progress(progress_b / 100)

st.subheader("🔥 AI / 鋼鐵領先指數")
leader_ai, leader_ai_msg = leader_index_score()
leader_steel, leader_steel_msg = steel_leader_index_score()
c1, c2 = st.columns(2)
c1.metric("AI領先指數", f"{leader_ai} 分", leader_ai_msg)
c2.metric("鋼鐵領先指數", f"{leader_steel} 分", leader_steel_msg)

st.subheader("🏆 法人強度排行榜")
rank_df = institutional_strength_rank()
st.dataframe(rank_df, use_container_width=True, hide_index=True)

st.divider()


st.subheader("🧰 V7.1 持股管理中心")
v64_df = v64_dashboard_rows(portfolio, cash_input)
if not v64_df.empty:
    st.dataframe(v64_df, use_container_width=True, hide_index=True)

st.subheader("🏆 持股績效排名")
perf_df = portfolio_performance_rows(portfolio, fee_discount)
if not perf_df.empty:
    st.dataframe(perf_df, use_container_width=True, hide_index=True)
else:
    st.info("目前沒有持股資料可排序。")

st.subheader("🚨 成本價警示")
warn_df = cost_warning_rows(portfolio)
if not warn_df.empty:
    st.dataframe(warn_df, use_container_width=True, hide_index=True)

st.divider()


# AI 市場
st.subheader("🤖 AI / 半導體市場儀表板")
st.markdown('<div class="section-note">強化版：台積電ADR、輝達、費半、NASDAQ為正向；美債10Y、VIX、DXY上升為壓力。</div>', unsafe_allow_html=True)

cols = st.columns(len(ai_market_list))

for i, (name, ticker) in enumerate(ai_market_list.items()):
    latest, pct = get_latest_pct(ticker)
    cols[i].markdown(market_card(name, "N/A" if latest is None else f"{latest:.2f}", pct), unsafe_allow_html=True)

st.metric("AI市場溫度", f"{ai_score} 分")
st.info(ai_temperature_comment(ai_score))

st.divider()

# 鋼鐵 / 原物料
st.subheader("🏗️ 鋼鐵 / 原物料儀表板")
st.markdown('<div class="section-note">強化版：熱軋鋼、鋁價、銅價偏正向；鐵礦砂上漲雖代表需求，但也可能推升成本。</div>', unsafe_allow_html=True)

cols = st.columns(len(commodity_list))

for i, (name, ticker) in enumerate(commodity_list.items()):
    latest, pct = get_latest_pct(ticker)
    cols[i].markdown(market_card(name, "N/A" if latest is None else f"{latest:.2f}", pct), unsafe_allow_html=True)

st.metric("鋼鐵市場溫度", f"{steel_score} 分")
st.info(steel_temperature_comment(steel_score))

st.divider()

# 法人籌碼
st.subheader("📊 法人籌碼中心：5日 / 20日趨勢")
chip_df = pd.DataFrame(chip_rows)
st.dataframe(chip_df, use_container_width=True, hide_index=True)

st.subheader("📈 法人連買天數")
consecutive_rows = []

for stock_name in stock_list:
    foreign_days = calc_consecutive_buy_days(
        stock_name,
        ["外資", "Foreign", "Foreign_Investor", "Foreign_Dealer"]
    )
    trust_days = calc_consecutive_buy_days(
        stock_name,
        ["投信", "Investment", "Investment_Trust"]
    )

    if foreign_days >= 5 or trust_days >= 5:
        signal = "🟢 籌碼偏多"
    elif foreign_days >= 2 or trust_days >= 2:
        signal = "🔵 籌碼轉強觀察"
    else:
        signal = "🟡 尚未連續買超"

    consecutive_rows.append({
        "股票": stock_name,
        "外資連買": f"{foreign_days} 天",
        "投信連買": f"{trust_days} 天",
        "籌碼燈號": signal,
    })

consecutive_df = pd.DataFrame(consecutive_rows)
st.dataframe(consecutive_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("🌙 台積電 ADR / 美股隔日提示")
adr_info = adr_prediction_text()
st.markdown(f"""
<div class="alert-card">
<b>{adr_info['判斷']}</b><br>
依據：{adr_info['依據']}<br>
建議：{adr_info['建議']}
</div>
""", unsafe_allow_html=True)

st.divider()

# 高檔風險雷達
st.subheader("🚦 高檔風險雷達")

risk_rows = []

for stock_name, ticker in stock_list.items():
    df = get_data(ticker, "1y")
    if df.empty or len(df) < 120:
        continue

    close = df.iloc[-1]["Close"]
    distance, risk_level = risk_distance_from_ma(df)

    risk_rows.append({
        "股票": stock_name,
        "現價": round(close, 2),
        "距離半年線": "N/A" if distance is None else f"{distance:+.2f}%",
        "風險判斷": risk_level,
    })

risk_df = pd.DataFrame(risk_rows)
st.dataframe(risk_df, use_container_width=True, hide_index=True)

st.divider()

# 新聞
st.subheader("📰 今日個股新聞摘要")

for name, info in news_targets.items():
    st.markdown(f"### {name}")

    ticker = info["ticker"]
    keyword = info["keyword"]

    if ticker.endswith(".TW"):
        news_rows = get_google_news(keyword, limit=3)
    else:
        news_rows = get_yahoo_news(ticker, limit=3)
        if not news_rows:
            news_rows = get_google_news(keyword, limit=3)

    if not news_rows:
        st.info("目前沒有抓到新聞。")
        continue

    for news in news_rows:
        sentiment = news_sentiment(news["標題"])
        link = news["連結"]

        if link:
            st.markdown(f"**{sentiment}｜{news['標題']}**  \n來源：{news['來源']}  \n[閱讀新聞]({link})")
        else:
            st.markdown(f"**{sentiment}｜{news['標題']}**  \n來源：{news['來源']}")

st.divider()


st.subheader("🎯 V7.1 個人加碼地圖")

map_rows = []
for stock_name, ticker in stock_list.items():
    df_tmp = get_data(ticker, "1y")
    if not df_tmp.empty:
        current_price = float(df_tmp.iloc[-1]["Close"])
        signal, diff_pct = calc_add_map(stock_name, current_price)
        map_rows.append({
            "股票": stock_name,
            "現價": round(current_price,2),
            "加碼價": long_term_rules[stock_name]["add"],
            "距離加碼區(%)": diff_pct,
            "燈號": signal
        })

if map_rows:
    st.dataframe(pd.DataFrame(map_rows), use_container_width=True, hide_index=True)

steel_score_v61, steel_msg = steel_stock_score()

st.subheader("🏭 大成鋼 / 中鋼 溫度中心")
c1,c2 = st.columns(2)
c1.metric("鋼鐵溫度", f"{steel_score_v61} 分")
c2.metric("景氣燈號", steel_msg)

st.divider()


# 長線投資儀表板
st.subheader("🎯 長線投資儀表板")

long_rows = []

for stock_name, ticker in stock_list.items():
    df = get_data(ticker, "1y")
    if df.empty or len(df) < 120:
        continue

    current = df.iloc[-1]["Close"]
    rule = long_term_rules[stock_name]
    advice, icon = stock_long_term_advice(stock_name, current)
    score = score_stock(stock_name, df, ai_score, steel_score, chip_score_map.get(stock_name, 0))

    add_gap = (current - rule["add"]) / current * 100
    reduce_gap = (rule["reduce"] - current) / current * 100
    _, risk_level = risk_distance_from_ma(df)

    if score >= 80:
        action = "🟢 可續抱，拉回分批"
    elif score >= 60:
        action = "🔵 續抱觀察"
    elif score >= 45:
        action = "🟡 停止加碼"
    else:
        action = "🔴 風險偏高，評估減碼"

    long_rows.append({
        "股票": stock_name,
        "現價": round(current, 2),
        "加碼價": rule["add"],
        "強力加碼價": rule["strong_add"],
        "減碼價": rule["reduce"],
        "距離加碼": f"{add_gap:.2f}%",
        "距離減碼": f"{reduce_gap:.2f}%",
        "評分": health_display(score),
        "加碼紅綠燈": add_reduce_light(stock_name, current, score, risk_level),
        "區間建議": f"{icon} {advice}",
        "操作建議": action,
        "高檔風險": risk_level,
    })

long_df = pd.DataFrame(long_rows)
st.dataframe(long_df, use_container_width=True, hide_index=True)

st.divider()

# 新資金配置
st.subheader("💵 新資金配置建議")
allocation_df = allocation_suggestion(cash_input, ai_score, steel_score)
st.dataframe(allocation_df, use_container_width=True, hide_index=True)

st.divider()

# 持股追蹤

st.divider()
st.subheader("❤️ 持股健康度評分")
st.markdown("""
<div style="
    background:#f8fafc;
    border-left:6px solid #60a5fa;
    padding:12px 16px;
    border-radius:10px;
    margin:8px 0 18px 0;
    font-size:20px;
    line-height:1.6;
">
<b>健康度說明：</b>
🟢 90以上 優秀　
🔵 75~89 良好　
🟡 60~74 普通　
🔴 60以下 偏弱
</div>
""", unsafe_allow_html=True)

health_rows = []
for stock_name, ticker in stock_list.items():
    df_h = get_data(ticker, "1y")
    if not df_h.empty:
        score_h = score_stock(stock_name, df_h, ai_score, steel_score, chip_score_map.get(stock_name,0))
        if score_h >= 85:
            level = "🟢 優秀"
        elif score_h >= 70:
            level = "🔵 良好"
        elif score_h >= 55:
            level = "🟡 普通"
        else:
            level = "🔴 偏弱"

        health_rows.append({
            "股票": stock_name,
            "健康度": health_display(score_h),
            "評級": level
        })

if health_rows:
    st.dataframe(pd.DataFrame(health_rows), use_container_width=True, hide_index=True)


st.subheader("💰 持股追蹤")

portfolio_rows = []
total_cost = 0
total_value = 0
total_profit = 0

for stock_name, info in portfolio.items():
    df = get_data(stock_list[stock_name], "5d")
    if df.empty or len(df) < 2:
        continue

    current = df.iloc[-1]["Close"]

    buy_amount, sell_amount, net_profit, net_profit_pct = calc_net_profit(
        info["shares"], info["cost"], current, fee_discount
    )

    total_cost += buy_amount
    total_value += sell_amount
    total_profit += net_profit

    portfolio_rows.append({
        "股票": stock_name,
        "股數": info["shares"],
        "成本": info["cost"],
        "現價": round(current, 2),
        "已扣費損益": colored_text(round(net_profit)),
        "報酬率": colored_text(round(net_profit_pct, 2), "%"),
    })

total_profit_pct = total_profit / total_cost * 100 if total_cost else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("投入成本", f"{total_cost:,.0f}")
c2.metric("目前市值", f"{total_value:,.0f}")
c3.markdown(f'<div>已扣費總損益</div><div class="big-profit {tw_color(total_profit)}-text">{total_profit:,.0f}</div>', unsafe_allow_html=True)
c4.markdown(f'<div>已扣費報酬率</div><div class="big-profit {tw_color(total_profit_pct)}-text">{total_profit_pct:.2f}%</div>', unsafe_allow_html=True)

portfolio_df = pd.DataFrame(portfolio_rows)
if not portfolio_df.empty:
    st.markdown(portfolio_df.to_html(escape=False, index=False), unsafe_allow_html=True)

st.divider()


st.subheader("🩺 V7.1 個股診斷中心")

diag_stock = st.selectbox("選擇要診斷的股票", list(stock_list.keys()), key="diag_stock")
diag = stock_diagnosis(diag_stock, stock_list[diag_stock], ai_score, steel_score, chip_score_map)

if diag:
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("現價", diag["現價"])
    d2.metric("健康度", diag["健康度"])
    d3.metric("趨勢", diag["趨勢"])
    d4.metric("操作建議", diag["操作建議"])

    st.markdown(f"""
<div class="alert-card">
<b>{diag['股票']} 診斷結果</b><br>
買點狀態：{diag['買點狀態']}<br>
高檔風險：{diag['高檔風險']}<br>
產業環境：{diag['產業環境']}<br>
原因：{diag['原因']}
</div>
""", unsafe_allow_html=True)

st.divider()


# 單檔股票分析
st.subheader("📊 單檔股票分析")

selected_stock = st.sidebar.selectbox("選擇股票", list(stock_list.keys()))
period = st.sidebar.selectbox("期間", ["1mo", "2mo", "3mo", "6mo", "1y", "2y"], index=4)

df = get_data(stock_list[selected_stock], period)

min_required = 15 if period in ["1mo", "2mo"] else 30

if df.empty or len(df) < min_required:
    st.warning("資料不足，請改選較長期間。")
else:
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    change = latest["Close"] - prev["Close"]
    change_pct = change / prev["Close"] * 100

    support, resistance = calc_support_resistance(df)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("股票", selected_stock)
    col2.metric("收盤價", f"{latest['Close']:.2f}")
    col3.markdown(f'<div>漲跌</div><div class="big-profit {tw_color(change)}-text">{change:+.2f}</div>', unsafe_allow_html=True)
    col4.markdown(f'<div>漲跌幅</div><div class="big-profit {tw_color(change_pct)}-text">{change_pct:+.2f}%</div>', unsafe_allow_html=True)
    col5.metric("近期支撐", f"{support:.2f}")
    col6.metric("近期壓力", f"{resistance:.2f}")

    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["MA120"] = df["Close"].rolling(120).mean()
    df["MA240"] = df["Close"].rolling(240).mean()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.76, 0.24])

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color="red",
            decreasing_line_color="green",
            increasing_fillcolor="red",
            decreasing_fillcolor="green",
            name="K線",
        ),
        row=1,
        col=1,
    )

    ma_settings = [
        ("MA5", "yellow"),
        ("MA20", "white"),
        ("MA60", "cyan"),
        ("MA120", "orange"),
        ("MA240", "magenta"),
    ]

    for ma, color in ma_settings:
        if df[ma].notna().sum() > 0:
            fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma, line=dict(color=color, width=2)), row=1, col=1)

    fig.add_hline(y=support, line_dash="dash", line_color="green", row=1, col=1)
    fig.add_hline(y=resistance, line_dash="dash", line_color="red", row=1, col=1)
    fig.add_hline(y=latest["Close"], line_dash="dot", line_color="white", row=1, col=1)

    volume_colors = ["red" if c >= o else "green" for c, o in zip(df["Close"], df["Open"])]

    fig.add_trace(go.Bar(x=df.index, y=df["Volume"] / 1000, name="成交量(張)", marker_color=volume_colors, opacity=0.65), row=2, col=1)

    fig.update_layout(
        height=620,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        font=dict(size=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=30, r=50, t=45, b=30),
    )

    fig.update_yaxes(title_text="股價", row=1, col=1)
    fig.update_yaxes(title_text="成交量(張)", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
