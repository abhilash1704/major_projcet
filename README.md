# 🚦 RouteFlow

### Dynamic Traffic Routing Optimization Using Dijkstra's and A*

> An intelligent traffic-routing platform that reduces false congestion by clustering nearby GPS users into estimated vehicles and dynamically updating road conditions for smarter route selection.

---

## 📌 Overview

**RouteFlow** is a smart transportation and navigation platform designed to improve traffic-aware route planning under dynamic road conditions.

Traditional GPS-based traffic estimation can overestimate congestion when multiple users inside the same vehicle are treated as separate vehicles.

RouteFlow addresses this problem by:

```text
GPS / Vehicle Observations
            ↓
      Preprocessing
            ↓
   Distance-Based Clustering
            ↓
     Estimated Vehicles
            ↓
    Road Vehicle Density
            ↓
   Dynamic Traffic Cost
            ↓
      Graph Update
            ↓
      ┌─────────────┐
      │             │
      ▼             ▼
   Dijkstra         A*
      │             │
      └──────┬──────┘
             ▼
       Efficient Route
```

The core project objective is to reduce false congestion by grouping nearby users that may belong to the same vehicle and then using the estimated vehicle count to improve traffic-aware routing. :contentReference[oaicite:2]{index=2}

---

# 🎯 Objectives

RouteFlow aims to:

- Collect GPS/location observations.
- Reduce false congestion caused by multiple users in the same vehicle.
- Apply distance-based clustering to estimate actual vehicles.
- Calculate vehicle density on roads.
- Update road-network edge weights dynamically.
- Compare Dijkstra and A* routing.
- Generate traffic-aware routes.
- Improve routing accuracy under changing traffic conditions.
- Reduce unnecessary travel time.

These objectives are directly based on the project's submitted scope and proposed system. :contentReference[oaicite:3]{index=3}

---

# ❗ Problem Statement

Traffic-routing systems often use user GPS data to estimate traffic conditions.

The problem occurs when multiple users travel in the same vehicle:

```text
             One Vehicle
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
    User A     User B    User C
```

A raw GPS-based system may interpret this as:

```text
3 users = 3 vehicles
```

when the actual situation is:

```text
3 users = 1 vehicle
```

This can produce:

```text
Inflated Vehicle Count
        ↓
False Congestion
        ↓
Incorrect Traffic Cost
        ↓
Poor Route Selection
```

The proposed system addresses this by clustering nearby users and treating each group as one estimated vehicle. :contentReference[oaicite:4]{index=4}

---

# 💡 Proposed Solution

The RouteFlow approach is:

```text
1. Collect GPS/location observations
              ↓
2. Preprocess and validate observations
              ↓
3. Calculate spatial proximity
              ↓
4. Apply clustering
              ↓
5. Estimate actual vehicles
              ↓
6. Calculate road-level vehicle density
              ↓
7. Update traffic-dependent edge weights
              ↓
8. Run Dijkstra / A*
              ↓
9. Generate the most efficient route
```

The project documentation explicitly defines this architecture and preprocessing flow. :contentReference[oaicite:5]{index=5}

---

# 🧠 Core Concept

## Multiple Users → One Vehicle

Example:

```text
Vehicle V1
 ├── User A
 ├── User B
 └── User C

Vehicle V2
 ├── User D
 └── User E
```

Raw observations:

```text
5 users
```

After clustering:

```text
Cluster 1 → Users A, B, C
Cluster 2 → Users D, E
```

Estimated vehicles:

```text
2
```

Instead of:

```text
5
```

This is the central idea behind the project's false-congestion reduction objective. :contentReference[oaicite:6]{index=6}

---

# 🏗️ System Architecture

