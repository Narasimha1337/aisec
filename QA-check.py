import re
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox
from typing import Iterable, Optional
import threading
import pythoncom


START_RE = re.compile(r"\bstart(?:ed)?\b", re.IGNORECASE)
STOP_RE = re.compile(r"\b(stop(?:ped)?|end(?:ed)?)\b", re.IGNORECASE)
TECH_QA_RE = re.compile(r"\btech\s*qa\b|\btechqa\b", re.IGNORECASE)
FINAL_QA_RE = re.compile(r"\bfinal\s*qa\b|\bfinalqa\b", re.IGNORECASE)
NOTIFICATION_RE = re.compile(r"\bnotifications?\b", re.IGNORECASE)
COMPLETED_RE = re.compile(r"\b(complet(?:e|ed)|done|closed?)\b", re.IGNORECASE)
PROCEED_FINAL_QA_RE = re.compile(r"\bproceed\b.*\bfinal\s*qa\b|\bfinal\s*qa\b.*\bproceed\b", re.IGNORECASE)
AAID_PATTERNS = [
    re.compile(r"\bAAID\s*[:=-]\s*(AA\d+)\b", re.IGNORECASE),
    re.compile(r"\bAAID\s+(AA\d+)\b", re.IGNORECASE),
    re.compile(r"\b(AA\d+)\b", re.IGNORECASE),
]
EXCEL_FORMULA_PREFIXES = ("=", "+", "-", "@")
MAX_EMAILS_LIMIT = 5000


@dataclass
class DashboardStats:
    start_notifications_count: int = 0
    stop_notifications_count: int = 0
    raw_start_notifications_count: int = 0
    raw_stop_notifications_count: int = 0
    techqa_start: Optional[datetime] = None
    techqa_stop: Optional[datetime] = None
    finalqa_start: Optional[datetime] = None
    finalqa_stop: Optional[datetime] = None
    techqa_milestone_at: Optional[datetime] = None  # First TechQA event
    techqa_person: Optional[str] = None   # TechQA person name
    finalqa_person: Optional[str] = None   # Final QA person name
    first_start_notification_at: Optional[datetime] = None
    first_start_notification_sender: Optional[str] = None
    last_stop_notification_at: Optional[datetime] = None
    completion_days_count: Optional[int] = None


@dataclass
class DailyNotificationCounts:
    start_count: int = 0
    stop_count: int = 0
    raw_start_count: int = 0
    raw_stop_count: int = 0


class OutlookFolderNotFoundError(Exception):
    pass


def extract_aaid(subject: str) -> str:
    clean_subject = _strip_prefixes(subject)
    for pattern in AAID_PATTERNS:
        match = pattern.search(clean_subject)
        if match:
            return match.group(1).upper()
    return "UNKNOWN"


def _is_start(subject: str) -> bool:
    return bool(START_RE.search(_strip_prefixes(subject)))


def _is_stop(subject: str) -> bool:
    return bool(STOP_RE.search(_strip_prefixes(subject)))


def _is_techqa(subject: str) -> bool:
    return bool(TECH_QA_RE.search(_strip_prefixes(subject)))


def _is_finalqa(subject: str) -> bool:
    return bool(FINAL_QA_RE.search(_strip_prefixes(subject)))


def _is_notification(subject: str) -> bool:
    return bool(NOTIFICATION_RE.search(_strip_prefixes(subject)))
def _strip_prefixes(subject: str) -> str:
    # Remove common reply/forward prefixes (RE:, FW:, FWD:) and whitespace
    return re.sub(r"^(\s*(RE|FW|FWD)\s*[:：])+", "", subject, flags=re.IGNORECASE).strip()


def _to_datetime(received_time) -> Optional[datetime]:
    # Preserve Outlook wall-clock time exactly so fetched timestamps match what
    # the user sees in Outlook UI.
    if isinstance(received_time, datetime):
        return datetime(
            received_time.year,
            received_time.month,
            received_time.day,
            received_time.hour,
            received_time.minute,
            received_time.second,
            received_time.microsecond,
        )
    if received_time is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(received_time))
        return datetime(
            parsed.year,
            parsed.month,
            parsed.day,
            parsed.hour,
            parsed.minute,
            parsed.second,
            parsed.microsecond,
        )
    except ValueError:
        return None


