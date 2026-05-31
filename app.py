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

st.set_page_config(page_title="Hsing 投資儀表板 V5.1", layout="wide")

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
html, body, [class*="css"] { font-size: 19px; }
.block-container { padding-top: 1.1rem; padding-left: 2rem; padding-right: 2rem; }
h1 { font-size: 42px !important; font-weight: 900 !important; }
h2, h3 { font-size: 28px !important; font-weight: 800 !important; }

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

st.title("📈 Hsing 投資儀表板 V5.1")

saved_portfolio = load_portfolio()

with st.sidebar:
    st.header("⚙️ 持股設定")

    fee_discount = st.number_input("元大手續費折扣", min_value=0.1, max_value=1.0, value=0.28, step=0.01)
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
        "評分": score,
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

# 單檔股票分析
st.subheader("📊 單檔股票分析")

selected_stock = st.sidebar.selectbox("選擇股票", list(stock_list.keys()))
period = st.sidebar.selectbox("期間", ["3mo", "6mo", "1y", "2y"], index=2)

df = get_data(stock_list[selected_stock], period)

if df.empty or len(df) < 30:
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
        height=900,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        font=dict(size=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=100, t=70, b=40),
    )

    fig.update_yaxes(title_text="股價", row=1, col=1)
    fig.update_yaxes(title_text="成交量(張)", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)
