"""
Shopping & Budget Agent (live pricing via Flipkart scraping)

Compatible with:
- RecipeAgentRunner.get_ingredients_for_shopping(), which returns:
    {
      "recipe_name": "...",
      "ingredients": {
        "Section 1": ["1 red bell pepper, chopped", ...],
        "Section 2": [...]
      }
    }

- main.py, which calls:
    shopping_agent = ShoppingBudgetAgent(currency="INR")
    shopping_agent.process_recipe_ingredients(
        recipe_data=...,
        stores=["Amazon", "Flipkart", "LocalStore"],
        budget=500.0
    )

This agent:
1. Extracts the ingredients dictionary from `recipe_data`
2. Parses human-readable ingredient lines
3. Normalizes ingredient names
4. Fetches live prices from Flipkart (first search result scraped)
5. Builds a shopping list + total estimated cost
6. Compares cost with budget and returns budget analysis

Dependencies (install once):
    pip install requests beautifulsoup4
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus


# =========================
#   BASIC PARSING SUPPORT
# =========================

NUMERIC_PATTERN = re.compile(r"^(\d+(\.\d+)?|\d+/\d+)$")

UNITS = {
    "cup", "cups",
    "tablespoon", "tablespoons", "tbsp",
    "teaspoon", "teaspoons", "tsp",
    "clove", "cloves",
    "pound", "pounds", "lb", "lbs",
    "gram", "grams", "g",
    "kg", "kilogram", "kilograms",
    "ml", "milliliter", "milliliters",
    "l", "liter", "liters",
}


def _parse_number(token: str) -> Optional[float]:
    """Parse '1', '1.5', '1/2' → float. Returns None if not numeric."""
    token = token.strip()
    if "/" in token:
        try:
            num, den = token.split("/", 1)
            return float(num) / float(den)
        except ValueError:
            return None
    try:
        return float(token)
    except ValueError:
        return None


def normalize_ingredient_name(name: str) -> str:
    """
    Normalize ingredient descriptions like:
      'red bell pepper, seeded and chopped' → 'red bell pepper'
    and map some synonyms to a generic search name.
    """
    name = name.lower().strip()

    # Remove trailing descriptions after comma
    if "," in name:
        name = name.split(",", 1)[0].strip()

    # Strip common prefixes
    for prefix in ["fresh ", "grated ", "chopped ", "sliced ", "minced "]:
        if name.startswith(prefix):
            name = name[len(prefix):]

    synonyms = {
        "red bell pepper": "red bell pepper",
        "yellow bell pepper": "yellow bell pepper",
        "bell pepper red": "red bell pepper",
        "bell pepper yellow": "yellow bell pepper",
        "broccoli": "broccoli",
        "broccoli florets": "broccoli",
        "zucchini": "zucchini",
        "green zucchini": "zucchini",
        "yellow squash": "yellow squash",
        "mushrooms": "mushrooms",
        "button mushrooms": "mushrooms",
        "mushroom": "mushrooms",
        "red onion": "onion",
        "onion": "onion",
        "garlic": "garlic",
        "olive oil": "olive oil",
        "extra virgin olive oil": "olive oil",
        "pasta": "pasta",
        "penne": "pasta",
        "farfalle": "pasta",
        "rotini": "pasta",
        "vegetable broth": "vegetable broth",
        "veg broth": "vegetable broth",
        "parmesan": "parmesan cheese",
        "parmesan cheese": "parmesan cheese",
        "basil": "basil",
        "fresh basil": "basil",
        "parsley": "parsley",
        "fresh parsley": "parsley",
        "salt": "salt",
        "black pepper": "black pepper",
        "freshly ground black pepper": "black pepper",
    }

    if name in synonyms:
        return synonyms[name]

    for key in synonyms:
        if name.startswith(key):
            return synonyms[key]

    return name


@dataclass
class ParsedIngredient:
    raw_text: str
    name: str
    quantity: float
    unit: str
    normalized_name: str


@dataclass
class ShoppingItem:
    ingredient_name: str
    normalized_name: str
    total_quantity: float
    unit: str
    product_title: Optional[str]
    product_url: Optional[str]
    price: Optional[float]


def parse_ingredient_line(line: str) -> Optional[ParsedIngredient]:
    """
    Parse lines like:
      '1 red bell pepper, seeded and chopped'
      '1 cup broccoli florets'
      '2 cloves garlic, minced'
      'Salt and freshly ground black pepper to taste'  → None (no fixed quantity)
    """
    raw = line.strip()
    if not raw:
        return None

    tokens = raw.split()
    if not tokens:
        return None

    qty = _parse_number(tokens[0])
    if qty is None:
        # No explicit quantity; skip for costing (e.g., 'Salt to taste')
        return None

    if len(tokens) == 1:
        unit = "unit"
        name_part = ""
    else:
        second = tokens[1].lower()
        if second in UNITS:
            unit = second
            name_part = " ".join(tokens[2:])
        else:
            unit = "piece"  # default "count" unit
            name_part = " ".join(tokens[1:])

    name_part = name_part.strip() or "unknown"
    normalized = normalize_ingredient_name(name_part)

    return ParsedIngredient(
        raw_text=raw,
        name=name_part,
        quantity=qty,
        unit=unit,
        normalized_name=normalized,
    )


# =========================
#   LIVE PRICE FETCHER
# =========================

class LivePriceFetcher:
    """
    Fetch live product prices from Flipkart search results via HTML scraping.
    """

    BASE_URL = "https://www.flipkart.com/search?q="

    def __init__(self, user_agent: Optional[str] = None):
        if user_agent is None:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            )
        self.headers = {"User-Agent": user_agent}

    def fetch_price(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search Flipkart for `query`, return first product's title + price + URL.
        Returns None on failure.
        """
        url = self.BASE_URL + quote_plus(query)
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
        except Exception:
            return None

        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to find a product card (Flipkart often uses div[data-id])
        product_card = soup.select_one("div[data-id]")
        if not product_card:
            # Fallback: any known product anchor
            product_card = soup.select_one("a._1fQZEK, a.s1Q9rs, a.IRpwTa")

        if not product_card:
            return None

        # Title
        title_elem = (
            product_card.select_one("a.s1Q9rs")
            or product_card.select_one("a.IRpwTa")
            or product_card.select_one("div._4rR01T")
            or product_card
        )
        title = title_elem.get_text(strip=True) if title_elem else query

        # Price (Flipkart uses div._30jeq3 for price in many layouts)
        price_elem = product_card.select_one("div._30jeq3") or soup.select_one("div._30jeq3")
        if not price_elem:
            return None

        price_text = price_elem.get_text(strip=True)
        price_digits = re.sub(r"[^\d.]", "", price_text)
        if not price_digits:
            return None

        try:
            price_value = float(price_digits)
        except ValueError:
            return None

        # URL
        href = None
        if hasattr(product_card, "get"):
            if product_card.name == "a":
                href = product_card.get("href")
            else:
                a_tag = product_card.select_one("a")
                if a_tag is not None:
                    href = a_tag.get("href")

        if href and href.startswith("/"):
            href = "https://www.flipkart.com" + href

        return {
            "query": query,
            "title": title,
            "price": price_value,
            "url": href or url,
        }