```text
                           ┌────────────────────┐
                           │       User         │
                           │  Route / Location  │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ GPS / Simulation   │
                           │   Observations     │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │   Preprocessing    │
                           │ Validation / Noise │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │     DBSCAN /       │
                           │ Distance Clustering│
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ Estimated Vehicles │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ Road Vehicle       │
                           │ Density            │
                           └─────────┬──────────┘
                                     │
                                     ▼
                           ┌────────────────────┐
                           │ Dynamic Edge       │
                           │ Weights             │
                           └─────────┬──────────┘
                                     │
                            ┌────────┴────────┐
                            ▼                 ▼
                       ┌─────────┐       ┌─────────┐
                       │Dijkstra │       │   A*    │
                       └────┬────┘       └────┬────┘
                            │                 │
                            └────────┬────────┘
                                     ▼
                           ┌────────────────────┐
                           │  Optimal Route     │
                           └────────────────────┘
```

---

# 🚗 Live Vehicle Clustering

RouteFlow includes an isolated **Live Vehicle Clustering** module.

The user selects:

```text
Analysis Area
[ JP Nagar ]

Radius
[ 500 m ] [ 1 km ] [ 2 km ]
```

and clicks:

```text
[ Analyze Live Area ]
```

After that, the analysis runs automatically.

### Live flow

```text
Existing Vehicle Simulation
            ↓
Current Vehicle Snapshot
            ↓
Generate User GPS Observations
            ↓
Preprocess
            ↓
DBSCAN
            ↓
Estimated Vehicles
            ↓
Users Grouped
            ↓
Road Density
            ↓
Traffic Level
            ↓
Automatic Update
```

The project presentation explicitly allows the methodology to operate using user data or simulated vehicles. :contentReference[oaicite:7]{index=7}

---

# 🔄 Automatic Live Analysis

The Live Vehicle Clustering module continuously updates the analysis.

Example:

```text
10:30:00

GPS Users:          137
Clusters:            52
Estimated Vehicles:  52
Grouped Users:       85
Reduction:         62.0%
```

After the next cycle:

```text
10:30:20

GPS Users:          143
Clusters:            55
Estimated Vehicles:  55
Grouped Users:       88
Reduction:         61.5%
```

The exact values depend on the active simulation state.

---

# 🧮 Vehicle Estimation

The main estimated-vehicle calculation is based on the number of valid clusters.

```text
Estimated Vehicles = Number of Valid Clusters
```

Example:

```text
137 GPS observations
        ↓
DBSCAN
        ↓
52 clusters
        ↓
52 estimated vehicles
```

---

# 📉 False Congestion Reduction

RouteFlow can compare:

```text
Raw User Count
        vs
Estimated Vehicle Count
```

Example:

```text
Users                  = 137
Estimated Vehicles     = 52
Users Grouped          = 85
```

Reduction:

```text
(137 - 52) / 137 × 100
= 62.0%
```

This metric represents the reduction of duplicated-user counting within the simulation/analysis model.

---

# 🛣️ Road Vehicle Density

Clustered vehicles are mapped to road segments.

Example:

```text
24th Main Road
Estimated Vehicles: 9
Density: HIGH
```

```text
Main Road B
Estimated Vehicles: 4
Density: MEDIUM
```

```text
Road C
Estimated Vehicles: 1
Density: LOW
```

Important:

```text
Raw Users
    ≠
Estimated Vehicles
```

Road density is based on estimated vehicle clusters.

---

# 🚦 Traffic Conditions

Traffic conditions can be classified into:

```text
🟢 LOW
🟠 MEDIUM
🔴 HIGH
```

The traffic state is derived from the traffic/density model used by RouteFlow.

Example:

```text
Road A → 2 vehicles → LOW
Road B → 6 vehicles → MEDIUM
Road C → 12 vehicles → HIGH
```

---

# 🧭 Navigation Engine

RouteFlow provides two major graph-routing algorithms:

## Dijkstra

Dijkstra searches the weighted road graph to determine a minimum-cost path.

```text
Source
  ↓
Weighted Road Graph
  ↓
Dijkstra
  ↓
Shortest / Lowest-Cost Route
```

