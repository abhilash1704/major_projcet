"""
Clustering Summary Metrics Calculator
"""
from typing import Dict, Any, List

def calculate_clustering_metrics(
    total_users: int,
    vehicle_clusters: List[Dict[str, Any]],
    noise_count: int = 0
) -> Dict[str, Any]:
    """
    Computes top-level vehicle estimation metrics.
    """
    estimated_vehicles = len(vehicle_clusters) + noise_count
    users_grouped = max(0, total_users - estimated_vehicles)
    
    if total_users > 0:
        reduction_pct = round((users_grouped / float(total_users)) * 100.0, 1)
        avg_users_per_veh = round(total_users / float(estimated_vehicles), 2) if estimated_vehicles > 0 else 0.0
    else:
        reduction_pct = 0.0
        avg_users_per_veh = 0.0

    return {
        "total_active_users": total_users,
        "estimated_vehicles": estimated_vehicles,
        "active_clusters": len(vehicle_clusters),
        "unclustered_users": noise_count,
        "users_grouped": users_grouped,
        "user_reduction_percentage": reduction_pct,
        "average_users_per_vehicle": avg_users_per_veh,
    }
