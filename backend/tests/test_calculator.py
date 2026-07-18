from tools.calculator import (
    calculate_cost_per_lead,
    calculate_percentage_growth,
    compare_two_metrics,
    calculate_budget_allocation,
    calculate_internet_penetration_gap
)
import json

print("Test 1: Cost Per Lead")
result = calculate_cost_per_lead(spend=10000, leads=100)
print(json.dumps(result, indent=2))

print("\n---\n")

print("Test 2: Percentage Growth (GDP)")
result = calculate_percentage_growth(start_value=35000, end_value=40000)
print(json.dumps(result, indent=2))

print("\n---\n")

print("Test 3: Compare two CPLs")
result = compare_two_metrics(value1=100, value2=150, label1="Japan CPL", label2="USA CPL")
print(json.dumps(result, indent=2))

print("\n---\n")

print("Test 4: Budget Allocation")
result = calculate_budget_allocation(
    total_budget=20000,
    percentages={"TikTok": 40, "LinkedIn": 35, "Instagram": 25}
)
print(json.dumps(result, indent=2))

print("\n---\n")

print("Test 5: Internet Penetration Gap")
result = calculate_internet_penetration_gap(
    country1_penetration=88.5,
    country2_penetration=92.1,
    country1_name="Japan",
    country2_name="USA"
)
print(json.dumps(result, indent=2))

print("\n---\n")

print("Test 6: Error handling - invalid percentages")
result = calculate_budget_allocation(
    total_budget=20000,
    percentages={"TikTok": 50, "LinkedIn": 30}  # Only 80%, should fail
)
print(json.dumps(result, indent=2))