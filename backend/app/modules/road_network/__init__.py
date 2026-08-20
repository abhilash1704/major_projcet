"""
Road Network Engine Module
Provides infrastructure for OpenStreetMap road network data parsing,
graph representation, nearest-node lookup, and geo utilities.
"""

from .routes import road_network_bp

__all__ = ["road_network_bp"]