# =========================
#   SHOPPING & BUDGET AGENT
# =========================

class ShoppingBudgetAgent:
    """
    Agent used in main.py:

        shopping_agent = ShoppingBudgetAgent(currency="INR")

        shopping_plan = shopping_agent.process_recipe_ingredients(
            recipe_data=recipe_data,
            stores=["Amazon", "Flipkart", "LocalStore"],
            budget=500.0
        )

    It returns a dict that includes:
        - items: list of shopping items with titles, URLs, prices
        - estimated_total_cost
        - currency
        - budget
        - within_budget
        - amount_over_budget / amount_under_budget
        - skipped_lines_no_quantity
        - items_without_price
    """

    def __init__(self, currency: str = "INR"):
        self.currency = currency
        self.price_fetcher = LivePriceFetcher()

    # --------- INTERNAL HELPERS ---------

    def _aggregate_ingredients(
        self, parsed: List[ParsedIngredient]
    ) -> Dict[str, ShoppingItem]:
        """
        Aggregate quantities by normalized ingredient name.
        """
        agg: Dict[str, ShoppingItem] = {}

        for ing in parsed:
            key = ing.normalized_name
            if key not in agg:
                agg[key] = ShoppingItem(
                    ingredient_name=ing.name,
                    normalized_name=key,
                    total_quantity=ing.quantity,
                    unit=ing.unit,
                    product_title=None,
                    product_url=None,
                    price=None,
                )
            else:
                if agg[key].unit == ing.unit:
                    agg[key].total_quantity += ing.quantity

        return agg

    def _attach_live_prices(self, agg: Dict[str, ShoppingItem]) -> None:
        """
        For each ingredient, run a live Flipkart search and attach the first price.
        """
        for key, item in agg.items():
            # Basic query (you can later incorporate store or quantity if you want)
            query = item.normalized_name
            info = self.price_fetcher.fetch_price(query)
            if info is None:
                continue

            item.product_title = info["title"]
            item.product_url = info["url"]
            item.price = info["price"]

    def _evaluate_budget(
        self,
        total_cost: float,
        budget: Optional[float],
    ) -> Dict[str, Optional[float] | Optional[bool]]:
        """Simple budget comparison."""
        if budget is None:
            return {
                "within_budget": None,
                "amount_over_budget": None,
                "amount_under_budget": None,
            }

        within_budget = total_cost <= budget
        if within_budget:
            return {
                "within_budget": True,
                "amount_over_budget": 0.0,
                "amount_under_budget": round(budget - total_cost, 2),
            }
        else:
            return {
                "within_budget": False,
                "amount_over_budget": round(total_cost - budget, 2),
                "amount_under_budget": 0.0,
            }

    # --------- PUBLIC ENTRYPOINT USED BY main.py ---------

    def process_recipe_ingredients(
        self,
        recipe_data: Dict[str, Any],
        stores: List[str],
        budget: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Main method called from FastAPI in main.py.

        `recipe_data` might be either:
        - full recipe (from /meal-plan): includes recipe_name, ingredients, etc.
        - ingredients-only (from /shopping): {"recipe_name": ..., "ingredients": {...}}

        We only care about:
            recipe_name
            ingredients (dict of section -> list of ingredient strings)
        """
        # Try to extract ingredients dict robustly
        recipe_name = recipe_data.get("recipe_name", "Unknown Recipe")
        ingredients_section = recipe_data.get("ingredients", {})

        if not isinstance(ingredients_section, dict):
            # If for some reason it's not a dict, fallback to empty
            ingredients_section = {}

        # 1) Flatten all ingredient lines
        all_lines: List[str] = []
        for section_name, lines in ingredients_section.items():
            if isinstance(lines, list):
                all_lines.extend(lines)

        # 2) Parse ingredient lines
        parsed: List[ParsedIngredient] = []
        skipped_lines: List[str] = []
        for line in all_lines:
            p = parse_ingredient_line(line)
            if p is None:
                skipped_lines.append(line)
            else:
                parsed.append(p)

        # 3) Aggregate + fetch live prices
        agg = self._aggregate_ingredients(parsed)
        self._attach_live_prices(agg)

        # 4) Build list of items + total cost
        items: List[Dict[str, Any]] = []
        total_cost = 0.0
        items_without_price: List[str] = []

        for key, item in agg.items():
            if item.price is None:
                items_without_price.append(item.ingredient_name)
                continue

            total_cost += item.price
            items.append(
                {
                    "ingredient_display_name": item.ingredient_name,
                    "normalized_name": item.normalized_name,
                    "recipe_quantity": item.total_quantity,
                    "recipe_unit": item.unit,
                    "product_title": item.product_title,
                    "product_url": item.product_url,
                    "price": item.price,
                    "currency": self.currency,
                }
            )

        # 5) Budget analysis
        budget_info = self._evaluate_budget(total_cost, budget)

        # 6) Final payload (main.py expects keys like estimated_total_cost & currency)
        return {
            "recipe_name": recipe_name,
            "currency": self.currency,
            "items": items,
            "estimated_total_cost": round(total_cost, 2),
            "budget": budget,
            "within_budget": budget_info["within_budget"],
            "amount_over_budget": budget_info["amount_over_budget"],
            "amount_under_budget": budget_info["amount_under_budget"],
            "skipped_lines_no_quantity": skipped_lines,
            "items_without_price": items_without_price,
        }


# =========================
#   LOCAL TEST (optional)
# =========================

if __name__ == "__main__":
    # Small self-test using your Vegetarian Pasta Primavera example
    ingredients_json = {
        "recipe_name": "Vegetarian Pasta Primavera",
        "ingredients": {
            "For the Vegetable Medley": [
                "1 red bell pepper, seeded and chopped",
                "1 yellow bell pepper, seeded and chopped",
                "1 cup broccoli florets",
                "1 cup sliced zucchini",
                "1 cup sliced yellow squash",
                "1 cup sliced mushrooms",
                "1/2 cup chopped red onion",
                "2 cloves garlic, minced",
                "2 tablespoons olive oil",
                "Salt and freshly ground black pepper to taste",
            ],
            "For the Pasta and Sauce": [
                "1 pound pasta (such as penne, farfalle, or rotini)",
                "1/4 cup olive oil",
                "1/4 cup vegetable broth",
                "1/4 cup grated Parmesan cheese (optional, for vegetarians)",
                "2 tablespoons fresh basil, chopped",
                "1 tablespoon fresh parsley, chopped",
                "Salt and freshly ground black pepper to taste",
            ],
        },
    }

    agent = ShoppingBudgetAgent(currency="INR")
    plan = agent.process_recipe_ingredients(
        recipe_data=ingredients_json,
        stores=["Flipkart"],
        budget=2000.0,
    )

    from pprint import pprint
    pprint(plan)
