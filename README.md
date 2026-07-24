# MDComputers Product Scraper

A Python command-line scraper that collects product details from MDComputers for any search term and exports the results to both CSV and JSON.

## Data collected

- Product name
- Current price
- Original price, when available
- Availability, when available
- Product URL
- Image URL

## Setup

```bash
python -m venv .venv
```

Activate the environment:

**Windows**

```bash
.venv\Scripts\activate
```

**macOS/Linux**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scraper.py "external harddrive"
```

Scrape multiple result pages:

```bash
python scraper.py "external harddrive" --pages 3
```

Choose an output directory:

```bash
python scraper.py "gaming mouse" --pages 2 --output-dir results
```

The script writes files such as:

```text
output/external_harddrive.csv
output/external_harddrive.json
```

## Example CSV fields

```text
name,price,original_price,availability,product_url,image_url
```

## Design decisions

- Uses a persistent `requests.Session` for connection reuse.
- Retries temporary HTTP failures with exponential backoff.
- Sends a browser-like user agent.
- Supports pagination and a configurable delay between requests.
- Deduplicates products by URL.
- Uses fallback CSS selectors to tolerate small website layout changes.
- Returns clear exit codes for request failures or empty results.

## Run tests

The tests use saved HTML and do not send requests to the website.

```bash
python -m unittest discover -s tests
```

## Notes

Website HTML can change over time. If MDComputers changes its product-card markup, update the fallback selectors in `parse_products()`.

Use the scraper responsibly, keep request volume low, and comply with the website's terms and robots policy.
