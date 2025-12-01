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
