"""
Base card class for modular dashboard
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseCard(ABC):
    """Base class for all dashboard cards"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self._cache = {}
    
    @abstractmethod
    async def get_data(self) -> Dict[str, Any]:
        """Get current card data"""
        pass
    
    @abstractmethod
    async def update(self) -> Dict[str, Any]:
        """Update card data and return new data"""
        pass
    
    def enable(self):
        """Enable the card"""
        self.enabled = True
    
    def disable(self):
        """Disable the card"""
        self.enabled = False
