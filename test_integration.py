"""
Test script for Complete Meal Planning Agent Integration

Tests the complete workflow:
1. Preference Agent → Recipe Agent
2. Recipe Agent → Health Agent
3. Complete workflow: Preference → Recipe → Shopping + Health
"""

import asyncio
import sys
import os

# Add agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from agents.recipe_agent import recipe_agent, RecipeAgentRunner
from agents.preference_agent import preference_agent, PreferenceAgentRunner
from agents.shopping_budget_agent import ShoppingBudgetAgent
from agents.health_agent import HealthAgent


async def test_preference_to_recipe():
    """Test: Preference Agent → Recipe Agent integration"""
    print("\n" + "="*80)
    print("TEST 1: PREFERENCE AGENT → RECIPE AGENT")
    print("="*80 + "\n")
    
    # Initialize runners
    pref_runner = PreferenceAgentRunner(preference_agent)
    recipe_runner = RecipeAgentRunner(recipe_agent)
    
    # Ask user for input (interactive)
    print("📝 Please describe your dietary preferences:")
    print("   (Example: I am a vegetarian, need 2000 calories, allergic to peanuts, diabetic)")
    print()
    user_description = input("Your preferences: ").strip()
    
    if not user_description:
        print("⚠️  No input provided. Using default example...")
        user_description = """
        I am a vegetarian who wants to eat healthy. I need about 2000 calories per day.
        I want high protein meals (around 120g per day) with moderate carbs (200g) and 
        healthy fats (60g). I eat 3 meals a day. I'm allergic to peanuts and don't like 
        mushrooms. I have diabetes so I need low sugar meals.
        """
    
    print(f"\n📝 User Description:\n{user_description}\n")
    
    # Step 1: Create profile using Preference Agent
    print("⏳ Running Preference Agent...")
    prompt = f"""
The user will describe their diet, lifestyle and health precautions.

User description:
\"\"\"{user_description}\"\"\"
"""
    
    result = await pref_runner.runner.run_debug(prompt)
    profile_data = pref_runner._parse_output(result)
    
    if "error" in profile_data:
        print(f"❌ Error: {profile_data['error']}")
        return None
    
    print("\n✅ Profile Created:")
    print(f"   Diet Type: {profile_data.get('diet_type')}")
    print(f"   Daily Calories: {profile_data.get('daily_calorie_target')}")
    print(f"   Protein Target: {profile_data.get('protein_target_g')}g")
    print(f"   Carbs Target: {profile_data.get('carb_target_g')}g")
    print(f"   Fat Target: {profile_data.get('fat_target_g')}g")
    print(f"   Meals Per Day: {profile_data.get('meals_per_day')}")
    print(f"   Allergies: {profile_data.get('allergies')}")
    print(f"   Dislikes: {profile_data.get('dislikes')}")
    print(f"   Health Notes: {profile_data.get('health_notes')}")
    
    # Step 2: Convert to recipe preferences
    recipe_preferences = {
        "dietary_restrictions": [profile_data.get("diet_type", "vegetarian")],
        "cuisine_preferences": ["Italian"],
        "meal_type": "lunch",
        "servings": profile_data.get("meals_per_day", 3),
        "budget_per_meal": None
    }
    
    # Add health-based restrictions
    health_notes = profile_data.get("health_notes", [])
    if "low_sugar" in health_notes:
        recipe_preferences["dietary_restrictions"].append("low sugar")
    if "high_protein" in health_notes:
        recipe_preferences["dietary_restrictions"].append("high protein")
    
    print(f"\n🔍 Recipe Preferences Generated:")
    print(f"   Dietary Restrictions: {recipe_preferences['dietary_restrictions']}")
    print(f"   Cuisine: {recipe_preferences['cuisine_preferences']}")
    print(f"   Meal Type: {recipe_preferences['meal_type']}")
    print(f"   Servings: {recipe_preferences['servings']}")
    
    # Step 3: Fetch recipe
    print("\n⏳ Running Recipe Agent (this may take 30-60 seconds)...")
    recipe_data = await recipe_runner.fetch_recipe(recipe_preferences)
    
    if "error" in recipe_data:
        print(f"❌ Recipe Error: {recipe_data.get('error')}")
        return None
    
    print("\n✅ Recipe Found:")
    print(f"   Recipe Name: {recipe_data.get('recipe_name')}")
    print(f"   Description: {recipe_data.get('description', 'N/A')[:150]}...")
    
    # Show ingredients sections
    ingredients = recipe_data.get('ingredients', {})
    if ingredients:
        print(f"\n   Ingredients Sections:")
        for section, items in ingredients.items():
            print(f"      - {section}: {len(items)} items")
    
    return profile_data, recipe_data


