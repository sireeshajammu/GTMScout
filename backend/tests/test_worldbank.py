from tools.worldbank import get_country_data
import json

# Test with Japan
result = get_country_data("Japan")
print(json.dumps(result, indent=2))

# Test with USA
print("\n---\n")
result = get_country_data("USA")
print(json.dumps(result, indent=2))

# Test with a country not in our list
print("\n---\n")
result = get_country_data("Random country")
print(json.dumps(result, indent=2))