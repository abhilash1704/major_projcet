# RouteFlow 🚀

**Dynamic Traffic Routing Optimization using Vehicle Clustering, Dijkstra and A* Algorithms**

Welcome to the RouteFlow project! This repository contains the complete production-grade foundation for a modern intelligent navigation system built to reduce false traffic congestion using advanced clustering and routing algorithms.

---

## 🎯 Sprint 1 Summary
**Sprint 1 is completely verified and finished.** We have successfully established:
- **Frontend Architecture**: React 19 + Vite initialized with a comprehensive Google Maps-inspired Design System, Reusable UI Components, and responsive placeholder Pages.
- **Backend Infrastructure**: Flask Application Factory initialized with blueprint architecture, robust configuration handling, logging, and global error handling.
- **Database Foundation**: SQLite configured via SQLAlchemy and Flask-Migrate, inclusive of an abstract `BaseModel` featuring UUIDs and soft delete functionality, a `User` model with strong validation, and a scalable Repository pattern.
- **Integration**: Secure `.env` handling across environments and an Axios-driven frontend API service communicating successfully with the Flask API `/health` endpoints.

---

## 🛠️ Technology Stack
### Frontend
- **Framework**: React 19, Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router DOM
- **API Client**: Axios
- **Icons**: Lucide React

### Backend
- **Framework**: Python 3.x, Flask, Flask-RESTful
- **Database**: SQLite (Development/Testing), SQLAlchemy (ORM)
- **Migrations**: Flask-Migrate (Alembic)
- **Security & APIs**: Flask-CORS, python-dotenv

---

## 📂 Folder Structure
```
RouteFlow/
├── frontend/                 # React + Vite Application
│   ├── src/
│   │   ├── app/              # App entry & Router
│   │   ├── components/       # Reusable UI & Layouts
│   │   ├── pages/            # View Pages
│   │   ├── services/         # Axios API Services
│   │   ├── styles/           # Global Tailwind Config
│   │   └── utils/            # Frontend Utilities
│   └── .env                  # Frontend Environment Variables
│
├── backend/                  # Flask API
│   ├── app/                  # Application Factory & Blueprints
│   ├── api/v1/               # API Endpoints
│   ├── config/               # Environment Configuration (Dev, Prod, Test)
│   ├── core/                 # Error Handlers & Loggers
│   ├── database/             # DB Connection & Migrations
│   ├── models/               # SQLAlchemy Models
│   ├── repositories/         # DB Abstraction Layer
│   └── utils/                # Response & Error Helpers
│
├── scripts/                  # Utility Scripts (e.g. database seeding)
└── docs/                     # Project Documentation
```

---

## 🚀 Installation & Developer Guide

### 1. Prerequisites
- Node.js (v18+)
- Python (v3.10+)

### 2. Backend Setup
Open a terminal and navigate to the backend directory:
```bash
cd RouteFlow/backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations to initialize the database
flask db upgrade

# Seed the database (Optional)
python ../scripts/seed.py

# Start the Flask API server
python run.py
```
*The API will be available at `http://localhost:5000/api/v1/`*

### 3. Frontend Setup
Open a new terminal and navigate to the frontend directory:
```bash
cd RouteFlow/frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
*The React app will be available at `http://localhost:5173`*

---

## 📈 Future Sprints
- **Sprint 2**: Authentication (JWT, User Management)
- **Sprint 3**: Interactive Maps & Leaflet Integration
- **Sprint 4**: Live Vehicle Simulation & Clustering Engine (DBSCAN)
- **Sprint 5**: Dynamic Traffic Routing (Dijkstra, A*)

---
*Created as part of Sprint 1 Foundation.*
