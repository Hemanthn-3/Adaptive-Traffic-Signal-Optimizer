<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=2,3,30&height=240&section=header&text=FlowMind%20AI&fontSize=80&fontColor=ffffff&fontAlignY=38&desc=Smart%20Traffic%20Management%20System&descAlignY=60&descSize=24&animation=fadeIn"/>

<br/>

<img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=18&duration=3000&pause=1000&color=38BDF8&center=true&vCenter=true&width=800&lines=🚦+Real-Time+Adaptive+Signal+Control+with+YOLOv8;🚨+Emergency+Green+Corridor+in+Seconds;📡+Live+WebSocket+Dashboard+%2B+MQTT+Hardware+Bridge;🧠+AI-Powered+Lane+Density+Estimation+from+Video;⚡+FastAPI+%2B+React+%2B+TimescaleDB+%2B+Redis+Stack" alt="Typing SVG" />

<br/>

<p>
  <img src="https://img.shields.io/badge/Status-🟢_Active-22d3ee?style=for-the-badge" />
  <img src="https://img.shields.io/badge/AI-YOLOv8_Vision-EF4444?style=for-the-badge&logo=opencv&logoColor=white" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Frontend-React+Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" />
  <img src="https://img.shields.io/badge/DB-TimescaleDB-FDB515?style=for-the-badge&logo=postgresql&logoColor=black" />
  <img src="https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge" />
</p>

<br/>

> ### *Cities don't have traffic problems — they have intelligence problems. We fix that.*

<br/>

<img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6edaec5c.gif" width="100%"/>

</div>

---

## 🧠 What is FlowMind AI?

**FlowMind AI** is a production-grade, AI-powered adaptive traffic management system that replaces dumb fixed-cycle signals with real-time intelligence. Using computer vision (YOLOv8), it continuously measures vehicle density per lane, dynamically computes optimal green durations, and instantly clears corridors for emergency vehicles — all visible on a live React dashboard with WebSocket updates.

```
📹 Live Video Feed  →  🧠 YOLOv8 Detects Vehicles  →  📊 Density Computed  →  🚦 Signal Adapts  →  📡 Dashboard Updates
```

This isn't a prototype. It's a full stack — FastAPI backend, React + Vite dashboard, PostgreSQL/TimescaleDB for time-series data, Redis for hot-path state, Mosquitto MQTT for hardware signalling, and a complete Docker Compose environment for one-command local deployment.

---

## ✨ Core Features

<div align="center">

| Module | Capability | Technology |
|:---:|---|:---:|
| 🎥 **Video Processing** | Frame-by-frame vehicle detection from live or uploaded feeds | YOLOv8 + OpenCV |
| 📊 **Density Engine** | Per-lane vehicle count normalized to capacity percentage | Custom ML Pipeline |
| 🚦 **Adaptive Signals** | Dynamic green/yellow durations scaled to real traffic load | FastAPI + Redis |
| 🚨 **Emergency Corridor** | One-click green path creation across any intersection chain | MQTT + WebSocket |
| 📡 **Live Dashboard** | Real-time signal states, density heatmaps, emergency alerts | React + WebSocket |
| 🕒 **Time-Series DB** | Full historical density & signal event storage with pagination | TimescaleDB (PostgreSQL) |
| 🔧 **Manual Override** | Per-intersection signal timing override for operators | REST API |
| 🐳 **Full Docker Stack** | One command brings up all 7 services including hardware sim | Docker Compose v2 |

</div>

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────┐
│         Browser Dashboard  (React + Vite)        │
│    REST  ◄──────────────────────►  WebSocket     │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              FastAPI  Backend                    │
│   ┌─────────┐  ┌──────────┐  ┌───────────────┐  │
│   │ Traffic │  │ Signals  │  │  Emergency    │  │
│   │  API    │  │  API     │  │   API         │  │
│   └────┬────┘  └────┬─────┘  └──────┬────────┘  │
└────────┼────────────┼───────────────┼────────────┘
         │            │               │