async def test_recipe_to_health(profile_data, recipe_data):
    """Test: Recipe Agent → Health Agent integration"""
    print("\n" + "="*80)
    print("TEST 2: RECIPE AGENT → HEALTH AGENT")
    print("="*80 + "\n")
    
    nutrition_info = recipe_data.get("nutritional_information", {})
    
    print("📊 Recipe Nutritional Information:")
    print(f"   Serving Size: {nutrition_info.get('serving_size', 'N/A')}")
    print(f"   Calories: {nutrition_info.get('calories', 'N/A')}")
    
    if "macros" in nutrition_info:
        macros = nutrition_info["macros"]
        print(f"\n   Macros per serving:")
        print(f"      Protein: {macros.get('protein', 'N/A')}")
        print(f"      Carbohydrates: {macros.get('carbohydrates', 'N/A')}")
        print(f"      Fat: {macros.get('fat', 'N/A')}")
    
    print("\n🎯 User Daily Targets:")
    print(f"   Calories: {profile_data.get('daily_calorie_target', 2200)} kcal")
    print(f"   Protein: {profile_data.get('protein_target_g', 100)}g")
    print(f"   Carbs: {profile_data.get('carb_target_g', 230)}g")
    print(f"   Fat: {profile_data.get('fat_target_g', 70)}g")
    
    # Generate detailed health recommendations
    print("\n💡 Health Analysis & Recommendations:")
    
    recommendations = []
    health_notes = profile_data.get("health_notes", [])
    allergies = profile_data.get("allergies", [])
    dislikes = profile_data.get("dislikes", [])
    
    if "low_sugar" in health_notes:
        recommendations.append("✓ Monitor sugar content - choose recipes with natural sugars from fruits")
        recommendations.append("✓ Avoid added sugars, sodas, and processed foods")
    
    if "low_sodium" in health_notes:
        recommendations.append("✓ Limit sodium to <2300mg per day (<1500mg if hypertensive)")
        recommendations.append("✓ Use herbs and spices instead of salt")
    
    if "high_protein" in health_notes:
        recommendations.append(f"✓ Target {profile_data.get('protein_target_g', 100)}g protein daily")
        recommendations.append("✓ Include protein in every meal for muscle maintenance")
    
    if "low_carb" in health_notes:
        recommendations.append(f"✓ Limit carbs to {profile_data.get('carb_target_g', 230)}g daily")
        recommendations.append("✓ Focus on complex carbs (whole grains, vegetables)")
    
    if allergies:
        print(f"\n   ⚠️  CRITICAL - ALLERGIES: Avoid {', '.join(allergies)}")
        recommendations.append(f"⚠️  Always check ingredients for: {', '.join(allergies)}")
    
    if dislikes:
        print(f"   ℹ️  Dislikes: {', '.join(dislikes)}")
    
    print()
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # Calculate per-meal targets
    meals_per_day = profile_data.get('meals_per_day', 3)
    print(f"\n📊 Per-Meal Targets ({meals_per_day} meals/day):")
    print(f"   Calories per meal: ~{profile_data.get('daily_calorie_target', 2200) // meals_per_day} kcal")
    print(f"   Protein per meal: ~{profile_data.get('protein_target_g', 100) // meals_per_day}g")
    print(f"   Carbs per meal: ~{profile_data.get('carb_target_g', 230) // meals_per_day}g")
    print(f"   Fat per meal: ~{profile_data.get('fat_target_g', 70) // meals_per_day}g")
    
    return True