## A*

A* uses a heuristic to guide the search toward the destination.

```text
Source
  ↓
Weighted Road Graph
  ↓
A* + Heuristic
  ↓
Efficient Route
```

---

# ⚖️ A* vs Dijkstra

RouteFlow can compare:

| Metric | A* | Dijkstra |
|---|---:|---:|
| Search Time | Measured | Measured |
| Explored Nodes | Measured | Measured |
| Distance | Measured | Measured |
| ETA | Measured | Measured |
| Traffic Cost | Measured | Measured |

Actual values are calculated from the current routing request.

---

# 🚦 Traffic-Aware Routing

RouteFlow supports:

### Normal Routing

Uses normal road costs.

### Traffic-Aware Routing

Uses traffic-dependent road costs.

```text
Vehicle Density
       ↓
Traffic Condition
       ↓
Traffic Penalty
       ↓
Dynamic Edge Weight
       ↓
A* / Dijkstra
       ↓
Route
```

The project proposal specifies dynamic updates to graph edge weights based on traffic conditions before applying Dijkstra and A*. :contentReference[oaicite:8]{index=8}

---

# 🔀 Alternative Routes

RouteFlow can generate alternative candidate routes using the available routing algorithms.

Conceptually:

```text
Current Route
      +
A* Candidate
      +
Dijkstra Candidate
      ↓
Candidate Filtering
      ↓
Alternative Routes
```

The interface keeps the current route visible while presenting valid alternatives separately.

---

# 🌆 Bengaluru Analysis

RouteFlow is designed around Bengaluru road-network analysis.

Example monitored/searchable locations include:

- JP Nagar
- Banashankari
- BTM Layout
- Whitefield
- Koramangala
- Electronic City
- Silk Board
- Malleswaram
- Indiranagar
- Chikkapete
- Basavanagudi

The selected analysis area is independent from the user's physical browser location.

---

# 🔐 Authentication

RouteFlow provides protected access to the application.

Basic flow:

```text
Landing Page
      ↓
Sign In / Register
      ↓
Authentication
      ↓
RouteFlow Platform
```

Authenticated access protects the main application modules.

User-specific information, such as route history, should be scoped to the authenticated account.

---

# 🧾 Route History

The History module stores successful route calculations.

A history record can include:

```text
Source
Destination
Distance
ETA
Algorithm
Routing Mode
Traffic Level
Traffic Penalty
Timestamp
```

Typical flow:

```text
Calculate Route
      ↓
Successful Result
      ↓
Save History
      ↓
History Page
```

---

# 🖥️ Main Modules

```text
RouteFlow
│
├── Dashboard
│
├── Navigation
│   ├── Route Planning
│   ├── A* Search
│   ├── Dijkstra
│   ├── Normal Routing
│   ├── Traffic-Aware Routing
│   └── Alternative Routes
│
├── Live Clustering
│   ├── Vehicle Simulation
│   ├── GPS Observations
│   ├── DBSCAN
│   ├── Vehicle Estimation
│   ├── User Grouping
│   ├── Road Density
│   └── Automatic Live Updates
│
├── Routes
├── History
├── Settings
└── Profile
```

---

# 🛠️ Technology Stack

The project is a full-stack web application built around:

### Frontend

- React
- JavaScript / JSX
- Vite
- Leaflet
- OpenStreetMap

### Backend

- Python
- Flask
- REST APIs

### Algorithms & Processing

- DBSCAN / distance-based clustering
- Dijkstra
- A*
- GPS preprocessing
- Traffic-density calculation
- Dynamic graph weighting

### Mapping

- Leaflet
- OpenStreetMap

---

# 📂 Repository Structure

A representative structure is:

