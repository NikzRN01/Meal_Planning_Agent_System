# Code : TJ
"""
Main API server for Meal Planner Agent System

This server handles:
1. Recipe Agent - Receives preferences, returns recipes with ingredients and nutrition
2. Shopping & Budget Agent - Receives ingredients, returns shopping list
3. Health Agent - Receives nutritional info (work in progress)
"""

import sys
import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

# Add agents directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

# Import agents
from agents.recipe_agent import recipe_agent, RecipeAgentRunner
from agents.shopping_budget_agent import ShoppingBudgetAgent
from agents.preference_agent import preference_agent, PreferenceAgentRunner
from agents.health_agent import HealthAgent

app = FastAPI(
    title="Meal Planner Agent API",
    description="API for Recipe, Shopping & Budget, and Health Agents",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent runners
recipe_runner = RecipeAgentRunner(recipe_agent)
shopping_agent = ShoppingBudgetAgent(currency="INR")
preference_runner = PreferenceAgentRunner(preference_agent)
health_agent = HealthAgent()


# =========================
#   REQUEST/RESPONSE MODELS
# =========================

class PreferenceRequest(BaseModel):
    """Request model for recipe preferences"""
    dietary_restrictions: Optional[List[str]] = []
    cuisine_preferences: Optional[List[str]] = []
    meal_type: str = "dinner"
    servings: int = 4
    budget_per_meal: Optional[float] = None


class RecipeResponse(BaseModel):
    """Response model for recipe data"""
    recipe_name: str
    description: str
    ingredients: Dict[str, List[str]]
    instructions: List[Dict[str, Any]]
    nutritional_information: Dict[str, Any]


class IngredientsRequest(BaseModel):
    """Request model for shopping & budget agent"""
    recipe_name: str
    ingredients: Dict[str, List[str]]
    budget: Optional[float] = 500.0
    stores: Optional[List[str]] = ["Amazon", "Flipkart", "LocalStore"]


class NutritionRequest(BaseModel):
    """Request model for health agent"""
    recipe_name: str
    nutritional_information: Dict[str, Any]


class UserPreferenceInput(BaseModel):
    """Request model for user preference description"""
    user_description: str
    user_id: Optional[str] = "user_001"


class UserProfileResponse(BaseModel):
    """Response model for user health profile"""
    diet_type: str
    daily_calorie_target: int
    protein_target_g: int
    carb_target_g: int
    fat_target_g: int
    meals_per_day: int
    allergies: List[str]
    dislikes: List[str]
    health_notes: List[str]


# =========================
#   PREFERENCE AGENT ENDPOINTS
# =========================

@app.post("/preference")
async def create_user_profile(preference_input: UserPreferenceInput):
    """
    Create user profile from natural language description using Preference Agent
    
    Args:
        preference_input: User's natural language description and user_id
    
    Returns:
        Structured user health profile
    """
    try:
        # Build prompt for Preference Agent
        prompt = f"""
The user will describe their diet, lifestyle and health precautions.

User description:
\"\"\"{preference_input.user_description}\"\"\"
"""
        
        # Run Preference Agent
        result = await preference_runner.runner.run_debug(prompt)
        profile_data = preference_runner._parse_output(result)
        
        if "error" in profile_data:
            raise HTTPException(
                status_code=500,
                detail=f"Preference Agent Error: {profile_data.get('error')}"
            )
        
        # Store the profile
        preference_runner._profiles[preference_input.user_id] = profile_data
        
        return {
            "success": True,
            "data": {
                "user_id": preference_input.user_id,
                "profile": profile_data
            },
            "message": "User profile created successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating user profile: {str(e)}"
        )


@app.get("/preference/{user_id}")
async def get_user_profile(user_id: str):
    """
    Get stored user profile by user_id
    
    Args:
        user_id: User identifier
    
    Returns:
        User health profile
    """
    try:
        profile = preference_runner.get_profile(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "profile": profile
            },
            "message": "User profile retrieved successfully"
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user profile: {str(e)}"
        )


