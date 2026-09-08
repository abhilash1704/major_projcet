"""
test_stale_request_protection.py — Out-of-Order Execution & Stale Response Protection
"""
import time
import threading
import pytest
from app.modules.routing.services.alternative_route_service import alternative_route_service


def test_stale_alternative_request_id_isolation():
    """Rapid requests carry monotonic request_ids allowing client to discard older out-of-order completions."""
    req_older = "seq-1-jp-nagar"
    req_newer = "seq-2-whitefield"

    # Simulate Request 1 starting first, but Request 2 completing first
    results = {}
    def worker(src, dst, req_id, delay):
        time.sleep(delay)
        res = alternative_route_service.generate_alternative_routes(
            source_node=src,
            destination_node=dst,
            request_id=req_id,
            max_alternatives=1,
        )
        results[req_id] = res

    # Thread 1: slow
    t1 = threading.Thread(target=worker, args=("7172568278", "1931983762", req_older, 0.3))
    # Thread 2: fast
    t2 = threading.Thread(target=worker, args=("10282796509", "309592695", req_newer, 0.0))

    t1.start()
    t2.start()
    t2.join(timeout=10)
    t1.join(timeout=10)

    assert req_newer in results
    assert req_older in results
    assert results[req_newer]["request_id"] == req_newer
    assert results[req_older]["request_id"] == req_older
