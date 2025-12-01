"""
API Test Script for Meal Planning System

Tests the FastAPI endpoints with sample requests
"""

import requests # type: ignore
import json

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the root endpoint"""
    print("\n" + "="*80)
    print("TEST 1: Health Check")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_complete_meal_plan():
    """Test the complete meal plan workflow"""
    print("\n" + "="*80)
    print("TEST 2: Complete Meal Plan Workflow")
    print("="*80)
    
    # Ask user for their preferences
    print("\n👋 Welcome! Please describe your dietary preferences and health goals.")
    print("\nYou can mention:")
    print("  - Diet type (vegetarian, vegan, keto, etc.)")
    print("  - Daily calorie goals")
    print("  - Protein, carbs, fat targets")
    print("  - Number of meals per day")
    print("  - Any food allergies")
    print("  - Foods you dislike")
    print("  - Health conditions (diabetes, high BP, etc.)")
    print("\nExample: 'I am vegetarian, need 2000 calories, 120g protein, 3 meals daily, allergic to peanuts, diabetic'\n")
    
    user_input = input("📝 Your preferences: ").strip()
    
    if not user_input:
        print("\n⚠️  No input provided. Using default example...")
        user_input = """
        I am a vegetarian who wants to eat healthy. I need about 2000 calories per day.
        I want high protein meals (around 120g per day) with moderate carbs (200g) and 
        healthy fats (60g). I eat 3 meals a day. I'm allergic to peanuts and don't like 
        mushrooms. I have diabetes so I need low sugar meals.
        """
    
    payload = {
        "user_description": user_input,
        "user_id": "test_user_001"
    }
    
    print("\n📤 Sending request to API...")
    print(f"User Description: {user_input[:100]}...")
    
    response = requests.post(f"{BASE_URL}/complete-meal-plan", json=payload)
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Success!")
        
        if "summary" in data:
            summary = data["summary"]
            print("\n📊 Summary:")
            print(f"   Recipe: {summary.get('recipe_name')}")
            print(f"   Total Cost: {summary.get('total_cost')}")
            print(f"   Within Budget: {summary.get('within_budget')}")
            print(f"   Recommendations: {summary.get('key_recommendations', [])}")
        
        # Show profile
        if "data" in data and "user_profile" in data["data"]:
            profile = data["data"]["user_profile"]
            print("\n👤 User Profile:")
            print(f"   Diet Type: {profile.get('diet_type')}")
            print(f"   Daily Calories: {profile.get('daily_calorie_target')}")
            print(f"   Protein: {profile.get('protein_target_g')}g")
            print(f"   Allergies: {profile.get('allergies')}")
            print(f"   Health Notes: {profile.get('health_notes')}")
        
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def test_preference_endpoint():
    """Test the preference agent endpoint"""
    print("\n" + "="*80)
    print("TEST 3: Preference Agent Endpoint")
    print("="*80)
    
    print("\n📝 Enter your dietary preferences:")
    user_input = input("Your description: ").strip()
    
    if not user_input:
        print("⚠️  No input. Using default example...")
        user_input = "I'm vegan, need 1800 calories, 90g protein, allergic to soy"
    
    payload = {
        "user_description": user_input,
        "user_id": "test_user_002"
    }
    
    print(f"\n📤 Sending: {user_input[:80]}...")
    
    response = requests.post(f"{BASE_URL}/preference", json=payload)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Profile created!")
        print(f"Profile: {json.dumps(data.get('data', {}).get('profile', {}), indent=2)}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def test_preference_to_recipe():
    """Test the preference-to-recipe workflow"""
    print("\n" + "="*80)
    print("TEST 4: Preference → Recipe Workflow")
    print("="*80)
    
    print("\n📝 Enter your preferences for recipe generation:")
    user_input = input("Your description: ").strip()
    
    if not user_input:
        print("⚠️  No input. Using default example...")
        user_input = "Vegetarian, Italian food lover, 2200 calories, 3 meals"
    
    payload = {
        "user_description": user_input,
        "user_id": "test_user_003"
    }
    
    print(f"\n📤 Sending: {user_input[:80]}...")
    
    response = requests.post(f"{BASE_URL}/preference-to-recipe", json=payload)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Workflow completed!")
        
        if "data" in data:
            recipe_name = data["data"].get("recipe", {}).get("recipe_name", "N/A")
            print(f"Recipe: {recipe_name}")
        
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False


def main():
    """Run all API tests"""
    print("\n" + "="*80)
    print("🧪 MEAL PLANNING API TESTS")
    print("="*80)
    print("\n⚠️  Make sure the API server is running on http://localhost:8000")
    print("   Run: python main.py")
    print("\n" + "="*80)
    print("INTERACTIVE MODE - You will be asked for your preferences")
    print("="*80)
    print("\nPress Enter to continue...")
    input()
    
    results = []
    
    # Test 1: Health check
    try:
        results.append(("Health Check", test_health_check()))
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        results.append(("Health Check", False))
    
    # Test 2: Complete workflow
    try:
        results.append(("Complete Meal Plan", test_complete_meal_plan()))
    except Exception as e:
        print(f"❌ Complete meal plan failed: {e}")
        results.append(("Complete Meal Plan", False))
    
    # Test 3: Preference endpoint
    try:
        results.append(("Preference Agent", test_preference_endpoint()))
    except Exception as e:
        print(f"❌ Preference endpoint failed: {e}")
        results.append(("Preference Agent", False))
    
    # Test 4: Preference to Recipe
    try:
        results.append(("Preference → Recipe", test_preference_to_recipe()))
    except Exception as e:
        print(f"❌ Preference to recipe failed: {e}")
        results.append(("Preference → Recipe", False))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, passed in results if passed)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