@app.post("/preference-to-recipe")
async def preference_to_recipe_workflow(preference_input: UserPreferenceInput):
    """
    Complete workflow: Preference Agent → Recipe Agent
    
    Args:
        preference_input: User's natural language description
    
    Returns:
        User profile and recipe based on preferences
    """
    try:
        # Step 1: Create user profile using Preference Agent
        prompt = f"""
The user will describe their diet, lifestyle and health precautions.

User description:
\"\"\"{preference_input.user_description}\"\"\"
"""
        
        result = await preference_runner.runner.run_debug(prompt)
        profile_data = preference_runner._parse_output(result)
        
        if "error" in profile_data:
            raise HTTPException(
                status_code=500,
                detail=f"Preference Agent Error: {profile_data.get('error')}"
            )
        
        # Store profile
        preference_runner._profiles[preference_input.user_id] = profile_data
        
        # Step 2: Convert profile to recipe preferences
        recipe_preferences = {
            "dietary_restrictions": [profile_data.get("diet_type", "vegetarian")],
            "cuisine_preferences": [],  # Can be enhanced later
            "meal_type": "lunch",
            "servings": profile_data.get("meals_per_day", 3),
            "budget_per_meal": None
        }
        
        # Add dietary restrictions from health notes
        health_notes = profile_data.get("health_notes", [])
        if "low_sugar" in health_notes:
            recipe_preferences["dietary_restrictions"].append("low sugar")
        if "low_sodium" in health_notes:
            recipe_preferences["dietary_restrictions"].append("low sodium")
        if "high_protein" in health_notes:
            recipe_preferences["dietary_restrictions"].append("high protein")
        if "low_carb" in health_notes:
            recipe_preferences["dietary_restrictions"].append("low carb")
        
        # Step 3: Fetch recipe using Recipe Agent
        recipe_data = await recipe_runner.fetch_recipe(recipe_preferences)
        
        if "error" in recipe_data:
            raise HTTPException(
                status_code=500,
                detail=f"Recipe Agent Error: {recipe_data.get('error')}"
            )
        
        return {
            "success": True,
            "data": {
                "user_id": preference_input.user_id,
                "user_profile": profile_data,
                "recipe": recipe_data
            },
            "message": "Profile created and recipe fetched successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in preference-to-recipe workflow: {str(e)}"
        )


# =========================
#   RECIPE AGENT ENDPOINTS
# =========================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Meal Planner Agent API",
        "version": "2.0.0",
        "description": "Complete multi-agent meal planning system",
        "endpoints": {
            "preference_agent": {
                "POST /preference": "Create user profile from natural language",
                "GET /preference/{user_id}": "Get stored user profile",
                "POST /preference-to-recipe": "Preference → Recipe workflow"
            },
            "recipe_agent": {
                "POST /recipe": "Get recipe from preferences",
                "GET /recipe/example": "Get example recipe"
            },
            "shopping_agent": {
                "POST /shopping": "Generate shopping list with pricing"
            },
            "health_agent": {
                "POST /health": "Analyze nutritional information",
                "POST /recipe-to-health": "Recipe → Health workflow"
            },
            "complete_workflow": {
                "POST /complete-meal-plan": "🌟 FULL WORKFLOW: Preference → Recipe → Shopping + Health",
                "POST /meal-plan": "Recipe → Shopping + Nutrition workflow"
            }
        }
    }


@app.post("/recipe")
async def get_recipe(preferences: PreferenceRequest):
    """
    Get recipe based on preferences
    
    Args:
        preferences: User dietary preferences and requirements
    
    Returns:
        Recipe with ingredients and nutritional information
    """
    try:
        # Convert Pydantic model to dict
        prefs_dict = preferences.model_dump()
        
        # Fetch recipe using the agent
        recipe_data = await recipe_runner.fetch_recipe(prefs_dict)
        
        # Check for errors in the response
        if "error" in recipe_data:
            raise HTTPException(
                status_code=500,
                detail=f"Recipe Agent Error: {recipe_data.get('error')}"
            )
        
        return {
            "success": True,
            "data": recipe_data,
            "message": "Recipe fetched successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching recipe: {str(e)}"
        )


@app.get("/recipe/example")
async def get_recipe_example():
    """Get an example recipe (for testing)"""
    try:
        example_prefs = {
            "dietary_restrictions": ["vegetarian"],
            "cuisine_preferences": ["Italian"],
            "meal_type": "dinner",
            "servings": 4,
            "budget_per_meal": 25
        }
        
        recipe_data = await recipe_runner.fetch_recipe(example_prefs)
        
        return {
            "success": True,
            "data": recipe_data,
            "message": "Example recipe fetched successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching example recipe: {str(e)}"
        )


