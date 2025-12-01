import json
from pathlib import Path
from typing import List
from models.schema import Meal, Ingredient, MealNutrition, UserHealthProfile


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class RecipeAgent:
    """
    Fetches recipes based on preferences and returns Meal objects.
    Currently uses local JSON + simple fake macro calculation.
    """

    def __init__(self):
        self._recipes = self._load_recipes()

    def _load_recipes(self) -> List[Meal]:
        path = DATA_DIR / "sample_recipes.json"
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        meals: List[Meal] = []
        for r in raw:
            ingredients = [Ingredient(**ing) for ing in r["ingredients"]]
            meals.append(Meal(id=r["id"], name=r["name"], ingredients=ingredients, servings=1))
        return meals

    def _fake_nutrition_lookup(self, ingredient: Ingredient) -> MealNutrition:
        """
        TEMP: approximate macros per 100g / piece.
        Replace this with a real nutrition API client.
        """
        name = ingredient.name.lower()
        if "tofu" in name:
            base = MealNutrition(calories=76, protein_g=8, carbs_g=1.9, fat_g=4.8)
        elif "oats" in name:
            base = MealNutrition(calories=389, protein_g=17, carbs_g=66, fat_g=7)
        elif "banana" in name:
            base = MealNutrition(calories=105, protein_g=1.3, carbs_g=27, fat_g=0.3)
        elif "olive oil" in name:
            base = MealNutrition(calories=884, protein_g=0, carbs_g=0, fat_g=100)
        else:
            base = MealNutrition(calories=50, protein_g=2, carbs_g=10, fat_g=1)

        # scale by quantity (assume 100 g or 1 piece reference)
        factor = ingredient.quantity / 100.0 if ingredient.unit in ("g", "ml") else ingredient.quantity
        return MealNutrition(
            calories=base.calories * factor,
            protein_g=base.protein_g * factor,
            carbs_g=base.carbs_g * factor,
            fat_g=base.fat_g * factor,
        )

    def _compute_meal_macros(self, meal: Meal) -> Meal:
        total = MealNutrition(calories=0, protein_g=0, carbs_g=0, fat_g=0)
        for ing in meal.ingredients:
            m = self._fake_nutrition_lookup(ing)
            total.calories += m.calories
            total.protein_g += m.protein_g
            total.carbs_g += m.carbs_g
            total.fat_g += m.fat_g
        meal.macros_per_serving = total
        return meal

    def generate_week_plan(self, profile: UserHealthProfile) -> "WeekPlan":
        """
        Very simple planner: repeat first N meals across 7 days.
        Later you can make this smart with LLM reasoning.
        """
        from models.schema import DayPlan, WeekPlan

        meals_with_macros = [self._compute_meal_macros(m) for m in self._recipes]
        days: List[DayPlan] = []

        for i in range(7):
            # naive: same two meals every day (replace with variety logic)
            day_meals = meals_with_macros[:profile.meals_per_day]
            days.append(DayPlan(day_name=f"Day {i + 1}", meals=day_meals))

        return WeekPlan(days=days)


# Code: TJ
"""
Recipe Agent for Meal Planning System

This agent receives input from the Preference Agent and:
1. Fetches recipes based on preferences using Google Search
2. Extracts ingredients for Shopping & Budget Agent
3. Extracts nutritional info for Health Agent
4. Outputs structured JSON data for downstream agents
"""

# Optional ADK-based runner (guarded imports)
import asyncio as _asyncio
from typing import Dict as _Dict, Any as _Any

_HAS_ADK_RECIPE = False
try:
    from google.adk.agents import Agent as _Agent
    from google.adk.models.google_llm import Gemini as _Gemini
    from google.adk.runners import InMemoryRunner as _InMemoryRunner
    from google.adk.tools import google_search as _google_search
    from google.genai import types as _types
    from dotenv import load_dotenv as _load_dotenv
    import json as _json
    import os as _os

    _load_dotenv()
    _HAS_ADK_RECIPE = True
