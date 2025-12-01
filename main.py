from core.orchestrator import MealPlanningOrchestrator

def main():
    orchestrator = MealPlanningOrchestrator()
    week_plan, health_report, estimated_cost = orchestrator.run_weekly_planning()

    print("=== Weekly Plan Overview ===")
    for day in week_plan.days:
        meal_names = ", ".join(m.name for m in day.meals)
        print(f"{day.day_name}: {meal_names}")

    print("\n=== Health Report ===")
    for r in health_report.daily_reports:
        print(
            f"{r.day_name}: "
            f"{r.total_calories} kcal "
            f"(Δ {r.calorie_delta}), "
            f"P {r.total_protein_g}g (Δ {r.protein_delta}), "
            f"C {r.total_carbs_g}g (Δ {r.carb_delta}), "
            f"F {r.total_fat_g}g (Δ {r.fat_delta}) "
            f"Score={r.score}, Flags={r.flags}"
        )

    print(f"\nAverage health score: {health_report.average_score}")
    print(f"Global flags: {health_report.global_flags}")
    print(f"Estimated weekly grocery cost: {estimated_cost}")

if __name__ == "__main__":
    main()


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
from agents.shopping_budget_agent import ShoppingBudgetAgentLive

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
shopping_agent = ShoppingBudgetAgentLive(currency="INR")


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


# =========================
#   RECIPE AGENT ENDPOINTS
# =========================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Meal Planner Agent API",
        "version": "1.0.0",
        "endpoints": {
            "recipe": "/recipe (POST)",
            "shopping": "/shopping (POST)",
            "health": "/health (POST - coming soon)"
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
    Analyze nutritional information (Health Agent - work in progress)
    
    Args:
        nutrition_data: Recipe name and nutritional information
    
    Returns:
        Nutritional analysis and health recommendations
    """
    try:
        # TODO: Integrate with health_agent when ready
        
        return {
            "success": True,
            "data": {
                "recipe_name": nutrition_data.recipe_name,
                "nutritional_information": nutrition_data.nutritional_information,
                "analysis": "Health Agent integration pending"
            },
            "message": "Nutritional information received. Analysis in progress."
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing nutrition: {str(e)}"
        )


# =========================
#   COMBINED WORKFLOW ENDPOINT
# =========================

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
    print("🚀 Starting Meal Planner Agent API...")
    print("📋 Available endpoints:")
    print("   - GET  / (Health check)")
    print("   - POST /recipe (Get recipe from preferences)")
    print("   - GET  /recipe/example (Get example recipe)")
    print("   - POST /shopping (Generate shopping list)")
    print("   - POST /health (Analyze nutrition)")
    print("   - POST /meal-plan (Complete workflow)")
    print("\n🌐 Server running at: http://localhost:8000")
    print("📚 API Docs at: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)