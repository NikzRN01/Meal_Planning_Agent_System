"""
Preference Agent for Meal Planning System (Interactive Terminal Agent)

Flow:
1. Agent greets user and asks for natural language description.
2. PreferenceAgent (Gemini) extracts structured JSON profile.
3. Agent interactively fills missing fields via terminal prompts.
4. Final complete profile stored in memory.
5. Health Agent can access via get_health_sync_payload(user_id)
"""

import asyncio
import json
import os
from typing import Dict, Any, List

try:
    from google.adk.agents import Agent
    from google.adk.models.google_llm import Gemini
    from google.adk.runners import InMemoryRunner, Runner
    from google.adk.memory import InMemoryMemoryService
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from dotenv import load_dotenv
    ADK_AVAILABLE = True
    load_dotenv()
except Exception:
    ADK_AVAILABLE = False
    Agent = Gemini = InMemoryRunner = Runner = types = load_memory = None

# ===============================
# API Key Setup
# ===============================
def setup_api_key():
    """Setup Google API key from environment."""
    try:
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in environment.")
    except Exception as e:
        print(f"🔑 Authentication Error: {e}\n")


setup_api_key()

# ===============================
# Memory & Session Services
# ===============================
if ADK_AVAILABLE:
    memory_service = InMemoryMemoryService()
    session_service = InMemorySessionService()
    print("✓ Preference Agent: Memory service initialized")
else:
    memory_service = None
    session_service = None

# ===============================
# Retry Configuration
# ===============================
if ADK_AVAILABLE:
    retry_config = types.HttpRetryOptions(
        attempts=8,
        exp_base=10,
        initial_delay=3,
        max_delay=60,
        http_status_codes=[429, 500, 503, 504],
    )
else:
    retry_config = None


# ===============================
# PreferenceAgent (LLM Agent)
# ===============================

if ADK_AVAILABLE:
    preference_agent = Agent(
        name="PreferenceAgent",
        model=Gemini(model="gemini-2.0-flash-lite", retry_options=retry_config),
        instruction="""
You are a Preference Agent in a multi-agent meal planning system with memory capabilities.

If the user asks about their past preferences or previous conversations, use the load_memory tool to search stored memories.

Your job:
- Read the user's natural language description of:
    - Diet type (veg, non-veg, vegan, keto, etc.)
    - Daily calories and macro goals (protein, carbs, fats)
    - Number of meals per day
    - Allergies (e.g., peanut, soy, gluten)
    - Disliked foods (e.g., broccoli, mushroom)
    - Health precautions / medical conditions:
        - diabetes / prediabetes / sugar control → use "low_sugar"
        - high BP / hypertension / heart issues → use "low_sodium"
        - wants high protein for muscle → use "high_protein"
        - low carb / keto / insulin sensitivity → use "low_carb"
        - you can add generic tags like "heart_friendly" if relevant

You MUST output ONLY valid JSON in this EXACT structure and keys:

{
  "diet_type": "vegetarian",
  "daily_calorie_target": 2200,
  "protein_target_g": 100,
  "carb_target_g": 230,
  "fat_target_g": 70,
  "meals_per_day": 3,
  "allergies": ["peanut"],
  "dislikes": ["broccoli"],
  "health_notes": ["low_sugar"]
}

Field rules and MISSING VALUES HANDLING:
- diet_type: string, e.g., "vegetarian", "vegan", "omnivore", "keto"
- daily_calorie_target: integer (no units)
- protein_target_g: integer
- carb_target_g: integer
- fat_target_g: integer
- meals_per_day: integer
- allergies: array of strings (["peanut", "soy"])
- dislikes: array of strings
- health_notes: array of strings such as:
    - "low_sugar"
    - "low_sodium"
    - "high_protein"
    - "low_carb"
    - "heart_friendly"

IMPORTANT:
- If the user DOES NOT clearly provide a value for a field,
  you MUST set that field to null (for numbers or diet_type) or [] (for arrays).
- DO NOT GUESS values that are not clearly stated or obviously implied.

CRITICAL:
- Only output JSON. No explanations, no markdown, no code fences.
- All fields MUST be present.
- All numbers MUST be plain numbers (no quotes, no 'kcal', no 'g'), or null if unknown.
""",
        tools=[],
        output_key="user_profile"
    )

