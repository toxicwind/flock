"""
Cannabis Analysis Service
Adapted from oneoff_cell.py to run as a reliable microservice

Features:
- OpenTHC-standard data models
- Medical flower price analysis
- Folium interactive map generation
- HTML report generation with plots
- JSON data endpoints
"""

import io
import base64
import random
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import folium
from folium.plugins import MarkerCluster
from fastapi import APIRouter, Response, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

router = APIRouter(prefix="/cannabis", tags=["cannabis"])

# --- OpenTHC Data Models (Simplified) ---

class Strain(BaseModel):
    id: str
    name: str
    type: str  # sativa, indica, hybrid
    thc_percent: float
    cbd_percent: float

class Product(BaseModel):
    id: str
    strain: Strain
    name: str
    category: str  # Flower, Pre-Roll, Concentrate
    weight_g: float
    price_cents: int
    price_per_g_cents: float
    dispensary_id: str

class Dispensary(BaseModel):
    id: str
    name: str
    address: str
    city: str
    state: str
    lat: float
    lon: float
    rating: float
    products: List[Product] = []

# --- Data Generation ---

def generate_synthetic_dispensaries(n_dispensaries=5, center_lat=34.0522, center_lon=-118.2437):
    """Generate realistic dispensaries with products using OpenTHC patterns"""
    np.random.seed(42)
    random.seed(42)
    
    dispensaries = []
    strain_types = ['Sativa', 'Indica', 'Hybrid']
    categories = ['Bulk Value', 'Pre-Pack Specialty', 'Shake/Popcorn/Trim', 'Premium Flower', 'Small Batch']
    
    # Generate some shared strains
    strains = []
    for i in range(20):
        strains.append(Strain(
            id=f"strain-{i}",
            name=f"{random.choice(['OG', 'Kush', 'Haze', 'Cookie', 'Glue'])} {random.choice(['Breath', 'Cake', 'Dream', 'Diesel'])}",
            type=random.choice(strain_types),
            thc_percent=random.uniform(15, 32),
            cbd_percent=random.uniform(0, 5)
        ))

    for i in range(n_dispensaries):
        # Cluster around center
        lat = center_lat + random.uniform(-0.1, 0.1)
        lon = center_lon + random.uniform(-0.1, 0.1)
        
        disp = Dispensary(
            id=f"disp-{i}",
            name=f"{random.choice(['Green', 'Healing', 'Wellness', 'Nature', 'Urban'])} {random.choice(['Center', 'Collective', 'Care', 'Leaf', 'Root'])}",
            address=f"{random.randint(100, 9999)} {random.choice(['Main', 'Broadway', 'Sunset', 'Highland'])} St",
            city="Los Angeles",
            state="CA",
            lat=lat,
            lon=lon,
            rating=random.uniform(3.5, 5.0)
        )
        
        # Add products
        n_products = random.randint(10, 30)
        for _ in range(n_products):
            strain = random.choice(strains)
            cat = random.choice(categories)
            weight = random.choice([3.5, 7.0, 14.0, 28.0])
            
            # Pricing logic
            base_ppg = {
                'Bulk Value': 500,
                'Pre-Pack Specialty': 1200,
                'Shake/Popcorn/Trim': 350,
                'Premium Flower': 1500,
                'Small Batch': 1800
            }[cat]
            
            price_cents = int(base_ppg * weight * random.uniform(0.9, 1.2))
            
            disp.products.append(Product(
                id=f"prod-{random.randint(1000,9999)}",
                strain=strain,
                name=f"{strain.name} ({cat})",
                category=cat,
                weight_g=weight,
                price_cents=price_cents,
                price_per_g_cents=price_cents / weight,
                dispensary_id=disp.id
            ))
            
        dispensaries.append(disp)
        
    return dispensaries

def create_folium_map(dispensaries: List[Dispensary]):
    """Generate Folium map of dispensaries"""
    if not dispensaries:
        return "<div>No data</div>"
        
    center_lat = np.mean([d.lat for d in dispensaries])
    center_lon = np.mean([d.lon for d in dispensaries])
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB dark_matter")
    marker_cluster = MarkerCluster().add_to(m)
    
    for d in dispensaries:
        avg_price_eighth = np.mean([p.price_cents for p in d.products if p.weight_g == 3.5]) / 100
        
        popup_html = f"""
        <div style="font-family: sans-serif; min-width: 200px">
            <h4 style="margin: 0 0 5px 0; color: #10b981">{d.name}</h4>
            <p style="margin: 0; font-size: 12px">{d.address}</p>
            <p style="margin: 5px 0; font-weight: bold">Rating: {d.rating:.1f}⭐</p>
            <p style="margin: 0; font-size: 12px">Products: {len(d.products)}</p>
            <p style="margin: 0; font-size: 12px">Avg 1/8th: ${avg_price_eighth:.2f}</p>
        </div>
        """
        
        folium.Marker(
            location=[d.lat, d.lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="green", icon="leaf", prefix="fa")
        ).add_to(marker_cluster)
        
    return m._repr_html_()

# --- Analysis Logic ---

