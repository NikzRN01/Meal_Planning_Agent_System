import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os, json, asyncio, re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types

load_dotenv()

def setup_api_key():
    try:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")
    except Exception as e:
        print(f"🔑 Authentication Error: {e}")

setup_api_key()

# Memory & Session Services
memory_service = InMemoryMemoryService()
session_service = InMemorySessionService()
print("✓ Shopping Agent: Memory service initialized")

retry_config = types.HttpRetryOptions(
    attempts=8, exp_base=10, initial_delay=3, max_delay=60,
    http_status_codes=[429, 500, 503, 504],
)

shopping_agent = Agent(
    name="ShoppingAgent",
    model=Gemini(model="gemini-2.0-flash-lite", retry_options=retry_config),
    instruction="""
You are a Shopping Agent in a meal planning system with memory capabilities.

If the user asks about past shopping lists or prices, use the load_memory tool to search stored memories.

Tasks:
1) From the user's natural-language description, Create a structured ingredients object with descriptive section keys and full ingredient strings including quantities.
2) Use the google_search tool to find current price and a purchase URL for each ingredient (search the normalized ingredient name + pack size where appropriate).
3) Return ONLY valid JSON in EXACTLY this format:

{
  "recipe_name": "Matter Paneer",
  "ingredients": {
    "Main": ["1 cup broccoli florets", "2 cloves garlic"]
  },
  "items": [
    {
      "ingredient": "broccoli florets",
      "normalized": "broccoli",
      "price": 50.0,
      "currency": "INR",
      "url": "https://example.com/product"
    }
  ],
  "instructions": [
    {"step": 1, "description": "…"},
    {"step": 2, "description": "…"}
  ],
  "serving_size": "2-3 people",
  "nutrition": {
    "calories": "450-550",
    "protein": "20-25g",
    "carbs": "40-50g",
    "fat": "15-20g"
  }
}

Rules:
- Only JSON (no markdown fences, no extra text).
- Ingredients must be a dictionary of sections → arrays of full strings with quantities.
- Each item must include ingredient, normalized, price (number), currency, and url.
- Use google_search for pricing and URLs; do not invent prices or links.
- Instructions must be helpful and sequential, starting at step 1.
- Provide serving_size and a reasonable nutrition range.
""",
    tools=[google_search],
    output_key="recipe_data",
)

# =========================
#   INGREDIENT PARSER
# =========================

UNITS = {"cup","cups","tablespoon","tbsp","teaspoon","tsp","clove","cloves",
         "pound","lb","gram","g","kg","ml","l"}

def normalize(name: str) -> str:
    name = name.lower().split(",")[0].strip()
    synonyms = {"broccoli florets":"broccoli","button mushrooms":"mushrooms",
                "red onion":"onion","extra virgin olive oil":"olive oil",
                "parmesan":"parmesan cheese","fresh basil":"basil"}
    return synonyms.get(name,name)

@dataclass
class ShoppingItem:
    ingredient:str; normalized:str; qty:float; unit:str
    title:str=None; url:str=None; price:float=None

# =========================
#   GOOGLE PRICE FETCHER
# =========================

class GooglePriceFetcher:
    """Fetch product prices using Google Shopping search API."""
    def fetch_price(self, query: str) -> Optional[Dict[str, Any]]:
        # Here you’d call search_products(query="milk", category="groceries")
        # For demo, return mocked structure
        return {"title": f"{query} - Sample Product",
                "price": 50.0,
                "url": f"https://www.google.com/search?q={query}"}

# =========================
#   SHOPPING & BUDGET AGENT
# =========================

class ShoppingBudgetAgent:
    def __init__(self,currency="INR"):
        self.currency,self.fetcher=currency,GooglePriceFetcher()

    def process(self,recipe:Dict[str,Any],budget:Optional[float]=None)->Dict[str,Any]:
        lines=[l for sec in recipe.get("ingredients",{}).values() if isinstance(sec,list) for l in sec]
        items=[]; total=0
        for line in lines:
            tokens=line.split()
            if not tokens: continue
            try: qty=float(tokens[0])
            except: continue
            unit=tokens[1].lower() if len(tokens)>1 and tokens[1].lower() in UNITS else "piece"
            name=" ".join(tokens[2:]) if unit!="piece" else " ".join(tokens[1:])
            norm=normalize(name)
            info=self.fetcher.fetch_price(norm)
            if info:
                total+=info["price"]
                items.append({"ingredient":name,"normalized":norm,"qty":qty,"unit":unit,
                              "title":info["title"],"url":info["url"],
                              "price":info["price"],"currency":self.currency})
        return {"recipe":recipe.get("recipe_name","Unknown"),"currency":self.currency,
                "items":items,"estimated_total_cost":round(total,2),"budget":budget,
                "within_budget":None if budget is None else total<=budget,
                "amount_over_budget":None if budget is None else max(0,total-budget),
                "amount_under_budget":None if budget is None else max(0,budget-total)}