```text
RouteFlow/
│
├── backend/
│   ├── app/
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── navigation/
│   │   │   ├── routing/
│   │   │   ├── road_network/
│   │   │   ├── traffic/
│   │   │   ├── vehicle_simulation/
│   │   │   ├── live_clustering/
│   │   │   └── history/
│   │   │
│   │   └── ...
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── context/
│   │   └── ...
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── README.md
├── .gitignore
└── ...
```

> Adjust the exact tree to the current repository structure if the implementation differs.

---

# ⚙️ Installation

## 1. Clone

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd RouteFlow
```

---

# 🐍 Backend Setup

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

### Windows

```powershell
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Configuration

Create a backend environment file according to the project's configuration.

Example:

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key

DATABASE_URL=your-database-url

LIVE_TRAFFIC_PROVIDER=your-provider
LIVE_TRAFFIC_API_KEY=your-api-key

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

### Never commit secrets

```gitignore
.env
.env.*
!.env.example
```

---

# ▶️ Start Backend

```bash
python run.py
```

---

# ⚛️ Frontend Setup

Open a new terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start development server:

```bash
npm run dev
```

Then open the URL provided by the Vite development server.

---

# 🧪 Testing

Run backend tests:

```bash
pytest
```

Build the frontend:

```bash
npm run build
```

If configured:

```bash
npm run lint
```

---

# ✅ End-to-End Demonstration

## 1. Authentication

```text
Register / Sign In
        ↓
Dashboard
```

## 2. Route Planning

```text
Source
   ↓
Destination
   ↓
A* / Dijkstra
   ↓
Route
```

## 3. Traffic-Aware Routing

```text
Traffic
   ↓
Traffic Penalty
   ↓
Dynamic Graph Weights
   ↓
A* / Dijkstra
   ↓
Traffic-Aware Route
```

## 4. Live Vehicle Clustering

```text
Select Area
      ↓
Select Radius
      ↓
Analyze Live Area
      ↓
Automatic vehicle/GPS observation processing
      ↓
DBSCAN
      ↓
Estimated Vehicles
      ↓
Road Density
      ↓
Traffic Level
```

## 5. History

```text
Successful Route
      ↓
History Record
      ↓
History Page
```

---

# 📊 Example Live Clustering Snapshot

```text
SIMULATION GPS SOURCE
---------------------

Status: LIVE

Simulated Vehicles:      50
GPS User Observations:   137
Observation Window:      5 sec
```

```text
DBSCAN CLUSTERING
-----------------

Clusters:                52
Estimated Vehicles:      52
Users Grouped:            85
Reduction:              62.0%
```

```text
ROAD VEHICLE DENSITY
--------------------

HIGH:                     8
MEDIUM:                  11
LOW:                     12
```

These numbers are illustrative simulation values, not claims of real-world live traffic measurements.

---

# 📈 Clustering Evaluation

When ground-truth vehicle identities are available from the simulation, the clustering estimator can be evaluated independently.

Example:

```text
Ground Truth Vehicles:   50
DBSCAN Estimated:        52
Count Error:              4%
```

Additional metrics:

```text
Precision
Recall
F1-Score
Cluster Purity
```

The ground-truth identifier should be used only for evaluation and must not be provided as an input to DBSCAN.

---

# 🔬 Methodology

The project methodology follows:

```text
1. Collect GPS / location observations
2. Validate and preprocess data
3. Reduce noise and invalid observations
4. Calculate spatial proximity
5. Apply clustering
6. Group users representing the same vehicle
7. Estimate vehicle count
8. Calculate traffic density
9. Update graph edge weights
10. Run Dijkstra / A*
11. Generate the optimal route
```

This matches the methodology presented in the project materials. :contentReference[oaicite:9]{index=9}

---

# 🎓 Academic Information

## Project Title

**Dynamic Traffic Routing Optimization Using Dijkstra's and A***

## Domain

```text
Data Structures & Algorithms
Smart Transportation
Optimization
Graph Algorithms
Traffic Analysis
```

## Institution

**Alva's Institute of Engineering & Technology**

## Department

**Information Science and Engineering**

