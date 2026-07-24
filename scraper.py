#!/usr/bin/env python3
"""Scrape product search results from MDComputers and export them to CSV/JSON."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://mdcomputers.in/"
DEFAULT_TIMEOUT = 25
LOGGER = logging.getLogger("mdcomputers_scraper")


@dataclass(frozen=True)
class Product:
    name: str
    price: str | None
    original_price: str | None
    availability: str | None
    product_url: str
    image_url: str | None


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def first_text(container: Tag, selectors: Iterable[str]) -> str | None:
    for selector in selectors:
        element = container.select_one(selector)
        if element:
            text = clean_text(element.get_text(" ", strip=True))
            if text:
                return text
    return None


def first_attr(container: Tag, selectors: Iterable[str], attribute: str) -> str | None:
    for selector in selectors:
        element = container.select_one(selector)
        if element and element.get(attribute):
            return clean_text(str(element.get(attribute)))
    return None


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def build_search_url(search_term: str, page: int = 1) -> str:
    query = {"route": "product/search", "search": search_term}
    if page > 1:
        query["page"] = str(page)
    return f"{BASE_URL}?{urlencode(query)}"


def parse_products(html: str) -> list[Product]:
    """Parse product cards from one MDComputers search-result page."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(
        ".product-layout, .product-grid, .product-list, "
        ".product-thumb, .product-item, [data-product-id]"
    )

    products: list[Product] = []
    seen_urls: set[str] = set()

    for card in cards:
        name_link = card.select_one(
            "h4 a, h3 a, .name a, .product-name a, .caption a[href], "
            "a.product-title, a[href*='product_id=']"
        )
        if not name_link:
            continue

        name = clean_text(name_link.get_text(" ", strip=True))
        href = name_link.get("href")
        if not name or not href:
            continue

        product_url = urljoin(BASE_URL, str(href))
        if product_url in seen_urls:
            continue

        price = first_text(
            card,
            (
                ".price-new",
                ".price .special",
                ".price .price-new",
                ".price-normal",
                ".price",
            ),
        )
        original_price = first_text(card, (".price-old", ".price .old", "del"))
        availability = first_text(
            card,
            (
                ".stock",
                ".availability",
                ".product-stock",
                ".status",
            ),
        )
        image = first_attr(
            card,
            (
                ".image img",
                ".product-image img",
                "img",
            ),
            "data-src",
        ) or first_attr(card, (".image img", ".product-image img", "img"), "src")

        products.append(
            Product(
                name=name,
                price=price,
                original_price=original_price,
                availability=availability,
                product_url=product_url,
                image_url=urljoin(BASE_URL, image) if image else None,
            )
        )
        seen_urls.add(product_url)

    return products


def scrape_products(
    search_term: str,
    max_pages: int = 1,
    delay: float = 1.0,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[Product]:
    if not search_term.strip():
        raise ValueError("Search term cannot be empty.")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")
    if delay < 0:
        raise ValueError("delay cannot be negative.")

    session = build_session()
    all_products: list[Product] = []
    seen_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        url = build_search_url(search_term, page)
        LOGGER.info("Scraping page %s: %s", page, url)

        response = session.get(url, timeout=timeout)
        response.raise_for_status()

        page_products = parse_products(response.text)
        if not page_products:
            LOGGER.warning("No products found on page %s; stopping.", page)
            break

        new_count = 0
        for product in page_products:
            if product.product_url not in seen_urls:
                all_products.append(product)
                seen_urls.add(product.product_url)
                new_count += 1

        LOGGER.info("Found %s new products on page %s.", new_count, page)
        if new_count == 0:
            break

        if page < max_pages and delay:
            time.sleep(delay)

    return all_products


def write_csv(products: list[Product], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(Product.__dataclass_fields__.keys())
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(product) for product in products)


def write_json(products: list[Product], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump([asdict(product) for product in products], file, indent=2, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape product details from MDComputers search results."
    )
    parser.add_argument("search_term", help='Search term, e.g. "external harddrive"')
    parser.add_argument("--pages", type=int, default=1, help="Maximum pages to scrape")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between pages")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    safe_name = re.sub(r"[^a-z0-9]+", "_", args.search_term.lower()).strip("_") or "products"
    output_dir = Path(args.output_dir)

    try:
        products = scrape_products(args.search_term, args.pages, args.delay)
    except (ValueError, requests.RequestException) as exc:
        LOGGER.error("Scraping failed: %s", exc)
        return 1

    if not products:
        LOGGER.error("No products were extracted. The website layout may have changed.")
        return 2

    csv_path = output_dir / f"{safe_name}.csv"
    json_path = output_dir / f"{safe_name}.json"
    write_csv(products, csv_path)
    write_json(products, json_path)

    print(f"Scraped {len(products)} products")
    print(f"CSV:  {csv_path.resolve()}")
    print(f"JSON: {json_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
