import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def load_css():
    with open("app.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

st.title("Stock Dashboard")

def search_companies(query):
    url = "https://query1.finance.yahoo.com/v1/finance/search"

    params = {
        "q": query,
        "quotesCount": 8,
        "newsCount": 0,
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            st.warning("Search service is not available now.")
            return []

        data = response.json()

    except Exception as error:
        st.warning("Could not search company name. Try ticker like AAPL.")
        return []

    results = []

    for item in data.get("quotes", []):
        symbol = item.get("symbol")
        name = item.get("shortname") or item.get("longname")

        if symbol and name:
            results.append(f"{symbol} — {name}")

    return results


query = st.text_input(
    "Ticker or company's name:",
    placeholder="Search")

selected_ticker = None

if query:
    suggestions = search_companies(query)

    if suggestions:
        selected = st.selectbox("Choose company:", suggestions)
        selected_ticker = selected.split(" — ")[0]
    else:
        selected_ticker = query.upper().strip()


periods = ["1d", "5d", "1mo", "6mo", "1y", "5y", "max"]

if "period" not in st.session_state:
    st.session_state.period = "1y"

cols = st.columns(len(periods))

for i, p in enumerate(periods):
    if cols[i].button(p.upper()):
        st.session_state.period = p

period = st.session_state.period

if "end_date" not in st.session_state:
    st.session_state.end_date = datetime.today()


today = datetime.today()

next_disabled = st.session_state.end_date >= today

def move_date_back(period):
    if period == "1d":
        return timedelta(days=1)
    elif period == "5d":
        return timedelta(days=5)
    elif period == "1mo":
        return relativedelta(months=1)
    elif period == "6mo":
        return relativedelta(months=6)
    elif period == "1y":
        return relativedelta(years=1)
    elif period == "5y":
        return relativedelta(years=5)
    else:
        return timedelta(days=0)

left, middle, right = st.columns([1.5, 5, 1.5])

with left:
    prev_clicked = st.button("← Previous", use_container_width=True)

with middle:
    st.empty()

with right:
    st.markdown('<div class="right-btn">', unsafe_allow_html=True)
    next_clicked = st.button(
        "Next →",
        disabled=next_disabled,
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

if prev_clicked:
    st.session_state.end_date -= move_date_back(period)

if next_clicked:
    st.session_state.end_date += move_date_back(period)

if st.session_state.end_date > today:
    st.session_state.end_date = today

if selected_ticker:
    
    interval = "1d"
    end_date = st.session_state.end_date

    if period == "1d":
        start_date = end_date - timedelta(days=1)
        interval = "5m"
    elif period == "5d":
        start_date = end_date - timedelta(days=5)
        interval = "15m"
    elif period == "1mo":
        start_date = end_date - relativedelta(months=1)
    elif period == "6mo":
        start_date = end_date - relativedelta(months=6)
    elif period == "1y":
        start_date = end_date - relativedelta(years=1)
    elif period == "5y":
        start_date = end_date - relativedelta(years=5)
        interval = "1wk"
    else:
        start_date = None
        interval = "1mo"

    if period == "max":
        df = yf.download(selected_ticker, period="max", progress=False)
    else:
        df = yf.download(
            selected_ticker,
            start=start_date,
            end=end_date + timedelta(days=1),
            interval=interval,
            progress=False
        )
    

    if df.empty:
        st.error("No data found.")
    else:
        close_data = df["Close"]

        if hasattr(close_data, "columns"):
            close_data = close_data.iloc[:, 0]

        close_data = close_data.dropna()

        if close_data.empty:
            st.error("No close price data found.")
        else:
            start_price = close_data.iloc[0]

            pnl_usd = close_data - start_price
            pnl_percent = (close_data / start_price - 1) * 100

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=close_data.index,
                    y=close_data,
                    mode="lines",
                    name="Close price",
                    line=dict(
                        color="#00E5A8",
                        width=3
                    ),
                    line_shape="spline",
                    customdata=list(zip(pnl_usd, pnl_percent)),
                    hovertemplate=
                        "Date: %{x}<br>"
                        "Price: $%{y:.2f}<br>"
                        "P&L: $%{customdata[0]:.2f}<br>"
                        "P&L: %{customdata[1]:.2f}%"
                        "<extra></extra>"
                )

            )

            fig.update_layout(
                title=f"{selected_ticker} price chart ({period})",
                paper_bgcolor="#0B1020",
                plot_bgcolor="#0B1020",
                font=dict(color="white", size=14),
                hovermode="x unified",
                margin=dict(l=20, r=20, t=50, b=20)
            )

            fig.update_xaxes(
                showgrid=False,
                fixedrange=True
            )

            fig.update_yaxes(
                showgrid=False,
                fixedrange=True
            )

            st.plotly_chart(fig, use_container_width=True)

            stock = yf.Ticker(selected_ticker)

            pricing_data, fundamental_data, news = st.tabs(
                ["Pricing Data", "Financial Statements", "Latest News"]
            )

            with pricing_data:
                st.subheader("Price Movements")
                st.dataframe(df.tail(20))

            with fundamental_data:                
                st.subheader("Income Statement")
                st.dataframe(stock.financials)

                st.subheader("Balance Sheet")
                st.dataframe(stock.balance_sheet)

                st.subheader("Cash Flow")
                st.dataframe(stock.cashflow)
                
            with news:
                news_items = stock.news

                if not news_items:
                    st.warning("No news found.")
                else:
                    shown_news = 0
                    
                    for item in news_items[:20]:
                        content = item.get("content") or {}

                        title = content.get("title") or "No title"
                        publisher = (
                            content.get("provider") or {}
                        ).get("displayName", "Unknown")

                        clickthrough = content.get("clickThroughUrl") or {}
                        canonical = content.get("canonicalUrl") or {}

                        link = (
                            clickthrough.get("url")
                            or canonical.get("url")
                            or ""
                        )

                        pub_date = content.get("pubDate") or ""
                        
                        if pub_date:
                            try:
                                pub_date = datetime.fromisoformat(
                                    pub_date.replace("Z", "+00:00")
                                )

                                pub_date = pub_date.strftime("%d %b %Y • %H:%M")
                                
                            except ValueError:
                                pass

                        shown_news += 1

                        st.html(
                            f"""
                            <div class="news-card">
                                <div class="news-title">
                                    {title}
                                </div>

                                <div class="news-meta">
                                    📰 {publisher} • {pub_date}
                                </div>
                            
                                <a
                                    class="news-link"
                                    href="{link}"
                                    target="_blank"
                                >
                                    Read article →
                                </a>
                            </div>
                            """,
                        )
                        
                    if shown_news == 0:
                        st.warning("No company-specific news found.")    