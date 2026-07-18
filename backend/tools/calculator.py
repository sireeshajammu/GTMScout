from typing import Dict, Union
import math

def calculate_cost_per_lead(spend: float, leads: int) -> Dict:
    """
    Calculate cost per lead.
    
    Args:
        spend: Total amount spent (currency amount)
        leads: Number of leads generated
    
    Returns:
        Dictionary with calculated CPL and details.
    """
    
    if not spend or spend <= 0:
        return {
            "success": False,
            "error": "Spend must be greater than 0"
        }
    
    if not leads or leads <= 0:
        return {
            "success": False,
            "error": "Leads must be greater than 0"
        }
    
    try:
        cpl = spend / leads
        return {
            "success": True,
            "spend": spend,
            "leads": leads,
            "cost_per_lead": round(cpl, 2),
            "metric": "CPL (Cost Per Lead)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Calculation failed: {str(e)}"
        }


def calculate_percentage_growth(start_value: float, end_value: float) -> Dict:
    """
    Calculate percentage growth between two values.
    
    Args:
        start_value: Initial value (e.g., 2015 GDP)
        end_value: Final value (e.g., 2025 GDP)
    
    Returns:
        Dictionary with growth percentage and details.
    """
    
    if start_value is None or end_value is None:
        return {
            "success": False,
            "error": "Both start and end values are required"
        }
    
    if start_value == 0:
        return {
            "success": False,
            "error": "Start value cannot be 0 (cannot calculate percentage from 0)"
        }
    
    try:
        growth = ((end_value - start_value) / abs(start_value)) * 100
        return {
            "success": True,
            "start_value": start_value,
            "end_value": end_value,
            "percentage_growth": round(growth, 2),
            "direction": "growth" if growth > 0 else "decline"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Calculation failed: {str(e)}"
        }


def compare_two_metrics(value1: float, value2: float, label1: str, label2: str) -> Dict:
    """
    Compare two metrics and determine which is larger and by how much.
    
    Args:
        value1: First value
        value2: Second value
        label1: Label for first value (e.g., "Japan CPL")
        label2: Label for second value (e.g., "USA CPL")
    
    Returns:
        Dictionary with comparison results.
    """
    
    if value1 is None or value2 is None:
        return {
            "success": False,
            "error": "Both values are required for comparison"
        }
    
    try:
        if value1 == value2:
            return {
                "success": True,
                "label1": label1,
                "value1": value1,
                "label2": label2,
                "value2": value2,
                "comparison": "equal",
                "difference": 0,
                "winner": "tie"
            }
        
        winner = label1 if value1 > value2 else label2
        loser = label2 if value1 > value2 else label1
        larger_value = max(value1, value2)
        smaller_value = min(value1, value2)
        
        difference = larger_value - smaller_value
        percentage_diff = ((larger_value - smaller_value) / smaller_value) * 100
        
        return {
            "success": True,
            "label1": label1,
            "value1": value1,
            "label2": label2,
            "value2": value2,
            "comparison": f"{winner} > {loser}",
            "winner": winner,
            "loser": loser,
            "absolute_difference": round(difference, 2),
            "percentage_difference": round(percentage_diff, 2)
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Comparison failed: {str(e)}"
        }


def calculate_budget_allocation(total_budget: float, percentages: Dict[str, float]) -> Dict:
    """
    Allocate a budget across channels based on percentages.
    
    Args:
        total_budget: Total budget to allocate
        percentages: Dictionary of channel names to percentage allocations
                    (e.g., {"TikTok": 40, "LinkedIn": 30, "Instagram": 30})
    
    Returns:
        Dictionary with budget allocation for each channel.
    """
    
    if not total_budget or total_budget <= 0:
        return {
            "success": False,
            "error": "Total budget must be greater than 0"
        }
    
    if not percentages or len(percentages) == 0:
        return {
            "success": False,
            "error": "At least one channel must be specified"
        }
    
    try:
        # Check that percentages sum to 100
        total_percent = sum(percentages.values())
        if abs(total_percent - 100) > 0.1:  # Allow for small floating point errors
            return {
                "success": False,
                "error": f"Percentages must sum to 100. Current total: {total_percent}%"
            }
        
        allocation = {
            "success": True,
            "total_budget": total_budget,
            "allocations": {}
        }
        
        for channel, percentage in percentages.items():
            amount = (total_budget * percentage) / 100
            allocation["allocations"][channel] = {
                "percentage": percentage,
                "amount": round(amount, 2)
            }
        
        return allocation
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Budget allocation failed: {str(e)}"
        }


def calculate_internet_penetration_gap(country1_penetration: float, country2_penetration: float, country1_name: str, country2_name: str) -> Dict:
    """
    Calculate the gap in internet penetration between two countries.
    
    Args:
        country1_penetration: Internet users % in country 1
        country2_penetration: Internet users % in country 2
        country1_name: Name of country 1
        country2_name: Name of country 2
    
    Returns:
        Dictionary with penetration gap analysis.
    """
    
    if country1_penetration is None or country2_penetration is None:
        return {
            "success": False,
            "error": "Both penetration values are required"
        }
    
    try:
        gap = abs(country1_penetration - country2_penetration)
        more_connected = country1_name if country1_penetration > country2_penetration else country2_name
        higher_penetration = max(country1_penetration, country2_penetration)
        lower_penetration = min(country1_penetration, country2_penetration)
        
        return {
            "success": True,
            f"{country1_name}_penetration": country1_penetration,
            f"{country2_name}_penetration": country2_penetration,
            "gap_percentage_points": round(gap, 2),
            "more_connected_country": more_connected,
            "implication": f"{more_connected} has {round(gap, 1)} percentage points higher internet penetration than {country1_name if more_connected == country2_name else country2_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Penetration calculation failed: {str(e)}"
        }