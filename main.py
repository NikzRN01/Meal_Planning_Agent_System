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
        shopping_plan = shopping_agent.process(
            recipe=recipe_data,
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
            "message": "Complete meal plan generated"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in complete meal plan workflow: {str(e)}"
        )

# =========================
#   SERVER STARTUP
# =========================

if __name__ == "__main__":
    print("🚀 Starting Meal Planner Agent API (v2.0)...")
    print("🌐 Server running at: http://localhost:8000")
    print("📚 API Docs at: http://localhost:8000/docs")
    print("📊 Health check: http://localhost:8000/\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)