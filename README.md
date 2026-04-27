# OpenClaw Dashboard

Modular dashboard for Raspberry Pi - Real-time download tracking, weather, and media suggestions.

## Features

- 🎯 **Modular Cards System**: Cards of different sizes (1x1, 2x1, 2x2, full-width)
- ⬇️ **Download Tracking**: Real-time monitoring of downloads via AllDebrid
- 🌤️ **Weather**: Current conditions and forecast for Ajaccio, France
- 💡 **Media Suggestions**: Movies, series, and books recommendations
- 🎨 **Responsive Design**: 4-column grid on desktop, adaptive on mobile
- 🔄 **Live Updates**: WebSocket connection for real-time data

## Quick Start

```bash
# Build and run
docker build -t openclaw-dashboard .
docker run -d -p 8080:8080 openclaw-dashboard
```

Access at `http://localhost:8080`

## Card Sizes

- **1x1** (card-size-1): Quarter width - perfect for compact info
- **2x1** (card-size-2): Half width - default for most cards
- **2x2** (card-size-3): Half width, double height - for detailed content
- **Full** (card-size-4): Full width - for extensive data

Double-click any card header to cycle through sizes.

## Project Structure

```
dashboard/
├── backend/
│   ├── cards/           # Modular card implementations
│   ├── main.py         # FastAPI server
│   └── requirements.txt
├── frontend/
│   ├── css/
│   ├── js/
│   └── index.html
└── Dockerfile
```

## Tech Stack

- **Backend**: FastAPI + SQLite + WebSocket
- **Frontend**: Vanilla JS + CSS Grid
- **Container**: Docker

## License

MIT