# =========================
#   SHOPPING & BUDGET AGENT ENDPOINTS
# =========================

@app.post("/shopping")
async def get_shopping_list(ingredients_data: IngredientsRequest):
    """
    Generate shopping list from recipe ingredients with pricing and budget analysis
    
    Args:
        ingredients_data: Recipe name, ingredients, budget, and stores
    
    Returns:
        Shopping list with prices, total cost, and budget recommendations
    """
    try:
        # Prepare recipe data for shopping agent
        recipe_data = {
            "recipe_name": ingredients_data.recipe_name,
            "ingredients": ingredients_data.ingredients
        }
        
        # Process ingredients and get shopping plan
        shopping_plan = shopping_agent.process_recipe_ingredients(
            recipe_data=recipe_data,
            stores=ingredients_data.stores,
            budget=ingredients_data.budget
        )
        
        return {
            "success": True,
            "data": shopping_plan,
            "message": "Shopping list generated successfully with pricing and budget analysis"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating shopping list: {str(e)}"
        )


# =========================
#   HEALTH AGENT ENDPOINTS
# =========================

@app.post("/health")
async def analyze_nutrition(nutrition_data: NutritionRequest):
    """
    Analyze nutritional information from recipe against user profile
    
    Args:
        nutrition_data: Recipe name and nutritional information
    
    Returns:
        Nutritional analysis and health recommendations
    """
    try:
        # Extract nutritional data
        nutrition_info = nutrition_data.nutritional_information
        
        # Parse nutritional information
        analysis = {
            "recipe_name": nutrition_data.recipe_name,
            "nutritional_info": nutrition_info,
            "health_evaluation": "Nutritional analysis complete"
        }
        
        # Extract macros if available
        if "macros" in nutrition_info:
            macros = nutrition_info["macros"]
            analysis["macros_summary"] = {
                "protein": macros.get("protein", "N/A"),
                "carbohydrates": macros.get("carbohydrates", "N/A"),
                "fat": macros.get("fat", "N/A")
            }
        
        return {
            "success": True,
            "data": analysis,
            "message": "Nutritional analysis completed"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing nutrition: {str(e)}"
        )


@app.post("/recipe-to-health")
async def recipe_to_health_workflow(recipe_name: str, user_id: str = "user_001"):
    """
    Workflow: Analyze recipe nutrition against user health profile
    
    Args:
        recipe_name: Name of the recipe to analyze
        user_id: User identifier for health profile lookup
    
    Returns:
        Health analysis comparing recipe nutrition to user goals
    """
    try:
        # Get user profile
        try:
            profile = preference_runner.get_profile(user_id)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"User profile not found for user_id: {user_id}"
            )
        
        # For now, return profile-based recommendations
        # TODO: Integrate with actual recipe data
        
        recommendations = []
        health_notes = profile.get("health_notes", [])
        
        if "low_sugar" in health_notes:
            recommendations.append("Monitor sugar content in recipes")
        if "low_sodium" in health_notes:
            recommendations.append("Choose low-sodium ingredients")
        if "high_protein" in health_notes:
            recommendations.append(f"Target protein: {profile.get('protein_target_g', 100)}g per day")
        if "low_carb" in health_notes:
            recommendations.append(f"Limit carbs to: {profile.get('carb_target_g', 230)}g per day")
        
        return {
            "success": True,
            "data": {
                "recipe_name": recipe_name,
                "user_profile": profile,
                "daily_targets": {
                    "calories": profile.get("daily_calorie_target", 2200),
                    "protein_g": profile.get("protein_target_g", 100),
                    "carbs_g": profile.get("carb_target_g", 230),
                    "fat_g": profile.get("fat_target_g", 70)
                },
                "recommendations": recommendations
            },
            "message": "Health analysis completed"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in recipe-to-health workflow: {str(e)}"
        )


# =========================
#   COMBINED WORKFLOW ENDPOINT
# =========================

