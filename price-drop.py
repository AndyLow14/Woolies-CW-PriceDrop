import re
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

log_f = open("log.txt", "w")

# Delay to allow website to load
WAIT_DELAY = 2

CW_BASE = "https://www.chemistwarehouse.com.au/buy/"
WOOLIES_BASE = "https://www.woolworths.com.au/shop/productdetails/"

toast_dict: Dict[str, str] = {}

def main():
    print("Fetching prices...")
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

    toast("Price Drop > 20%", notification.rstrip(", "), scenario='incomingCall')

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

            product_name = soup.find("div", {"itemprop": "name"}).text.strip()
            current_price = soup.find("span", {"class": "product__price"}).text

            print_w_log(product_name)

            price = f"Price: {current_price}"
            print_w_log(price)

        except Exception as e:
            print_w_log(f"Network Error: {e}")

        try:
            price_off = soup.find("div", {"class": "Savings"}).text.strip()
            curr_price_f = float(current_price.replace("$", ""))
            price_off_f = float(re.findall(r'\$([\d.]+)', price_off)[0])

            percentage_drop = round((1 - (curr_price_f / (price_off_f + curr_price_f))) * 100)

            savings = f"Savings: {price_off} (-{percentage_drop}%)\n"
            print_w_log(savings)

            if percentage_drop >= 20:
                toast_dict[cwref] = f"(-{percentage_drop}%)"
        
        except:
            print_w_log("No price drop \n")


def woolies_scraper(driver):
    print_w_log("WOOLIES ITEMS\n-------------")
    for wlref, wlid in watchlist["Woolworths"].items():
        full_link = WOOLIES_BASE + wlid

        try:
            retries = 0
            while retries < 5:
                driver.get(full_link)
                product_name = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, "shelfProductTile-title"))).text
                current_price_dollars = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, "price-dollars"))).text
                current_price_cents = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, "price-cents"))).text
                if product_name and current_price_dollars and current_price_cents:
                    break
                retries += 1
            
            curr_price = f"{current_price_dollars or '0'}.{current_price_cents or '00'}"
            curr_price_f = float(curr_price)

            print_w_log(product_name)
            print_w_log(f"Price: ${curr_price}")

        except Exception as e:
            print_w_log(f"Network Error: {e}")

        try:
            price_was = WebDriverWait(driver, WAIT_DELAY).until(EC.presence_of_element_located((By.CLASS_NAME, "price-was")))
            price_was = price_was.text
            # Slice the string to remove the "was and $ sign"
            was_price_f = float(re.findall(r'\d+\.\d+', price_was)[0])
            percentage_drop = round((1-(curr_price_f/was_price_f))*100)
            print_w_log(price_was)
            print_w_log(f"Price drop: -{percentage_drop}%\n")

            if percentage_drop >= 20:
                toast_dict[wlref] = f"(-{percentage_drop}%)"

        except:
            print_w_log("No price drop\n")
        
def print_divider():
    print("-----------------------------------------------------")
    log_f.write("-----------------------------------------------------\n")   
    
if __name__ == "__main__":
    main()
