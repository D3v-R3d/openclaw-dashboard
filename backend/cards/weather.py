"""
Weather card for dashboard
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import urllib.request
import urllib.parse

from .base import BaseCard


class WeatherCard(BaseCard):
    """Card for displaying weather information"""
    
    def __init__(self, location: str = "Ajaccio, France"):
        super().__init__("Météo", enabled=True)
        self.location = location
        self.lat = 41.9189  # Ajaccio latitude
        self.lon = 8.7381   # Ajaccio longitude
        self.weather_data = {}
        self.last_update = None
    
    async def get_data(self) -> Dict[str, Any]:
        """Get current weather data"""
        return {
            "location": self.location,
            "current": self.weather_data.get("current", {}),
            "forecast": self.weather_data.get("forecast", []),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
    
    async def update(self) -> Dict[str, Any]:
        """Fetch weather data from Open-Meteo API (free, no key needed)"""
        try:
            # Using Open-Meteo API (free, no registration required)
            url = f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,weather_code&timezone=Europe/Paris"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-Dashboard/1.0'})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Parse current weather
            current = data.get("current", {})
            daily = data.get("daily", {})
            
            self.weather_data = {
                "current": {
                    "temp": current.get("temperature_2m"),
                    "feels_like": current.get("apparent_temperature"),
                    "humidity": current.get("relative_humidity_2m"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "precipitation": current.get("precipitation"),
                    "is_day": current.get("is_day"),
                    "weather_code": current.get("weather_code"),
                    "condition": self._get_weather_condition(current.get("weather_code", 0))
                },
                "forecast": [
                    {
                        "date": daily.get("time", [])[i],
                        "temp_max": daily.get("temperature_2m_max", [])[i],
                        "temp_min": daily.get("temperature_2m_min", [])[i],
                        "condition": self._get_weather_condition(daily.get("weather_code", [])[i])
                    }
                    for i in range(min(5, len(daily.get("time", []))))
                ]
            }
            
            self.last_update = datetime.now()
            
        except Exception as e:
            print(f"Error fetching weather: {e}")
            # Fallback data if API fails
            self.weather_data = {
                "current": {
                    "temp": 18.5,
                    "feels_like": 17.0,
                    "humidity": 65,
                    "wind_speed": 12.5,
                    "precipitation": 0.0,
                    "is_day": 1,
                    "weather_code": 1,
                    "condition": "Partiellement nuageux"
                },
                "forecast": []
            }
        
        return await self.get_data()
    
    def _get_weather_condition(self, code: int) -> str:
        """Convert WMO weather code to French description"""
        codes = {
            0: "Ensoleillé",
            1: "Partiellement nuageux",
            2: "Nuageux",
            3: "Couvert",
            45: "Brouillard",
            48: "Brouillard givrant",
            51: "Bruine légère",
            53: "Bruine modérée",
            55: "Bruine dense",
            61: "Pluie légère",
            63: "Pluie modérée",
            65: "Pluie forte",
            71: "Neige légère",
            73: "Neige modérée",
            75: "Neige forte",
            95: "Orage",
            96: "Orage avec grêle",
        }
        return codes.get(code, "Inconnu")