@app.post("/complete-meal-plan")
async def complete_meal_plan_workflow(preference_input: UserPreferenceInput):
    """
    COMPLETE WORKFLOW: Preference Agent → Recipe Agent → Shopping & Budget Agent + Health Agent
    
    This is the main endpoint that orchestrates all agents:
    1. Preference Agent: Parse user description into structured profile
    2. Recipe Agent: Fetch recipe based on user preferences
    3. Shopping & Budget Agent: Generate shopping list with pricing
    4. Health Agent: Analyze nutrition against user goals
    
    Args:
        preference_input: User's natural language description and user_id
    
    Returns:
        Complete meal plan with profile, recipe, shopping list, and health analysis
    """
    try:
        # ==========================================
        # STEP 1: PREFERENCE AGENT - Create Profile
        # ==========================================
        prompt = f"""
The user will describe their diet, lifestyle and health precautions.

User description:
\"\"\"{preference_input.user_description}\"\"\"
"""
        
        result = await preference_runner.runner.run_debug(prompt)
        profile_data = preference_runner._parse_output(result)
        
        if "error" in profile_data:
            raise HTTPException(
                status_code=500,
                detail=f"Preference Agent Error: {profile_data.get('error')}"
            )
        
        # Store profile
        preference_runner._profiles[preference_input.user_id] = profile_data
        
        # ==========================================
        # STEP 2: RECIPE AGENT - Fetch Recipe
        # ==========================================
        # Convert profile to recipe preferences
        recipe_preferences = {
            "dietary_restrictions": [profile_data.get("diet_type", "vegetarian")],
            "cuisine_preferences": [],
            "meal_type": "lunch",
            "servings": profile_data.get("meals_per_day", 3),
            "budget_per_meal": None
        }
        
        # Add health-based dietary restrictions
        health_notes = profile_data.get("health_notes", [])
        if "low_sugar" in health_notes:
            recipe_preferences["dietary_restrictions"].append("low sugar")
        if "low_sodium" in health_notes:
            recipe_preferences["dietary_restrictions"].append("low sodium")
        if "high_protein" in health_notes:
            recipe_preferences["dietary_restrictions"].append("high protein")
        if "low_carb" in health_notes:
            recipe_preferences["dietary_restrictions"].append("low carb")
        
        # Fetch recipe
        recipe_data = await recipe_runner.fetch_recipe(recipe_preferences)
        
        if "error" in recipe_data:
            raise HTTPException(
                status_code=500,
                detail=f"Recipe Agent Error: {recipe_data.get('error')}"
            )
        
        # ==========================================
        # STEP 3: SHOPPING & BUDGET AGENT
        # ==========================================
        budget = 500.0  # Default budget
        shopping_plan = shopping_agent.process_recipe_ingredients(
            recipe_data=recipe_data,
            stores=["Amazon", "Flipkart", "LocalStore"],
            budget=budget
        )
        
        # ==========================================
        # STEP 4: HEALTH AGENT - Analyze Nutrition
        # ==========================================
        nutrition_info = recipe_data.get("nutritional_information", {})
        
        # Generate health recommendations
        recommendations = []
        if "low_sugar" in health_notes:
            recommendations.append("Monitor sugar content - aim for natural sugars from fruits")
        if "low_sodium" in health_notes:
            recommendations.append("Limit sodium to <2300mg per day")
        if "high_protein" in health_notes:
            recommendations.append(f"Target {profile_data.get('protein_target_g', 100)}g protein daily")
        if "low_carb" in health_notes:
            recommendations.append(f"Limit carbs to {profile_data.get('carb_target_g', 230)}g daily")
        
        # Add allergy warnings
        allergies = profile_data.get("allergies", [])
        if allergies:
            recommendations.append(f"⚠️ ALLERGIES: Avoid {', '.join(allergies)}")
        
        health_analysis = {
            "daily_targets": {
                "calories": profile_data.get("daily_calorie_target", 2200),
                "protein_g": profile_data.get("protein_target_g", 100),
                "carbs_g": profile_data.get("carb_target_g", 230),
                "fat_g": profile_data.get("fat_target_g", 70)
            },
            "recipe_nutrition": nutrition_info,
            "recommendations": recommendations,
            "allergies": allergies,
            "dislikes": profile_data.get("dislikes", [])
        }
        
        # ==========================================
        # RETURN COMPLETE MEAL PLAN
        # ==========================================
        return {
            "success": True,
            "data": {
                "user_id": preference_input.user_id,
                "user_profile": profile_data,
                "recipe": recipe_data,
                "shopping_plan": shopping_plan,
                "health_analysis": health_analysis
            },
            "summary": {
                "recipe_name": recipe_data.get("recipe_name", "Unknown"),
                "total_cost": f"₹{shopping_plan.get('estimated_total_cost', 0):.2f}",
                "within_budget": shopping_plan.get("within_budget", True),
                "health_status": "Profile-based recommendations provided",
                "key_recommendations": recommendations[:3] if recommendations else []
            },
            "message": "Complete meal plan created successfully with all agent integrations"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in complete meal plan workflow: {str(e)}"
        )