def _normalize_for_comparison(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        # Outlook ReceivedTime is already displayed in local wall time for the
        # current profile. Preserve that wall-clock and only drop tzinfo so
        # date bucketing doesn't shift yesterday mails into today.
        return value.replace(tzinfo=None)
    return value


def _latest(current: Optional[datetime], candidate: Optional[datetime]) -> Optional[datetime]:
    if candidate is None:
        return current
    if current is None or candidate > current:
        return candidate
    return current


def _earliest(current: Optional[datetime], candidate: Optional[datetime]) -> Optional[datetime]:
    if candidate is None:
        return current
    if current is None or candidate < current:
        return candidate
    return current


def _normalize_sender_name(sender_name: Optional[object]) -> Optional[str]:
    if sender_name is None:
        return None
    normalized = str(sender_name).strip()
    return normalized or None


def _sender_dedupe_key(sender_name: Optional[str]) -> str:
    normalized = _normalize_sender_name(sender_name)
    if normalized is None:
        return "__unknown_sender__"
    return normalized.casefold()


def _unpack_message(message) -> tuple[str, object, Optional[str], str]:
    if len(message) >= 4:
        subject, received_time, sender_name, body_text = message[:4]
    elif len(message) == 3:
        subject, received_time, sender_name = message
        body_text = ""
    elif len(message) == 2:
        subject, received_time = message
        sender_name = None
        body_text = ""
    else:
        raise ValueError("Each message must include at least subject and received time.")

    return str(subject or ""), received_time, _normalize_sender_name(sender_name), str(body_text or "")


def _combine_message_text(subject_text: str, body_text: str) -> str:
    if not body_text:
        return subject_text
    return f"{subject_text}\n{body_text}"


def _is_completed(text: str) -> bool:
    return bool(COMPLETED_RE.search(text))


def _is_techqa_completed(text: str) -> bool:
    return _is_techqa(text) and _is_completed(text)


def _is_finalqa_handoff(text: str) -> bool:
    return bool(FINAL_QA_RE.search(text) or PROCEED_FINAL_QA_RE.search(text))


def _safe_log_text(value: object, max_len: int = 500) -> str:
    text = str(value).replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > max_len:
        return text[:max_len] + "...(truncated)"
    return text


def _sanitize_excel_cell(value: object) -> object:
    if not isinstance(value, str):
        return value
    trimmed = value.lstrip()
    if trimmed.startswith(EXCEL_FORMULA_PREFIXES):
        return "'" + value
    return value


def count_days_inclusive(start_day: date, end_day: date) -> int:
    if end_day < start_day:
        return 0
    return (end_day - start_day).days + 1


def _apply_message_to_stats(
    stats: DashboardStats,
    subject_text: str,
    event_time: Optional[datetime],
    sender_name: Optional[str] = None,
) -> None:



    # Exclude automatic replies from notification stats
    lowered = subject_text.lower()
    if "automatic reply" in lowered or "autoreply" in lowered or "auto-reply" in lowered:
        return

    is_start = _is_start(subject_text)
    is_stop = _is_stop(subject_text)
    is_bracket_start = "[START]" in subject_text.upper()
    is_bracket_stop = "[STOP]" in subject_text.upper()
    is_notification_type = _is_notification(subject_text)
    is_pentest = "[PENTEST]" in subject_text.upper()

    # DEBUG: Log every subject processed and what is detected
    if hasattr(stats, '_log_debug'):
        stats._log_debug(f"Processing subject: {subject_text} | is_pentest={is_pentest} is_bracket_start={is_bracket_start} is_bracket_stop={is_bracket_stop} is_start={is_start} is_stop={is_stop} is_notification_type={is_notification_type}")

    # Only count if [PENTEST] is present in subject
    if is_pentest and (is_bracket_start or (is_notification_type and is_start)):
        stats.raw_start_notifications_count += 1
        start_key = _sender_dedupe_key(sender_name)
        seen_start = getattr(stats, "_seen_start_notification_senders", set())
        if start_key not in seen_start:
            seen_start.add(start_key)
            setattr(stats, "_seen_start_notification_senders", seen_start)
            stats.start_notifications_count += 1
        previous_first_start = stats.first_start_notification_at
        stats.first_start_notification_at = _earliest(stats.first_start_notification_at, event_time)
    if is_pentest and (is_bracket_stop or (is_notification_type and is_stop)):
        stats.raw_stop_notifications_count += 1
        stop_key = _sender_dedupe_key(sender_name)
        seen_stop = getattr(stats, "_seen_stop_notification_senders", set())
        if stop_key not in seen_stop:
            seen_stop.add(stop_key)
            setattr(stats, "_seen_stop_notification_senders", seen_stop)
            stats.stop_notifications_count += 1
        stats.last_stop_notification_at = _latest(stats.last_stop_notification_at, event_time)

    # TechQA / FinalQA subjects don't carry [START]/[STOP] brackets and the
    # Start/End values are sender-aware, so they are computed in the second pass
    # of parse_stats_by_aaid_from_messages, not here. We only collect the latest
    # FinalQA-subject email here as a fallback for Final QA End.
    if _is_finalqa(subject_text):
        stats.finalqa_stop = _latest(stats.finalqa_stop, event_time)


def parse_stats_from_messages(messages: Iterable[tuple[str, object]]) -> DashboardStats:
    stats = DashboardStats()

    for message in messages:
        subject, received_time, sender_name, _body_text = _unpack_message(message)
        if not subject:
            continue

        event_time = _to_datetime(received_time)
        _apply_message_to_stats(stats, subject, event_time, sender_name)

    return stats


def parse_stats_by_aaid_from_messages(messages: Iterable[tuple[str, object]], filter_aaid: Optional[set[str]] = None) -> dict[str, DashboardStats]:
    message_list = list(messages)
    stats_by_aaid: dict[str, DashboardStats] = {}
    
    # Track all start notifications by AAID to capture sender of earliest one
    start_notifications_by_aaid: dict[str, list[tuple[Optional[datetime], Optional[str]]]] = {}

    # First pass: collect stats and track start notifications
    for msg in message_list:
        subject, received_time, sender_name, _body_text = _unpack_message(msg)
        if not subject:
            continue

        event_time = _to_datetime(received_time)
        aaid = extract_aaid(subject)
        # DEBUG: Log extracted AAID and subject
        try:
            with open("outlook_qa_dashboard_debug.log", "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[PARSE] Subject: {_safe_log_text(subject)} | "
                    f"Extracted AAID: {_safe_log_text(aaid)}\n"
                )
        except Exception:
            pass
        # Filter by AAID if specified
        if filter_aaid is not None and aaid not in filter_aaid:
            continue
        if aaid not in stats_by_aaid:
            stats_by_aaid[aaid] = DashboardStats()

        _apply_message_to_stats(
            stats_by_aaid[aaid],
            subject,
            event_time,
            sender_name,
        )

        # Track start notifications
        is_start = _is_start(subject)
        is_bracket_start = "[START]" in subject.upper()
        is_notification_type = _is_notification(subject)

        if is_bracket_start or (is_notification_type and is_start):
            if aaid not in start_notifications_by_aaid:
                start_notifications_by_aaid[aaid] = []
            start_notifications_by_aaid[aaid].append((event_time, sender_name))
    
    # Second pass: set sender for earliest start notification
    for aaid, start_notifications in start_notifications_by_aaid.items():
        if aaid in stats_by_aaid and start_notifications:
            # Sort by time to find earliest
            earliest_with_sender = None
            for event_time, sender in sorted(start_notifications, key=lambda x: (x[0] is None, x[0])):
                if sender:
                    earliest_with_sender = sender
                    break
            # If we found a sender, use it
            if earliest_with_sender:
                stats_by_aaid[aaid].first_start_notification_sender = earliest_with_sender

    sorted_for_timeline = sorted(
        message_list,
        key=lambda item: (
            _normalize_for_comparison(_to_datetime(item[1])) is None,
            _normalize_for_comparison(_to_datetime(item[1])) or datetime.min,
        ),
    )

    # Second pass:
    #   - TechQA Send Date = earliest TechQA email sent BY the tester
    #     (sender == first_start_notification_sender).
    #   - TechQA Person    = earliest TechQA email sender that is NOT the tester
    #     (i.e. the QA reviewer who picked it up).
    #   - Final QA Person  = earliest FinalQA email sender that is NOT the tester.
    # Start/Stop datetimes are still driven by _apply_message_to_stats.
    for msg in sorted_for_timeline:
        subject, received_time, sender_name, _body_text = _unpack_message(msg)
        if not subject:
            continue

        event_time = _normalize_for_comparison(_to_datetime(received_time))
        if event_time is None:
            continue

        aaid = extract_aaid(subject)
        if aaid not in stats_by_aaid:
            continue

        stats = stats_by_aaid[aaid]
        tester_name = stats.first_start_notification_sender

        if (
            _is_techqa(subject)
            and stats.techqa_milestone_at is None
            and tester_name is not None
            and sender_name is not None
            and sender_name == tester_name
        ):
            stats.techqa_milestone_at = event_time

        if (
            _is_techqa(subject)
            and stats.techqa_person is None
            and sender_name is not None
            and (tester_name is None or sender_name != tester_name)
        ):
            stats.techqa_person = sender_name

        # TechQA Start = earliest TechQA email from someone OTHER than the tester
        # (i.e. when the QA reviewer first responds).
        if (
            _is_techqa(subject)
            and stats.techqa_start is None
            and sender_name is not None
            and tester_name is not None
            and sender_name != tester_name
        ):
            stats.techqa_start = event_time

        # TechQA End = earliest FinalQA-subject email sent by the TechQA Person
        # (the same QA reviewer changes the subject to Final QA, handing off).
        if (
            _is_finalqa(subject)
            and stats.techqa_stop is None
            and stats.techqa_person is not None
            and sender_name is not None
            and sender_name == stats.techqa_person
        ):
            stats.techqa_stop = event_time

        if (
            _is_finalqa(subject)
            and stats.finalqa_person is None
            and sender_name is not None
            and (tester_name is None or sender_name != tester_name)
        ):
            stats.finalqa_person = sender_name

        # Final QA Start = earliest FinalQA email from someone OTHER than the tester.
        if (
            _is_finalqa(subject)
            and stats.finalqa_start is None
            and sender_name is not None
            and tester_name is not None
            and sender_name != tester_name
        ):
            stats.finalqa_start = event_time

    for stats in stats_by_aaid.values():
        if stats.first_start_notification_at and stats.last_stop_notification_at:
            stats.completion_days_count = count_days_inclusive(
                stats.first_start_notification_at.date(),
                stats.last_stop_notification_at.date(),
            )

    return stats_by_aaid


def parse_daily_notification_counts_by_aaid(
    messages: Iterable[tuple[str, object]],
    filter_aaid: Optional[set[str]] = None,
) -> dict[str, dict[str, DailyNotificationCounts]]:
    daily_counts_by_aaid: dict[str, dict[str, DailyNotificationCounts]] = {}
    seen_daily_start_senders: dict[tuple[str, str], set[str]] = {}
    seen_daily_stop_senders: dict[tuple[str, str], set[str]] = {}

    for message in messages:
        try:
            subject, received_time, sender_name, _body_text = _unpack_message(message)
        except ValueError:
            continue
        if not subject:
            continue

        subject_text = str(subject)


        # Exclude automatic replies from notification stats
        lowered = subject_text.lower()
        if "automatic reply" in lowered or "autoreply" in lowered or "auto-reply" in lowered:
            continue

        is_start = _is_start(subject_text)
        is_stop = _is_stop(subject_text)
        is_bracket_start = "[START]" in subject_text.upper()
        is_bracket_stop = "[STOP]" in subject_text.upper()
        is_notification_type = _is_notification(subject_text)
        is_pentest = "[PENTEST]" in subject_text.upper()

        # Only count if [PENTEST] is present in subject
        if not (is_pentest and ((is_bracket_start or is_bracket_stop) or (is_notification_type and (is_start or is_stop)))):
            continue

        event_time = _to_datetime(received_time)
        if not event_time:
            continue

        aaid = extract_aaid(subject_text)

        # Filter by AAID if specified
        if filter_aaid is not None and aaid not in filter_aaid:
            continue

        date_key = event_time.strftime("%Y-%m-%d")

        if aaid not in daily_counts_by_aaid:
            daily_counts_by_aaid[aaid] = {}
        if date_key not in daily_counts_by_aaid[aaid]:
            daily_counts_by_aaid[aaid][date_key] = DailyNotificationCounts()

        day_counts = daily_counts_by_aaid[aaid][date_key]
        sender_key = _sender_dedupe_key(sender_name)
        sender_bucket_key = (aaid, date_key)

        if is_bracket_start or (is_notification_type and is_start):
            day_counts.raw_start_count += 1
            start_seen = seen_daily_start_senders.setdefault(sender_bucket_key, set())
            if sender_key not in start_seen:
                start_seen.add(sender_key)
                day_counts.start_count += 1
        if is_bracket_stop or (is_notification_type and is_stop):
            day_counts.raw_stop_count += 1
            stop_seen = seen_daily_stop_senders.setdefault(sender_bucket_key, set())
            if sender_key not in stop_seen:
                stop_seen.add(sender_key)
                day_counts.stop_count += 1

    return daily_counts_by_aaid


def _format_dt(value: Optional[datetime]) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_custom_date(date_text: str) -> datetime:
    return datetime.strptime(date_text.strip(), "%Y-%m-%d")


def get_date_range(range_option: str, custom_start: str, custom_end: str, now: Optional[datetime] = None) -> tuple[Optional[datetime], Optional[datetime]]:
    current = now or datetime.now()
    option = range_option.strip().lower()

    # Snap presets to whole-day boundaries using local system time.
    today_midnight = current.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = current.replace(hour=23, minute=59, second=59, microsecond=999999)

    preset_days = {
        "last 1 week": 7,
        "last 1 month": 30,
        "last 3 months": 90,
        "last 2 months": 60,
        "last 6 months": 180,
    }
    if option in preset_days:
        start = today_midnight - timedelta(days=preset_days[option])
        return start, end_of_today

    if option == "custom range":
        start_date = _parse_custom_date(custom_start)
        end_date = _parse_custom_date(custom_end)
        # Include full end date by setting to last second of the day.
        end_inclusive = end_date + timedelta(days=1) - timedelta(seconds=1)
        if start_date > end_inclusive:
            raise ValueError("Custom start date must be on or before end date.")
        return start_date, end_inclusive
    raise ValueError("Unsupported date range option.")


def build_export_rows(stats_by_aaid: dict[str, DashboardStats]) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []


    for aaid in sorted(stats_by_aaid.keys()):
        stats = stats_by_aaid[aaid]
        rows.append(
            {
                "AAID": aaid,
                "Start Notifications Count": stats.start_notifications_count,
                "Stop Notifications Count": stats.stop_notifications_count,
                "TechQA Start": _format_dt(stats.techqa_start),
                "TechQA End": _format_dt(stats.techqa_stop),
                "Final QA Start": _format_dt(stats.finalqa_start),
                "Final QA End": _format_dt(stats.finalqa_stop),
                "TechQA Send Date": _format_dt(stats.techqa_milestone_at),
                "TechQA Person": stats.techqa_person or "N/A",
                "Final QA Person": stats.finalqa_person or "N/A",
                "First Start Notification": _format_dt(stats.first_start_notification_at),
                "Tester Name": stats.first_start_notification_sender or "N/A",
                "Last Stop Notification": _format_dt(stats.last_stop_notification_at),
                "Completion Days Count": stats.completion_days_count or 0,
            }
        )

    return rows


@dataclass
class AggregateStatistics:
    total_applications: int = 0
    avg_techqa_seconds: Optional[float] = None
    avg_finalqa_seconds: Optional[float] = None
    avg_totalqa_seconds: Optional[float] = None
    missing_start_count: int = 0
    missing_stop_count: int = 0
    techqa_sample_size: int = 0
    finalqa_sample_size: int = 0
    totalqa_sample_size: int = 0


@dataclass
class TrendStatistics:
    older_missing_start: int = 0
    recent_missing_start: int = 0
    older_missing_stop: int = 0
    recent_missing_stop: int = 0
    start_trend_text: str = "N/A"
    stop_trend_text: str = "N/A"
    has_comparison: bool = False


def compute_aggregate_statistics(stats_by_aaid: dict[str, DashboardStats]) -> AggregateStatistics:
    aggregate = AggregateStatistics()
    aggregate.total_applications = len(stats_by_aaid)

    techqa_durations: list[float] = []
    finalqa_durations: list[float] = []
    totalqa_durations: list[float] = []

    for stats in stats_by_aaid.values():
        if stats.techqa_start and stats.techqa_stop and stats.techqa_stop >= stats.techqa_start:
            techqa_durations.append((stats.techqa_stop - stats.techqa_start).total_seconds())
        if stats.finalqa_start and stats.finalqa_stop and stats.finalqa_stop >= stats.finalqa_start:
            finalqa_durations.append((stats.finalqa_stop - stats.finalqa_start).total_seconds())
        if (
            stats.techqa_start
            and stats.techqa_stop
            and stats.finalqa_start
            and stats.finalqa_stop
            and stats.techqa_stop >= stats.techqa_start
            and stats.finalqa_stop >= stats.finalqa_start
        ):
            totalqa_durations.append(
                (stats.techqa_stop - stats.techqa_start).total_seconds()
                + (stats.finalqa_stop - stats.finalqa_start).total_seconds()
            )
        if stats.start_notifications_count == 0:
            aggregate.missing_start_count += 1
        if stats.stop_notifications_count == 0:
            aggregate.missing_stop_count += 1

    if techqa_durations:
        aggregate.avg_techqa_seconds = sum(techqa_durations) / len(techqa_durations)
        aggregate.techqa_sample_size = len(techqa_durations)
    if finalqa_durations:
        aggregate.avg_finalqa_seconds = sum(finalqa_durations) / len(finalqa_durations)
        aggregate.finalqa_sample_size = len(finalqa_durations)
    if totalqa_durations:
        aggregate.avg_totalqa_seconds = sum(totalqa_durations) / len(totalqa_durations)
        aggregate.totalqa_sample_size = len(totalqa_durations)

    return aggregate


def _trend_text(older: int, recent: int, can_compare: bool) -> str:
    if not can_compare:
        return "Need >=2 days"
    if recent < older:
        return f"Decreased ({older} -> {recent})"
    if recent > older:
        return f"Increased ({older} -> {recent})"
    return f"No change ({older} -> {recent})"


def compute_missing_notification_trends(
    messages: Iterable[tuple[str, object, Optional[str], str]],
    filter_aaid: Optional[set[str]] = None,
) -> TrendStatistics:
    # day_aaid_status[date_key][aaid] = {"active": bool, "start": bool, "stop": bool}
    day_aaid_status: dict[str, dict[str, dict[str, bool]]] = {}

    for message in messages:
        subject, received_time, _sender_name, _body_text = _unpack_message(message)
        if not subject:
            continue

        event_time = _to_datetime(received_time)
        if event_time is None:
            continue

        date_key = event_time.strftime("%Y-%m-%d")
        aaid = extract_aaid(subject)
        if filter_aaid is not None and aaid not in filter_aaid:
            continue

        if date_key not in day_aaid_status:
            day_aaid_status[date_key] = {}
        if aaid not in day_aaid_status[date_key]:
            day_aaid_status[date_key][aaid] = {"active": True, "start": False, "stop": False}

        is_start = _is_start(subject)
        is_stop = _is_stop(subject)
        is_bracket_start = "[START]" in subject.upper()
        is_bracket_stop = "[STOP]" in subject.upper()
        is_notification_type = _is_notification(subject)
        is_pentest = "[PENTEST]" in subject.upper()

        if is_pentest and (is_bracket_start or (is_notification_type and is_start)):
            day_aaid_status[date_key][aaid]["start"] = True
        if is_pentest and (is_bracket_stop or (is_notification_type and is_stop)):
            day_aaid_status[date_key][aaid]["stop"] = True

    dates = sorted(day_aaid_status.keys())
    if not dates:
        return TrendStatistics()

    can_compare = len(dates) >= 2
    split_idx = max(len(dates) // 2, 1)
    older_dates = dates[:split_idx]
    recent_dates = dates[split_idx:]
    if not recent_dates:
        recent_dates = older_dates
        can_compare = False

    def count_missing(target_dates: list[str]) -> tuple[int, int]:
        missing_start = 0
        missing_stop = 0
        for date_key in target_dates:
            for status in day_aaid_status[date_key].values():
                if status["active"] and not status["start"]:
                    missing_start += 1
                if status["active"] and not status["stop"]:
                    missing_stop += 1
        return missing_start, missing_stop

    older_missing_start, older_missing_stop = count_missing(older_dates)
    recent_missing_start, recent_missing_stop = count_missing(recent_dates)

    return TrendStatistics(
        older_missing_start=older_missing_start,
        recent_missing_start=recent_missing_start,
        older_missing_stop=older_missing_stop,
        recent_missing_stop=recent_missing_stop,
        start_trend_text=_trend_text(older_missing_start, recent_missing_start, can_compare),
        stop_trend_text=_trend_text(older_missing_stop, recent_missing_stop, can_compare),
        has_comparison=can_compare,
    )


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "N/A"
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def export_stats_to_excel(stats_by_aaid: dict[str, DashboardStats], file_path: str) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for Excel export. Run: pip install openpyxl") from exc

    rows = build_export_rows(stats_by_aaid)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "AAID Summary"

    headers = [
        "AAID",
        "Start Notifications Count",
        "Stop Notifications Count",
        "TechQA Start",
        "TechQA End",
        "Final QA Start",
        "Final QA End",
        "TechQA Send Date",
        "TechQA Person",
        "Final QA Person",
        "Tester Name",
        "Completion Days Count",
    ]
    sheet.append(headers)

    for row in rows:
        sheet.append([_sanitize_excel_cell(row[header]) for header in headers])

    workbook.save(file_path)


def _split_path(folder_path: str) -> list[str]:
    return [part.strip() for part in folder_path.split("/") if part.strip()]


def _get_default_inbox(namespace):
    # 6 is olFolderInbox.
    return namespace.GetDefaultFolder(6)


def _resolve_child_path(base_folder, parts: list[str]):
    current = base_folder
    for part in parts:
        current = current.Folders.Item(part)
    return current


def _list_store_names(namespace) -> list[str]:
    stores = []
    for i in range(1, namespace.Folders.Count + 1):
        stores.append(str(namespace.Folders.Item(i).Name))
    return stores


def _get_sender_name(item) -> Optional[str]:
    sender_name = _normalize_sender_name(getattr(item, "SenderName", None))
    if sender_name:
        return sender_name

    sent_on_behalf_of = _normalize_sender_name(getattr(item, "SentOnBehalfOfName", None))
    if sent_on_behalf_of:
        return sent_on_behalf_of

    sender = getattr(item, "Sender", None)
    if sender is not None:
        try:
            exchange_user = sender.GetExchangeUser()
            exchange_name = _normalize_sender_name(getattr(exchange_user, "Name", None))
            if exchange_name:
                return exchange_name
        except Exception:
            pass

        try:
            address_entry_name = _normalize_sender_name(getattr(sender, "Name", None))
            if address_entry_name:
                return address_entry_name
        except Exception:
            pass

    return _normalize_sender_name(getattr(item, "SenderEmailAddress", None))


def get_outlook_folder(namespace, folder_path: str):
    parts = _split_path(folder_path)
    if not parts:
        return _get_default_inbox(namespace)

    if len(parts) == 1 and parts[0].lower() == "inbox":
        return _get_default_inbox(namespace)

    # Try treating the first segment as mailbox/store name.
    try:
        store_root = namespace.Folders.Item(parts[0])
        return _resolve_child_path(store_root, parts[1:])
    except Exception:
        pass

    # Fallback: treat path as relative to default Inbox.
    try:
        inbox = _get_default_inbox(namespace)
        if parts[0].lower() == "inbox":
            return _resolve_child_path(inbox, parts[1:])
        return _resolve_child_path(inbox, parts)
    except Exception as exc:
        stores = ", ".join(_list_store_names(namespace))
        raise OutlookFolderNotFoundError(
            "Could not find Outlook folder. Try one of these formats:\n"
            "- Inbox\n"
            "- Inbox/Your Subfolder\n"
            "- Mailbox - Your Name/Inbox/Your Subfolder\n"
            f"Available mailbox roots: {stores}"
        ) from exc


def read_messages_from_outlook(
    folder_path: str,
    max_emails: int,
    subject_contains: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[tuple[str, object, Optional[str], str]]:
    import win32com.client  # Local import so tests can run without Outlook dependency.
    import pythoncom
    pythoncom.CoInitialize()

    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    folder = get_outlook_folder(namespace, folder_path)

    items = folder.Items
    items.Sort("[ReceivedTime]", True)

    results: list[tuple[str, object, Optional[str], str]] = []
    filter_text = subject_contains.strip().lower()
    normalized_start = _normalize_for_comparison(start_date)
    normalized_end = _normalize_for_comparison(end_date)
    count = 0


    # DEBUG: Log every subject fetched from Outlook
    try:
        debug_log = open("outlook_qa_dashboard_debug.log", "a", encoding="utf-8")
        debug_log.write(f"[FILTER] Subject contains filter: '{_safe_log_text(filter_text)}'\n")
        debug_log.write(
            "[FILTER] Strict mode: only subjects containing '[PENTEST]', "
            "'Tech QA' / 'techqa', or 'Final QA' / 'finalqa' will be read.\n"
        )
        if normalized_start or normalized_end:
            debug_log.write(
                f"[FILTER] Date range: {normalized_start} -> {normalized_end}\n"
            )
    except Exception:
        debug_log = None

    # Strict subject match: read [PENTEST] thread emails plus any TechQA / Final QA
    # related messages (these keywords drive the dashboard's QA milestones).
    pentest_event_re = re.compile(
        r"\[PENTEST\]|\btech\s*qa\b|\btechqa\b|\bfinal\s*qa\b|\bfinalqa\b",
        re.IGNORECASE,
    )

    matched_subject_count = 0
    skipped_by_date_count = 0
    skipped_by_filter_count = 0

    for item in items:
        # 43 is olMail class; skip non-mail items to avoid attribute issues.
        if getattr(item, "Class", None) != 43:
            continue

        subject = getattr(item, "Subject", "") or ""

        # Skip anything that isn't a [PENTEST] [START]/[STOP] message before doing any further work.
        if not pentest_event_re.search(subject):
            continue

        matched_subject_count += 1

        received_time = _to_datetime(getattr(item, "ReceivedTime", None))
        normalized_received = _normalize_for_comparison(received_time)
        if debug_log:
            debug_log.write(
                f"[TIME_CHECK] raw={_safe_log_text(getattr(item, 'ReceivedTime', None))} | "
                f"parsed={_safe_log_text(received_time)}\n"
            )

        if normalized_end and normalized_received and normalized_received > normalized_end:
            skipped_by_date_count += 1
            if debug_log:
                debug_log.write(
                    f"[SKIPPED_NEWER_THAN_END] {_safe_log_text(normalized_received)} | "
                    f"{_safe_log_text(subject)}\n"
                )
            continue
        if normalized_start and normalized_received and normalized_received < normalized_start:
            # Items are sorted by newest first, so we can stop once we pass lower bound.
            skipped_by_date_count += 1
            if debug_log:
                debug_log.write(
                    f"[SKIPPED_OLDER_THAN_START] {_safe_log_text(normalized_received)} | "
                    f"{_safe_log_text(subject)}\n"
                )
            break

        if filter_text and filter_text not in subject.lower():
            skipped_by_filter_count += 1
            if debug_log:
                debug_log.write(f"[SKIPPED_SUBJECT_FILTER] {_safe_log_text(subject)}\n")
            continue

        if debug_log:
            debug_log.write(
                f"[FETCHED] {_safe_log_text(normalized_received)} | {_safe_log_text(subject)}\n"
            )

        results.append(
            (
                subject,
                normalized_received or received_time,
                _get_sender_name(item),
                getattr(item, "Body", "") or "",
            )
        )
        count += 1
        if count >= max_emails:
            break

    if debug_log:
        debug_log.write(
            f"[SUMMARY] PENTEST subjects matched: {matched_subject_count} | "
            f"excluded by date: {skipped_by_date_count} | "
            f"excluded by subject filter: {skipped_by_filter_count} | "
            f"kept: {len(results)}\n"
        )
        debug_log.close()

    return results


class DashboardUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Outlook QA Dashboard")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{int(screen_width * 0.95)}x{int(screen_height * 0.95)}")
        self.root.update_idletasks()

        self.mailbox_names = []
        self.selected_mailbox = tk.StringVar(value="")
        self.folder_path = tk.StringVar(value="Inbox")
        self.max_emails = tk.StringVar(value="100")
        self.subject_contains = tk.StringVar(value="")
        self.range_option = tk.StringVar(value="Last 1 Week")
        self.custom_start_date = tk.StringVar(value="")
        self.custom_end_date = tk.StringVar(value="")
        self.aaid_filter = tk.StringVar(value="")
        self.debug_enabled = tk.BooleanVar(value=False)

        self.selected_aaid = tk.StringVar(value="N/A")
        self.start_count = tk.StringVar(value="0")
        self.stop_count = tk.StringVar(value="0")
        self.techqa_start = tk.StringVar(value="N/A")
        self.techqa_stop = tk.StringVar(value="N/A")
        self.finalqa_start = tk.StringVar(value="N/A")
        self.finalqa_stop = tk.StringVar(value="N/A")
        self.first_start_notification_at = tk.StringVar(value="N/A")
        self.tester_name = tk.StringVar(value="N/A")
        self.last_stop_notification_at = tk.StringVar(value="N/A")
        self.completion_days_count = tk.StringVar(value="N/A")
        self.techqa_milestone_at = tk.StringVar(value="N/A")
        self.techqa_person = tk.StringVar(value="N/A")
        self.finalqa_person = tk.StringVar(value="N/A")
        self.aaid_keys: list[str] = []
        self.current_page_keys: list[str] = []
        self.stats_by_aaid: dict[str, DashboardStats] = {}
        self.daily_counts_by_aaid: dict[str, dict[str, DailyNotificationCounts]] = {}
        self._aaid_search_after_id: Optional[str] = None
        self.aaid_page_size = 50
        self.aaid_current_page = 0
        self.aaid_total_pages = 0
        self.aaid_page_info = tk.StringVar(value="Total: 0 | Page: 0/0")

        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, anchor="w", fg="blue")
        self.status_label.pack(fill="x", padx=12, pady=(0, 4))

        # Aggregate statistics StringVars (Statistics tab)
        self.stat_total_apps = tk.StringVar(value="0")
        self.stat_avg_techqa = tk.StringVar(value="N/A")
        self.stat_avg_finalqa = tk.StringVar(value="N/A")
        self.stat_avg_totalqa = tk.StringVar(value="N/A")
        self.stat_missing_start = tk.StringVar(value="0")
        self.stat_missing_stop = tk.StringVar(value="0")
        self.stat_techqa_sample = tk.StringVar(value="0")
        self.stat_finalqa_sample = tk.StringVar(value="0")
        self.stat_date_range = tk.StringVar(value="N/A")
        self.trend_stats = TrendStatistics()
        self.graphs_enabled = tk.BooleanVar(value=True)
        self._graph_canvas = None
        self._graph_figure = None
        self._graph_resize_after_id: Optional[str] = None

        self._init_mailboxes()
        self._build()
        self._auto_adjust_max_emails()
        self._update_stat_date_range_preview()

    def _log_debug(self, message: str) -> None:
        if not self.debug_enabled.get():
            return
        try:
            with open("outlook_qa_dashboard_debug.log", "a", encoding="utf-8") as log_file:
                log_file.write(f"[{datetime.now().isoformat()}] {_safe_log_text(message, max_len=2000)}\n")
        except Exception:
            pass

    def _init_mailboxes(self):
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            mailbox_names = []
            def is_mail_folder(folder):
                try:
                    PR_CONTAINER_CLASS = 0x3613001E
                    container_class = folder.PropertyAccessor.GetProperty(f"http://schemas.microsoft.com/mapi/proptag/{PR_CONTAINER_CLASS:08X}")
                    return container_class == "IPF.Note"
                except Exception:
                    # Fallback: check for Inbox, Sent Items, etc.
                    mail_names = ["Inbox", "Sent Items", "Drafts", "Outbox", "Deleted Items", "Junk Email"]
                    return folder.Name in mail_names or hasattr(folder, 'Items')

            for i in range(1, namespace.Folders.Count + 1):
                folder = namespace.Folders.Item(i)
                name = str(folder.Name).strip()
                # Exclude Online Archive roots
                if name.lower().startswith("online archive"):
                    continue
                # Only add root mailbox/account name
                mailbox_names.append(name)
            # Remove duplicates and sort
            mailbox_names = sorted(set(mailbox_names))
            self.mailbox_names = mailbox_names if mailbox_names else ["Default Mailbox"]
            self.selected_mailbox.set(self.mailbox_names[0])
        except Exception:
            self.mailbox_names = ["Default Mailbox"]
            self.selected_mailbox.set("Default Mailbox")

    def _toggle_custom_dates(self):
        if self.range_option.get() == "Custom Range":
            self.custom_dates_row.grid()
        else:
            self.custom_dates_row.grid_remove()

    def _on_range_option_changed(self, _selected=None):
        self._toggle_custom_dates()
        self._auto_adjust_max_emails()
        self._update_stat_date_range_preview(now=datetime.now())

    def _on_custom_date_changed(self, _event=None):
        if self.range_option.get() == "Custom Range":
            self._auto_adjust_max_emails()
        self._update_stat_date_range_preview(now=datetime.now())

    def _update_stat_date_range_preview(self, now: Optional[datetime] = None) -> None:
        try:
            start_date, end_date = get_date_range(
                self.range_option.get(),
                self.custom_start_date.get(),
                self.custom_end_date.get(),
                now=now,
            )
            self.stat_date_range.set(
                f"{start_date.strftime('%Y-%m-%d')}  to  {end_date.strftime('%Y-%m-%d')}"
            )
        except Exception:
            self.stat_date_range.set(self.range_option.get())

    def _auto_adjust_max_emails(self) -> None:
        # Use fixed values for preset ranges and fallback estimation for custom range.
        preset_max_emails = {
            "last 1 week": 200,
            "last 1 month": 500,
            "last 3 months": 1500,
            "last 6 months": 3000,
        }

        option = self.range_option.get().strip().lower()
        if option in preset_max_emails:
            self.max_emails.set(str(min(preset_max_emails[option], MAX_EMAILS_LIMIT)))
            return

        try:
            start_date, end_date = get_date_range(
                self.range_option.get(),
                self.custom_start_date.get(),
                self.custom_end_date.get(),
            )
        except Exception:
            return

        span_days = max((end_date.date() - start_date.date()).days + 1, 1)
        estimated_per_day = 80
        recommended = max(100, span_days * estimated_per_day)
        recommended = min(recommended, MAX_EMAILS_LIMIT)
        self.max_emails.set(str(recommended))

    def _build(self):
        frame = tk.Frame(self.root, padx=12, pady=0)
        frame.pack(fill="both", expand=True)
        frame.grid_rowconfigure(7, weight=1)

        # Statistics panel in top-right corner spanning the input rows.
        stats_panel = tk.LabelFrame(frame, text="Statistics", padx=10, pady=6)
        stats_panel.grid(row=0, column=4, rowspan=7, sticky="nsew", padx=(8, 0), pady=(2, 8))
        self._build_statistics_panel(stats_panel)

        tk.Label(frame, text="Mailbox:").grid(row=0, column=0, sticky="w", pady=(2, 2))
        mailbox_row = tk.Frame(frame)
        mailbox_row.grid(row=0, column=1, columnspan=2, sticky="w", pady=(2, 2))
        # Ensure OptionMenu always has at least one value to avoid init error
        mailbox_options = self.mailbox_names if self.mailbox_names else ["Default Mailbox"]
        mailbox_menu = tk.OptionMenu(mailbox_row, self.selected_mailbox, *mailbox_options)
        mailbox_menu.pack(side="left")
        tk.Checkbutton(mailbox_row, text="Enable Debug Logs", variable=self.debug_enabled).pack(
            side="left", padx=(10, 0)
        )

    # _reload_mailboxes removed; mailboxes now load automatically at startup

        tk.Label(frame, text="Outlook Folder (use /):").grid(row=1, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.folder_path, width=50).grid(row=1, column=1, sticky="ew", pady=4)

        tk.Label(frame, text="Max Emails:").grid(row=2, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.max_emails, width=12).grid(row=2, column=1, sticky="w", pady=4)

        tk.Label(frame, text="Subject Contains (optional):").grid(row=3, column=0, sticky="w")
        subject_frame = tk.Frame(frame)
        subject_frame.grid(row=3, column=1, sticky="ew", pady=4)
        tk.Entry(subject_frame, textvariable=self.subject_contains, width=50).pack(side="left", fill="x", expand=True)

        tk.Label(frame, text="Date Range:").grid(row=4, column=0, sticky="w")
        range_menu = tk.OptionMenu(
            frame,
            self.range_option,
            "Last 1 Week",
            "Last 1 Month",
            "Last 3 Months",
            "Last 6 Months",
            "Custom Range",
            command=self._on_range_option_changed,
        )
        range_menu.grid(row=4, column=1, sticky="w", pady=4)

        self.custom_dates_row = tk.Frame(frame)
        self.custom_dates_row.grid(row=5, column=0, columnspan=4, sticky="w", pady=4)
        self.custom_start_label = tk.Label(self.custom_dates_row, text="Custom Start (YYYY-MM-DD):")
        self.custom_start_label.pack(side="left")
        self.custom_start_entry = tk.Entry(self.custom_dates_row, textvariable=self.custom_start_date, width=14)
        self.custom_start_entry.pack(side="left", padx=(6, 16))
        self.custom_end_label = tk.Label(self.custom_dates_row, text="End:")
        self.custom_end_label.pack(side="left")
        self.custom_end_entry = tk.Entry(self.custom_dates_row, textvariable=self.custom_end_date, width=14)
        self.custom_end_entry.pack(side="left", padx=(6, 0))
        self.custom_dates_row.grid_remove()
        self.custom_start_entry.bind("<KeyRelease>", self._on_custom_date_changed)
        self.custom_end_entry.bind("<KeyRelease>", self._on_custom_date_changed)

        button_frame = tk.Frame(frame)
        button_frame.grid(row=6, column=1, sticky="w", pady=8)
        tk.Button(button_frame, text="Refresh", command=self.refresh).grid(row=0, column=0, padx=(0, 8))
        tk.Button(button_frame, text="Export to Excel", command=self.export_excel).grid(row=0, column=1)

        results_frame = tk.Frame(frame)
        results_frame.grid(row=7, column=0, columnspan=5, sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=0)
        results_frame.grid_columnconfigure(1, weight=1)

        left_panel = tk.LabelFrame(results_frame, text="AAID Results", padx=8, pady=6)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        left_panel.grid_rowconfigure(2, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)
        tk.Label(left_panel, text="Application [AAID]:").grid(row=0, column=0, sticky="w", pady=(4, 2))
        aaid_entry = tk.Entry(left_panel, textvariable=self.aaid_filter, width=30)
        aaid_entry.grid(row=1, column=0, sticky="ew", pady=(4, 16))
        aaid_entry.bind("<KeyRelease>", self._on_aaid_filter_change)

        aaid_list_frame = tk.Frame(left_panel)
        aaid_list_frame.grid(row=2, column=0, sticky="nsew")
        aaid_list_frame.grid_rowconfigure(0, weight=1)
        aaid_list_frame.grid_columnconfigure(0, weight=1)
        self.aaid_listbox = tk.Listbox(aaid_list_frame, exportselection=False, height=8, justify="center")
        self.aaid_listbox.grid(row=0, column=0, sticky="nsew")
        aaid_scrollbar = tk.Scrollbar(aaid_list_frame, orient="vertical", command=self.aaid_listbox.yview)
        aaid_scrollbar.grid(row=0, column=1, sticky="ns")
        self.aaid_listbox.configure(yscrollcommand=aaid_scrollbar.set)
        self.aaid_listbox.bind("<<ListboxSelect>>", self.on_select_aaid)

        pager_frame = tk.Frame(left_panel)
        pager_frame.grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.prev_page_btn = tk.Button(pager_frame, text="Prev", width=7, command=self._go_prev_page)
        self.prev_page_btn.grid(row=0, column=0, padx=(0, 6))
        self.next_page_btn = tk.Button(pager_frame, text="Next", width=7, command=self._go_next_page)
        self.next_page_btn.grid(row=0, column=1, padx=(0, 8))
        tk.Label(pager_frame, textvariable=self.aaid_page_info).grid(row=0, column=2, sticky="w")

        detail_panel = tk.LabelFrame(results_frame, text="AAID Details", padx=10, pady=6)
        detail_panel.grid(row=0, column=1, sticky="nsew")
        detail_panel.grid_columnconfigure(1, weight=1)
        detail_panel.grid_columnconfigure(3, weight=1)

        def add_metric_pair(
            row_idx: int,
            left_label: str,
            left_var: tk.StringVar,
            right_label: Optional[str] = None,
            right_var: Optional[tk.StringVar] = None,
            top_pad: int = 2,
            bottom_pad: int = 2,
        ) -> None:
            tk.Label(detail_panel, text=left_label).grid(row=row_idx, column=0, sticky="w", pady=(top_pad, bottom_pad))
            tk.Label(detail_panel, textvariable=left_var, anchor="w").grid(row=row_idx, column=1, sticky="ew", pady=(top_pad, bottom_pad))
            if right_label is not None and right_var is not None:
                tk.Label(detail_panel, text=right_label).grid(
                    row=row_idx,
                    column=2,
                    sticky="w",
                    pady=(top_pad, bottom_pad),
                    padx=(24, 0),
                )
                tk.Label(detail_panel, textvariable=right_var, anchor="w").grid(
                    row=row_idx,
                    column=3,
                    sticky="ew",
                    pady=(top_pad, bottom_pad),
                )

        add_metric_pair(8, "Selected AAID:", self.selected_aaid, "Tester Name:", self.tester_name, top_pad=1, bottom_pad=1)
        add_metric_pair(9, "Start Notifications Count:", self.start_count, "Stop Notifications Count:", self.stop_count, top_pad=1, bottom_pad=1)
        add_metric_pair(10, "First Start Notification:", self.first_start_notification_at, "Last Stop Notification:", self.last_stop_notification_at, top_pad=1, bottom_pad=1)
        add_metric_pair(11, "Completion Days Count:", self.completion_days_count, "TechQA Send Date:", self.techqa_milestone_at, top_pad=1, bottom_pad=1)
        add_metric_pair(12, "TechQA Start:", self.techqa_start, "TechQA End:", self.techqa_stop, top_pad=1, bottom_pad=1)
        add_metric_pair(13, "Final QA Start:", self.finalqa_start, "Final QA End:", self.finalqa_stop, top_pad=1, bottom_pad=1)
        add_metric_pair(14, "TechQA Person:", self.techqa_person, "Final QA Person:", self.finalqa_person, top_pad=1, bottom_pad=1)

        tk.Label(detail_panel, text="Daily Notification Check (expected 1 start and 1 stop):").grid(
            row=15, column=0, columnspan=4, sticky="w", pady=(6, 2)
        )
        daily_list_frame = tk.Frame(detail_panel)
        daily_list_frame.grid(row=16, column=0, columnspan=4, sticky="nsew")
        daily_list_frame.grid_rowconfigure(0, weight=1)
        daily_list_frame.grid_columnconfigure(0, weight=1)

        self.daily_listbox = tk.Listbox(
            daily_list_frame,
            exportselection=False,
            height=5,
            width=66,
            xscrollcommand=lambda *args: daily_h_scroll.set(*args),
            yscrollcommand=lambda *args: daily_v_scroll.set(*args),
        )
        self.daily_listbox.grid(row=0, column=0, sticky="nsew")

        daily_v_scroll = tk.Scrollbar(daily_list_frame, orient="vertical", command=self.daily_listbox.yview)
        daily_v_scroll.grid(row=0, column=1, sticky="ns")
        daily_h_scroll = tk.Scrollbar(daily_list_frame, orient="horizontal", command=self.daily_listbox.xview)
        daily_h_scroll.grid(row=1, column=0, sticky="ew")
        self.daily_listbox.configure(xscrollcommand=daily_h_scroll.set, yscrollcommand=daily_v_scroll.set)

        detail_panel.grid_rowconfigure(16, weight=1)

        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_columnconfigure(3, weight=0)
        frame.grid_columnconfigure(4, weight=1)

    def _build_statistics_panel(self, parent: tk.LabelFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        stats_left = tk.Frame(parent)
        stats_left.grid(row=0, column=0, sticky="nw")

        tk.Label(stats_left, text="Date Range:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        tk.Label(stats_left, textvariable=self.stat_date_range, fg="#444").grid(
            row=0, column=1, sticky="w", pady=(0, 4), padx=(6, 0)
        )

        tk.Label(stats_left, text="Total Applications:", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky="w", pady=2
        )
        tk.Label(stats_left, textvariable=self.stat_total_apps).grid(
            row=1, column=1, sticky="w", padx=(6, 0)
        )

        tk.Label(stats_left, text="Avg TechQA Duration:", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=2
        )
        tk.Label(stats_left, textvariable=self.stat_avg_techqa).grid(row=2, column=1, sticky="w", padx=(6, 0))

        tk.Label(stats_left, text="Avg Final QA Duration:", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=2
        )
        tk.Label(stats_left, textvariable=self.stat_avg_finalqa).grid(row=3, column=1, sticky="w", padx=(6, 0))

        tk.Label(stats_left, text="Avg QA Completion:", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", pady=2
        )
        tk.Label(stats_left, textvariable=self.stat_avg_totalqa).grid(row=4, column=1, sticky="w", padx=(6, 0))

        tk.Label(stats_left, text="Missing Start Notifications:", font=("Segoe UI", 9, "bold")).grid(
            row=5, column=0, sticky="w", pady=2
        )
        tk.Label(stats_left, textvariable=self.stat_missing_start, fg="red").grid(
            row=5, column=1, sticky="w", padx=(6, 0)
        )

        tk.Label(stats_left, text="Missing Stop Notifications:", font=("Segoe UI", 9, "bold")).grid(
            row=6, column=0, sticky="w", pady=2
        )
        tk.Label(stats_left, textvariable=self.stat_missing_stop, fg="red").grid(
            row=6, column=1, sticky="w", padx=(6, 0)
        )

    def _toggle_graphs(self) -> None:
        if self.graphs_enabled.get():
            self.graph_frame.grid()
            self._render_graphs()
        else:
            self.graph_frame.grid_remove()

    def _on_graph_frame_configure(self, _event=None) -> None:
        if not self.graphs_enabled.get() or self._graph_figure is None or self._graph_canvas is None:
            return

        if self._graph_resize_after_id is not None:
            self.root.after_cancel(self._graph_resize_after_id)

        self._graph_resize_after_id = self.root.after(120, self._resize_graph_to_frame)

    def _resize_graph_to_frame(self) -> None:
        self._graph_resize_after_id = None
        if not self.graphs_enabled.get() or self._graph_figure is None or self._graph_canvas is None:
            return

        width = max(self.graph_frame.winfo_width(), 260)
        height = max(self.graph_frame.winfo_height(), 180)
        dpi = self._graph_figure.get_dpi() or 100
        self._graph_figure.set_size_inches(width / dpi, height / dpi, forward=True)
        self._graph_canvas.draw_idle()

    def _render_graphs(self) -> None:
        # Clear any existing chart.
        for child in self.graph_frame.winfo_children():
            child.destroy()
        self._graph_canvas = None
        self._graph_figure = None

        if not self.graphs_enabled.get():
            return

        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            tk.Label(
                self.graph_frame,
                text="matplotlib not installed.\nRun: pip install matplotlib",
                fg="gray",
                justify="left",
            ).pack(anchor="w")
            return

        aggregate = compute_aggregate_statistics(self.stats_by_aaid)

        # Render donut chart with legend + counts (dashboard style).
        width = max(self.graph_frame.winfo_width(), 260)
        height = max(self.graph_frame.winfo_height(), 180)
        compact_layout = width < 560
        dpi = 100
        figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        if compact_layout:
            figure.subplots_adjust(left=0.03, right=0.98, top=0.88, bottom=0.10)
        else:
            figure.subplots_adjust(left=0.03, right=0.97, top=0.88, bottom=0.10)

        ax = figure.add_subplot(1, 1, 1)
        complete_count = 0
        missing_start_only = 0
        missing_stop_only = 0
        missing_both = 0

        for stats in self.stats_by_aaid.values():
            has_start = stats.start_notifications_count > 0
            has_stop = stats.stop_notifications_count > 0
            if has_start and has_stop:
                complete_count += 1
            elif (not has_start) and has_stop:
                missing_start_only += 1
            elif has_start and (not has_stop):
                missing_stop_only += 1
            else:
                missing_both += 1

        labels = [
            "Missing Start",
            "Missing Both",
        ]
        values = [
            missing_start_only,
            missing_both,
        ]
        colors = ["#f2c500", "#ef5350"]

        filtered = [(label, value, color) for label, value, color in zip(labels, values, colors) if value > 0]
        if not filtered:
            filtered = [("No Data", 1, "#d0d0d0")]

        f_labels = [item[0] for item in filtered]
        f_values = [item[1] for item in filtered]
        f_colors = [item[2] for item in filtered]

        pie_radius = 0.78 if compact_layout else 1.0
        pie_center = (-0.34, 0.0) if compact_layout else (0.0, 0.0)
        wedges, _ = ax.pie(
            f_values,
            colors=f_colors,
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.42, "edgecolor": "white"},
            radius=pie_radius,
            center=pie_center,
        )
        ax.set(aspect="equal")
        ax.set_title(f"Notification Completeness | Apps: {aggregate.total_applications}", fontsize=9)

        avg_completion_text = format_duration(aggregate.avg_totalqa_seconds)
        center_x = pie_center[0]
        ax.text(
            center_x,
            0,
            f"Avg QA\n{avg_completion_text}",
            ha="center",
            va="center",
            fontsize=8,
            color="#333",
        )

        legend_labels = [f"{label}    {value}" for label, value in zip(f_labels, f_values)]
        legend_title = f"Start Missing: {aggregate.missing_start_count}\nStop Missing: {aggregate.missing_stop_count}"
        legend_anchor_x = 0.52 if compact_layout else 1.02
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(legend_anchor_x, 0.5),
            frameon=False,
            fontsize=8,
            title=legend_title,
            title_fontsize=8,
            handlelength=1.2,
            handletextpad=0.5,
            labelspacing=0.9,
        )

        canvas = FigureCanvasTkAgg(figure, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._graph_canvas = canvas
        self._graph_figure = figure
        self._resize_graph_to_frame()

    def _update_statistics_panel(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        now: Optional[datetime] = None,
    ) -> None:
        aggregate = compute_aggregate_statistics(self.stats_by_aaid)
        self.stat_total_apps.set(str(aggregate.total_applications))
        self.stat_avg_techqa.set(format_duration(aggregate.avg_techqa_seconds))
        self.stat_avg_finalqa.set(format_duration(aggregate.avg_finalqa_seconds))
        self.stat_avg_totalqa.set(format_duration(aggregate.avg_totalqa_seconds))
        self.stat_missing_start.set(str(aggregate.missing_start_count))
        self.stat_missing_stop.set(str(aggregate.missing_stop_count))
        self.stat_techqa_sample.set(str(aggregate.techqa_sample_size))
        self.stat_finalqa_sample.set(str(aggregate.finalqa_sample_size))

        if start_date is not None and end_date is not None:
            self.stat_date_range.set(
                f"{start_date.strftime('%Y-%m-%d')}  to  {end_date.strftime('%Y-%m-%d')}"
            )
        else:
            try:
                computed_start, computed_end = get_date_range(
                    self.range_option.get(),
                    self.custom_start_date.get(),
                    self.custom_end_date.get(),
                    now=now,
                )
                self.stat_date_range.set(
                    f"{computed_start.strftime('%Y-%m-%d')}  to  {computed_end.strftime('%Y-%m-%d')}"
                )
            except Exception:
                self.stat_date_range.set(self.range_option.get())

        # Graph section removed from UI.

    def _on_aaid_filter_change(self, _event=None) -> None:
        if self._aaid_search_after_id is not None:
            self.root.after_cancel(self._aaid_search_after_id)

        aaid_filter_str = self.aaid_filter.get().strip()
        if aaid_filter_str:
            filter_list = [aaid.strip() for aaid in aaid_filter_str.split(",") if aaid.strip()]
            if len(filter_list) > 10:
                self.status_var.set("AAID search supports a maximum of 10 values.")
                return

        def run_search():
            self.refresh()

        self._aaid_search_after_id = self.root.after(350, run_search)

    def _apply_stats_to_view(self, stats: DashboardStats) -> None:
        self.start_count.set(str(stats.start_notifications_count))
        self.stop_count.set(str(stats.stop_notifications_count))
        self.techqa_start.set(_format_dt(stats.techqa_start))
        self.techqa_stop.set(_format_dt(stats.techqa_stop))
        self.finalqa_start.set(_format_dt(stats.finalqa_start))
        self.finalqa_stop.set(_format_dt(stats.finalqa_stop))
        self.first_start_notification_at.set(_format_dt(stats.first_start_notification_at))
        self.tester_name.set(stats.first_start_notification_sender or "N/A")
        self.last_stop_notification_at.set(_format_dt(stats.last_stop_notification_at))
        self.completion_days_count.set("N/A" if stats.completion_days_count is None else str(stats.completion_days_count))
        self.techqa_milestone_at.set(_format_dt(stats.techqa_milestone_at))
        self.techqa_person.set(stats.techqa_person or "N/A")
        self.finalqa_person.set(stats.finalqa_person or "N/A")

    def _go_prev_page(self) -> None:
        if self.aaid_current_page <= 0:
            return
        self.aaid_current_page -= 1
        self._reload_aaid_list(reset_page=False)
        if self.current_page_keys:
            self.aaid_listbox.selection_set(0)
            self.on_select_aaid()

    def _go_next_page(self) -> None:
        if self.aaid_current_page >= self.aaid_total_pages - 1:
            return
        self.aaid_current_page += 1
        self._reload_aaid_list(reset_page=False)
        if self.current_page_keys:
            self.aaid_listbox.selection_set(0)
            self.on_select_aaid()

    def _update_pagination_controls(self) -> None:
        total_count = len(self.aaid_keys)
        if total_count == 0:
            self.aaid_total_pages = 0
            self.aaid_current_page = 0
            self.aaid_page_info.set("Total: 0 | Page: 0/0")
            self.prev_page_btn.config(state="disabled")
            self.next_page_btn.config(state="disabled")
            return

        self.aaid_total_pages = (total_count + self.aaid_page_size - 1) // self.aaid_page_size
        self.aaid_current_page = min(self.aaid_current_page, self.aaid_total_pages - 1)
        self.aaid_current_page = max(self.aaid_current_page, 0)
        self.aaid_page_info.set(f"Total: {total_count} | Page: {self.aaid_current_page + 1}/{self.aaid_total_pages}")
        self.prev_page_btn.config(state="normal" if self.aaid_current_page > 0 else "disabled")
        self.next_page_btn.config(state="normal" if self.aaid_current_page < self.aaid_total_pages - 1 else "disabled")

    def _reload_aaid_list(self, reset_page: bool = True) -> None:
        self.aaid_listbox.delete(0, tk.END)
        self.aaid_keys = sorted(self.stats_by_aaid.keys())
        if reset_page:
            self.aaid_current_page = 0
        self._update_pagination_controls()

        start_idx = self.aaid_current_page * self.aaid_page_size
        end_idx = start_idx + self.aaid_page_size
        self.current_page_keys = self.aaid_keys[start_idx:end_idx]

        if not self.current_page_keys:
            self.selected_aaid.set("N/A")
            self._apply_stats_to_view(DashboardStats())
            self.daily_listbox.delete(0, tk.END)
            self.daily_listbox.insert(tk.END, "No AAID data found for selected range.")
            return

        for key in self.current_page_keys:
            item_stats = self.stats_by_aaid[key]
            display = f"{key}  |  Start: {item_stats.start_notifications_count}  Stop: {item_stats.stop_notifications_count}"
            self.aaid_listbox.insert(tk.END, display)

    def on_select_aaid(self, _event=None):
        selected = self.aaid_listbox.curselection()
        if not selected:
            return

        index = selected[0]
        if index < 0 or index >= len(self.current_page_keys):
            return

        key = self.current_page_keys[index]
        self.selected_aaid.set(key)
        self._apply_stats_to_view(self.stats_by_aaid[key])
        self._load_daily_counts_for_aaid(key)

    def _load_daily_counts_for_aaid(self, aaid: str) -> None:
        self.daily_listbox.delete(0, tk.END)
        daily_counts = self.daily_counts_by_aaid.get(aaid, {})
        if not daily_counts:
            self.daily_listbox.insert(tk.END, "No notification entries for this AAID in selected range.")
            return

        sorted_dates = sorted(daily_counts.keys(), reverse=True)
        for date_key in sorted_dates:
            counts = daily_counts[date_key]
            is_alert = counts.start_count > 1 or counts.stop_count > 1
            status = "ALERT" if is_alert else "OK"
            start_text = str(counts.start_count)
            stop_text = str(counts.stop_count)
            if counts.raw_start_count > counts.start_count:
                start_text = f"{counts.start_count} [{counts.raw_start_count}]"
            if counts.raw_stop_count > counts.stop_count:
                stop_text = f"{counts.stop_count} [{counts.raw_stop_count}]"
            row_text = f"{date_key} | Start: {start_text} | Stop: {stop_text} | {status}"
            self.daily_listbox.insert(tk.END, row_text)
            row_index = self.daily_listbox.size() - 1
            if is_alert:
                self.daily_listbox.itemconfig(row_index, fg="red")

    def export_excel(self):
        if not self.stats_by_aaid:
            messagebox.showinfo("No Data", "No results available. Click Refresh before exporting.")
            return

        default_name = f"outlook_qa_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path = filedialog.asksaveasfilename(
            title="Export Results to Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if not file_path:
            return

        try:
            export_stats_to_excel(self.stats_by_aaid, file_path)
            messagebox.showinfo("Export Complete", f"Exported results to:\n{file_path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Export Error", str(exc))

    def refresh(self):
        # Initialize mailboxes only if not already loaded (or always, if you want to refresh list)
        if not self.mailbox_names or self.mailbox_names == ["Default Mailbox"]:
            self._init_mailboxes()
            # If only initializing mailboxes, do not start refresh thread
            self.status_var.set("Ready.")
            return
        self.status_var.set("Loading emails and parsing...")
        self.root.after(100, self._start_refresh_thread)

    def _start_refresh_thread(self):
        thread = threading.Thread(target=self._refresh_worker, daemon=True)
        thread.start()

    def _refresh_worker(self):
        try:
            self._log_debug("Starting refresh worker.")
            system_now = datetime.now()
            filter_aaid = None
            aaid_filter_str = self.aaid_filter.get().strip()
            if aaid_filter_str:
                filter_list = [aaid.strip().upper() for aaid in aaid_filter_str.split(",") if aaid.strip()]
                if len(filter_list) > 10:
                    self.root.after(0, lambda: messagebox.showerror("Too many AAIDs", "You can search for up to 10 AAIDs at a time."))
                    self.root.after(0, lambda: self.status_var.set(""))
                    return
                filter_aaid = set(filter_list)

            try:
                max_emails = int(self.max_emails.get().strip())
                if max_emails <= 0 or max_emails > MAX_EMAILS_LIMIT:
                    raise ValueError("max emails must be positive")
            except ValueError:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Invalid value",
                        f"Max Emails must be a positive integer up to {MAX_EMAILS_LIMIT}.",
                    ),
                )
                self.root.after(0, lambda: self.status_var.set(""))
                return

            subject_contains = self.subject_contains.get()

            try:
                start_date, end_date = get_date_range(
                    self.range_option.get(),
                    self.custom_start_date.get(),
                    self.custom_end_date.get(),
                    now=system_now,
                )
            except ValueError:
                self.root.after(0, lambda: messagebox.showerror(
                    "Invalid date range",
                    "Use Last 1 Week/1/2/6 months or enter valid custom dates in YYYY-MM-DD format.",
                ))
                self.root.after(0, lambda: self.status_var.set(""))
                return

            try:
                folder_path = self._get_full_folder_path()
                messages = read_messages_from_outlook(
                    folder_path=folder_path,
                    max_emails=max_emails,
                    subject_contains=subject_contains,
                    start_date=start_date,
                    end_date=end_date,
                )
                self._log_debug(f"Total messages fetched: {len(messages)}")
                for msg in messages:
                    subject = msg[0] if msg else ""
                    self._log_debug(f"[MESSAGE_TO_PARSE] {subject}")
                stats_by_aaid = parse_stats_by_aaid_from_messages(messages, filter_aaid=filter_aaid)
                daily_counts_by_aaid = parse_daily_notification_counts_by_aaid(messages, filter_aaid=filter_aaid)
                trend_stats = compute_missing_notification_trends(messages, filter_aaid=filter_aaid)
            except Exception as exc:
                self.root.after(0, lambda: self.status_var.set(""))
                self.root.after(0, lambda: messagebox.showerror("Outlook Read Error", str(exc)))
                import traceback

                self._log_debug(f"Outlook Read Error: {exc}\n{traceback.format_exc()}")
                return

            def update_ui():
                self.stats_by_aaid = stats_by_aaid
                self.daily_counts_by_aaid = daily_counts_by_aaid
                self.trend_stats = trend_stats
                self._reload_aaid_list()
                self._update_statistics_panel(start_date=start_date, end_date=end_date, now=system_now)
                self._update_stat_date_range_preview(now=system_now)
                if not self.aaid_keys:
                    self.selected_aaid.set("N/A")
                    self._apply_stats_to_view(DashboardStats())
                    self.daily_listbox.delete(0, tk.END)
                    self.daily_listbox.insert(tk.END, "No AAID data found for selected range.")
                    self.status_var.set(f"No records found (0 of {len(messages)} messages matched).")
                else:
                    self.aaid_listbox.selection_set(0)
                    self.on_select_aaid()
                    self.status_var.set(
                        f"Found {len(self.aaid_keys)} AAID(s) from {len(messages)} message(s)."
                    )

            self.root.after(0, update_ui)
        except Exception as exc:
            self.root.after(0, lambda: self.status_var.set(""))
            self.root.after(0, lambda: messagebox.showerror("Thread Error", str(exc)))
            self._log_debug(f"Thread Error: {exc}")

    def _get_full_folder_path(self):
        mailbox = self.selected_mailbox.get().strip()
        folder = self.folder_path.get().strip()
        if not mailbox or mailbox.lower() == "default mailbox":
            return folder or "Inbox"
        if folder.lower().startswith(mailbox.lower() + "/"):
            folder = folder[len(mailbox) + 1:]
        folder = folder.strip("/")
        if not folder:
            folder = "Inbox"
        return f"{mailbox}/{folder}"


def main():
    try:
        root = tk.Tk()
        app = DashboardUI(root)
        app.refresh()
        root.mainloop()
    except Exception as exc:
        import traceback
        error_message = f"[FATAL ERROR] {exc}\n{traceback.format_exc()}"
        print(error_message)
        try:
            with open("outlook_qa_dashboard_debug.log", "a", encoding="utf-8") as log_file:
                log_file.write(error_message + "\n")
        except Exception:
            pass


if __name__ == '__main__':
    main()
