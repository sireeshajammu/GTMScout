from pytrends.request import TrendReq
from typing import Dict, List, Optional
import time

def search_platform_trends(platform: str, country_code: str = "US", timeframe: str = "today 1-m", retries: int = 3) -> Dict:
    """
    Search for platform popularity/interest using Google Trends.
    
    Args:
        platform: The platform name (e.g., "TikTok", "LinkedIn", "Instagram")
        country_code: Two-letter country code (e.g., "JP" for Japan, "US" for USA)
        timeframe: Time period for trends (default: last month)
        retries: Number of times to retry on rate limit
    
    Returns:
        A dictionary with trend data or error information.
    """
    
    if not platform or not platform.strip():
        return {
            "success": False,
            "error": "Platform name cannot be empty",
            "platform": platform,
            "country": country_code
        }
    
    for attempt in range(retries):
        try:
            print(f"DEBUG: Fetching trends for '{platform}' in {country_code} (attempt {attempt + 1})")
            
            # Wait before request if this is a retry
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                print(f"DEBUG: Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            
            # Create a TrendReq object
            pytrends = TrendReq(hl='en-US', tz=360)
            
            # Build payload with the platform name
            pytrends.build_payload([platform], cat=0, timeframe=timeframe, geo=country_code)
            
            # Get interest over time
            interest_over_time = pytrends.interest_over_time()
            
            if interest_over_time.empty:
                return {
                    "success": False,
                    "error": f"No trend data found for '{platform}' in {country_code}",
                    "platform": platform,
                    "country": country_code
                }
            
            # Get current interest level (most recent data point)
            latest_interest = int(interest_over_time[platform].iloc[-1])
            average_interest = int(interest_over_time[platform].mean())
            
            # Get related queries
            related_queries = pytrends.related_queries()
            top_queries = related_queries.get(platform, {}).get("top", [])
            
            top_related = []
            if not top_queries.empty:
                top_related = top_queries.head(3)["query"].tolist()
            
            return {
                "success": True,
                "platform": platform,
                "country": country_code,
                "current_interest": latest_interest,
                "average_interest": average_interest,
                "timeframe": timeframe,
                "top_related_queries": top_related,
                "source": "Google Trends",
                "note": "Interest level is on a scale of 0-100, where 100 is peak popularity"
            }
        
        except Exception as e:
            error_msg = str(e)
            
            # If it's a rate limit error and we have retries left, try again
            if "429" in error_msg and attempt < retries - 1:
                print(f"DEBUG: Rate limited, will retry...")
                continue
            
            # Otherwise, return the error
            return {
                "success": False,
                "error": f"Trends search failed: {error_msg}",
                "platform": platform,
                "country": country_code,
                "attempt": attempt + 1
            }
    
    return {
        "success": False,
        "error": f"Failed after {retries} attempts. Google Trends is rate-limited.",
        "platform": platform,
        "country": country_code
    }


def compare_platforms(platforms: List[str], country_code: str = "US", timeframe: str = "today 1-m", retries: int = 3) -> Dict:
    """
    Compare interest levels across multiple platforms in a country.
    
    Args:
        platforms: List of platform names (e.g., ["TikTok", "LinkedIn", "Instagram"])
        country_code: Two-letter country code
        timeframe: Time period for trends
        retries: Number of times to retry on rate limit
    
    Returns:
        A dictionary with comparison results.
    """
    
    if not platforms or len(platforms) == 0:
        return {
            "success": False,
            "error": "Platform list cannot be empty",
            "country": country_code
        }
    
    for attempt in range(retries):
        try:
            print(f"DEBUG: Comparing {platforms} in {country_code} (attempt {attempt + 1})")
            
            # Wait before request if this is a retry
            if attempt > 0:
                wait_time = 2 ** attempt
                print(f"DEBUG: Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            
            pytrends = TrendReq(hl='en-US', tz=360)
            pytrends.build_payload(platforms, cat=0, timeframe=timeframe, geo=country_code)
            
            interest_over_time = pytrends.interest_over_time()
            
            if interest_over_time.empty:
                return {
                    "success": False,
                    "error": f"No trend data found for any platforms in {country_code}",
                    "platforms": platforms,
                    "country": country_code
                }
            
            # Get latest interest for each platform
            latest_data = interest_over_time.iloc[-1].to_dict()
            
            # Sort by interest (highest first)
            sorted_platforms = sorted(latest_data.items(), key=lambda x: x[1], reverse=True)
            
            comparison = []
            for platform, interest in sorted_platforms:
                if platform != "isPartial":
                    comparison.append({
                        "platform": platform,
                        "interest": int(interest)
                    })
            
            return {
                "success": True,
                "country": country_code,
                "timeframe": timeframe,
                "comparison": comparison,
                "source": "Google Trends",
                "note": "Interest level is on a scale of 0-100, where 100 is peak popularity relative to the platforms compared"
            }
        
        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg and attempt < retries - 1:
                print(f"DEBUG: Rate limited, will retry...")
                continue
            
            return {
                "success": False,
                "error": f"Platform comparison failed: {error_msg}",
                "platforms": platforms,
                "country": country_code,
                "attempt": attempt + 1
            }
    
    return {
        "success": False,
        "error": f"Failed after {retries} attempts. Google Trends is rate-limited.",
        "platforms": platforms,
        "country": country_code
    }


def search_web(query: str, country_code: str = "US") -> Dict:
    """
    Generic search using Google Trends.
    
    Args:
        query: Search term or platform name
        country_code: Two-letter country code
    
    Returns:
        Trend data for the query.
    """
    
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Query cannot be empty",
            "query": query
        }
    
    return search_platform_trends(query, country_code)