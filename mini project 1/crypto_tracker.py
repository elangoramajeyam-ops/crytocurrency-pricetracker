"""
Cryptocurrency Price Tracker
Scrapes the top 10 coins from CoinMarketCap using Selenium and
appends timestamped data to a CSV file.

Install:  pip install selenium pandas webdriver-manager
Run:      python crypto_tracker.py
          python crypto_tracker.py --headless
          python crypto_tracker.py --headless --min-price 1000
          python crypto_tracker.py --top-gainers 3
"""

import argparse
import os
import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://coinmarketcap.com/"
CSV_FILE = "crypto_prices.csv"


def create_driver(headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    try:
        # Selenium 4.6+ finds/downloads the right ChromeDriver by itself
        return webdriver.Chrome(options=options)
    except Exception as e:
        print("Could not start Chrome:")
        print(str(e).split("\n")[0])
        raise SystemExit(1)

def to_float(text: str) -> float:
    """Convert strings like '$67,123.45' or '-1.23%' to float."""
    cleaned = text.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return float("nan")


def scrape_top_coins(driver: webdriver.Chrome, limit: int = 10) -> pd.DataFrame:
    driver.get(URL)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
    )
    # Scroll a bit so lazy-loaded content renders
    driver.execute_script("window.scrollTo(0, 600);")
    time.sleep(2)

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    data = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 9:
            continue
        try:
            name_lines = [l for l in cells[2].text.split("\n") if l.strip()]
            name = name_lines[0]
            symbol = name_lines[1] if len(name_lines) > 1 else ""
            price = to_float(cells[3].text)
            change_24h = to_float(cells[5].text)
            market_cap = cells[7].text.split("\n")[0].strip()
            data.append(
                {
                    "Rank": cells[1].text.strip(),
                    "Name": name,
                    "Symbol": symbol,
                    "Price (USD)": price,
                    "24h Change (%)": change_24h,
                    "Market Cap": market_cap,
                }
            )
        except Exception as e:
            print(f"Skipping a row: {e}")
        if len(data) >= limit:
            break

    df = pd.DataFrame(data)
    df.insert(0, "Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return df


def save_to_csv(df: pd.DataFrame, path: str = CSV_FILE) -> None:
    """Append to the CSV so history builds up over time."""
    file_exists = os.path.isfile(path)
    df.to_csv(path, mode="a", header=not file_exists, index=False)
    print(f"Saved {len(df)} rows to {path}")


def main():
    parser = argparse.ArgumentParser(description="Crypto Price Tracker")
    parser.add_argument("--headless", action="store_true", help="Run without opening a browser window")
    parser.add_argument("--min-price", type=float, help="Only show coins priced above this value")
    parser.add_argument("--top-gainers", type=int, help="Show N coins with highest 24h gain")
    parser.add_argument("--interval", type=int, default=0,
                        help="Repeat every N seconds (0 = run once)")
    args = parser.parse_args()

    driver = create_driver(args.headless)
    try:
        while True:
            df = scrape_top_coins(driver)
            if df.empty:
                print("No data scraped. The site layout may have changed.")
            else:
                save_to_csv(df)

                view = df
                if args.min_price is not None:
                    view = view[view["Price (USD)"] > args.min_price]
                if args.top_gainers:
                    view = view.nlargest(args.top_gainers, "24h Change (%)")

                print("\n" + view.drop(columns=["Timestamp"]).to_string(index=False) + "\n")

            if args.interval <= 0:
                break
            print(f"Waiting {args.interval}s for next run... (Ctrl+C to stop)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()