"""
Unit Tests for Trajectory Replay Engine
"""
import unittest
import time
from app import create_app
from app.modules.live_clustering.trajectory.generator import generator
from app.modules.live_clustering.trajectory.replay_engine import replay_engine

class TestTrajectoryReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        replay_engine.stop()

    def tearDown(self):
        replay_engine.stop()

    def test_replay_lifecycle(self):
        """Tests READY -> RUNNING -> PAUSED -> STOPPED lifecycle and speed control."""
        with self.app.app_context():
            dataset, gt_map = generator.generate_area_trajectories(
                center_lat=12.9698,
                center_lon=77.7499,
                radius_meters=1000.0,
                num_vehicles=5,
                duration_minutes=1.0,
                seed=42,
            )
            
            # 1. Load dataset
            st = replay_engine.load_dataset(dataset, gt_map)
            self.assertEqual(st["status"], "READY")

            # 2. Set speed
            st_speed = replay_engine.set_speed(10.0)
            self.assertEqual(st_speed["speed"], 10.0)

            # 3. Start replay
            st_start = replay_engine.start()
            self.assertEqual(st_start["status"], "RUNNING")

            time.sleep(0.5)

            # 4. Snapshot check
            snap = replay_engine.get_snapshot()
            self.assertIn(snap["status"], ["RUNNING", "STOPPED"])
            self.assertGreater(len(snap.get("window_observations", [])), 0)

            # 5. Pause replay
            st_pause = replay_engine.pause()
            self.assertEqual(st_pause["status"], "PAUSED")

            # 6. Stop replay
            st_stop = replay_engine.stop()
            self.assertEqual(st_stop["status"], "STOPPED")

if __name__ == "__main__":
    unittest.main()