┌────────▼───┐  ┌─────▼──────┐  ┌────▼──────────┐
│ TimescaleDB│  │   Redis    │  │  Mosquitto    │
│(time-series│  │(state cache│  │  MQTT Broker  │
│  history)  │  │  hot-path) │  │ (HW signals)  │
└────────────┘  └────────────┘  └───────────────┘
                                        │
                              ┌─────────▼─────────┐
                              │  Signal Hardware  │
                              │  / Simulator      │
                              └───────────────────┘
         ▲
         │
┌────────┴──────────────────────────────────────┐
│        ML Pipeline  (YOLOv8)                   │
│  video_processor.py  ──►  POST /api/traffic/   │
│                              video/process     │
└────────────────────────────────────────────────┘
```

---

## 🔁 Signal Optimization Flow

```mermaid
flowchart TD
    A([📹 Video Frame Received]) --> B[🧠 YOLOv8 Vehicle Detection]
    B --> C[📊 Per-Lane Density Calculation]
    C --> D{Density vs Capacity}
    D -- Normal --> E[⚙️ Adaptive Green Duration\nscaled to density %]
    D -- Emergency Active --> F[🚨 Override: Full Green\non Emergency Corridor]
    E --> G[📡 MQTT Signal Command\nto Hardware / Simulator]
    F --> G
    G --> H[💾 TimescaleDB\nEvent Logged]
    H --> I[🔄 WebSocket Push\nto All Dashboard Clients]
    I --> J([🖥️ Live Dashboard Updated])

    style A fill:#0f172a,color:#38bdf8,stroke:#38bdf8
    style B fill:#0f172a,color:#a78bfa,stroke:#a78bfa
    style C fill:#0f172a,color:#34d399,stroke:#34d399
    style D fill:#0f172a,color:#fbbf24,stroke:#fbbf24
    style E fill:#0f172a,color:#34d399,stroke:#34d399
    style F fill:#0f172a,color:#f87171,stroke:#f87171
    style G fill:#0f172a,color:#60a5fa,stroke:#60a5fa
    style H fill:#0f172a,color:#fbbf24,stroke:#fbbf24
    style I fill:#0f172a,color:#818cf8,stroke:#818cf8
    style J fill:#0f172a,color:#38bdf8,stroke:#38bdf8
```

---

## 🧰 Tech Stack

<div align="center">

**Backend**

![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic_Migrations-6B7280?style=for-the-badge&logo=alembic&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Live_Updates-0EA5E9?style=for-the-badge)

**Database & Messaging**

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-Time--Series-FDB515?style=for-the-badge&logo=timescale&logoColor=black)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![MQTT](https://img.shields.io/badge/Mosquitto_MQTT-660066?style=for-the-badge&logo=eclipsemosquitto&logoColor=white)

**AI / ML**

![YOLOv8](https://img.shields.io/badge/YOLOv8-Object_Detection-EF4444?style=for-the-badge&logo=opencv&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Video_Pipeline-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)

**Frontend**

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)

**Infrastructure**

![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

</div>

---

## 📂 Project Structure

```
flowmind-ai/
│
├── 📁 backend/                          # FastAPI application
│   ├── 📁 app/
│   │   ├── main.py                      # App entry point, WebSocket hub
│   │   ├── 📁 api/
│   │   │   ├── traffic.py               # Density & intersection endpoints
│   │   │   ├── signals.py               # Signal state & override endpoints
│   │   │   └── emergency.py             # Corridor activation endpoints
│   │   ├── 📁 services/
│   │   │   ├── signal_optimizer.py      # Adaptive timing algorithm
│   │   │   ├── mqtt_client.py           # MQTT hardware bridge
│   │   │   └── redis_cache.py           # Hot-path state management
│   │   └── 📁 models/                   # SQLAlchemy ORM models
│   ├── 📁 migrations/                   # Alembic migration scripts
│   └── requirements.txt
│
├── 📁 frontend/                         # React + Vite dashboard
│   ├── 📁 src/
│   │   ├── 📁 components/
│   │   │   ├── IntersectionCard.jsx     # Per-intersection signal display
│   │   │   ├── DensityHeatmap.jsx       # Live lane density visualization
│   │   │   ├── EmergencyPanel.jsx       # Corridor control UI
│   │   │   └── WebSocketProvider.jsx   # Live update context
│   │   └── 📁 pages/
│   │       ├── Dashboard.jsx            # Main ops dashboard
│   │       └── History.jsx              # Time-series density history
│   └── package.json
│
├── 📁 ml/                               # YOLOv8 ML pipeline
│   ├── video_processor.py               # Core detection + density script
│   ├── 📁 test_videos/                  # Sample footage for testing
│   └── requirements.txt
│
├── 📁 mosquitto/                        # MQTT broker config
│   └── mosquitto.conf
│
├── demo.py                              # End-to-end demo script
├── docker-compose.yml                   # Full local stack definition
├── .env.example                         # Environment template
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites

| Tool | Min Version |
|---|:---:|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker + Compose | 24+ / v2+ |

---

### Option A — Full Docker Stack (Recommended)

One command brings up all 7 services.

```bash
git clone https://github.com/your-username/flowmind-ai.git
cd flowmind-ai
cp .env.example .env
docker compose up -d --build
```

| Service | URL |
|---|---|
| 🖥️ Dashboard | http://localhost:5173 |
| ⚙️ API | http://localhost:8000 |
| 📄 API Docs (Swagger) | http://localhost:8000/docs |
| 📡 MQTT | localhost:1883 |
| 📡 MQTT WebSocket | localhost:9001 |

---

### Option B — Local Development

**1. Start infrastructure services**
```bash
cp .env.example .env
docker compose up -d postgres redis mosquitto
```

**2. Backend**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev
```

**4. Open Dashboard** → `http://localhost:5173`

---

## 🔧 Environment Variables

> Copy `.env.example` to `.env` and configure:

**Application**
| Variable | Description |
|---|---|
| `APP_ENV` | `development` or `production` |
| `SECRET_KEY` | Secret key for auth & signing |
| `DEBUG` | Enable debug logging (`true`/`false`) |

**Database**
| Variable | Example |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/traffic_db` |

**Redis**
| Variable | Example |
|---|---|
| `REDIS_URL` | `redis://:password@host:6379/0` |

**MQTT**
| Variable | Description |
|---|---|
| `MQTT_BROKER_HOST` | Broker hostname |
| `MQTT_BROKER_PORT` | Default `1883` |
| `MQTT_USERNAME` | Broker auth username |
| `MQTT_PASSWORD` | Broker auth password |
| `MQTT_CLIENT_ID` | Unique client identifier |

**Frontend**
| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | REST API base URL |
| `VITE_WS_URL` | WebSocket URL for live updates |

**ML / YOLOv8**
| Variable | Example |
|---|---|
| `YOLO_MODEL_PATH` | `yolov8n.pt` |
| `VEHICLE_CLASSES` | `2,3,5,7` (COCO class IDs) |
| `MAX_LANE_CAPACITY` | Used to normalize density (e.g. `20`) |
| `FRAME_SKIP` | Process every Nth frame (e.g. `3`) |

**Signal Timing**
| Variable | Description |
|---|---|
| `MIN_GREEN_DURATION` | Minimum green phase (seconds) |
| `MAX_GREEN_DURATION` | Maximum green phase (seconds) |
| `DEFAULT_YELLOW_DURATION` | Yellow transition duration |
| `EMERGENCY_GREEN_DURATION` | Override duration for emergency corridors |

**CORS**
| Variable | Example |
|---|---|
| `ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` |

---

## 🌐 API Reference

### Traffic

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/traffic/intersections` | List all intersections |
| `GET` | `/api/traffic/density` | Latest density for all lanes |
| `GET` | `/api/traffic/density/history` | Paginated historical density |
| `POST` | `/api/traffic/video/process` | Upload & process a video file |

### Signals

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/signals/all` | All current signal states |
| `GET` | `/api/signals/{id}` | Single intersection signal state |
| `POST` | `/api/signals/{id}/manual` | Manual timing override |

