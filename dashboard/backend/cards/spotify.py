"""
Spotify card for dashboard using SpotAPI
Public API + Private Player API access
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import BaseCard

# Try to import SpotAPI, handle gracefully if not installed
try:
    from spotapi import Song, Artist, PublicPlaylist, Login, Player, JSONSaver, Config, NoopLogger
    SPOTAPI_AVAILABLE = True
except ImportError:
    SPOTAPI_AVAILABLE = False


class SpotifyCard(BaseCard):
    """Card for Spotify search, discovery and playback (public + private API)"""
    
    def __init__(self):
        super().__init__("Spotify", enabled=True)
        self.last_search_results = {
            "tracks": [],
            "artists": [],
            "albums": []
        }
        self.last_update = None
        self._song_client = None
        self._artist_client = None
        self._album_client = None
        self._playlist_client = None
        
        # Player / Private API
        self._login_instance = None
        self._player = None
        self._player_status = None
        self._playback_state = {
            "is_playing": False,
            "track_id": None,
            "track_name": None,
            "artist_name": None,
            "album_name": None,
            "progress_ms": 0,
            "duration_ms": 0,
            "volume_percent": 100,
            "device_id": None,
            "timestamp": None
        }
        self._session_file = Path("/app/data/spotify_session.json")
        self._is_logged_in = False
        self._login_error = None
        
        # Auto-login from environment variables if available
        if SPOTAPI_AVAILABLE:
            self._init_clients()
            self._auto_login_from_env()
    
    def _auto_login_from_env(self):
        """Try to login using environment variables (SP_DC, SP_KEY, SP_T)"""
        import os
        sp_dc = os.environ.get('SP_DC')
        sp_key = os.environ.get('SP_KEY')
        sp_t = os.environ.get('SP_T')
        email = os.environ.get('SP_EMAIL', 'ajendouz.redwan@gmail.com')
        
        if sp_dc and sp_key and sp_t:
            try:
                dump = {
                    'identifier': email,
                    'cookies': {
                        'sp_dc': sp_dc,
                        'sp_key': sp_key,
                        'sp_t': sp_t
                    }
                }
                # Create login instance with cookies
                cfg = Config(logger=NoopLogger())
                self._login_instance = Login.from_cookies(dump, cfg)
                self._login_instance.login()
                
                # Initialize player
                self._player = Player(self._login_instance)
                self._is_logged_in = True
                print("✅ Spotify auto-login successful from environment variables")
            except Exception as e:
                error_str = str(e)
                # "User already logged in" is actually a success - we're already authenticated
                if "already logged in" in error_str.lower():
                    self._is_logged_in = True
                    # Initialize player even if login() raised this
                    try:
                        self._player = Player(self._login_instance)
                        print("✅ Spotify auto-login successful (already authenticated)")
                    except Exception as player_e:
                        self._login_error = f"Login OK but player init failed: {player_e}"
                        print(f"⚠️ Spotify login OK but player init failed: {player_e}")
                else:
                    self._login_error = error_str
                    print(f"❌ Spotify auto-login failed: {e}")
    
    def _init_clients(self):
        """Initialize SpotAPI clients if available"""
        if SPOTAPI_AVAILABLE and not self._song_client:
            self._song_client = Song()
            self._artist_client = Artist()
            self._album_client = None  # Album search done via song client
            self._playlist_client = None  # PublicPlaylist requires playlist ID
    
    async def get_data(self) -> Dict[str, Any]:
        """Get current card data including playback state"""
        return {
            "available": SPOTAPI_AVAILABLE,
            "logged_in": self._is_logged_in,
            "login_error": self._login_error,
            "playback_state": self._playback_state,
            "last_search": self.last_search_results,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
    
    async def update(self) -> Dict[str, Any]:
        """Update card - refresh playback state if logged in"""
        if SPOTAPI_AVAILABLE:
            self._init_clients()
            if self._is_logged_in:
                await self._refresh_playback_state()
        return await self.get_data()

    # ==================== AUTHENTICATION ====================

    async def login_with_cookies(self, cookies: Dict[str, str], email: Optional[str] = None) -> Dict[str, Any]:
        """
        Login using cookies from browser session
        
        Args:
            cookies: Dictionary of cookies from Spotify web session
            email: Optional email identifier for the session
        
        Returns:
            Dictionary with success status and error message if any
        """
        if not SPOTAPI_AVAILABLE:
            return {"success": False, "error": "SpotAPI not installed"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _do_login():
                cfg = Config(logger=NoopLogger())
                saver = JSONSaver(self._session_file)
                
                # Create login instance with cookies
                identifier = email or list(cookies.keys())[0] if cookies else "user"
                instance = Login.from_saver(saver, cfg, identifier)
                
                # Save the session for future use
                instance.save(saver)
                return instance
            
            self._login_instance = await loop.run_in_executor(None, _do_login)
            
            # Initialize player
            self._player = Player(self._login_instance)
            self._player_status = PlayerStatus(self._login_instance)
            self._is_logged_in = True
            self._login_error = None
            
            # Save cookies to session file for persistence
            self._session_file.parent.mkdir(parents=True, exist_ok=True)
            
            return {"success": True}
            
        except Exception as e:
            self._is_logged_in = False
            self._login_error = str(e)
            return {"success": False, "error": str(e)}

    async def login_with_password(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login using email and password (requires CAPTCHA solver)
        
        Args:
            email: Spotify account email
            password: Spotify account password
        
        Returns:
            Dictionary with success status and error message if any
        """
        if not SPOTAPI_AVAILABLE:
            return {"success": False, "error": "SpotAPI not installed"}
        
        return {
            "success": False, 
            "error": "Login with password requires CAPTCHA solver. Please use cookie-based login instead."
        }

    async def logout(self) -> Dict[str, Any]:
        """Logout and clear session"""
        self._login_instance = None
        self._player = None
        self._player_status = None
        self._is_logged_in = False
        self._login_error = None
        self._playback_state = {
            "is_playing": False,
            "track_id": None,
            "track_name": None,
            "artist_name": None,
            "album_name": None,
            "progress_ms": 0,
            "duration_ms": 0,
            "volume_percent": 100,
            "device_id": None,
            "timestamp": None
        }
        
        # Clear session file
        if self._session_file.exists():
            self._session_file.unlink()
        
        return {"success": True}

    async def check_session(self) -> Dict[str, Any]:
        """Check if saved session is still valid"""
        if not SPOTAPI_AVAILABLE:
            return {"valid": False, "error": "SpotAPI not installed"}
        
        if not self._session_file.exists():
            return {"valid": False, "error": "No saved session"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _check():
                cfg = Config(logger=NoopLogger())
                saver = JSONSaver(self._session_file)
                # Try to load the session
                identifier = "user"  # Default identifier
                instance = Login.from_saver(saver, cfg, identifier)
                return instance
            
            self._login_instance = await loop.run_in_executor(None, _check)
            self._player = Player(self._login_instance)
            self._player_status = PlayerStatus(self._login_instance)
            self._is_logged_in = True
            
            return {"valid": True}
            
        except Exception as e:
            self._is_logged_in = False
            return {"valid": False, "error": str(e)}

    # ==================== PLAYER CONTROLS ====================

    async def _refresh_playback_state(self):
        """Refresh current playback state from Spotify"""
        if not self._is_logged_in or not self._player_status:
            return
        
        try:
            loop = asyncio.get_event_loop()
            
            def _get_state():
                return self._player_status.get_current_state()
            
            state = await loop.run_in_executor(None, _get_state)
            
            if state:
                self._playback_state = {
                    "is_playing": state.get("is_playing", False),
                    "track_id": state.get("item", {}).get("id") if state.get("item") else None,
                    "track_name": state.get("item", {}).get("name") if state.get("item") else None,
                    "artist_name": state.get("item", {}).get("artists", [{}])[0].get("name") if state.get("item") else None,
                    "album_name": state.get("item", {}).get("album", {}).get("name") if state.get("item") else None,
                    "progress_ms": state.get("progress_ms", 0),
                    "duration_ms": state.get("item", {}).get("duration_ms", 0) if state.get("item") else 0,
                    "volume_percent": state.get("device", {}).get("volume_percent", 100) if state.get("device") else 100,
                    "device_id": state.get("device", {}).get("id") if state.get("device") else None,
                    "device_name": state.get("device", {}).get("name") if state.get("device") else None,
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            print(f"Error refreshing playback state: {e}")
            # Don't mark as logged out on error, just keep old state

    async def play_track(self, track_id: str, context_uri: Optional[str] = None) -> Dict[str, Any]:
        """
        Play a specific track
        
        Args:
            track_id: Spotify track ID
            context_uri: Optional context (playlist/album URI)
        
        Returns:
            Dictionary with success status
        """
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _play():
                # Format track URI
                track_uri = f"spotify:track:{track_id}"
                self._player.play_track(track_uri, context_uri)
            
            await loop.run_in_executor(None, _play)
            await self._refresh_playback_state()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def pause(self) -> Dict[str, Any]:
        """Pause playback"""
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _pause():
                self._player.pause()
            
            await loop.run_in_executor(None, _pause)
            await self._refresh_playback_state()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def resume(self) -> Dict[str, Any]:
        """Resume playback"""
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _resume():
                self._player.resume()
            
            await loop.run_in_executor(None, _resume)
            await self._refresh_playback_state()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def next_track(self) -> Dict[str, Any]:
        """Skip to next track"""
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _next():
                self._player.skip_next()
            
            await loop.run_in_executor(None, _next)
            await self._refresh_playback_state()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def previous_track(self) -> Dict[str, Any]:
        """Go to previous track"""
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _prev():
                self._player.skip_prev()
            
            await loop.run_in_executor(None, _prev)
            await self._refresh_playback_state()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def seek(self, position_ms: int) -> Dict[str, Any]:
        """
        Seek to position in current track
        
        Args:
            position_ms: Position in milliseconds
        """
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _seek():
                self._player.seek_to(position_ms)
            
            await loop.run_in_executor(None, _seek)
            await self._refresh_playback_state()
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_volume(self, volume_percent: float) -> Dict[str, Any]:
        """
        Set playback volume
        
        Args:
            volume_percent: Volume from 0.0 to 1.0
        """
        if not self._is_logged_in or not self._player:
            return {"success": False, "error": "Not logged in"}
        
        try:
            loop = asyncio.get_event_loop()
            
            def _set_volume():
                self._player.set_volume(volume_percent)
            
            await loop.run_in_executor(None, _set_volume)
            self._playback_state["volume_percent"] = int(volume_percent * 100)
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_playback_state(self) -> Dict[str, Any]:
        """Get current playback state"""
        await self._refresh_playback_state()
        return self._playback_state

    # ==================== SEARCH (Public API) ====================
    
    # ==================== SEARCH (Public API) ====================

    async def search(self, query: str, search_type: str = "track", limit: int = 10) -> Dict[str, Any]:
        """
        Search Spotify for tracks, artists, or albums
        
        Args:
            query: Search query string
            search_type: Type of search - "track", "artist", "album", or "all"
            limit: Maximum number of results
        
        Returns:
            Dictionary with search results
        """
        if not SPOTAPI_AVAILABLE:
            return {
                "error": "SpotAPI not installed",
                "tracks": [],
                "artists": [],
                "albums": []
            }
        
        self._init_clients()
        
        results = {
            "tracks": [],
            "artists": [],
            "albums": []
        }
        
        try:
            if search_type in ["track", "all"]:
                results["tracks"] = await self._search_tracks(query, limit)
            
            if search_type in ["artist", "all"]:
                results["artists"] = await self._search_artists(query, limit)
            
            if search_type in ["album", "all"]:
                results["albums"] = await self._search_albums(query, limit)
            
            self.last_search_results = results
            self.last_update = datetime.now()
            
        except Exception as e:
            print(f"Spotify search error: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _search_tracks(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search for tracks"""
        if not self._song_client:
            return []
        
        try:
            # Run synchronous SpotAPI calls in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self._song_client.query_songs(query, limit=limit)
            )
            
            # Extract tracks from response structure
            # Response format: {'data': {'searchV2': {'tracksV2': {'items': [{'item': {'data': ...}}]}}}}
            tracks = []
            if isinstance(response, dict):
                data = response.get('data', {})
                search_v2 = data.get('searchV2', {})
                tracks_v2 = search_v2.get('tracksV2', {})
                items = tracks_v2.get('items', [])
                # Each item has 'item' key with 'data' containing track info
                for item in items:
                    if isinstance(item, dict) and 'item' in item:
                        item_data = item['item']
                        if isinstance(item_data, dict) and 'data' in item_data:
                            tracks.append(item_data['data'])
            
            # Format results
            formatted = []
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                artists = track.get('artists', {}).get('items', [])
                artist_name = artists[0].get('profile', {}).get('name', 'Unknown') if artists else 'Unknown'
                
                album = track.get('albumOfTrack', {})
                album_name = album.get('name', 'Unknown')
                
                track_id = track.get('id', '')
                track_name = track.get('name', 'Unknown')
                duration = track.get('duration', {}).get('totalMilliseconds', 0)
                
                formatted.append({
                    "id": track_id,
                    "name": track_name,
                    "artist": artist_name,
                    "album": album_name,
                    "duration_ms": duration,
                    "popularity": track.get('popularity', 0),
                    "preview_url": None,  # Not available in this API
                    "external_url": f"https://open.spotify.com/track/{track_id}"
                })
            return formatted
            
        except Exception as e:
            print(f"Track search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _search_artists(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search for artists"""
        if not self._artist_client:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            artists = await loop.run_in_executor(
                None,
                lambda: self._artist_client.search_artist(query, limit=limit)
            )
            
            formatted = []
            for artist in artists:
                formatted.append({
                    "id": artist.get("id"),
                    "name": artist.get("name"),
                    "genres": artist.get("genres", []),
                    "popularity": artist.get("popularity"),
                    "followers": artist.get("followers", {}).get("total", 0),
                    "images": artist.get("images", []),
                    "external_url": f"https://open.spotify.com/artist/{artist.get('id')}"
                })
            return formatted
            
        except Exception as e:
            print(f"Artist search error: {e}")
            return []
    
    async def _search_albums(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search for albums"""
        if not self._song_client:
            return []
        
        try:
            # Album search is done through song client with album filter
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._song_client.query_songs(f"album:{query}", limit=limit)
            )
            
            # Extract unique albums
            albums_map = {}
            for track in results:
                album = track.get("album", {})
                album_id = album.get("id")
                if album_id and album_id not in albums_map:
                    albums_map[album_id] = {
                        "id": album_id,
                        "name": album.get("name"),
                        "artist": album.get("artists", [{}])[0].get("name", "Unknown"),
                        "release_date": album.get("release_date"),
                        "total_tracks": album.get("total_tracks"),
                        "images": album.get("images", []),
                        "external_url": f"https://open.spotify.com/album/{album_id}"
                    }
            
            return list(albums_map.values())[:limit]
            
        except Exception as e:
            print(f"Album search error: {e}")
            return []
    
    async def get_track_info(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific track"""
        if not SPOTAPI_AVAILABLE or not self._song_client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(
                None,
                lambda: self._song_client.get_song_info(track_id)
            )
            
            if not track:
                return None
            
            return {
                "id": track.get("id"),
                "name": track.get("name"),
                "artists": [a.get("name") for a in track.get("artists", [])],
                "album": track.get("album", {}).get("name"),
                "duration_ms": track.get("duration_ms"),
                "duration_formatted": self._format_duration(track.get("duration_ms", 0)),
                "popularity": track.get("popularity"),
                "explicit": track.get("explicit"),
                "preview_url": track.get("preview_url"),
                "external_url": f"https://open.spotify.com/track/{track_id}",
                "images": track.get("album", {}).get("images", [])
            }
            
        except Exception as e:
            print(f"Track info error: {e}")
            return None
    
    async def get_artist_info(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific artist"""
        if not SPOTAPI_AVAILABLE or not self._artist_client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            artist = await loop.run_in_executor(
                None,
                lambda: self._artist_client.get_artist(artist_id)
            )
            
            if not artist:
                return None
            
            return {
                "id": artist.get("id"),
                "name": artist.get("name"),
                "genres": artist.get("genres", []),
                "popularity": artist.get("popularity"),
                "followers": artist.get("followers", {}).get("total", 0),
                "images": artist.get("images", []),
                "external_url": f"https://open.spotify.com/artist/{artist_id}"
            }
            
        except Exception as e:
            print(f"Artist info error: {e}")
            return None
    
    async def get_album_info(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific album"""
        if not SPOTAPI_AVAILABLE or not self._album_client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            album = await loop.run_in_executor(
                None,
                lambda: self._album_client.get_album_info(album_id)
            )
            
            if not album:
                return None
            
            return {
                "id": album.get("id"),
                "name": album.get("name"),
                "artists": [a.get("name") for a in album.get("artists", [])],
                "release_date": album.get("release_date"),
                "total_tracks": album.get("total_tracks"),
                "album_type": album.get("album_type"),
                "images": album.get("images", []),
                "external_url": f"https://open.spotify.com/album/{album_id}"
            }
            
        except Exception as e:
            print(f"Album info error: {e}")
            return None
    
    async def get_playlist_info(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a public playlist"""
        if not SPOTAPI_AVAILABLE or not self._playlist_client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            playlist = await loop.run_in_executor(
                None,
                lambda: self._playlist_client.get_playlist_info(playlist_id)
            )
            
            if not playlist:
                return None
            
            return {
                "id": playlist.get("id"),
                "name": playlist.get("name"),
                "description": playlist.get("description"),
                "owner": playlist.get("owner", {}).get("display_name"),
                "followers": playlist.get("followers", {}).get("total", 0),
                "images": playlist.get("images", []),
                "external_url": f"https://open.spotify.com/playlist/{playlist_id}"
            }
            
        except Exception as e:
            print(f"Playlist info error: {e}")
            return None
    
    @staticmethod
    def _format_duration(ms: int) -> str:
        """Format milliseconds to MM:SS"""
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"