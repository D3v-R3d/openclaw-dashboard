/**
 * OpenClaw Dashboard - Main App
 */

class Dashboard {
    constructor() {
        this.ws = null;
        this.cards = {};
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.init();
    }

    init() {
        this.initTheme();
        this.initWebSocket();
        this.fetchCards();
        this.initEventListeners();
        
        // Update time every second
        setInterval(() => this.updateTimestamp(), 1000);
        
        // Periodic fetch (fallback if WebSocket fails)
        setInterval(() => this.fetchCards(), 30000);
    }
    
    // Event Listeners
    initEventListeners() {
        // Refresh button - reloads all card data
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                refreshBtn.style.transform = 'rotate(360deg)';
                setTimeout(() => refreshBtn.style.transform = '', 500);
                this.fetchCards();
            });
        }
    }

    // Theme Management
    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        document.getElementById('theme-toggle').addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // WebSocket Connection
    initWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
            this.reconnectDelay = 1000; // Reset delay
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        // Send ping every 30s to keep connection alive
        setInterval(() => {
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000);
    }

    scheduleReconnect() {
        setTimeout(() => {
            console.log(`Reconnecting in ${this.reconnectDelay}ms...`);
            this.initWebSocket();
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        }, this.reconnectDelay);
    }

    handleWebSocketMessage(data) {
        if (data.type === 'card_update') {
            this.updateCard(data.card, data.data);
        } else if (data.type === 'pong') {
            // Connection is alive
        }
    }

    updateConnectionStatus(connected) {
        const statusBadge = document.getElementById('connection-status');
        if (connected) {
            statusBadge.innerHTML = '🟢 Connecté';
            statusBadge.style.color = 'var(--accent-success)';
        } else {
            statusBadge.innerHTML = '🔴 Déconnecté';
            statusBadge.style.color = 'var(--accent-danger)';
        }
    }

    // Fetch Cards Data
    async fetchCards() {
        try {
            const response = await fetch('/api/cards');
            const cards = await response.json();
            this.renderCards(cards);
        } catch (error) {
            console.error('Error fetching cards:', error);
        }
    }

    // Render Cards
    renderCards(cards) {
        const container = document.getElementById('cards-container');
        
        // Default sizes for each card type
        const defaultSizes = {
            'downloads': 'card-size-2',
            'weather': 'card-size-1',
            'suggestions': 'card-size-2'
        };
        
        for (const [cardId, cardData] of Object.entries(cards)) {
            if (!this.cards[cardId]) {
                // Create new card
                const cardElement = this.createCardElement(cardId, cardData);
                // Apply saved or default size
                const savedSize = localStorage.getItem(`card-${cardId}-size`) || defaultSizes[cardId] || 'card-size-1';
                cardElement.classList.add(savedSize);
                container.appendChild(cardElement);
                this.cards[cardId] = cardElement;
            }
            // Update card content
            this.updateCardContent(cardId, cardData);
        }
    }

    createCardElement(cardId, cardData) {
        const card = document.createElement('div');
        card.className = 'card';
        card.id = `card-${cardId}`;
        card.dataset.cardId = cardId;
        
        // Load collapsed state from localStorage
        const isCollapsed = localStorage.getItem(`card-${cardId}-collapsed`) === 'true';
        
        card.innerHTML = `
            <div class="card-header ${isCollapsed ? 'collapsed' : ''}" data-card-id="${cardId}">
                <h2 class="card-title">
                    <span class="card-icon">${this.getCardIcon(cardId)}</span>
                    ${cardData.name}
                </h2>
                <div class="card-actions">
                    <span class="card-badge" id="badge-${cardId}">Chargement...</span>
                    <span class="card-toggle">▼</span>
                </div>
            </div>
            <div class="card-content ${isCollapsed ? 'collapsed' : ''}" id="content-${cardId}">
                <div class="loading">Chargement...</div>
            </div>
        `;
        
        // Attach click event properly
        const header = card.querySelector('.card-header');
        header.addEventListener('click', () => this.toggleCard(cardId));
        
        // Double-click to cycle size
        header.addEventListener('dblclick', () => this.cycleCardSize(cardId));
        
        return card;
    }
    
    cycleCardSize(cardId) {
        const card = document.getElementById(`card-${cardId}`);
        const sizes = ['card-size-1', 'card-size-2', 'card-size-3', 'card-size-4'];
        
        // Find current size
        let currentSize = sizes.find(s => card.classList.contains(s)) || 'card-size-1';
        let currentIndex = sizes.indexOf(currentSize);
        
        // Remove current size
        card.classList.remove(currentSize);
        
        // Next size (cycle)
        let nextSize = sizes[(currentIndex + 1) % sizes.length];
        card.classList.add(nextSize);
        
        // Save
        localStorage.setItem(`card-${cardId}-size`, nextSize);
        
        console.log(`Card ${cardId} size: ${nextSize}`);
    }
    
    toggleCard(cardId) {
        const header = document.querySelector(`#card-${cardId} .card-header`);
        const content = document.getElementById(`content-${cardId}`);
        const isCollapsed = content.classList.toggle('collapsed');
        header.classList.toggle('collapsed', isCollapsed);
        
        // Save state
        localStorage.setItem(`card-${cardId}-collapsed`, isCollapsed);
    }

    getCardIcon(cardId) {
        const icons = {
            'downloads': '⬇️',
            'weather': '🌤️',
            'suggestions': '💡',
            'system': '💻',
            'network': '🌐',
            'spotify': '🎵',
            'default': '📊'
        };
        return icons[cardId] || icons['default'];
    }

    updateCard(cardId, data) {
        const cardData = { name: this.cards[cardId]?.querySelector('.card-title')?.textContent?.trim() || cardId, data };
        this.updateCardContent(cardId, cardData);
    }

    updateCardContent(cardId, cardData) {
        const content = document.getElementById(`content-${cardId}`);
        const badge = document.getElementById(`badge-${cardId}`);
        
        if (!content) return;

        // Update badge based on card type
        if (cardId === 'downloads') {
            const active = cardData.data?.active_count || 0;
            badge.textContent = active > 0 ? `${active} actif(s)` : 'À jour';
        } else if (cardId === 'weather') {
            badge.textContent = cardData.data?.current?.temp ? `${cardData.data.current.temp}°C` : '-';
        } else if (cardId === 'suggestions') {
            badge.textContent = '✨';
        }

        // Render specific card content
        switch (cardId) {
            case 'downloads':
                content.innerHTML = this.renderDownloadsCard(cardData.data);
                break;
            case 'weather':
                content.innerHTML = this.renderWeatherCard(cardData.data);
                break;
            case 'suggestions':
                content.innerHTML = this.renderSuggestionsCard(cardData.data);
                break;
            case 'spotify':
                content.innerHTML = this.renderSpotifyCard(cardData.data);
                break;
            default:
                content.innerHTML = `<pre>${JSON.stringify(cardData.data, null, 2)}</pre>`;
        }
    }

    // Downloads Card Renderer
    renderDownloadsCard(data) {
        if (!data?.downloads?.length) {
            return '<div class="downloads-list"><p style="text-align: center; color: var(--text-muted);">Aucun téléchargement actif</p></div>';
        }

        const downloads = data.downloads.map(dl => `
            <div class="download-item ${dl.status}">
                <div class="download-header">
                    <div class="download-name">${dl.name}</div>
                    <span class="download-status ${dl.status}">${dl.status === 'completed' ? '✓ Terminé' : '⬇️ Téléchargement'}</span>
                </div>
                <div class="download-meta">
                    <span>${dl.size_gb} GB • ${dl.source}</span>
                    <span>${dl.location}</span>
                </div>
                ${dl.status === 'downloading' ? `
                    <div class="download-progress">
                        <div class="download-progress-bar" style="width: ${dl.progress}%"></div>
                    </div>
                    <div class="download-stats">
                        <span>${dl.progress}%</span>
                        <span>${dl.speed} • ${dl.eta}</span>
                    </div>
                ` : ''}
            </div>
        `).join('');

        return `<div class="downloads-list">${downloads}</div>`;
    }

    // Weather Card Renderer
    renderWeatherCard(data) {
        if (!data?.current) {
            return '<div style="text-align: center; color: var(--text-muted);">Chargement météo...</div>';
        }

        const current = data.current;
        const forecast = data.forecast || [];
        
        const forecastHtml = forecast.slice(0, 3).map(day => `
            <div class="forecast-day">
                <div class="forecast-date">${new Date(day.date).toLocaleDateString('fr-FR', { weekday: 'narrow' })}</div>
                <div class="forecast-temps">
                    <span class="forecast-temp-high">${Math.round(day.temp_max)}°</span>
                    <span class="forecast-temp-low">${Math.round(day.temp_min)}°</span>
                </div>
            </div>
        `).join('');

        return `
            <div class="weather-compact">
                <div class="weather-main">
                    <div class="weather-temp-large">${Math.round(current.temp)}°</div>
                    <div class="weather-info">
                        <div class="weather-condition">${current.condition}</div>
                        <div class="weather-location-small">${data.location}</div>
                    </div>
                </div>
                <div class="weather-forecast-compact">
                    ${forecastHtml}
                </div>
            </div>
        `;
    }

    // Suggestions Card Renderer
    renderSuggestionsCard(data) {
        if (!data?.suggestions) {
            return '<div style="text-align: center; color: var(--text-muted);">Chargement suggestions...</div>';
        }

        const s = data.suggestions;
        
        const filmsHtml = s.films.map(film => `
            <div class="suggestion-item film">
                <div class="suggestion-icon">🎬</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">${film.title}</div>
                    <div class="suggestion-meta">${film.year} • ${film.genre} • ⭐ ${film.rating}</div>
                </div>
                <button class="btn-download" onclick="window.open('https://c411.org', '_blank')">🔍</button>
            </div>
        `).join('');
        
        const seriesHtml = s.series.map(serie => `
            <div class="suggestion-item serie">
                <div class="suggestion-icon">📺</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">${serie.title}</div>
                    <div class="suggestion-meta">${serie.seasons} saisons • ${serie.genre} • ⭐ ${serie.rating}</div>
                </div>
                <button class="btn-download" onclick="window.open('https://c411.org', '_blank')">🔍</button>
            </div>
        `).join('');
        
        const livresHtml = s.livres.map(livre => `
            <div class="suggestion-item livre">
                <div class="suggestion-icon">📚</div>
                <div class="suggestion-content">
                    <div class="suggestion-title">${livre.title}</div>
                    <div class="suggestion-meta">${livre.author} • ${livre.genre}</div>
                </div>
                <button class="btn-download" onclick="window.open('https://www.google.com/search?q=${encodeURIComponent(livre.title + ' ' + livre.author)}', '_blank')">🔍</button>
            </div>
        `).join('');
        
        return `
            <div class="suggestions-list">
                ${filmsHtml}
                ${seriesHtml}
                ${livresHtml}
            </div>
            
            <div class="suggestion-refresh">
                <button class="btn-refresh" onclick="dashboard.refreshSuggestions()">
                    🔄 Nouvelles suggestions
                </button>
            </div>
        `;
    }

    refreshSuggestions() {
        // Force refresh via API
        fetch('/api/cards/suggestions/refresh', { method: 'POST' })
            .then(() => this.fetchCards())
            .catch(err => console.error('Error refreshing suggestions:', err));
    }


    // Spotify Card Renderer
    renderSpotifyCard(data) {
        if (!data) data = {};
        
        if (!data.available) {
            return `<div class="spotify-status">
                <div class="spotify-status-icon">🎧</div>
                <div class="spotify-status-text">SpotAPI n'est pas installé</div>
            </div>`;
        }

        if (!data.logged_in) {
            return `<div class="spotify-login">
                <div class="spotify-login-header">
                    <div class="spotify-login-icon">🎧</div>
                    <h3>Connectez votre compte Spotify</h3>
                </div>
                <button class="spotify-btn" onclick="dashboard.spotifyRefresh()">🔄 Rafraîchir</button>
            </div>`;
        }

        return this.renderSpotifyPlayer(data);
    }

    renderSpotifyPlayer(data) {
        const playback = (data && data.playback_state) || {};
        const isPlaying = (playback && playback.is_playing) || false;
        const trackName = (playback && playback.track_name) || 'Aucune lecture';
        const artistName = (playback && playback.artist_name) || '-';
        const progress = (playback && playback.progress_ms) || 0;
        const duration = (playback && playback.duration_ms) || 0;
        
        const progressPercent = duration > 0 ? (progress / duration) * 100 : 0;
        const currentTime = this.formatDuration(progress);
        const totalTime = this.formatDuration(duration);
        
        return `<div class="spotify-player">
            <div class="spotify-track-info">
                <div>${trackName}</div>
                <div>${artistName}</div>
            </div>
            <div class="spotify-progress-bar">
                <div style="width: ${progressPercent}%"></div>
            </div>
            <div class="spotify-time">${currentTime} / ${totalTime}</div>
            <div class="spotify-controls">
                <button onclick="dashboard.spotifyPrevious()">⏮️</button>
                <button onclick="dashboard.spotifyPlayPause()">${isPlaying ? '⏸️' : '▶️'}</button>
                <button onclick="dashboard.spotifyNext()">⏭️</button>
            </div>
            <div class="spotify-search">
                <input type="text" id="spotify-search-input" placeholder="Rechercher..."
                       onkeypress="if(event.key==='Enter')dashboard.spotifySearch()">
                <button onclick="dashboard.spotifySearch()">🔍</button>
            </div>
            <div id="spotify-search-results"></div>
        </div>`;
    }

    async spotifySearch() {
        const input = document.getElementById('spotify-search-input');
        if (!input) return;
        const query = input.value.trim();
        if (!query) return;
        
        try {
            const response = await fetch(`/api/cards/spotify/search?query=${encodeURIComponent(query)}&type=track&limit=10`);
            const data = await response.json();
            
            const resultsDiv = document.getElementById('spotify-search-results');
            if (!resultsDiv) return;
            
            if (data.tracks && data.tracks.length > 0) {
                resultsDiv.innerHTML = data.tracks.map(track => `
                    <div onclick="dashboard.spotifyPlayTrack('${track.id}')"
                         style="cursor: pointer; padding: 8px; border-bottom: 1px solid #eee;">
                        <div>${track.name}</div>
                        <div style="font-size: 0.8em; color: #666;">${track.artist}</div>
                    </div>
                `).join('');
            } else {
                resultsDiv.innerHTML = '<div>Aucun résultat</div>';
            }
        } catch (e) {
            console.error('Search error:', e);
        }
    }

    async spotifyPlayTrack(trackId) {
        try {
            await fetch(`/api/cards/spotify/play/${trackId}`, { method: 'POST' });
        } catch (e) {
            console.error('Play error:', e);
        }
    }

    async spotifyPlayPause() {
        try {
            await fetch('/api/cards/spotify/resume', { method: 'POST' });
        } catch (e) {
            console.error('Play/pause error:', e);
        }
    }

    async spotifyNext() {
        try {
            await fetch('/api/cards/spotify/next', { method: 'POST' });
        } catch (e) {
            console.error('Next error:', e);
        }
    }

    async spotifyPrevious() {
        try {
            await fetch('/api/cards/spotify/previous', { method: 'POST' });
        } catch (e) {
            console.error('Previous error:', e);
        }
    }

    async spotifyRefresh() {
        this.fetchCards();
    }

    updateTimestamp() {
        const element = document.getElementById('last-update');
        if (element) {
            element.textContent = new Date().toLocaleTimeString('fr-FR');
        }
    }
    
        // Utility: Format duration in ms to mm:ss
    formatDuration(ms) {
        if (!ms || ms <= 0) return '0:00';
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
}

// Initialize Dashboard when DOM is ready
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new Dashboard();
});
