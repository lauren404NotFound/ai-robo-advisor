import yfinance as yf
from database import update_market_cache, init_db
import time

# Essential ETFs the platform supports based on app.py
ETFS = [
    "VOO",   # S&P 500
    "QQQ",   # Nasdaq 100
    "VWRA.L",# Global
    "AGG",   # US Aggregate Bond
    "GLD",   # Gold
    "VNQ",   # Real Estate
    "ESGU",  # ESG
    "PDBC"   # Commodities
]

def fetch_and_update_market_data():
    print("Initiating Market Data Fetch...")
    
    # Force initialize the database indexes (This ensures the collections appear in MongoDB)
    try:
        init_db()
        print("MongoDB Indexes & Collections verified.")
    except Exception as e:
        print(f"Warning on DB init: {e}")

    for ticker in ETFS:
        try:
            print(f"Fetching data for {ticker}...")
            stock = yf.Ticker(ticker)
            
            # Get 1-month historical data for sparkline
            hist = stock.history(period="1mo")
            if hist.empty:
                print(f"No historical data found for {ticker}")
                continue
                
            # Grab latest 30 days of closing prices for sparklines
            sparkline_prices = hist['Close'].tolist()
            
            # Calculate metrics
            last_price = sparkline_prices[-1]
            if len(sparkline_prices) >= 2:
                prev_close = sparkline_prices[-2]
                change_pct = ((last_price - prev_close) / prev_close) * 100
            else:
                change_pct = 0.0

            # Update cache in MongoDB
            update_market_cache(
                ticker=ticker,
                last_price=float(last_price),
                change_pct=float(change_pct),
                sparkline_data=sparkline_prices
            )
            print(f"✅ Successfully updated {ticker} at {last_price:.2f}")

        except Exception as e:
            print(f"❌ Error updating {ticker}: {e}")

if __name__ == "__main__":
    fetch_and_update_market_data()
    print("Market sync complete. The 'market_data_cache' collection should now be visible in MongoDB Atlas.")