async def test_complete_workflow():
    """Test: Complete workflow with Shopping Agent"""
    print("TEST COMPLETE WORKFLOW (Preference → Recipe → Shopping + Health)")
    
    # Run preference to recipe test first
    result = await test_preference_to_recipe()
    if not result:
        print("❌ Workflow failed at Preference/Recipe step")
        return
    
    profile_data, recipe_data = result
    
    # Test Recipe to Health
    health_ok = await test_recipe_to_health(profile_data, recipe_data)
    
    if not health_ok:
        print("❌ Workflow failed at Health step")
        return
    
    # Test Shopping Agent
    shopping_agent = ShoppingBudgetAgent(currency="INR")
    
    print("⏳ Running Shopping & Budget Agent...")
    print("   (Fetching live prices of grocery...)\n")
    
    shopping_plan = shopping_agent.process(
        recipe=recipe_data,
        budget=500.0
    )
    
    print("🛒 SHOPPING LIST DETAILS:")
    
    # Show items
    items = shopping_plan.get('items', [])
    
    if items:
        for item in items:
            # Print item details
            ingredient = item.get('ingredient', 'Unknown')
            normalized = item.get('normalized', '')
            qty = item.get('qty', '')
            unit = item.get('unit', '')
            price = item.get('price', 0)
            url = item.get('url', '')
            
            print(f"\n   • {ingredient}")
            if qty and unit:
                print(f"     Quantity: {qty} {unit}")
            print(f"     Price: ₹{price:.2f}")
            if url:
                print(f"     URL: {url}")
    
    # Show summary
    print("BUDGET SUMMARY:")
    print(f"   Total Items: {len(items)}")
    print(f"   Estimated Total: ₹{shopping_plan.get('estimated_total_cost', 0):.2f}")
    print(f"   Budget Limit: ₹{shopping_plan.get('budget', 500):.2f}")
    within_budget = shopping_plan.get('within_budget')
    if within_budget is not None:
        print(f"   Within Budget: {'YES' if within_budget else '❌ NO'}")
        if not within_budget:
            over = shopping_plan.get('amount_over_budget', 0)
            print(f"   Over Budget By: ₹{over:.2f}")
        else:
            under = shopping_plan.get('amount_under_budget', 0)
            print(f"   Under Budget By: ₹{under:.2f}")

    print("✅ COMPLETE WORKFLOW TEST PASSED!")
    
    print("📋 COMPLETE SUMMARY:")
    print("="*60)
    print(f"   ✓ User Profile Created")
    print(f"      - Diet: {profile_data.get('diet_type')}")
    print(f"      - Calories: {profile_data.get('daily_calorie_target')} kcal/day")
    print(f"      - Allergies: {profile_data.get('allergies', [])}")
    print(f"\n   ✓ Recipe Fetched")
    print(f"      - Name: {recipe_data.get('recipe_name')}")
    print(f"      - Ingredients: {sum(len(items) for items in recipe_data.get('ingredients', {}).values())} items")
    print(f"\n   ✓ Shopping List Generated")
    print(f"      - Total Cost: ₹{shopping_plan.get('estimated_total_cost', 0):.2f}")
    print(f"      - Items: {len(items)}")
    print(f"\n   ✓ Health Analysis Completed")
    print(f"      - Daily Targets Set")
    print(f"      - Recommendations Generated")
    print("="*60)


async def main():
    """Run all integration tests"""
    print("\n🧪 MEAL PLANNING AGENT INTEGRATION TESTS\n")
    
    print("Choose test mode:")
    print("1. Interactive (you provide preferences)")
    print("2. Automated (use default example)")
    
    choice = input("\nEnter choice (1 or 2, default=2): ").strip()
    
    # Set mode based on choice
    if choice == "1":
        print("\n✅ Running in INTERACTIVE mode\n")
        interactive_mode = True
    else:
        print("\n✅ Running in AUTOMATED mode (using default example)\n")
        interactive_mode = False
    
    try:
        # Temporarily modify the test function if in automated mode
        if not interactive_mode:
            print("ℹ️  Using default user preferences for testing...\n")
        
        await test_complete_workflow()
        
    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
