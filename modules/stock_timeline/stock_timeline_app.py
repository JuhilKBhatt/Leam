import os
import sys
import json
import random
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path so we can import core
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from core.utils.common import load_module_config
from core.api.llm import gpt_request
from core.api.serpapi import get_google_image_from_serpapi

MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR / "output"
LOG_DIR = MODULE_DIR / "logs"

def parse_price_range(price_range_str):
    """Parses a price range string like '100-1000', '1000,500,250', or '500' and returns a random price."""
    try:
        if '-' in price_range_str:
            parts = price_range_str.split('-')
            min_p = float(parts[0].strip())
            max_p = float(parts[1].strip())
            return round(random.uniform(min_p, max_p), 2)
        elif ',' in price_range_str:
            parts = price_range_str.split(',')
            choices = [float(p.strip()) for p in parts if p.strip()]
            return float(random.choice(choices))
        else:
            return float(price_range_str.strip())
    except Exception as e:
        print(f"Error parsing price range '{price_range_str}': {e}. Defaulting to 1000.")
        return 1000.0

def get_random_company():
    """Picks a random company from the local nasdaq_top_50.json file."""
    nasdaq_file = MODULE_DIR / "nasdaq_top_50.json"
    if not nasdaq_file.exists():
        print("nasdaq_top_50.json not found, falling back to Apple (AAPL)")
        return {"name": "Apple Inc.", "ticker": "AAPL"}
        
    with open(nasdaq_file, 'r') as f:
        companies = json.load(f)
    return random.choice(companies)

def fetch_stock_data(ticker, years_back):
    """Fetches historical stock data using yfinance."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years_back * 365)
    
    print(f"Fetching data for {ticker} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({years_back} years)...")
    
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    return hist

def run():
    print("Starting stock timeline generation...")
    # 1. Load Config
    config = load_module_config(MODULE_DIR)
    settings = config.get("settings", {})
    
    # 2. Pick a random price from PRICE RANGE
    # Trying the configured Price_Range, if empty fallback to Initial_Investment or default
    price_range_str = settings.get("Price_Range-stringME", "")
    if not price_range_str:
        # Fallback to older settings format if Price_Range isn't set
        price_range_str = str(settings.get("Initial_Investment-integerFE", "100-1000"))
        
    initial_investment = parse_price_range(price_range_str)
    print(f"Selected Initial Investment: ${initial_investment:.2f}")

    # 3. Pick a random company and get valid stock market data (retry if delisted)
    max_retries = 5
    hist = None
    
    for attempt in range(max_retries):
        company = get_random_company()
        ticker = company["ticker"]
        company_name = company["name"]
        print(f"Attempt {attempt+1}: Selected Company: {company_name} ({ticker})")

        # 4. Get stock market data for 5 to 10 years
        years_back = random.randint(5, 10)
        hist = fetch_stock_data(ticker, years_back)
        
        if not hist.empty:
            break
        print(f"No historical data found for {ticker} (might be delisted). Retrying...")

    if hist is None or hist.empty:
        print("Failed to find historical data after multiple attempts. Exiting.")
        return

    first_price = hist['Close'].iloc[0]
    last_price = hist['Close'].iloc[-1]
    
    # Calculate gain
    shares_bought = initial_investment / first_price
    final_value = shares_bought * last_price
    gain = (final_value - initial_investment) + initial_investment  # Total value after investment
    
    print(f"Initial Price: ${first_price:.2f}, Final Price: ${last_price:.2f}")
    print(f"Final Value: ${final_value:.2f}, Gain: ${gain:.2f}")

    # 5. Ask AI for a product similar to the initial investment
    prompt_product_template = settings.get("prompt_product-stringLE")
    prompt_product = prompt_product_template.replace("{price}", f"{initial_investment:.2f}")
    
    print("Asking AI for an equivalent product for the initial investment...")
    product_response = gpt_request(prompt_product).strip()
    print(f"Product for ${initial_investment:.2f}: {product_response}")

    # Download product image
    product_image_path = get_google_image_from_serpapi(product_response, str(DATA_DIR))

    # 6. Ask AI what people can buy with the gain
    prompt_gain_template = settings.get("prompt_gain-stringLE")
    prompt_gain = prompt_gain_template.replace("{price}", f"{gain:.2f}")
    
    print("Asking AI for an equivalent purchase for the total gain...")
    gain_response = gpt_request(prompt_gain).strip()
    print(f"What to buy with ${gain:.2f} gain: {gain_response}")

    # Download gain image
    gain_image_path = get_google_image_from_serpapi(gain_response, str(DATA_DIR))

    # Extract historical prices for the chart
    prices = []
    for date, row in hist.iterrows():
        prices.append({
            "date": date.strftime('%Y-%m-%d'),
            "price": row['Close']
        })

    # Save output for further processing (like video generation)
    summary = {
        "company": company_name,
        "ticker": ticker,
        "years": years_back,
        "initial_investment": initial_investment,
        "first_price": first_price,
        "last_price": last_price,
        "gain": gain,
        "initial_product_idea": product_response,
        "initial_product_image": product_image_path,
        "gain_purchase_idea": gain_response,
        "gain_purchase_image": gain_image_path,
        "prices": prices
    }
    
    os.makedirs(DATA_DIR, exist_ok=True)
    out_file = DATA_DIR / f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, 'w') as f:
        json.dump(summary, f, indent=4)
        
    print(f"Finished! JSON output saved to {out_file}")

    # 7. Render the video using Remotion
    import subprocess
    
    print("Triggering Remotion video render...")
    remotion_dir = project_root / "remotion"
    out_video = DATA_DIR / f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    try:
        subprocess.run([
            "npx", "remotion", "render", "src/index.ts", "StockTimeline",
            str(out_video),
            f"--props={out_file}"
        ], cwd=remotion_dir, check=True)
        print(f"Video successfully rendered to: {out_video}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to render video: {e}")

if __name__ == "__main__":
    run()
