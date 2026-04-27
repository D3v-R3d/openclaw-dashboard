#!/usr/bin/env python3
"""
Dashboard modulaire pour Raspberry Pi
- Backend FastAPI
- Cards modulaires (téléchargements, météo, etc.)
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any
import uvicorn

from cards.downloads import DownloadsCard
from cards.weather import WeatherCard
from cards.suggestions import SuggestionsCard
from cards.spotify import SpotifyCard

app = FastAPI(title="OpenClaw Dashboard", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")

# Database setup
def init_db():
    conn = sqlite3.connect('dashboard.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS downloads
                 (id TEXT PRIMARY KEY, name TEXT, size INTEGER, 
                  downloaded INTEGER, speed INTEGER, eta TEXT, 
                  status TEXT, updated_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS weather
                 (id INTEGER PRIMARY KEY, location TEXT, temp REAL,
                  condition TEXT, humidity INTEGER, wind_speed REAL,
                  updated_at TIMESTAMP)''')
    conn.commit()
    conn.close()

# Card registry
CARDS: Dict[str, Any] = {
    "downloads": DownloadsCard(),
    "weather": WeatherCard(),
    "suggestions": SuggestionsCard(),
    "spotify": SpotifyCard(),
}

# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.on_event("startup")
async def startup():
    init_db()
    # Start background tasks
    asyncio.create_task(update_cards())

@app.get("/")
async def root():
    return FileResponse("/app/frontend/index.html")

@app.get("/api/cards")
async def get_cards():
    """List all available cards"""
    return {
        card_id: {
            "name": card.name,
            "enabled": card.enabled,
            "data": await card.get_data()
        }
        for card_id, card in CARDS.items()
    }

@app.get("/api/cards/{card_id}")
async def get_card(card_id: str):
    """Get specific card data"""
    if card_id not in CARDS:
        return {"error": "Card not found"}
    card = CARDS[card_id]
    return {
        "name": card.name,
        "enabled": card.enabled,
        "data": await card.get_data()
    }

@app.post("/api/cards/{card_id}/refresh")
async def refresh_card(card_id: str):
    """Refresh card data"""
    if card_id not in CARDS:
        return {"error": "Card not found"}
    card = CARDS[card_id]
    if hasattr(card, 'refresh'):
        card.refresh()
    return {"status": "refreshed"}


# Spotify API endpoints
@app.get("/api/cards/spotify/search")
async def spotify_search(query: str, type: str = "track", limit: int = 10):
    """Search Spotify for tracks, artists, or albums"""
    card = CARDS.get("spotify")
    if not card:
        return {"error": "Spotify card not found"}
    return await card.search(query, type, limit)


@app.post("/api/cards/spotify/play/{track_id}")
async def spotify_play(track_id: str):
    """Play a specific track"""
    card = CARDS.get("spotify")
    if not card:
        return {"error": "Spotify card not found"}
    return await card.play_track(track_id)


@app.post("/api/cards/spotify/pause")
async def spotify_pause():
    """Pause playback"""
    card = CARDS.get("spotify")
    if not card:
        return {"error": "Spotify card not found"}
    return await card.pause()


@app.post("/api/cards/spotify/resume")
async def spotify_resume():
    """Resume playback"""
    card = CARDS.get("spotify")
    if not card:
        return {"error": "Spotify card not found"}
    return await card.resume()


@app.post("/api/cards/spotify/next")
async def spotify_next():
    """Skip to next track"""
    card = CARDS.get("spotify")
    if not card:
        return {"error": "Spotify card not found"}
    return await card.next_track()


@app.post("/api/cards/spotify/previous")
async def spotify_previous():
    """Go to previous track"""
    card = CARDS.get("spotify")
    if not card:
        return {"error": "Spotify card not found"}
    return await card.previous_track()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive ping from client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def update_cards():
    """Background task to update cards and broadcast changes"""
    while True:
        try:
            for card_id, card in CARDS.items():
                if card.enabled:
                    data = await card.update()
                    await manager.broadcast({
                        "type": "card_update",
                        "card": card_id,
                        "data": data
                    })
            await asyncio.sleep(5)  # Update every 5 seconds
        except Exception as e:
            print(f"Error updating cards: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Hot reload enabled for development
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True, reload_dirs=["/app/backend", "/app/frontend"])
