"""
Test the Sequential Agent Orchestrator

This script demonstrates the new Sequential Agent workflow
for complete meal planning.
"""

import asyncio
from orchestrator import run_meal_planner_workflow


async def test_sequential_workflow():
    """Test the Sequential Agent orchestrator"""
    print("TESTING SEQUENTIAL AGENT WORKFLOW")
    
    # Get user input
    print("Choose test mode:")
    print("1. Interactive (you provide preferences)")
    print("2. Automated (use default example)")
    
    choice = input("\nEnter choice (1 or 2, default=2): ").strip()
    
    if choice == "1":
        print("\nEnter your dietary preferences and health information:")
        user_input = input("> ").strip()
        if not user_input:
            print("No input provided. Using default example...")
            user_input = None
    else:
        user_input = None
    
    # Default example
    if not user_input:
        user_input = """
I'm vegetarian and need 2200 calories per day with high protein (120g). 
I want to gain muscle, so I need healthy fats (60g). I eat 3 meals a day. 
I'm allergic to peanuts and don't like mushrooms. 
I have diabetes so I need low sugar meals.
"""
        print("\nUsing default example:")
        print(user_input)
    
    # Run the workflow
    print("🚀 Starting Sequential Agent Workflow...")
    
    result = await run_meal_planner_workflow(
        user_description=user_input,
        user_id="test_user_001",
        budget=500.0
    )
    
    # Display results
    print(" WORKFLOW RESULT")
    
    if result.get("success"):
        print("MEAL PLAN:")
        print(result.get("response", "No response available"))
    else:
        print("\n❌ Status: FAILED")
        print(f"Error: {result.get('error')}")
        print(f"Message: {result.get('message')}")


async def test_memory_recall():
    """Test memory recall from previous sessions"""
    print("🧠 TESTING MEMORY RECALL")
    
    user_input = "What did I tell you about my dietary preferences before?"
    
    print("Query:", user_input)
    print("\n🔍 Searching memories...")
    
    # Use a different user_id to avoid session conflicts
    result = await run_meal_planner_workflow(
        user_description=user_input,
        user_id="test_user_002",  # Different user to avoid session conflicts
        budget=500.0
    )
    
    if result.get("success"):
        print("\n✓ Memory recall successful")
        print("\nResponse:")
        print(result.get("response"))
    else:
        print("\n❌ Memory recall failed")
        print(f"Error: {result.get('error')}")


async def main():
    """Run all tests"""
    try:
        # Test 1: Complete workflow
        await test_sequential_workflow()
        
        # Test 2: Memory recall (optional)
        print("\n\nWould you like to test memory recall? (y/n): ", end="")
        test_memory = input().strip().lower()
        
        if test_memory == 'y':
            await test_memory_recall()
        
    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())