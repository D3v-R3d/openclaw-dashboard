"""
Suggestions card for dashboard
Recommends movies, series, books based on preferences
"""

import random
from datetime import datetime
from typing import Dict, Any, List

from .base import BaseCard


class SuggestionsCard(BaseCard):
    """Card for download suggestions"""
    
    def __init__(self):
        super().__init__("Suggestions", enabled=True)
        self.suggestions_db = {
            "films": [
                {"title": "Dune: Part Two", "year": 2024, "genre": "Sci-Fi", "quality": "4K", "rating": "8.9"},
                {"title": "Oppenheimer", "year": 2023, "genre": "Biopic", "quality": "4K", "rating": "8.4"},
                {"title": "The Batman", "year": 2022, "genre": "Action", "quality": "4K", "rating": "7.8"},
                {"title": "Top Gun: Maverick", "year": 2022, "genre": "Action", "quality": "4K", "rating": "8.3"},
                {"title": "Everything Everywhere All at Once", "year": "2022", "genre": "Sci-Fi", "quality": "4K", "rating": "7.9"},
                {"title": "Nosferatu", "year": 2024, "genre": "Horreur", "quality": "4K", "rating": "7.6"},
                {"title": "Gladiator II", "year": 2024, "genre": "Action", "quality": "4K", "rating": "7.2"},
            ],
            "series": [
                {"title": "The Last of Us", "seasons": 2, "genre": "Drama/Horreur", "platform": "HBO", "rating": "8.7"},
                {"title": "Silo", "seasons": 2, "genre": "Sci-Fi", "platform": "Apple TV+", "rating": "8.1"},
                {"title": "Severance", "seasons": 2, "genre": "Sci-Fi/Thriller", "platform": "Apple TV+", "rating": "8.7"},
                {"title": "Slow Horses", "seasons": 4, "genre": "Thriller", "platform": "Apple TV+", "rating": "8.5"},
                {"title": "Dark", "seasons": 3, "genre": "Sci-Fi/Mystère", "platform": "Netflix", "rating": "8.7"},
                {"title": "Lupin", "seasons": 3, "genre": "Thriller", "platform": "Netflix", "rating": "7.5"},
            ],
            "livres": [
                {"title": "Dune", "author": "Frank Herbert", "genre": "Sci-Fi", "pages": 896},
                {"title": "Project Hail Mary", "author": "Andy Weir", "genre": "Sci-Fi", "pages": 496},
                {"title": "Les Misérables", "author": "Victor Hugo", "genre": "Classique", "pages": 1463},
                {"title": "1984", "author": "George Orwell", "genre": "Dystopie", "pages": 368},
                {"title": "Le Seigneur des Anneaux", "author": "J.R.R. Tolkien", "genre": "Fantasy", "pages": 1216},
                {"title": "The Martian", "author": "Andy Weir", "genre": "Sci-Fi", "pages": 384},
            ]
        }
        self.daily_suggestions = None
        self.last_update = None
    
    async def get_data(self) -> Dict[str, Any]:
        """Get current suggestions"""
        if not self.daily_suggestions:
            self._generate_suggestions()
        
        return {
            "suggestions": self.daily_suggestions,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "categories": list(self.suggestions_db.keys())
        }
    
    async def update(self) -> Dict[str, Any]:
        """Update suggestions (daily refresh)"""
        now = datetime.now()
        if not self.last_update or (now - self.last_update).days >= 1:
            self._generate_suggestions()
        return await self.get_data()
    
    def _generate_suggestions(self):
        """Generate daily suggestions"""
        self.daily_suggestions = {
            "films": random.sample(self.suggestions_db["films"], min(3, len(self.suggestions_db["films"]))),
            "series": random.sample(self.suggestions_db["series"], min(3, len(self.suggestions_db["series"]))),
            "livres": random.sample(self.suggestions_db["livres"], min(3, len(self.suggestions_db["livres"])))
        }
        self.last_update = datetime.now()
    
    def refresh(self):
        """Force refresh suggestions"""
        self._generate_suggestions()
