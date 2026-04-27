import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

st.set_page_config(page_title="HOOD & RVI News Tracker", layout="wide", page_icon="📰")
st.title("📰 HOOD & RVI Stock News Tracker")
st.caption("Real-time prices, charts & news for Robinhood Markets (HOOD) and Robinhood Ventures Fund I (RVI)")

tickers = {"HOOD": "Robinhood Markets (HOOD)", "RVI": "Robinhood Ventures Fund I (RVI)"}

st.sidebar.header("Settings")
selected = st.sidebar.multiselect("Select stocks to show", list(tickers.keys()), default=list(tickers.keys()))
refresh = st.sidebar.button("🔄 Refresh Data")
interval = st.sidebar.selectbox("Chart interval", ["1d", "5d", "1mo", "3mo", "ytd", "1y"], index=2)

@st.cache_data(ttl=60)
def get_stock_data(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.fast_info
    history = ticker.history(period=interval)
    news = ticker.news[:10]
    return info, history, news

data = {}
for sym in selected:
    data[sym] = get_stock_data(sym)

# Price cards
cols = st.columns(len(selected))
for i, sym in enumerate(selected):
    info, hist, _ = data[sym]
    price = info['lastPrice']
    change = info['lastPrice'] - info['previousClose']
    pct_change = (change / info['previousClose']) * 100 if info['previousClose'] else 0
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

# News
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

st.success("✅ Data refreshes every 60 seconds (or tap Refresh)")
st.caption("Built with ❤️ using Streamlit + yfinance")
