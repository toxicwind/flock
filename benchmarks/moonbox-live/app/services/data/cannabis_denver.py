
import random
from typing import List, Dict, Any

# Denver Coordinates
DENVER_LAT = 39.7392
DENVER_LON = -104.9903

# Real-ish street names in Denver
STREETS = [
    "Colfax Ave", "Broadway", "Speer Blvd", "Federal Blvd", "Colorado Blvd",
    "Santa Fe Dr", "Larimer St", "Blake St", "Market St", "16th St"
]

DISPENSARY_NAMES = [
    "Mile High Green", "Denver Relief", "Rocky Mountain High", "Elevation Dispensary",
    "The Green Solution", "Native Roots", "L'Eagle Services", "Verde Natural",
    "Good Chemistry", "Lightshade"
]

def generate_denver_dispensaries(count: int = 20) -> List[Dict[str, Any]]:
    """Generate synthetic but realistic Denver dispensary data"""
    dispensaries = []
    
    for i in range(count):
        name = random.choice(DISPENSARY_NAMES) + " " + random.choice(["Downtown", "South", "North", "West", "RiNo", "LoDo"])
        lat = DENVER_LAT + random.uniform(-0.05, 0.05)
        lon = DENVER_LON + random.uniform(-0.05, 0.05)
        address = f"{random.randint(100, 9999)} {random.choice(STREETS)}"
        
        dispensaries.append({
            "id": f"denver-disp-{i}",
            "name": name,
            "address": address,
            "city": "Denver",
            "state": "CO",
            "zip": "80202",
            "lat": lat,
            "lon": lon,
            "rating": round(random.uniform(4.0, 5.0), 1),
            "reviews": random.randint(50, 2000),
            "open_now": random.choice([True, False]),
            "products_count": random.randint(50, 500)
        })
        
    return dispensaries
