import re
import sqlite3
import json
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from win11toast import toast
from typing import Dict

watchlist_f = open("watchlist.json", "r")
watchlist = json.load(watchlist_f)
watchlist_f.close()

# modified_time = os.path.getmtime("log.txt")
# if datetime.fromtimestamp(modified_time).date() < datetime.now().date():

log_f = open(r"C:\Users\jumpa\OneDrive\Code\PriceDropLog.txt", "w")


# Delay to allow website to load
WAIT_DELAY = 2

CW_BASE = "https://www.chemistwarehouse.com.au/buy/"
WOOLIES_BASE = "https://www.woolworths.com.au/shop/productdetails/"
DB_PATH = r"C:\Users\jumpa\Desktop\Code\Python-PriceDrop\prices.db"

toast_dict: Dict[str, str] = {}

DROP_THRESHOLD = 20

def init_db():
    """Initialize database with prices table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS all_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wlref TEXT NOT NULL,
            product_name TEXT NOT NULL,
            product_id TEXT NOT NULL,
            full_link TEXT NOT NULL,
            price REAL NOT NULL,
            percentage_drop INTEGER,
            date_scanned DATE DEFAULT (DATE('now'))
        )
    ''')
    conn.commit()
    conn.close()

def drop_table(table_name: str):
    """Drop a table from the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.commit()
    conn.close()
    print(f"Table '{table_name}' has been dropped.")

def store_price(wlref: str, product_name: str, product_id: str, full_link: str, price: float, percentage_drop: int = 0):
    """Store a product price in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if a record for the same product and date already exists
    cursor.execute('''
        SELECT id FROM all_prices
        WHERE product_id = ?
        AND strftime('%W', date_scanned) = strftime('%W', 'now')
        AND strftime('%Y', date_scanned) = strftime('%Y', 'now')
    ''', (product_id,))
    existing_record = cursor.fetchone()

    if not existing_record:
        # Insert only if no record exists for the same product and date
        cursor.execute('''
            INSERT INTO all_prices (wlref, product_name, product_id, full_link, price, percentage_drop)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (wlref, product_name, product_id, full_link, price, percentage_drop))
        conn.commit()

    conn.close()

def main():
    print("Fetching prices...")
    init_db()  
    # Scraping the website
    options = Options()
    # Hides the firefox window when selenium is executing
    options.add_argument("--headless")

    driver = webdriver.Firefox(options=options)
   
    print_date()
    cw_scraper(driver)
    print_divider()
    woolies_scraper(driver)

    if toast_dict:
        notify() 

    driver.close()
    log_f.close()
    input("Press enter to close...")

def notify():
    notification = ""
    for product, price in toast_dict.items(): 
        notification += f"{product} {price}, "

    notification = notification.rstrip(", ")
    toast(f"Price Drop > {DROP_THRESHOLD}%", notification, scenario='incomingCall')

    log_f.write("\n--- SUMMARY " + datetime.now().strftime("%d %b | %I:%M %p") + " ---\n")
    log_f.write(notification + "\n")

def print_date():
    date_scanned = datetime.now().strftime("%d %b | %I:%M %p")
    print(f"Date scanned: {date_scanned}")
    log_f.write(f"Date scanned: {date_scanned}\n")
    print_divider()

def print_w_log(text):
    print(text)
    log_f.write(text + "\n")

# Finds the elements of interest in the html page (chemist_warehouse)
def cw_scraper(driver):
    print_w_log("CHEMIST WAREHOUSE ITEMS\n-----------------------")
    
    for cwref, cwid in watchlist["Chemist_Warehouse"].items():
        full_link = CW_BASE + cwid
        driver.get(full_link)

        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            product_name = soup.find("h1", {"class": "headline-xl text-colour-title-light"}).text.strip()
            current_price = soup.find("h2", {"class": "display-l text-colour-title-light"}).text.strip()

            print_w_log(product_name)

            price = f"Price: {current_price}"
            print_w_log(price)

        except Exception as e:
            print_w_log(f"Network Error: {e}")

        try:
            price_off = soup.find("p", {"class": "body-m-emphasis text-brand-red"}).text.strip()
            curr_price_f = float(current_price.replace("$", ""))
            price_off_f = float(re.findall(r'\$([\d.]+)', price_off)[0])

            percentage_drop = round((1 - (curr_price_f / (price_off_f + curr_price_f))) * 100)

            savings = f"Savings: {price_off} (-{percentage_drop}%)\n"
            print_w_log(savings)

            if percentage_drop >= DROP_THRESHOLD:
                toast_dict[cwref] = f"(-{percentage_drop}%)"
            
            store_price(cwref, product_name, cwid, full_link, curr_price_f, percentage_drop)
        
        except:
            print_w_log("No price drop \n")


def woolies_scraper(driver):
    PRODUCT_NAME_CLASSNAME = "product-title_component_product-title"
    CURRENT_PRICE_CLASSNAME = "product-price_component_price-lead"
    PRICE_WAS_CLASSNAME = "product-unit-price_component_price-was-amount"

    print_w_log("WOOLIES ITEMS\n-------------")
    for wlref, wlid in watchlist["Woolworths"].items():
        full_link = WOOLIES_BASE + wlid

        try:
            retries = 0
            while retries < 5:
                driver.get(full_link)
                product_name = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[class^={PRODUCT_NAME_CLASSNAME}]'))).text
                current_price_dollars = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[class^={CURRENT_PRICE_CLASSNAME}]'))).text
                if product_name and current_price_dollars:
                    break
                retries += 1
                        
            # Remove the dollar sign
            curr_price_f = float(current_price_dollars[1:])
            curr_price = "{:.2f}".format(curr_price_f)

            print_w_log(product_name)
            print_w_log(f"Price: ${curr_price}")

        except Exception as e:
            print_w_log(f"Network Error: {e}")
            continue
        
        percentage_drop = 0
        try:
            price_was = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[class^={PRICE_WAS_CLASSNAME}]'))).text
            # Slice the string to remove the $ sign
            was_price_f = float(price_was[1:])
            percentage_drop = round((1-(curr_price_f/was_price_f))*100)
            print_w_log(f"Was:   {price_was}")
            print_w_log(f"Price drop: -{percentage_drop}%\n")

            if percentage_drop >= DROP_THRESHOLD:
                toast_dict[wlref] = f"(-{percentage_drop}%)"

        except:
            print_w_log("No price drop\n")
        
        store_price(wlref, product_name, wlid, full_link, curr_price_f, percentage_drop)

def print_divider():
    print("-----------------------------------------------------")
    log_f.write("-----------------------------------------------------\n")   
    
if __name__ == "__main__":
    main()
