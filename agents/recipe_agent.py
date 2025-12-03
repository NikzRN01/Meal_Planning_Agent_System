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

load_dotenv()


# Configure API Key (supports multiple environments)
def setup_api_key():
    """Setup Google API key from various sources"""
    try:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    except Exception as e:
        print(f"Authentication Error: {e}")

setup_api_key()

# Configure retry options
retry_config = types.HttpRetryOptions(
    attempts=8,  # Maximum retry attempts
    exp_base=10,  # Delay multiplier
    initial_delay=3,
    max_delay=60,
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
