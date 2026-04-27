import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import time
from yfinance.exceptions import YFRateLimitError
import requests

st.set_page_config(page_title="HOOD & RVI News Tracker", layout="wide", page_icon="📰")
st.title("📰 HOOD & RVI Stock News Tracker")
st.caption("Real-time prices, charts & news for Robinhood Markets (HOOD) and Robinhood Ventures Fund I (RVI)")

tickers = {"HOOD": "Robinhood Markets (HOOD)", "RVI": "Robinhood Ventures Fund I (RVI)"}

st.sidebar.header("Settings")
selected = st.sidebar.multiselect("Select stocks to show", list(tickers.keys()), default=list(tickers.keys()))
refresh = st.sidebar.button("🔄 Refresh Data")
interval = st.sidebar.selectbox("Chart interval", ["1d", "5d", "1mo", "3mo", "ytd", "1y"], index=2)

@st.cache_data(ttl=300)  # 5 minutes - much better for rate limits
def get_stock_data(ticker_symbol, period):
    # Browser-like session to reduce rate limiting
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    })
    
    ticker = yf.Ticker(ticker_symbol, session=session)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            info = ticker.fast_info
            history = ticker.history(period=period)
            news = ticker.news[:10]
            return info, history, news
        except YFRateLimitError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # exponential backoff
        except Exception as e:
            st.error(f"Error fetching {ticker_symbol}: {str(e)[:100]}")
            raise
    return None, pd.DataFrame(), []

data = {}
for sym in selected:
    data[sym] = get_stock_data(sym, interval)

# Price cards
cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    info, hist, _ = data[sym]
    if info:
        price = info.get('lastPrice', 0)
        prev = info.get('previousClose', price)
        change = price - prev
        pct_change = (change / prev * 100) if prev else 0
        with cols[i]:
            st.metric(
                label=tickers[sym],
                value=f"${price:,.2f}",
                delta=f"{change:+.2f} ({pct_change:+.2f}%)"
            )

# Charts
st.subheader("Price Charts")
chart_cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    _, hist, _ = data[sym]
    with chart_cols[i]:
        if not hist.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist['Open'],
                high=hist['High'],
                low=hist['Low'],
                close=hist['Close'],
                name=sym
            ))
            fig.update_layout(title=f"{sym} - {interval.upper()}", xaxis_title="Date", yaxis_title="Price ($)", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No data available yet")

# News section (same as before)
st.subheader("📰 Latest News")
tab_names = ["Combined Feed"] + [tickers[s] for s in selected]
tabs = st.tabs(tab_names)

with tabs[0]:
    all_news = []
    for sym in selected:
        _, _, news_list = data[sym]
        for item in news_list:
            all_news.append({
                "stock": sym,
                "title": item.get("title", "No title"),
                "publisher": item.get("publisher", "Unknown"),
                "time": datetime.fromtimestamp(item.get("providerPublishTime", 0)),
                "link": item.get("link", "#"),
                "summary": item.get("summary", "")[:200] + "..." if item.get("summary") else ""
            })
    all_news.sort(key=lambda x: x["time"], reverse=True)
    for news in all_news[:15]:
        st.markdown(f"**{news['stock']}** • {news['publisher']} • {news['time'].strftime('%b %d, %H:%M')}")
        st.markdown(f"[{news['title']}]({news['link']})")
        if news['summary']:
            st.caption(news['summary'])
        st.divider()

for i, sym in enumerate(selected, start=1):
    with tabs[i]:
        _, _, news_list = data[sym]
        for item in news_list:
            time_str = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime('%b %d, %H:%M')
            st.markdown(f"**{item.get('publisher', 'Unknown')}** • {time_str}")
            st.markdown(f"[{item.get('title', 'No title')}]({item.get('link', '#')})")
            if item.get("summary"):
                st.caption(item.get("summary")[:250] + "...")
            st.divider()

st.success("✅ Data refreshes every 5 minutes (or tap Refresh)")
st.caption("Built with ❤️ using Streamlit + yfinance • Rate-limit protected")