else:
    preference_agent = None

# ===============================
# PreferenceAgentRunner
# ===============================

if ADK_AVAILABLE:
    class PreferenceAgentRunner:
        """Interactive terminal-based runner for preference agent."""

        def __init__(self, agent: Any):
            self.agent = agent
            self.runner = InMemoryRunner(agent=agent, app_name="PreferenceAgentApp")
            self._profiles: Dict[str, Dict[str, Any]] = {}

        async def start_interactive_session(self, user_id: str) -> Dict[str, Any]:
            """
            Start an interactive terminal session:
            1. Greet user
            2. Get natural language description
            3. Call PreferenceAgent
            4. Interactively fill missing fields
            5. Store and return profile
            """
            user_description = input("Your description: ").strip()
            profile_json = await self.runner.run(user_description)
            
            if "error" in profile_json:
                print(f"❌ Error: {profile_json['error']}")
                return None
            
            # Interactive completion
            profile_json = self._fill_missing_fields_interactively(profile_json)
            
            # Store profile
            self._profiles[user_id] = profile_json
            print("Great! I’ve saved your profile.")
            print("From now on, I’ll suggest meals that match your preferences and goals.")

            return profile_json

        def _parse_output(self, result: Any) -> Dict[str, Any]:
            """Parse agent output and extract JSON."""
            json_string_output = None

            if isinstance(result, list) and len(result) > 0:
                event = result[0]
                json_string_output = event.actions.state_delta.get("user_profile")

            if json_string_output:
                # Strip Markdown fences if present
                if json_string_output.startswith("```json\n") and json_string_output.endswith("\n```"):
                    json_string_output = json_string_output[len("```json\n") : -len("\n```")]
                elif json_string_output.startswith("```json") and json_string_output.endswith("```"):
                    json_string_output = json_string_output[len("```json") : -len("```")]

                try:
                    json_object = json.loads(json_string_output)
                    return json_object
                except json.JSONDecodeError as e:
                    print(f"\n⚠️ Error decoding JSON: {e}")
                    return {"error": str(e)}
            else:
                print("⚠️ Error: 'user_profile' not found in the agent's output.")
                return {"error": "No user_profile found"}

        def _fill_missing_fields_interactively(self, profile: Dict[str, Any]) -> Dict[str, Any]:
            """Interactively fill missing or null fields."""

            required_keys = [
                "diet_type",
                "daily_calorie_target",
                "protein_target_g",
                "carb_target_g",
                "fat_target_g",
                "meals_per_day",
                "allergies",
                "dislikes",
                "health_notes",
            ]
            
            for key in required_keys:
                if key not in profile:
                    profile[key] = None

            print("📋 Completing your profile...\n")

            # 1) diet_type
            if profile["diet_type"] is None:
                val = input("🥗 What kind of diet do you usually follow? (e.g., vegetarian, vegan, keto, or just a mix): ").strip()

                profile["diet_type"] = val if val else "omnivore"

            # Helper to get a positive integer
            def ask_int(prompt_text: str) -> int:
                while True:
                    val = input(prompt_text).strip()
                    try:
                        num = int(val)
                        if num <= 0:
                            print("   ⚠️ Please enter a positive number.")
                            continue
                        return num
                    except ValueError:
                        print("   ⚠️ Please enter a valid integer.")

            # 2) daily_calorie_target
            if profile["daily_calorie_target"] is None:
                profile["daily_calorie_target"] = ask_int("🔥 Daily calorie target (e.g., 2200): ")

            # 3) protein_target_g
            if profile["protein_target_g"] is None:
                profile["protein_target_g"] = ask_int("💪 Daily protein target in grams (e.g., 100): ")

            # 4) carb_target_g
            if profile["carb_target_g"] is None:
                profile["carb_target_g"] = ask_int("🌾 Daily carbs target in grams (e.g., 230): ")

            # 5) fat_target_g
            if profile["fat_target_g"] is None:
                profile["fat_target_g"] = ask_int("🧈 Daily fat target in grams (e.g., 70): ")

            # 6) meals_per_day
            if profile["meals_per_day"] is None:
                profile["meals_per_day"] = ask_int("🍽️  Meals per day (e.g., 3): ")

            # Helper to ask for comma-separated list
            def ask_list(prompt_text: str) -> List[str]:
                val = input(prompt_text).strip()
                if not val or val.lower() in ["none", "no", "nil", "n/a"]:
                    return []
                items = [x.strip() for x in val.split(",") if x.strip()]
                return items

            # 7) allergies
            if not isinstance(profile.get("allergies"), list) or profile["allergies"] == []:
                profile["allergies"] = ask_list("⚠️  Food allergies (comma-separated, or 'none'): ")

            # 8) dislikes
            if not isinstance(profile.get("dislikes"), list) or profile["dislikes"] == []:
                profile["dislikes"] = ask_list("😒 Foods you dislike (comma-separated, or 'none'): ")

            # 9) health_notes
            if not isinstance(profile.get("health_notes"), list) or profile["health_notes"] == []:
                raw_notes = ask_list(
                    "🏥 Health precautions (low_sugar/low_sodium/high_protein/low_carb, or 'none'): "
                )

                canonical_notes: List[str] = []
                for note in raw_notes:
                    lower = note.lower().replace("-", " ").replace("_", " ").strip()
                    if "sugar" in lower:
                        canonical_notes.append("low_sugar")
                    elif "pressure" in lower or "bp" in lower or "sodium" in lower or "salt" in lower:
                        canonical_notes.append("low_sodium")
                    elif "protein" in lower:
                        canonical_notes.append("high_protein")
                    elif "carb" in lower or "keto" in lower:
                        canonical_notes.append("low_carb")
                    elif "heart" in lower:
                        canonical_notes.append("heart_friendly")
                    else:
                        canonical_notes.append(lower.replace(" ", "_"))

                profile["health_notes"] = canonical_notes

            return profile

        def get_profile(self, user_id: str) -> Dict[str, Any]:
            """Return the stored profile."""
            if user_id not in self._profiles:
                raise ValueError(f"No profile found for user_id={user_id}")
            return self._profiles[user_id]

        def get_health_sync_payload(self, user_id: str) -> Dict[str, Any]:
            """SYNC POINT FOR HEALTH AGENT - Returns profile data for other agents."""
            profile = self.get_profile(user_id)
            return {
                "user_id": user_id,
                "health_profile": profile
            }

        def display_profile(self, user_id: str):
            """Display the stored profile in a nice format."""
            profile = self.get_profile(user_id)
            print("\nYOUR MEAL PLANNING PROFILE\n")
            print(f"Diet: {profile['diet_type']}")
            print(f"Calories per day: {profile['daily_calorie_target']} kcal")
            print(f"Protein: {profile['protein_target_g']} g | Carbs: {profile['carb_target_g']} g | Fat: {profile['fat_target_g']} g")
            print(f"Meals per day: {profile['meals_per_day']}")
            print(f"Allergies: {', '.join(profile['allergies']) if profile['allergies'] else 'None'}")
            print(f"Dislikes: {', '.join(profile['dislikes']) if profile['dislikes'] else 'None'}")
            print(f"Health notes: {', '.join(profile['health_notes']) if profile['health_notes'] else 'None'}")

else:
    class PreferenceAgentRunner:  # type: ignore
        def __init__(self, *_, **__):  # pragma: no cover
            raise ImportError("Google ADK not installed; interactive PreferenceAgent unavailable.")
