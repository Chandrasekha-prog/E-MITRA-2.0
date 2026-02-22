import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenWeatherMap API configuration
API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5"
CACHE_DURATION = int(os.getenv("WEATHER_CACHE_DURATION", "3600"))

# Simple in-memory cache
weather_cache = {}

# District/Mandal to coordinates mapping (for NTR district)
# In production, this would be a comprehensive database
LOCATION_COORDS = {
    "NTR": {
        "IBRAHIMPATNAM": {"lat": 16.5500, "lon": 80.7500},
        "A KONDURU": {"lat": 16.6167, "lon": 80.8500},
        "CHANDARLAPADU": {"lat": 16.4833, "lon": 80.5833},
        "GAMPALAGUDEM": {"lat": 16.5833, "lon": 80.6167},
        "KANCHIKA CHERLA": {"lat": 16.4500, "lon": 80.6500},
        "TIRUVURU": {"lat": 16.7667, "lon": 80.8333},
        "VEERULLAPADU": {"lat": 16.4667, "lon": 80.6333},
    }
}

def get_coordinates(district: str, mandal: str) -> Optional[Dict[str, float]]:
    """Get latitude and longitude for a given district and mandal"""
    district_upper = district.upper()
    mandal_upper = mandal.upper()
    
    if district_upper in LOCATION_COORDS:
        if mandal_upper in LOCATION_COORDS[district_upper]:
            return LOCATION_COORDS[district_upper][mandal_upper]
    
    # Default to NTR district center if not found
    return {"lat": 16.5062, "lon": 80.6480}

def get_cache_key(district: str, mandal: str, weather_type: str) -> str:
    """Generate cache key for weather data"""
    return f"{district}_{mandal}_{weather_type}"

def is_cache_valid(cache_entry: Dict) -> bool:
    """Check if cached data is still valid"""
    if not cache_entry:
        return False
    
    cached_time = cache_entry.get("cached_at")
    if not cached_time:
        return False
    
    age = (datetime.now() - cached_time).total_seconds()
    return age < CACHE_DURATION

def get_mock_weather_data(district: str, mandal: str) -> Dict:
    """Generate mock weather data as fallback"""
    return {
        "location": f"{mandal}, {district}",
        "temperature": 28.5,
        "feels_like": 30.2,
        "humidity": 65,
        "description": "Partly cloudy",
        "main": "Clouds",
        "icon": "02d",
        "wind_speed": 3.5,
        "clouds": 40,
        "rain_1h": 0,
        "rain_3h": 0,
        "timestamp": datetime.now().isoformat(),
        "is_mock": True
    }

def get_current_weather(district: str, mandal: str) -> Dict:
    """
    Get current weather for a location
    
    Args:
        district: District name
        mandal: Mandal name
    
    Returns:
        Dictionary with current weather data
    """
    # Check cache first
    cache_key = get_cache_key(district, mandal, "current")
    if cache_key in weather_cache and is_cache_valid(weather_cache[cache_key]):
        return weather_cache[cache_key]["data"]
    
    # Remove API Key check as we will use Open-Meteo which does not need one
    
    # Get coordinates
    coords = get_coordinates(district, mandal)
    if not coords:
        return get_mock_weather_data(district, mandal)
    
    try:
        # Call Open-Meteo API for current weather
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,cloud_cover",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        current = data.get("current", {})
        
        weather_code = current.get("weather_code", 0)
        desc = "Clear sky"
        main = "Clear"
        
        if weather_code in [1, 2, 3]:
            desc = "Partly cloudy"
            main = "Clouds"
        elif weather_code in [45, 48]:
            desc = "Fog"
            main = "Fog"
        elif 50 <= weather_code <= 69:
            desc = "Rain"
            main = "Rain"
        elif 80 <= weather_code <= 82:
            desc = "Showers"
            main = "Rain"
        elif weather_code >= 95:
            desc = "Thunderstorm"
            main = "Thunderstorm"
            
        # Extract relevant weather information
        weather_data = {
            "location": f"{mandal}, {district}",
            "temperature": current.get("temperature_2m", 25),
            "feels_like": current.get("apparent_temperature", 25),
            "humidity": current.get("relative_humidity_2m", 50),
            "description": desc,
            "main": main,
            "icon": "02d", # Default fallback
            "wind_speed": current.get("wind_speed_10m", 0),
            "clouds": current.get("cloud_cover", 0),
            "rain_1h": current.get("precipitation", 0),
            "rain_3h": current.get("precipitation", 0) * 3, # Estimation
            "timestamp": datetime.now().isoformat(),
            "is_mock": False
        }
        
        # Cache the data
        weather_cache[cache_key] = {
            "data": weather_data,
            "cached_at": datetime.now()
        }
        
        return weather_data
        
    except Exception as e:
        print(f"Error fetching real weather data: {e}")
        return get_mock_weather_data(district, mandal)