except Exception:
    _Agent = _Gemini = _InMemoryRunner = _google_search = _types = None


if _HAS_ADK_RECIPE:
    _retry_config = _types.HttpRetryOptions(
        attempts=5, exp_base=7, initial_delay=1, http_status_codes=[429, 500, 503, 504]
    )

    recipe_agent = _Agent(
        name="RecipeAgent",
        model=_Gemini(model="gemini-2.0-flash-lite", retry_options=_retry_config),
        instruction=(
            "You are a Recipe Agent. Return ONLY valid JSON with recipe_name, description,"
            " ingredients (object of section->list), instructions (array of steps),"
            " nutritional_information (serving_size, calories, macros)."
        ),
        tools=[_google_search],
        output_key="recipe_data",
    )

    class RecipeAgentRunner:
        """Runner class for Recipe Agent with helper methods"""

        def __init__(self, agent: _Agent):
            self.agent = agent
            self.runner = _InMemoryRunner(agent=agent, app_name="RecipeAgentApp")

        async def fetch_recipe(self, preferences: _Dict[str, _Any]) -> _Dict[str, _Any]:
            query = self._build_query(preferences)
            result = await self.runner.run_debug(query)
            return self._parse_output(result)

        def _build_query(self, preferences: _Dict[str, _Any]) -> str:
            parts = ["Find a recipe for"]
            if "meal_type" in preferences:
                parts.append(preferences["meal_type"])
            if "cuisine_preferences" in preferences and preferences["cuisine_preferences"]:
                parts.append(preferences["cuisine_preferences"][0])
            if "dietary_restrictions" in preferences and preferences["dietary_restrictions"]:
                parts.append("that is " + " and ".join(preferences["dietary_restrictions"]))
            parts.append("with ingredients, instructions, and nutritional information")
            return " ".join(parts)

        def _parse_output(self, result: _Any) -> _Dict[str, _Any]:
            json_string_output = None
            if isinstance(result, list) and result:
                event = result[0]
                json_string_output = event.actions.state_delta.get("recipe_data")
            if not json_string_output:
                return {"error": "No recipe_data found in output", "raw_result": str(result)[:500]}
            try:
                if json_string_output.startswith("```json"):
                    json_string_output = json_string_output.split("```", 2)[-1]
                return _json.loads(json_string_output)
            except Exception as e:
                return {"error": str(e), "raw_output": json_string_output}

    async def _example_usage() -> None:
        runner = RecipeAgentRunner(recipe_agent)
        prefs = {"dietary_restrictions": ["vegetarian"], "cuisine_preferences": ["Italian"], "meal_type": "dinner"}
        data = await runner.fetch_recipe(prefs)
        print(_json.dumps(data, indent=2))

    if __name__ == "__main__":
        try:
            _asyncio.run(_example_usage())
        except KeyboardInterrupt:
            print("\nCancelled")

# Code: TJ
"""
Recipe Agent for Meal Planning System

This agent receives input from the Preference Agent and:
1. Fetches recipes based on preferences using Google Search
2. Extracts ingredients for Shopping & Budget Agent
3. Extracts nutritional info for Health Agent
4. Outputs structured JSON data for downstream agents
"""

## Import ADK components
import asyncio
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search
from google.genai import types
from dotenv import load_dotenv
import json
import os
from typing import Dict, List, Any

print("ADK Component imported!\n")
load_dotenv()


# Configure API Key (supports multiple environments)
def setup_api_key():
    """Setup Google API key from various sources"""
    try:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        print("✅ Gemini API key setup complete (Colab).")
    except ImportError:
        # Fallback to environment variable
        if "GOOGLE_API_KEY" in os.environ:
            print("✅ Gemini API key setup complete (Environment).")
        else:
            print(
                "⚠️ Warning: GOOGLE_API_KEY not found. Please set it in environment variables."
            )
    except Exception as e:
        print(f"🔑 Authentication Error: {e}")


setup_api_key()