@app.post("/meal-plan")
async def create_meal_plan(preferences: PreferenceRequest):
    """
    Complete workflow: Get recipe and forward data to other agents
    
    Args:
        preferences: User dietary preferences and requirements
    
    Returns:
        Complete meal plan with recipe, shopping list, and health analysis
    """
    try:
        # Step 1: Get recipe from Recipe Agent
        prefs_dict = preferences.model_dump()
        recipe_data = await recipe_runner.fetch_recipe(prefs_dict)
        
        if "error" in recipe_data:
            raise HTTPException(
                status_code=500,
                detail=f"Recipe Agent Error: {recipe_data.get('error')}"
            )
        
        # Step 2: Extract ingredients for Shopping & Budget Agent
        ingredients_for_shopping = recipe_runner.get_ingredients_for_shopping(recipe_data)
        
        # Step 3: Generate shopping list with pricing
        budget = prefs_dict.get("budget_per_meal", 500.0)
        shopping_plan = shopping_agent.process_recipe_ingredients(
            recipe_data=recipe_data,
            stores=["Amazon", "Flipkart", "LocalStore"],
            budget=budget
        )
        
        # Step 4: Extract nutrition for Health Agent
        nutrition_for_health = recipe_runner.get_nutrition_for_health(recipe_data)
        
        # Step 5: Return combined response
        return {
            "success": True,
            "data": {
                "recipe": recipe_data,
                "shopping_plan": shopping_plan,
                "nutrition_for_health": nutrition_for_health
            },
            "message": "Complete meal plan created successfully",
            "summary": {
                "recipe_name": recipe_data.get("recipe_name", "Unknown"),
                "total_cost": shopping_plan.get("estimated_total_cost", 0),
                "currency": shopping_plan.get("currency", "INR"),
                "within_budget": shopping_plan.get("within_budget", True),
                "budget_status": f"₹{shopping_plan.get('estimated_total_cost', 0):.2f} / ₹{budget:.2f}"
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating meal plan: {str(e)}"
        )


# =========================
#   SERVER STARTUP
# =========================

if __name__ == "__main__":
    print("🚀 Starting Meal Planner Agent API (v2.0)...")
    print("\n" + "="*60)
    print("📋 AVAILABLE ENDPOINTS:")
    print("="*60)
    print("\n🔹 PREFERENCE AGENT:")
    print("   - POST /preference (Create user profile)")
    print("   - GET  /preference/{user_id} (Get stored profile)")
    print("   - POST /preference-to-recipe (Preference → Recipe)")
    print("\n🔹 RECIPE AGENT:")
    print("   - POST /recipe (Get recipe from preferences)")
    print("   - GET  /recipe/example (Get example recipe)")
    print("\n🔹 SHOPPING & BUDGET AGENT:")
    print("   - POST /shopping (Generate shopping list with pricing)")
    print("\n🔹 HEALTH AGENT:")
    print("   - POST /health (Analyze nutrition)")
    print("   - POST /recipe-to-health (Recipe → Health analysis)")
    print("\n🌟 COMPLETE WORKFLOWS:")
    print("   - POST /complete-meal-plan (🎯 FULL: Preference → Recipe → Shopping + Health)")
    print("   - POST /meal-plan (Recipe → Shopping + Nutrition)")
    print("\n" + "="*60)
    print("🌐 Server running at: http://localhost:8000")
    print("📚 API Docs at: http://localhost:8000/docs")
    print("📊 Health check: http://localhost:8000/")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)