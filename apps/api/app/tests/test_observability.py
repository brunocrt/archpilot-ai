import unittest

from app.observability import MetricsStore


class ObservabilityTests(unittest.TestCase):
    def test_metrics_render_prometheus_counters_and_durations(self) -> None:
        metrics = MetricsStore()
        metrics.increment("archpilot_chat_requests_total")
        metrics.observe_duration("archpilot_retrieval_duration", 12.5)

        rendered = metrics.render_prometheus()

        self.assertIn("archpilot_chat_requests_total 1", rendered)
        self.assertIn("archpilot_retrieval_duration_milliseconds_count 1", rendered)
        self.assertIn("archpilot_retrieval_duration_milliseconds_sum 12.5000", rendered)


if __name__ == "__main__":
    unittest.main()