def get_weather_forecast(district: str, mandal: str) -> List[Dict]:
    """
    Get 5-day weather forecast for a location
    
    Args:
        district: District name
        mandal: Mandal name
    
    Returns:
        List of forecast data for next 5 days
    """
    # Check cache first
    cache_key = get_cache_key(district, mandal, "forecast")
    if cache_key in weather_cache and is_cache_valid(weather_cache[cache_key]):
        return weather_cache[cache_key]["data"]
    
    # Removed API Key check
    
    # Get coordinates
    coords = get_coordinates(district, mandal)
    if not coords:
        return []
    
    try:
        # Call Open-Meteo API for forecast
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,weather_code",
            "timezone": "auto"
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        daily = data.get("daily", {})
        
        forecast_list = []
        for i in range(min(5, len(daily.get("time", [])))):
            w_code = daily["weather_code"][i]
            desc = "Clear"
            if w_code in [1, 2, 3]: desc = "Cloudy"
            elif 50 <= w_code <= 69: desc = "Rain"
            elif 80 <= w_code <= 82: desc = "Showers"
            elif w_code >= 95: desc = "Thunderstorm"
            
            forecast_list.append({
                "date": daily["time"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "description": desc,
                "rain_probability": daily["precipitation_probability_max"][i],
                "rain_mm": daily["precipitation_sum"][i]
            })
        
        # Cache the data
        weather_cache[cache_key] = {
            "data": forecast_list,
            "cached_at": datetime.now()
        }
        
        return forecast_list
        
    except Exception as e:
        print(f"Error fetching forecast data: {e}")
        return []

def get_weather_condition(weather_data: Dict) -> str:
    """
    Determine weather condition category
    
    Returns: 'SUNNY', 'CLOUDY', 'RAINY', or 'CLEAR'
    """
    main = weather_data.get("main", "").upper()
    rain_3h = weather_data.get("rain_3h", 0)
    clouds = weather_data.get("clouds", 0)
    
    if main == "RAIN" or rain_3h > 0:
        return "RAINY"
    elif clouds > 70:
        return "CLOUDY"
    elif clouds < 20:
        return "SUNNY"
    else:
        return "CLOUDY"

def analyze_weather_for_fertilizer(weather_data: Dict, forecast: List[Dict]) -> Dict:
    """
    Analyze weather conditions and provide fertilizer application recommendations
    
    Args:
        weather_data: Current weather data
        forecast: 5-day forecast data
    
    Returns:
        Dictionary with weather analysis and recommendations
    """
    condition = get_weather_condition(weather_data)
    temperature = weather_data.get("temperature", 25)
    rain_3h = weather_data.get("rain_3h", 0)
    
    # Analyze forecast for next 24-48 hours
    rain_expected = False
    if forecast:
        next_day_rain = forecast[0].get("rain_mm", 0) if len(forecast) > 0 else 0
        rain_expected = next_day_rain > 5
    
    # Determine application advice
    can_apply = True
    timing_advice = "Apply fertilizer as planned"
    weather_notes = []
    
    # Heavy rain - delay application
    if rain_3h > 10:
        can_apply = False
        timing_advice = "⛔ Delay application - Heavy rainfall detected"
        weather_notes.append("Heavy rain will cause nutrient runoff and waste")
        weather_notes.append("Wait 24-48 hours after rain stops")
    
    # Moderate rain - postpone if possible
    elif rain_3h > 5:
        can_apply = False
        timing_advice = "⚠️ Postpone if possible - Moderate rainfall"
        weather_notes.append("Moderate rain may reduce fertilizer effectiveness")
        weather_notes.append("Consider waiting for better conditions")
    
    # Rain expected in forecast
    elif rain_expected:
        timing_advice = "⚠️ Rain expected within 24 hours - Apply soon or wait"
        weather_notes.append("Rain forecasted in next 24 hours")
        weather_notes.append("Either apply immediately or wait until after rain")
    
    # Hot and sunny
    elif condition == "SUNNY" and temperature > 35:
        timing_advice = "🌡️ Apply early morning (6-8 AM) or evening (5-7 PM)"
        weather_notes.append("High temperature - avoid midday application")
        weather_notes.append("Ensure adequate soil moisture before application")
        weather_notes.append("Water the field after fertilizer application")
    
    # Cloudy - ideal conditions
    elif condition == "CLOUDY":
        timing_advice = "✅ Excellent conditions - Cloudy weather is ideal"
        weather_notes.append("Cloudy conditions reduce evaporation")
        weather_notes.append("Nutrients will be absorbed effectively")
    
    # Light rain or clear
    else:
        timing_advice = "✅ Good conditions for fertilizer application"
        weather_notes.append("Weather conditions are favorable")
        weather_notes.append("Ensure soil has adequate moisture")
    
    return {
        "condition": condition,
        "can_apply": can_apply,
        "timing_advice": timing_advice,
        "weather_notes": weather_notes,
        "temperature": temperature,
        "rainfall_3h": rain_3h,
        "rain_expected_24h": rain_expected
    }
