import unittest

from scraper import build_search_url, parse_products


SAMPLE_HTML = """
<div class="product-layout product-grid">
  <div class="product-thumb">
    <div class="image">
      <a href="https://mdcomputers.in/sample-drive.html">
        <img data-src="https://mdcomputers.in/image/sample.jpg" />
      </a>
    </div>
    <div class="caption">
      <h4><a href="https://mdcomputers.in/sample-drive.html">Sample External Drive 1TB</a></h4>
      <p class="price"><span class="price-new">₹5,499</span><span class="price-old">₹6,999</span></p>
      <span class="stock">In Stock</span>
    </div>
  </div>
</div>
"""


class ScraperTests(unittest.TestCase):
    def test_parse_products(self):
        products = parse_products(SAMPLE_HTML)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Sample External Drive 1TB")
        self.assertEqual(products[0].price, "₹5,499")
        self.assertEqual(products[0].original_price, "₹6,999")
        self.assertEqual(products[0].availability, "In Stock")
        self.assertEqual(products[0].product_url, "https://mdcomputers.in/sample-drive.html")
        self.assertEqual(products[0].image_url, "https://mdcomputers.in/image/sample.jpg")

    def test_search_url_encodes_term(self):
        url = build_search_url("external harddrive", page=2)
        self.assertIn("search=external+harddrive", url)
        self.assertIn("page=2", url)


if __name__ == "__main__":
    unittest.main()
