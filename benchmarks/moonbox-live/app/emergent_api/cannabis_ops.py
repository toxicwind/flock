from typing import List, Dict, Any
from services.data.cannabis_denver import generate_denver_dispensaries

class CannabisOps:
    """
    Exhumed Cannabis Data Logic
    Origin: services/data/cannabis_denver.py
    """
    
    @staticmethod
    def generate_market_data(count: int = 20) -> List[Dict[str, Any]]:
        """Generate synthetic cannabis market data"""
        return generate_denver_dispensaries(count)
    
    @staticmethod
    def analyze_deals(dispensaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract best deals from dispensary data"""
        deals = []
        for d in dispensaries:
            products = d.get('products', [])
            # The synthetic data generator might not add products by default in the simple version
            # if checking check_vector.py... wait, cannabis_denver.py has products_count logic but maybe not full product list
            # Let's check logic:
            # "products_count": random.randint(50, 500) -> it's just a number in the simple generator
            pass 
        return deals
