"""
Meal Planner Orchestrator using Sequential Agent Pattern

This orchestrator chains all agents in a sequential workflow:
Preference Agent → Recipe Agent → Shopping Agent
"""

import asyncio
from typing import Dict, Any, Optional
from google.adk.agents import SequentialAgent
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# Import individual agents
from agents.preference_agent import preference_agent
from agents.recipe_agent import recipe_agent
from agents.shopping_budget_agent import shopping_agent

# =========================
#   ORCHESTRATOR SETUP
# =========================

# Shared services
APP_NAME = "meal_planner_orchestrator"
memory_service = InMemoryMemoryService()
session_service = InMemorySessionService()

# Create orchestrator agent that coordinates the workflow
# SequentialAgent executes sub-agents in order automatically
meal_planner_orchestrator = SequentialAgent(
    name="MealPlannerOrchestrator",
    sub_agents=[
        preference_agent,   
        recipe_agent,       
        shopping_agent,    
    ],
    description="Executes meal planning workflow in sequence: Preference → Recipe → Shopping",
)

# Create runner with memory and session services
orchestrator_runner = Runner(
    agent=meal_planner_orchestrator,
    app_name=APP_NAME,
    session_service=session_service,
    memory_service=memory_service
)

# =========================
#   HELPER FUNCTIONS
# =========================

async def run_meal_planner_workflow(
    user_description: str,
    user_id: str = "default_user",
    budget: float = 500.0
) -> Dict[str, Any]:
    """
    Run the complete meal planning workflow using Sequential Agent
    
    Args:
        user_description: Natural language description of user's dietary needs
        user_id: User identifier
        budget: Budget for shopping
    
    Returns:
        Complete meal plan with profile, recipe, shopping list, and health analysis
    """
    try:
        # Create or reuse session
        session_id = f"meal_plan_{user_id}"
        try:
            await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
        except Exception as e:
            if "already exists" in str(e):
                print(f"ℹ️  Using existing session: {session_id}")
            else:
                raise
        
        # Create input message
        from google.genai.types import Content, Part
        user_message = Content(
            parts=[Part(text=f"""
User's dietary preferences and health information:

{user_description}

Budget: ₹{budget}

Please create a complete meal plan including:
1. User health profile
2. Suitable recipe
3. Shopping list with prices
4. Health and nutrition analysis
""")],
            role="user"
        )
        
        # Run the orchestrator
        print("🚀 Starting Sequential Agent workflow...")
        final_response = None
        async for event in orchestrator_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
                print("✓ Workflow completed")
        
        # Save session to memory
        completed_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
        await memory_service.add_session_to_memory(completed_session)
        print("✓ Session saved to memory")
        
        return {
            "success": True,
            "user_id": user_id,
            "session_id": session_id,
            "response": final_response,
            "message": "Complete meal plan generated successfully"
        }
    
    except Exception as e:
        print(f"❌ Error in workflow: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate meal plan"
        }


# =========================
#   EXAMPLE USAGE
# =========================

async def example_usage():
    """Example of using the orchestrator"""
    user_input = """
I'm vegetarian and need 2200 calories per day with high protein (120g). 
I want to gain muscle, so I need healthy fats (60g). I eat 3 meals a day. 
I'm allergic to peanuts and don't like mushrooms. 
I have diabetes so I need low sugar meals.
"""
    
    result = await run_meal_planner_workflow(
        user_description=user_input,
        user_id="test_user_001",
        budget=500.0
    )
    
    print("MEAL PLAN RESULT:")
    print(result.get("response", result.get("error")))

if __name__ == "__main__":
    print("Running example workflow...")
    asyncio.run(example_usage())