def run_analysis(dispensaries: List[Dispensary], title: str = "Market Analysis"):
    """Run full analysis pipeline and return HTML report"""
    
    # Flatten products for analysis
    all_products = []
    for d in dispensaries:
        for p in d.products:
            all_products.append({
                'name': p.name,
                'strain_type': p.strain.type,
                'category': p.category,
                'weight_g': p.weight_g,
                'price': p.price_cents / 100,
                'price_per_oz': (p.price_cents / 100 / p.weight_g) * 28.0,
                'dispensary': d.name
            })
            
    df = pd.DataFrame(all_products)
    
    # 1. Config & Styling
    sns.set_theme(style="whitegrid")
    
    # Categories order
    cat_order = (
        df.groupby('category')['price_per_oz']
        .median()
        .sort_values()
        .index
        .tolist()
    )
    
    # 2. Plots
    def _encode_fig(fig, dpi=100):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    # Box Plot
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.boxplot(
        data=df, x="price_per_oz", y="category",
        order=cat_order, hue="category",
        palette="pastel", legend=False, ax=ax1,
        fliersize=5, linewidth=1.2
    )
    ax1.set_title("Price Distribution by Product Type")
    img_box = _encode_fig(fig1)
    
    # 3. Metrics
    best_row = df.loc[df['price_per_oz'].idxmin()]
    
    # 4. Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <meta charset="utf-8">
        <title>Cannabis Price Analysis</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>body {{ font-family: system-ui, sans-serif; }}</style>
    </head>
    <body class="bg-gray-900 text-gray-100 p-8 max-w-5xl mx-auto">
        <header class="mb-10 text-center">
            <h1 class="text-4xl font-bold text-emerald-400">{title}</h1>
            <p class="text-gray-400 mt-2">Analyzed {len(dispensaries)} dispensaries, {len(df)} products</p>
        </header>
        
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div class="text-gray-400 text-sm">Best Value (28g eq)</div>
                <div class="text-3xl font-bold text-emerald-400">${best_row['price_per_oz']:.2f}/oz</div>
                <div class="text-sm text-gray-500 mt-1">{best_row['name']}</div>
                <div class="text-xs text-gray-600">@ {best_row['dispensary']}</div>
            </div>
             <div class="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <div class="text-gray-400 text-sm">Market Median</div>
                <div class="text-3xl font-bold text-white">${df['price_per_oz'].median():.0f}/oz</div>
                <div class="text-sm text-gray-500 mt-1">Typical price point</div>
            </div>
            <div class="bg-gray-800 p-6 rounded-xl border border-gray-700">
                 <div class="text-gray-400 text-sm">Dispensaries Tracked</div>
                <div class="text-3xl font-bold text-blue-400">{len(dispensaries)}</div>
                <div class="text-sm text-gray-500 mt-1">Los Angeles Area</div>
            </div>
        </div>
        
        <h2 class="text-2xl font-semibold text-emerald-400 mb-6 border-b border-gray-700 pb-2">Price Landscape</h2>
        
        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 mb-8">
            <img src="data:image/png;base64,{img_box}" class="w-full rounded bg-white p-2">
        </div>
        
        <h2 class="text-2xl font-semibold text-emerald-400 mb-6 border-b border-gray-700 pb-2">Analyzed Dispensaries</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {"".join([f'<div class="bg-gray-800 p-4 rounded-lg border border-gray-700"><div class="font-bold text-white">{d.name}</div><div class="text-sm text-gray-400">{d.address}</div><div class="text-emerald-400 text-sm">{d.rating}⭐ • {len(d.products)} products</div></div>' for d in dispensaries])}
        </div>

        <footer class="mt-12 text-center text-gray-600 text-sm">
            Powered by Effusion Labs Orchestrator • OpenTHC Standards
        </footer>
    </body>
    </html>
    """
    
    return html

# --- Endpoints ---

@router.get("/report/demo", response_class=Response)
async def get_demo_report():
    """Get a full HTML analysis report using synthetic data"""
    dispensaries = generate_synthetic_dispensaries()
    html_content = run_analysis(dispensaries, "Market Report: Los Angeles")
    return Response(content=html_content, media_type="text/html")

@router.get("/map/demo", response_class=Response)
async def get_demo_map():
    """Get a Folium interactive map of dispensaries"""
    dispensaries = generate_synthetic_dispensaries()
    html_content = create_folium_map(dispensaries)
    return Response(content=html_content, media_type="text/html")

@router.get("/data/synthetic")
async def get_synthetic_data():
    """Get raw synthetic data for frontend visualization"""
    dispensaries = generate_synthetic_dispensaries()
    return [d.dict() for d in dispensaries]

from services.mildlyawesome.scrapers.weedmaps import WeedmapsScraper

@router.get("/denver")
async def get_denver_data():
    """Get Denver-specific dispensary data via Scraper"""
    scraper = WeedmapsScraper()
    return await scraper.scrape_denver()

@router.get("/")
async def get_cannabis_summary():
    """Unified cannabis market summary"""
    scraper = WeedmapsScraper()
    dispensaries = await scraper.scrape_denver()
    
    # Extract "deals" (e.g., lowest price per oz)
    deals = []
    for d in dispensaries:
        # Pydantic models have .products, but generate_denver_dispensaries might return dicts
        # Based on weedmaps.py, it uses generate_denver_dispensaries which returns dicts
        products = d.get('products', [])
        if products:
            best_deal = min(products, key=lambda p: p['price_per_g_cents'])
            deals.append({
                "dispensary": d['name'],
                "product": best_deal['name'],
                "price_per_g": best_deal['price_per_g_cents'] / 100,
                "category": best_deal['category']
            })

    return {
        "last_scrape_time": datetime.utcnow().isoformat(),
        "dispensaries_count": len(dispensaries),
        "dispensaries": [
            {
                "id": d['id'],
                "name": d['name'],
                "address": d['address'],
                "rating": d['rating'],
                "lat": d['lat'],
                "lon": d['lon']
            } for d in dispensaries
        ],
        "deals": sorted(deals, key=lambda x: x['price_per_g'])[:5]
    }
