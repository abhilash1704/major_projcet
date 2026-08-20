"""
Vehicle Simulation Constants — Sprint 4.1 / 4.2 / 4.3

Centralises all configurable values for the vehicle simulation engine.
Do not hardcode these values in services or models."""
import os

# ── Module Metadata ────────────────────────────────────────────────────────────
MODULE_NAME = "vehicle-simulation"
MODULE_VERSION = "1.0.0"

# ── Vehicle Status Values ──────────────────────────────────────────────────────
VEHICLE_STATUS_ACTIVE    = "active"
VEHICLE_STATUS_STOPPED   = "stopped"
VEHICLE_STATUS_COMPLETED = "completed"
VEHICLE_STATUS_INACTIVE  = "inactive"

VALID_VEHICLE_STATUSES = {
    VEHICLE_STATUS_ACTIVE,
    VEHICLE_STATUS_STOPPED,
    VEHICLE_STATUS_COMPLETED,
    VEHICLE_STATUS_INACTIVE,
}

# ── Vehicle ID ─────────────────────────────────────────────────────────────────
VEHICLE_ID_PREFIX = "veh_"

# ── Generation Limits ──────────────────────────────────────────────────────────
# Maximum vehicles that can be generated in a single request.
MAX_GENERATION_COUNT = int(os.environ.get("MAX_VEHICLE_GENERATION", "500"))

# Default count when no count is specified.
DEFAULT_GENERATION_COUNT = int(os.environ.get("DEFAULT_VEHICLE_GENERATION", "100"))

# ── Speed Configuration ────────────────────────────────────────────────────────
# Fraction of the road's speed_limit applied to each vehicle.
SPEED_FRACTION = float(os.environ.get("VEHICLE_SPEED_FRACTION", "0.75"))

# Fallback speed (km/h) when a road edge has no speed-limit information.
FALLBACK_SPEED_KMH = float(os.environ.get("VEHICLE_FALLBACK_SPEED", "35.0"))

# Random noise factor: ±SPEED_NOISE_FRACTION applied on top of base speed.
SPEED_NOISE_FRACTION = float(os.environ.get("VEHICLE_SPEED_NOISE", "0.15"))

# ── Edge Population Limit ──────────────────────────────────────────────────────
# Maximum vehicles placed on the same road edge before preferring another edge.
MAX_VEHICLES_PER_EDGE = int(os.environ.get("MAX_VEHICLES_PER_EDGE", "3"))

# ── Random Seed ────────────────────────────────────────────────────────────────
# Set to an integer for reproducible generation; None = truly random.
DEFAULT_RANDOM_SEED = None  # overridable in tests via the API / service call

# ── Graph Cache ────────────────────────────────────────────────────────────────
# Cache key used when no explicit key is provided by the caller.
DEFAULT_CACHE_KEY = os.environ.get("DEFAULT_GRAPH_CACHE_KEY", "bangalore_default")

# ── Movement Engine — Sprint 4.3 ───────────────────────────────────────────────
# Duration of one simulation tick in seconds (configurable).
TICK_DURATION_SECONDS = float(os.environ.get("SIM_TICK_SECONDS", "1.0"))

# Maximum ticks per /tick request.
MAX_TICKS_PER_REQUEST = int(os.environ.get("SIM_MAX_TICKS", "60"))

# Maximum vehicles advanced per tick (protects against huge fleet overhead).
MAX_VEHICLES_PER_TICK = int(os.environ.get("SIM_MAX_VEHICLES_PER_TICK", "500"))
