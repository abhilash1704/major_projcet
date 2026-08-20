"""
Ground Truth Vehicle Clustering Evaluation Engine
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger("routeflow.live_clustering.evaluation.clustering_metrics")


class ClusteringEvaluationEngine:
    """
    Evaluates DBSCAN vehicle clustering accuracy against synthetic ground truth vehicle metadata.
    Ground truth vehicle IDs are ONLY used in this evaluation engine.
    """
    
    def evaluate_clustering(
        self,
        clusters: List[Dict[str, Any]],
        ground_truth_map: Dict[str, str], # user_id -> ground_truth_vehicle_id
        actual_vehicle_count: int
    ) -> Dict[str, Any]:
        """
        Computes evaluation metrics:
          - Count Error (%)
          - Precision, Recall, F1 Score (Pairwise co-location)
          - Cluster Purity
        """
        estimated_count = len(clusters)
        
        if actual_vehicle_count <= 0:
            return {
                "status": "INACTIVE",
                "actual_vehicle_count": 0,
                "estimated_vehicle_count": estimated_count,
                "absolute_error": estimated_count,
                "percentage_error": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "cluster_purity": 0.0,
            }

        abs_err = abs(estimated_count - actual_vehicle_count)
        pct_err = round((abs_err / float(actual_vehicle_count)) * 100.0, 1)

        if not clusters or not ground_truth_map:
            return {
                "status": "ACTIVE",
                "actual_vehicle_count": actual_vehicle_count,
                "estimated_vehicle_count": estimated_count,
                "absolute_error": abs_err,
                "percentage_error": pct_err,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "cluster_purity": 0.0,
            }

        # 1. Calculate Cluster Purity
        purity_scores = []
        for clus in clusters:
            user_ids = clus.get("user_ids", [])
            if not user_ids:
                continue
            gt_veh_counts: Dict[str, int] = {}
            for u in user_ids:
                gt_v = ground_truth_map.get(u, "gt_unknown")
                gt_veh_counts[gt_v] = gt_veh_counts.get(gt_v, 0) + 1
            max_count = max(gt_veh_counts.values()) if gt_veh_counts else 0
            purity = max_count / float(len(user_ids))
            purity_scores.append(purity)

        avg_purity = round(sum(purity_scores) / float(len(purity_scores)), 3) if purity_scores else 1.0

        # 2. Pairwise Precision, Recall, F1 Score
        # True Positive (TP): Pair in same GT vehicle AND same predicted cluster
        # False Positive (FP): Pair in different GT vehicle BUT same predicted cluster
        # False Negative (FN): Pair in same GT vehicle BUT different predicted cluster
        tp, fp, fn = 0, 0, 0

        # Build predicted cluster map user_id -> cluster_id
        pred_map: Dict[str, str] = {}
        for clus in clusters:
            cid = clus["cluster_id"]
            for u in clus.get("user_ids", []):
                pred_map[u] = cid

        all_users = list(ground_truth_map.keys())
        n_users = len(all_users)

        for i in range(n_users):
            u1 = all_users[i]
            gt1 = ground_truth_map[u1]
            pred1 = pred_map.get(u1)

            for j in range(i + 1, n_users):
                u2 = all_users[j]
                gt2 = ground_truth_map[u2]
                pred2 = pred_map.get(u2)

                same_gt = (gt1 == gt2)
                same_pred = (pred1 is not None and pred1 == pred2)

                if same_gt and same_pred:
                    tp += 1
                elif not same_gt and same_pred:
                    fp += 1
                elif same_gt and not same_pred:
                    fn += 1

        precision = tp / float(tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / float(tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        precision_val = round(precision, 3)
        recall_val = round(recall, 3)
        f1_val = round(f1, 3)

        if estimated_count > actual_vehicle_count:
            estimation_label = "OVER-CLUSTERING"
        elif estimated_count < actual_vehicle_count:
            estimation_label = "UNDER-CLUSTERING"
        else:
            estimation_label = "GOOD ESTIMATION"

        return {
            "status": "ACTIVE",
            "actual_vehicle_count": actual_vehicle_count,
            "ground_truth_vehicles": actual_vehicle_count,
            "estimated_vehicle_count": estimated_count,
            "estimated_clusters": estimated_count,
            "absolute_error": abs_err,
            "percentage_error": pct_err,
            "vehicle_count_error_pct": pct_err,
            "precision": precision_val,
            "recall": recall_val,
            "f1_score": f1_val,
            "cluster_purity": avg_purity,
            "purity": avg_purity,
            "estimation_label": estimation_label,
            "confusion_pairs": {"tp": tp, "fp": fp, "fn": fn},
        }


evaluation_engine = ClusteringEvaluationEngine()