# Configure retry options
retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# Recipe Agent Configuration
recipe_agent = Agent(
    name="RecipeAgent",
    model=Gemini(model="gemini-2.0-flash-lite", retry_options=retry_config),
    instruction="""You are a Recipe Agent in a meal planning system. Your task is to find recipes based on user preferences, including ingredients, step-by-step instructions, and nutritional information.

CRITICAL: You MUST respond with ONLY valid JSON in the EXACT format specified below. Do not include any text before or after the JSON.

OUTPUT the data in this EXACT JSON format:
{
  "recipe_name": "Name of the Recipe",
  "description": "A brief description of the dish, highlighting key flavors and characteristics.",
  "ingredients": {
    "Section Name 1 (e.g., For the Tomato Sauce)": [
      "2 tablespoons ingredient with full quantity and description",
      "1 onion, chopped",
      "Add more ingredients as needed"
    ],
    "Section Name 2 (e.g., For the Vegetable Medley)": [
      "1 red bell pepper, chopped",
      "Add more ingredients as needed"
    ],
    "Section Name 3 (e.g., For the Pasta and Assembly)": [
      "1 pound pasta (penne, rigatoni, or your favorite)",
      "Add more ingredients as needed"
    ]
  },
  "instructions": [
    {
      "step": 1,
      "description": "Detailed description of step 1 with cooking times and techniques."
    },
    {
      "step": 2,
      "description": "Detailed description of step 2 with cooking times and techniques."
    },
    {
      "step": 3,
      "description": "Continue with all necessary steps in sequential order."
    }
  ],
  "nutritional_information": {
    "serving_size": "X servings",
    "calories": "Approximately XXX-XXX calories per serving (This is an estimate and can vary based on specific ingredients and brands used.)",
    "macros": {
      "protein": "Approximately XXg or XX-XXg",
      "carbohydrates": "Approximately XXg or XX-XXg",
      "fat": "Approximately XXg or XX-XXg"
    }
  }
}

IMPORTANT RULES:
1. Always respond with ONLY valid JSON - no markdown code blocks, no extra text
2. Use the ingredients structure as a DICTIONARY/OBJECT with section names as keys
3. Each section key should be descriptive (e.g., "For the Tomato Sauce", "For the Vegetable Medley")
4. Each section contains an ARRAY of ingredient strings with full quantities and descriptions
5. Instructions MUST be an array of objects with "step" (number) and "description" (string)
6. Number steps sequentially starting from 1
7. Include detailed, helpful descriptions for each step
8. Provide serving size and estimated nutritional information
9. Use ranges for nutritional values when appropriate (e.g., "450-550 calories")
10. Ensure all JSON is properly formatted with correct commas, quotes, and brackets""",
    tools=[google_search],
    output_key="recipe_data",
)

print("✅ RecipeAgent created.")


