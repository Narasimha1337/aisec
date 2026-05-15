import unittest
from datetime import datetime
from datetime import timezone

from outlook_qa_dashboard import (
    DashboardStats,
    build_export_rows,
    count_days_inclusive,
    extract_aaid,
    get_date_range,
    parse_daily_notification_counts_by_aaid,
    parse_stats_by_aaid_from_messages,
    parse_stats_from_messages,
    _normalize_for_comparison,
)


class ParseStatsTests(unittest.TestCase):
    def test_counts_and_dates_are_calculated(self):
        messages = [
            ("Start notification", datetime(2026, 5, 15, 10, 0, 0)),
            ("Stop notification", datetime(2026, 5, 15, 11, 0, 0)),
            ("TechQA started", datetime(2026, 5, 14, 9, 0, 0)),
            ("Tech QA stopped", datetime(2026, 5, 14, 12, 30, 0)),
            ("Final QA start", datetime(2026, 5, 13, 8, 15, 0)),
            ("FinalQA ended", datetime(2026, 5, 13, 17, 45, 0)),
        ]

        stats = parse_stats_from_messages(messages)

        self.assertEqual(stats.start_notifications_count, 1)
        self.assertEqual(stats.stop_notifications_count, 1)
        self.assertEqual(stats.techqa_start, datetime(2026, 5, 14, 9, 0, 0))
        self.assertEqual(stats.techqa_stop, datetime(2026, 5, 14, 12, 30, 0))
        self.assertEqual(stats.finalqa_start, datetime(2026, 5, 13, 8, 15, 0))
        self.assertEqual(stats.finalqa_stop, datetime(2026, 5, 13, 17, 45, 0))

    def test_latest_event_wins_for_each_type(self):
        messages = [
            ("TechQA started", datetime(2026, 5, 14, 9, 0, 0)),
            ("TechQA started", datetime(2026, 5, 14, 10, 0, 0)),
            ("Final QA stop", datetime(2026, 5, 15, 11, 0, 0)),
            ("Final QA stop", datetime(2026, 5, 15, 12, 0, 0)),
        ]

        stats = parse_stats_from_messages(messages)

        self.assertEqual(stats.techqa_start, datetime(2026, 5, 14, 10, 0, 0))
        self.assertEqual(stats.finalqa_stop, datetime(2026, 5, 15, 12, 0, 0))

    def test_extract_aaid(self):
        self.assertEqual(extract_aaid("AAID: AA101 Start notification"), "AA101")
        self.assertEqual(extract_aaid("AAID AA202 Final QA started"), "AA202")
        self.assertEqual(extract_aaid("AA12345 Start notification"), "AA12345")
        self.assertEqual(extract_aaid("aa98765 Final QA end"), "AA98765")
        self.assertEqual(extract_aaid("AAID: APP101 Start notification"), "UNKNOWN")
        self.assertEqual(extract_aaid("AAABC Final QA end"), "UNKNOWN")
        self.assertEqual(extract_aaid("Start notification without app id"), "UNKNOWN")

    def test_parse_stats_grouped_by_aaid(self):
        messages = [
            ("AAID: APP101 Start notification", datetime(2026, 5, 15, 9, 0, 0)),
            ("AAID: AA101 Stop notification", datetime(2026, 5, 15, 10, 0, 0)),
            ("AAID AA101 TechQA started", datetime(2026, 5, 15, 11, 0, 0)),
            ("AAID AA101 TechQA stopped", datetime(2026, 5, 15, 12, 0, 0)),
            ("AAID: AA202 Start notification", datetime(2026, 5, 15, 13, 0, 0)),
            ("AAID: AA202 Final QA start", datetime(2026, 5, 15, 14, 0, 0)),
            ("AAID: AA202 Final QA end", datetime(2026, 5, 15, 15, 0, 0)),
            ("AA12345 Start notification", datetime(2026, 5, 15, 15, 30, 0)),
            ("Start notification", datetime(2026, 5, 15, 16, 0, 0)),
        ]

        grouped = parse_stats_by_aaid_from_messages(messages)

        self.assertEqual(grouped["UNKNOWN"].start_notifications_count, 2)
        self.assertEqual(grouped["AA101"].stop_notifications_count, 1)
        self.assertEqual(grouped["AA101"].techqa_start, datetime(2026, 5, 15, 11, 0, 0))
        self.assertEqual(grouped["AA101"].techqa_stop, datetime(2026, 5, 15, 12, 0, 0))

        self.assertEqual(grouped["AA202"].start_notifications_count, 1)
        self.assertEqual(grouped["AA202"].finalqa_start, datetime(2026, 5, 15, 14, 0, 0))
        self.assertEqual(grouped["AA202"].finalqa_stop, datetime(2026, 5, 15, 15, 0, 0))

        self.assertEqual(grouped["AA12345"].start_notifications_count, 1)

    def test_techqa_milestone(self):
        messages = [
            ("AA12345 Start notification", datetime(2026, 5, 1, 9, 0, 0)),
            ("AA12345 Start notification", datetime(2026, 5, 2, 9, 0, 0)),
            ("AA12345 TechQA started", datetime(2026, 5, 3, 10, 0, 0)),
            ("AA12345 TechQA stopped", datetime(2026, 5, 3, 12, 0, 0)),
            ("AA12345 Final QA start", datetime(2026, 5, 4, 11, 0, 0)),
        ]

        grouped = parse_stats_by_aaid_from_messages(messages)
        stats = grouped["AA12345"]

        self.assertEqual(stats.techqa_milestone_at, datetime(2026, 5, 3, 10, 0, 0))

    def test_techqa_start_uses_first_non_tester_reply(self):
        messages = [
            ("AA12345 Start notification", datetime(2026, 5, 1, 9, 0, 0), "ABC Tester", ""),
            ("AA12345 Stop notification", datetime(2026, 5, 1, 17, 0, 0), "ABC Tester", ""),
            ("AA12345 TechQA report", datetime(2026, 5, 2, 9, 0, 0), "ABC Tester", "Please take this in TechQA"),
            ("RE: AA12345 TechQA report", datetime(2026, 5, 2, 10, 0, 0), "XYZ Person", "I am working on it"),
            ("RE: AA12345 TechQA report", datetime(2026, 5, 2, 11, 0, 0), "XYZ Person", "Started analysis"),
        ]

        grouped = parse_stats_by_aaid_from_messages(messages)
        stats = grouped["AA12345"]

        self.assertEqual(stats.first_start_notification_sender, "ABC Tester")
        self.assertEqual(stats.techqa_start, datetime(2026, 5, 2, 10, 0, 0))

    def test_finalqa_start_uses_techqa_completion_handoff(self):
        messages = [
            ("AA12345 Start notification", datetime(2026, 5, 1, 9, 0, 0), "ABC Tester", ""),
            ("AA12345 TechQA report", datetime(2026, 5, 2, 9, 0, 0), "ABC Tester", "Please take this in TechQA"),
            ("RE: AA12345 TechQA report", datetime(2026, 5, 2, 10, 0, 0), "XYZ Person", "I am working on it"),
            (
                "RE: AA12345 TechQA report",
                datetime(2026, 5, 3, 16, 0, 0),
                "XYZ Person",
                "TechQA completed. Proceed with Final QA",
            ),
            (
                "RE: AA12345 TechQA report",
                datetime(2026, 5, 3, 17, 0, 0),
                "Final QA User",
                "Picking this up for Final QA",
            ),
            (
                "AA12345 FinalQA closed",
                datetime(2026, 5, 4, 10, 0, 0),
                "Final QA User",
                "Closed",
            ),
        ]

        grouped = parse_stats_by_aaid_from_messages(messages)
        stats = grouped["AA12345"]

        self.assertEqual(stats.techqa_stop, datetime(2026, 5, 3, 16, 0, 0))
        self.assertEqual(stats.finalqa_start, datetime(2026, 5, 3, 16, 0, 0))
        self.assertEqual(stats.finalqa_stop, datetime(2026, 5, 4, 10, 0, 0))

    def test_first_start_last_stop_and_working_days(self):
        messages = [
            ("AA12345 Start notification", datetime(2026, 5, 11, 9, 0, 0)),
            ("AA12345 Stop notification", datetime(2026, 5, 13, 18, 0, 0)),
            ("AA12345 Start notification", datetime(2026, 5, 12, 9, 0, 0)),
            ("AA12345 Stop notification", datetime(2026, 5, 15, 18, 0, 0)),
        ]

        grouped = parse_stats_by_aaid_from_messages(messages)
        stats = grouped["AA12345"]

        self.assertEqual(stats.first_start_notification_at, datetime(2026, 5, 11, 9, 0, 0))
        self.assertEqual(stats.last_stop_notification_at, datetime(2026, 5, 15, 18, 0, 0))
        self.assertEqual(stats.completion_days_count, 5)

    def test_first_start_notification_sender_is_used_as_tester_name(self):
        messages = [
            ("AA12345 Start notification", datetime(2026, 5, 12, 9, 0, 0), "Later Tester"),
            ("AA12345 Start notification", datetime(2026, 5, 11, 9, 0, 0), "First Tester"),
            ("AA12345 Stop notification", datetime(2026, 5, 15, 18, 0, 0), "Reviewer"),
        ]

        grouped = parse_stats_by_aaid_from_messages(messages)
        stats = grouped["AA12345"]

        self.assertEqual(stats.first_start_notification_at, datetime(2026, 5, 11, 9, 0, 0))
        self.assertEqual(stats.first_start_notification_sender, "First Tester")

    def test_build_export_rows(self):
        grouped = {
            "AA123": DashboardStats(
                start_notifications_count=2,
                stop_notifications_count=1,
                techqa_start=datetime(2026, 5, 15, 9, 0, 0),
                techqa_stop=datetime(2026, 5, 15, 10, 0, 0),
                finalqa_start=None,
                finalqa_stop=None,
                techqa_milestone_at=datetime(2026, 5, 15, 9, 0, 0),
                first_start_notification_at=datetime(2026, 5, 1, 9, 0, 0),
                first_start_notification_sender="First Tester",
                last_stop_notification_at=datetime(2026, 5, 8, 18, 0, 0),
                completion_days_count=8,
            ),
            "AA999": DashboardStats(
                start_notifications_count=1,
                stop_notifications_count=1,
                techqa_start=None,
                techqa_stop=None,
                finalqa_start=datetime(2026, 5, 15, 11, 0, 0),
                finalqa_stop=datetime(2026, 5, 15, 12, 0, 0),
            ),
        }

        rows = build_export_rows(grouped)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["AAID"], "AA123")
        self.assertEqual(rows[0]["Start Notifications Count"], 2)
        self.assertEqual(rows[0]["TechQA Start"], "2026-05-15 09:00:00")
        self.assertEqual(rows[0]["Final QA Start"], "N/A")
        self.assertEqual(rows[0]["TechQA Milestone At"], "2026-05-15 09:00:00")
        self.assertEqual(rows[0]["First Start Notification"], "2026-05-01 09:00:00")
        self.assertEqual(rows[0]["Tester Name"], "First Tester")
        self.assertEqual(rows[0]["Last Stop Notification"], "2026-05-08 18:00:00")
        self.assertEqual(rows[0]["Completion Days Count"], 8)
        self.assertEqual(rows[1]["AAID"], "AA999")

    def test_count_days_inclusive(self):
        self.assertEqual(count_days_inclusive(datetime(2026, 5, 11).date(), datetime(2026, 5, 15).date()), 5)
        self.assertEqual(count_days_inclusive(datetime(2026, 5, 15).date(), datetime(2026, 5, 15).date()), 1)
        self.assertEqual(count_days_inclusive(datetime(2026, 5, 16).date(), datetime(2026, 5, 17).date()), 2)

    def test_get_date_range_presets(self):
        now = datetime(2026, 5, 15, 12, 0, 0)

        start_1, end_1 = get_date_range("Last 1 Month", "", "", now=now)
        self.assertEqual(start_1, datetime(2026, 4, 15, 12, 0, 0))
        self.assertEqual(end_1, now)

        start_2, end_2 = get_date_range("Last 2 Months", "", "", now=now)
        self.assertEqual(start_2, datetime(2026, 3, 16, 12, 0, 0))
        self.assertEqual(end_2, now)

        start_6, end_6 = get_date_range("Last 6 Months", "", "", now=now)
        self.assertEqual(start_6, datetime(2025, 11, 16, 12, 0, 0))
        self.assertEqual(end_6, now)

    def test_get_date_range_custom(self):
        start, end = get_date_range("Custom Range", "2026-01-01", "2026-01-31")
        self.assertEqual(start, datetime(2026, 1, 1, 0, 0, 0))
        self.assertEqual(end, datetime(2026, 1, 31, 23, 59, 59))

    def test_get_date_range_custom_invalid(self):
        with self.assertRaises(ValueError):
            get_date_range("Custom Range", "2026-02-01", "2026-01-31")

        with self.assertRaises(ValueError):
            get_date_range("Custom Range", "invalid", "2026-01-31")

    def test_daily_notification_counts_by_aaid(self):
        messages = [
            ("AA12345 Start notification", datetime(2026, 5, 15, 9, 0, 0)),
            ("AA12345 Start notification", datetime(2026, 5, 15, 10, 0, 0)),
            ("AA12345 Stop notification", datetime(2026, 5, 15, 18, 0, 0)),
            ("AA12345 Stop notification", datetime(2026, 5, 16, 18, 0, 0)),
            ("AA54321 Start notification", datetime(2026, 5, 15, 11, 0, 0)),
            ("AA54321 Stop notification", datetime(2026, 5, 15, 17, 0, 0)),
            ("AA54321 TechQA started", datetime(2026, 5, 15, 8, 0, 0)),
        ]

        daily = parse_daily_notification_counts_by_aaid(messages)

        self.assertEqual(daily["AA12345"]["2026-05-15"].start_count, 2)
        self.assertEqual(daily["AA12345"]["2026-05-15"].stop_count, 1)
        self.assertEqual(daily["AA12345"]["2026-05-16"].start_count, 0)
        self.assertEqual(daily["AA12345"]["2026-05-16"].stop_count, 1)
        self.assertEqual(daily["AA54321"]["2026-05-15"].start_count, 1)
        self.assertEqual(daily["AA54321"]["2026-05-15"].stop_count, 1)

    def test_normalize_for_comparison_accepts_aware_datetime(self):
        aware_value = datetime(2026, 5, 15, 10, 30, 0, tzinfo=timezone.utc)
        normalized = _normalize_for_comparison(aware_value)

        self.assertIsNotNone(normalized)
        self.assertIsNone(normalized.tzinfo)


if __name__ == "__main__":
    unittest.main()