## Academic Year

**2025–26**

## Team

**Team B14**

- Abhilash C M M
- Karthik K M
- Nikhitha
- Sinchana

## Project Guide

**Mr. Mounesh Arkachari**

The submitted synopsis identifies the project title, domain, academic year, team, and guide. :contentReference[oaicite:10]{index=10}

---

# 🌍 Applications

Potential application areas include:

- Traffic management systems
- Navigation platforms
- Smart-city transportation systems
- Ride-sharing applications
- Emergency routing

These applications are identified in the project documentation. :contentReference[oaicite:11]{index=11}

---

# ⚠️ Data & Simulation Disclaimer

RouteFlow can use simulation-based vehicle/GPS observations for controlled demonstrations and algorithm evaluation.

Therefore:

```text
Simulation Data
        ≠
Real-world Vehicle Telemetry
```

Likewise, external traffic-provider data should always be displayed with its actual source/status.

The project methodology explicitly allows GPS/location data from users **or simulated vehicles** for the clustering workflow. :contentReference[oaicite:12]{index=12}

---

# 🔒 Security

Never commit:

```text
.env
API keys
OAuth secrets
database credentials
private tokens
passwords
```

Use environment variables for sensitive configuration.

Use secure authentication and ensure user-owned information remains isolated between accounts.

---

# 🧪 Suggested Evaluation

A useful experimental setup is:

```text
Actual simulated vehicles
        ↓
Multiple users per vehicle
        ↓
Raw user count
        ↓
DBSCAN
        ↓
Estimated vehicle count
```

Example:

```text
Actual vehicles:      10
GPS users:            28
Estimated vehicles:   11
Count error:           10%
```

Then compare:

```text
Without clustering
        ↓
Raw user count used for traffic

vs

With clustering
        ↓
Estimated vehicle count used for traffic
```

This directly demonstrates the project's main false-congestion problem. :contentReference[oaicite:13]{index=13}

---

# 🚀 Future Enhancements

Possible future work:

- Real-world probe/GPS integration
- Larger Bengaluru mobility datasets
- Adaptive clustering thresholds
- Improved user-to-vehicle association
- Trajectory-based clustering
- Traffic prediction
- Historical traffic analytics
- Incident detection
- Cloud deployment
- Distributed stream processing
- Machine-learning-based traffic forecasting

These are future enhancements and should not be interpreted as existing features unless implemented and verified.

---

# 🤝 Contribution

For project development:

```text
1. Create a feature branch
2. Implement the change
3. Run backend tests
4. Run frontend build/tests
5. Check for regressions
6. Create a pull request
```

Example:

```bash
git checkout -b feature/<feature-name>

git add .

git commit -m "feat: <description>"

git push origin feature/<feature-name>
```

---

# 📌 Development Principles

RouteFlow development follows these principles:

- Keep routing algorithms isolated.
- Keep vehicle simulation isolated.
- Keep clustering isolated.
- Keep traffic processing isolated.
- Avoid unnecessary database writes during high-frequency simulation.
- Prefer in-memory state for high-frequency transient processing.
- Never fabricate real-world traffic data.
- Keep simulation data clearly labeled.
- Protect authenticated user data.
- Add tests before changing critical algorithms.
- Preserve existing routing behavior during feature development.

---

# 🏁 Project Summary

RouteFlow combines:

```text
GPS Observations
       +
Clustering
       +
Vehicle Estimation
       +
Traffic Density
       +
Dynamic Graph Weights
       +
Dijkstra
       +
A*
       ↓
Dynamic Traffic Routing
```

The central contribution is the reduction of false congestion by recognizing that multiple nearby user observations can represent a smaller number of actual vehicles. The resulting vehicle estimate is then used to improve traffic-density estimation and dynamic route selection. :contentReference[oaicite:14]{index=14}

---

## ⭐ RouteFlow

**Turning GPS observations into better vehicle estimates and smarter routes.**