### Emergency

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/emergency/activate` | Activate a green corridor |
| `POST` | `/api/emergency/deactivate` | Clear an active corridor |
| `GET` | `/api/emergency/active` | List all active emergencies |
| `POST` | `/api/emergency/simulate` | One-click end-to-end test |

---

## 📡 WebSocket Events

Connect to `/ws` for live push updates.

| Event | Payload | Description |
|---|---|---|
| `init` | Full state snapshot | Sent on connection |
| `density_update` | Per-intersection density | Continuous ML feed |
| `signal_update` | Signal phase + timing | Every signal change |
| `emergency_alert` | Corridor + intersection IDs | Emergency activated |
| `emergency_clear` | Corridor ID | Emergency cleared |
| `ping` | — | Heartbeat keepalive |

---

## 🎥 ML Pipeline Usage

**Run the detector on a local video**
```bash
python ml/video_processor.py --video ml/test_videos/sample.mp4
```

**Run and post results directly to the API**
```bash
python ml/video_processor.py --video ml/test_videos/sample.mp4 --post-api
```

**Run headless (no display window)**
```bash
python ml/video_processor.py --video ml/test_videos/sample.mp4 --no-display
```

**Run full end-to-end demo**
```bash
python demo.py ml/test_videos/sample.mp4
```

---

## 🧪 Testing

```bash
cd backend
pytest
```

---

## 🚀 Deployment

### Frontend — Vercel

| Setting | Value |
|---|---|
| Project root | `frontend/` |
| Build command | `npm run build` |
| Output directory | `dist` |
| `VITE_API_BASE_URL` | `https://<your-backend-domain>` |
| `VITE_WS_URL` | `wss://<your-backend-domain>/ws` |

### Backend — Render

| Setting | Value |
|---|---|
| Service root | `backend/` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

> **Note:** Provide production-grade PostgreSQL (TimescaleDB-enabled), Redis, and an MQTT broker. If your PostgreSQL instance does not support the TimescaleDB extension, remove or guard the `create_hypertable` calls in the Alembic migration.

### 🔐 Production Hardening Checklist

- [ ] Set `DEBUG=false`
- [ ] Use a cryptographically strong `SECRET_KEY`
- [ ] Lock `ALLOWED_ORIGINS` to your exact Vercel domain
- [ ] Enforce TLS — HTTPS for REST, WSS for WebSocket
- [ ] Use managed credentials for database and MQTT (no defaults)
- [ ] Enable TimescaleDB retention policies for density history

---

## 🔮 Roadmap

<div align="center">

| Status | Feature |
|:---:|---|
| 🔜 | 🛰 Multi-camera multi-intersection federated control |
| 🔜 | 📱 Mobile operator app for field management |
| 🔜 | 🤖 Reinforcement learning for intersection-level signal optimization |
| 🔜 | 🗺 City-level traffic flow simulation and prediction |
| 🔜 | 📶 V2X (Vehicle-to-Infrastructure) integration |
| 🔜 | 🔔 Operator alerting (email/SMS) for density threshold breaches |
| 🔜 | 📊 Prometheus + Grafana observability stack |
| 🔜 | 🏙 Multi-city / multi-tenant architecture |

</div>

---

## 🤝 Contributing

All contributions are welcome.

```bash
# 1. Fork the repository via GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/flowmind-ai.git
cd flowmind-ai

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make changes and commit
git add .
git commit -m "feat: describe your change clearly"

# 5. Push and open a Pull Request
git push origin feature/your-feature-name
```

### Commit Convention

| Prefix | Use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code restructure, no behaviour change |
| `perf:` | Performance improvement |
| `test:` | Tests added or updated |
| `chore:` | Build, tooling, or config changes |

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for full terms.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=2,3,30&height=120&section=footer&animation=fadeIn"/>

<br/>

**Built to make every green light count.**

*If this project helped you or impressed you, a* ⭐ *on GitHub goes a long way.*

</div>
