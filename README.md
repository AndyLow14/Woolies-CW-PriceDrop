# Woolworths and Chemist Warehouse Price Scraper

Gone are the days of manually checking discounts on your favourite items.

Add a list of item ids and the script will automatically scrape the website by using Selenium to check if there is a price drop.

Cheeky woolies have restricted their API access, thats why I used trusty bots instead of GET requests.

The script currently supports items from [chemistwarehouse.com.au](https://chemistwarehouse.com.au) and [woolworths.com.au](https://woolworths.com.au)

### Running the script

Install dependencies
```
uv sync
```

Start the program
```
uv run price-drop.py
```

### JSON Format

```
{
  "Chemist_Warehouse": {
    "ItemName1(For reference only)": "12345",
    "ItemName2": "54321",
    ...
  },
  "Woolworths": {
    "ItemName1(For reference only)": "12345",
    "ItemName2": "54321",
    ...
  }
}
```

### How to get Product Ids

When you view a product from a CW (chemistwarehouse.com.au/buy/`{id}`/foo-bar) or Woolies (woolworths.com.au/shop/productdetails/`{id}`/foo-bar) website, the ids should be in the url.

**Requires Firefox browser to work**
