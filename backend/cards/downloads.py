"""
Download monitoring card for Synology NAS
Reads from SQLite database where real downloads are logged
"""

import asyncio
import sqlite3
import os
from typing import Dict, Any, List
from datetime import datetime

from .base import BaseCard


class DownloadsCard(BaseCard):
    """Card for monitoring real downloads"""
    
    def __init__(self):
        super().__init__("Téléchargements", enabled=True)
        self.db_path = os.environ.get('DASHBOARD_DB_PATH', '/app/data/dashboard.db')
        self.init_db()
    
    def init_db(self):
        """Initialize downloads table"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS downloads
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      filename TEXT NOT NULL,
                      size_gb REAL,
                      status TEXT DEFAULT 'pending',
                      source TEXT,
                      location TEXT,
                      progress INTEGER DEFAULT 0,
                      speed TEXT,
                      eta TEXT,
                      added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      completed_at TIMESTAMP)''')
        conn.commit()
        conn.close()
    
    async def get_data(self) -> Dict[str, Any]:
        """Get current download data from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Get recent downloads (last 20)
        c.execute('''SELECT * FROM downloads 
                     ORDER BY added_at DESC 
                     LIMIT 20''')
        rows = c.fetchall()
        
        downloads = []
        for row in rows:
            downloads.append({
                "id": row['id'],
                "name": row['filename'],
                "size_gb": row['size_gb'],
                "status": row['status'],
                "progress": row['progress'],
                "speed": row['speed'] or "-",
                "eta": row['eta'] or "-",
                "source": row['source'] or "Unknown",
                "location": row['location'] or "/volume1/Storage/Video/Films/",
                "added_at": row['added_at']
            })
        
        active_count = len([d for d in downloads if d['status'] == 'downloading'])
        completed_count = len([d for d in downloads if d['status'] == 'completed'])
        
        conn.close()
        
        return {
            "downloads": downloads,
            "active_count": active_count,
            "completed_count": completed_count,
        }
    
    async def update(self) -> Dict[str, Any]:
        """Update - just refresh from DB"""
        return await self.get_data()
    
    def add_download(self, filename: str, size_gb: float, source: str, location: str):
        """Add a new download record (called by download script)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO downloads (filename, size_gb, status, source, location, progress)
                     VALUES (?, ?, 'downloading', ?, ?, 0)''',
                  (filename, size_gb, source, location))
        conn.commit()
        download_id = c.lastrowid
        conn.close()
        return download_id
    
    def update_progress(self, download_id: int, progress: int, speed: str = None, eta: str = None):
        """Update download progress"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''UPDATE downloads 
                     SET progress = ?, speed = ?, eta = ?
                     WHERE id = ?''',
                  (progress, speed, eta, download_id))
        conn.commit()
        conn.close()
    
    def complete_download(self, download_id: int):
        """Mark download as completed"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''UPDATE downloads 
                     SET status = 'completed', progress = 100, speed = NULL, eta = NULL, completed_at = CURRENT_TIMESTAMP
                     WHERE id = ?''',
                  (download_id,))
        conn.commit()
        conn.close()