class RecipeAgentRunner:
    """Runner class for Recipe Agent with helper methods"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.runner = InMemoryRunner(agent=agent, app_name="RecipeAgentApp")

    async def fetch_recipe(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch recipe based on preferences from Preference Agent

        Args:
            preferences: Dictionary containing user preferences
                {
                    "dietary_restrictions": ["vegetarian", "gluten-free"],
                    "cuisine_preferences": ["Italian", "Mexican"],
                    "meal_type": "dinner",
                    "servings": 4,
                    "budget_per_meal": 20
                }

        Returns:
            Dictionary containing recipe, ingredients, and nutrition data
        """
        # Construct query from preferences
        query = self._build_query(preferences)

        # Run the agent
        result = await self.runner.run_debug(query)
        # Parse and validate the output
        recipe_data = self._parse_output(result)

        return recipe_data

    def _build_query(self, preferences: Dict[str, Any]) -> str:
        """Build search query from preferences"""
        query_parts = ["Find a recipe for"]

        if "meal_type" in preferences:
            query_parts.append(preferences["meal_type"])

        if "cuisine_preferences" in preferences and preferences["cuisine_preferences"]:
            query_parts.append(preferences["cuisine_preferences"][0])

        if (
            "dietary_restrictions" in preferences
            and preferences["dietary_restrictions"]
        ):
            restrictions = " and ".join(preferences["dietary_restrictions"])
            query_parts.append(f"that is {restrictions}")

        query_parts.append(
            "with ingredients, instructions, and nutritional information"
        )

        return " ".join(query_parts)

    def _parse_output(self, result: Any) -> Dict[str, Any]:
        """Parse agent output and extract JSON data"""
        json_string_output = None
        
        if isinstance(result, list) and len(result) > 0:
            # Assuming the first event contains the recipe details
            event = result[0]

            # Extract the JSON string from the state_delta
            # The output key 'recipe_data' is defined in the RecipeAgent.
            json_string_output = event.actions.state_delta.get("recipe_data")
        
        if json_string_output:
            # Remove markdown code block delimiters if present
            if json_string_output.startswith(
                "```json\n"
            ) and json_string_output.endswith("\n```"):
                json_string_output = json_string_output[
                    len("```json\n") : -len("\n```")
                ]
            elif json_string_output.startswith(
                "```json"
            ) and json_string_output.endswith("```"):
                json_string_output = json_string_output[len("```json") : -len("```")]

            try:
                # Parse the JSON string into a Python dictionary
                json_object = json.loads(json_string_output)
                return json_object
                
            except json.JSONDecodeError as e:
                print(f"\n⚠️ Error decoding JSON: {e}")
                
                # Show context around the error
                error_pos = e.pos if hasattr(e, 'pos') else 0
                start = max(0, error_pos - 100)
                end = min(len(json_string_output), error_pos + 100)
                
                print(f"\n📍 Error location (position {error_pos}):")
                print(f"Context: ...{json_string_output[start:end]}...")
                print(f"\n📄 Full JSON output:")
                print(json_string_output)
                
                return {"error": str(e), "raw_output": json_string_output}
        else:
            print("⚠️ Error: 'recipe_data' not found in the agent's output.")
            print("Error: 'result' variable is not defined or is not in the expected format.")
            return {"error": "No recipe_data found in output", "raw_result": str(result)[:500]}

    def get_ingredients_for_shopping(
        self, recipe_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract ingredients in format for Shopping & Budget Agent

        Returns:
            JSON formatted ingredients list with all sections
        """
        return {
            "recipe_name": recipe_data.get("recipe_name", "Unknown"),
            "ingredients": recipe_data.get("ingredients", []),
        }

    def get_nutrition_for_health(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract nutritional info in format for Health Agent

        Returns:
            JSON formatted nutritional information
        """
        return {
            "recipe_name": recipe_data.get("recipe_name", "Unknown"),
            "nutritional_information": recipe_data.get("nutritional_information", {}),
        }

# Example usage function
async def example_usage():
    """Example of how to use the Recipe Agent"""

    # Initialize the runner
    runner = RecipeAgentRunner(recipe_agent)

    # Example preferences from Preference Agent
    preferences = {
        "dietary_restrictions": ["vegetarian"],
        "cuisine_preferences": ["Italian"],
        "meal_type": "dinner",
        "servings": 4,
        "budget_per_meal": 25,
    }

    # Fetch recipe
    print("\n🔍 Fetching recipe based on preferences...")
    recipe_data = await runner.fetch_recipe(preferences)

    print("\n📋 Recipe Data:")
    print(json.dumps(recipe_data, indent=2))

    # Extract data for other agents
    ingredients_json = runner.get_ingredients_for_shopping(recipe_data)
    print("\n🛒 Ingredients for Shopping & Budget Agent:")
    print(json.dumps(ingredients_json, indent=2))

    nutrition_json = runner.get_nutrition_for_health(recipe_data)
    print("\n💊 Nutrition for Health Agent:")
    print(json.dumps(nutrition_json, indent=2))

    return recipe_data


# Uncomment to run example (requires async environment)
asyncio.run(example_usage())