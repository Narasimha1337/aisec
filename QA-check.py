import re
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox
from typing import Iterable, Optional


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


@dataclass
class DashboardStats:
    start_notifications_count: int = 0
    stop_notifications_count: int = 0
    techqa_start: Optional[datetime] = None
    techqa_stop: Optional[datetime] = None
    finalqa_start: Optional[datetime] = None
    finalqa_stop: Optional[datetime] = None
    techqa_milestone_at: Optional[datetime] = None  # First TechQA event
    techqa_milestone_sender: Optional[str] = None   # Sender for TechQA milestone
    first_start_notification_at: Optional[datetime] = None
    first_start_notification_sender: Optional[str] = None
    last_stop_notification_at: Optional[datetime] = None
    completion_days_count: Optional[int] = None


@dataclass
class DailyNotificationCounts:
    start_count: int = 0
    stop_count: int = 0


class OutlookFolderNotFoundError(Exception):
    pass


def extract_aaid(subject: str) -> str:
    for pattern in AAID_PATTERNS:
        match = pattern.search(subject)
        if match:
            return match.group(1).upper()
    return "UNKNOWN"


def _is_start(subject: str) -> bool:
    return bool(START_RE.search(subject))


def _is_stop(subject: str) -> bool:
    return bool(STOP_RE.search(subject))


def _is_techqa(subject: str) -> bool:
    return bool(TECH_QA_RE.search(subject))


def _is_finalqa(subject: str) -> bool:
    return bool(FINAL_QA_RE.search(subject))


def _is_notification(subject: str) -> bool:
    return bool(NOTIFICATION_RE.search(subject))


def _to_datetime(received_time) -> Optional[datetime]:
    # Outlook typically returns datetime already; convert fallback string safely.
    if isinstance(received_time, datetime):
        return received_time
    if received_time is None:
        return None
    try:
        return datetime.fromisoformat(str(received_time))
    except ValueError:
        return None


def _normalize_for_comparison(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        # Convert aware datetimes to local wall time and drop tzinfo so all comparisons use same type.
        return value.astimezone().replace(tzinfo=None)
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
    is_start = _is_start(subject_text)
    is_stop = _is_stop(subject_text)

    if _is_notification(subject_text):
        if is_start:
            stats.start_notifications_count += 1
            previous_first_start = stats.first_start_notification_at
            stats.first_start_notification_at = _earliest(stats.first_start_notification_at, event_time)
            if stats.first_start_notification_at != previous_first_start:
                stats.first_start_notification_sender = sender_name
        if is_stop:
            stats.stop_notifications_count += 1
            stats.last_stop_notification_at = _latest(stats.last_stop_notification_at, event_time)

    if _is_techqa(subject_text):
        if is_start:
            stats.techqa_start = _latest(stats.techqa_start, event_time)
        if is_stop or _is_completed(subject_text):
            stats.techqa_stop = _latest(stats.techqa_stop, event_time)

    if _is_finalqa(subject_text):
        if is_start:
            stats.finalqa_start = _latest(stats.finalqa_start, event_time)
        if is_stop or _is_completed(subject_text):
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


def parse_stats_by_aaid_from_messages(messages: Iterable[tuple[str, object]]) -> dict[str, DashboardStats]:
    message_list = list(messages)
    stats_by_aaid: dict[str, DashboardStats] = {}

    for msg in message_list:
        subject, received_time, sender_name, _body_text = _unpack_message(msg)
        if not subject:
            continue

        event_time = _to_datetime(received_time)
        aaid = extract_aaid(subject)
        if aaid not in stats_by_aaid:
            stats_by_aaid[aaid] = DashboardStats()

        _apply_message_to_stats(
            stats_by_aaid[aaid],
            subject,
            event_time,
            sender_name,
        )

    sorted_for_timeline = sorted(
        message_list,
        key=lambda item: (
            _normalize_for_comparison(_to_datetime(item[1])) is None,
            _normalize_for_comparison(_to_datetime(item[1])) or datetime.min,
        ),
    )

    techqa_owner_by_aaid: dict[str, Optional[str]] = {}
    techqa_completed_at_by_aaid: dict[str, Optional[datetime]] = {}

    for msg in sorted_for_timeline:
        subject, received_time, sender_name, body_text = _unpack_message(msg)
        if not subject:
            continue

        event_time = _normalize_for_comparison(_to_datetime(received_time))
        if event_time is None:
            continue

        subject_text = subject
        message_text = _combine_message_text(subject_text, body_text)
        aaid = extract_aaid(subject_text)
        if aaid not in stats_by_aaid:
            continue

        stats = stats_by_aaid[aaid]

        if aaid not in techqa_owner_by_aaid:
            techqa_owner_by_aaid[aaid] = None
        if aaid not in techqa_completed_at_by_aaid:
            techqa_completed_at_by_aaid[aaid] = None

        if _is_techqa(subject_text) and stats.techqa_milestone_at is None:
            stats.techqa_milestone_at = event_time
            stats.techqa_milestone_sender = sender_name

        tester_name = stats.first_start_notification_sender
        if (
            _is_techqa(subject_text)
            and sender_name is not None
            and sender_name != tester_name
            and stats.techqa_start is None
        ):
            stats.techqa_start = event_time
            techqa_owner_by_aaid[aaid] = sender_name

        if _is_techqa_completed(message_text):
            stats.techqa_stop = _latest(stats.techqa_stop, event_time)
            techqa_completed_at_by_aaid[aaid] = event_time

        completed_at = techqa_completed_at_by_aaid[aaid]
        if completed_at is not None and event_time >= completed_at and _is_finalqa_handoff(message_text):
            if stats.finalqa_start is None or event_time < stats.finalqa_start:
                stats.finalqa_start = event_time

        if _is_finalqa(message_text) and _is_stop(message_text):
            stats.finalqa_stop = _latest(stats.finalqa_stop, event_time)

    for aaid, stats in stats_by_aaid.items():
        if stats.techqa_start is None and techqa_owner_by_aaid.get(aaid) is None:
            # Keep prior subject-only TechQA start fallback when sender-based inference is unavailable.
            pass

    for stats in stats_by_aaid.values():
        if stats.first_start_notification_at and stats.last_stop_notification_at:
            stats.completion_days_count = count_days_inclusive(
                stats.first_start_notification_at.date(),
                stats.last_stop_notification_at.date(),
            )

    return stats_by_aaid


def parse_daily_notification_counts_by_aaid(
    messages: Iterable[tuple[str, object]],
) -> dict[str, dict[str, DailyNotificationCounts]]:
    daily_counts_by_aaid: dict[str, dict[str, DailyNotificationCounts]] = {}

    for message in messages:
        if len(message) >= 2:
            subject, received_time = message[:2]
        else:
            continue
        if not subject:
            continue

        subject_text = str(subject)
        if not _is_notification(subject_text):
            continue

        event_time = _to_datetime(received_time)
        if not event_time:
            continue

        aaid = extract_aaid(subject_text)
        date_key = event_time.strftime("%Y-%m-%d")

        if aaid not in daily_counts_by_aaid:
            daily_counts_by_aaid[aaid] = {}
        if date_key not in daily_counts_by_aaid[aaid]:
            daily_counts_by_aaid[aaid][date_key] = DailyNotificationCounts()

        day_counts = daily_counts_by_aaid[aaid][date_key]
        if _is_start(subject_text):
            day_counts.start_count += 1
        if _is_stop(subject_text):
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

    if option == "last 1 month":
        return current - timedelta(days=30), current
    if option == "last 2 months":
        return current - timedelta(days=60), current
    if option == "last 6 months":
        return current - timedelta(days=180), current
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
                "TechQA Stop": _format_dt(stats.techqa_stop),
                "Final QA Start": _format_dt(stats.finalqa_start),
                "Final QA Stop": _format_dt(stats.finalqa_stop),
                "TechQA Milestone At": _format_dt(stats.techqa_milestone_at),
                "TechQA Milestone Sender": stats.techqa_milestone_sender or "N/A",
                "First Start Notification": _format_dt(stats.first_start_notification_at),
                "Tester Name": stats.first_start_notification_sender or "N/A",
                "Last Stop Notification": _format_dt(stats.last_stop_notification_at),
                "Completion Days Count": stats.completion_days_count or 0,
            }
        )

    return rows


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
        "TechQA Stop",
        "Final QA Start",
        "Final QA Stop",
        "TechQA Milestone At",
        "TechQA Milestone Sender",
        "First Start Notification",
        "Tester Name",
        "Last Stop Notification",
        "Completion Days Count",
    ]
    sheet.append(headers)

    for row in rows:
        sheet.append([row[header] for header in headers])

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

    for item in items:
        # 43 is olMail class; skip non-mail items to avoid attribute issues.
        if getattr(item, "Class", None) != 43:
            continue

        received_time = _to_datetime(getattr(item, "ReceivedTime", None))
        normalized_received = _normalize_for_comparison(received_time)

        if normalized_end and normalized_received and normalized_received > normalized_end:
            continue
        if normalized_start and normalized_received and normalized_received < normalized_start:
            # Items are sorted by newest first, so we can stop once we pass lower bound.
            break

        subject = getattr(item, "Subject", "") or ""
        if filter_text and filter_text not in subject.lower():
            continue

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

    return results


class DashboardUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Outlook QA Dashboard")
        self.root.geometry("1100x500")

        self.folder_path = tk.StringVar(value="Inbox")
        self.max_emails = tk.StringVar(value="500")
        self.subject_contains = tk.StringVar(value="")
        self.range_option = tk.StringVar(value="Last 1 Month")
        self.custom_start_date = tk.StringVar(value="")
        self.custom_end_date = tk.StringVar(value="")

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
        self.techqa_milestone_sender = tk.StringVar(value="N/A")
        self.aaid_keys: list[str] = []
        self.stats_by_aaid: dict[str, DashboardStats] = {}
        self.daily_counts_by_aaid: dict[str, dict[str, DailyNotificationCounts]] = {}

        self._build()

    def _build(self):
        frame = tk.Frame(self.root, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Outlook Folder (use /):").grid(row=0, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.folder_path, width=50).grid(row=0, column=1, sticky="ew", pady=4)

        tk.Label(frame, text="Max Emails:").grid(row=1, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.max_emails, width=12).grid(row=1, column=1, sticky="w", pady=4)

        tk.Label(frame, text="Subject Contains (optional):").grid(row=2, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.subject_contains, width=50).grid(row=2, column=1, sticky="ew", pady=4)

        tk.Label(frame, text="Date Range:").grid(row=3, column=0, sticky="w")
        range_menu = tk.OptionMenu(frame, self.range_option, "Last 1 Month", "Last 2 Months", "Last 6 Months", "Custom Range")
        range_menu.grid(row=3, column=1, sticky="w", pady=4)

        tk.Label(frame, text="Custom Start (YYYY-MM-DD):").grid(row=4, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.custom_start_date, width=16).grid(row=4, column=1, sticky="w", pady=4)

        tk.Label(frame, text="Custom End (YYYY-MM-DD):").grid(row=4, column=1, sticky="e")
        tk.Entry(frame, textvariable=self.custom_end_date, width=16).grid(row=4, column=2, sticky="w", pady=4)

        button_frame = tk.Frame(frame)
        button_frame.grid(row=5, column=1, sticky="w", pady=8)
        tk.Button(button_frame, text="Refresh", command=self.refresh).grid(row=0, column=0, padx=(0, 8))
        tk.Button(button_frame, text="Export Excel", command=self.export_excel).grid(row=0, column=1)

        tk.Label(frame, text="Applications (AAID):").grid(row=6, column=0, sticky="w", pady=(8, 4))
        self.aaid_listbox = tk.Listbox(frame, exportselection=False, height=8)
        self.aaid_listbox.grid(row=7, column=0, rowspan=8, sticky="nsew", padx=(0, 12))
        self.aaid_listbox.bind("<<ListboxSelect>>", self.on_select_aaid)

        def add_metric_pair(
            row_idx: int,
            left_label: str,
            left_var: tk.StringVar,
            right_label: Optional[str] = None,
            right_var: Optional[tk.StringVar] = None,
            top_pad: int = 2,
            bottom_pad: int = 2,
        ) -> None:
            tk.Label(frame, text=left_label).grid(row=row_idx, column=1, sticky="w", pady=(top_pad, bottom_pad))
            tk.Label(frame, textvariable=left_var, anchor="w").grid(row=row_idx, column=2, sticky="ew", pady=(top_pad, bottom_pad))
            if right_label is not None and right_var is not None:
                tk.Label(frame, text=right_label).grid(
                    row=row_idx,
                    column=3,
                    sticky="w",
                    pady=(top_pad, bottom_pad),
                    padx=(18, 0),
                )
                tk.Label(frame, textvariable=right_var, anchor="w").grid(
                    row=row_idx,
                    column=4,
                    sticky="ew",
                    pady=(top_pad, bottom_pad),
                )

        add_metric_pair(6, "Selected AAID:", self.selected_aaid, "Tester Name:", self.tester_name, top_pad=8, bottom_pad=4)
        add_metric_pair(7, "Start Notifications Count:", self.start_count, "Stop Notifications Count:", self.stop_count)
        add_metric_pair(8, "TechQA Start:", self.techqa_start, "TechQA Stop:", self.techqa_stop)
        add_metric_pair(9, "Final QA Start:", self.finalqa_start, "Final QA Stop:", self.finalqa_stop)
        add_metric_pair(10, "First Start Notification:", self.first_start_notification_at, "Last Stop Notification:", self.last_stop_notification_at)
        add_metric_pair(11, "Completion Days Count:", self.completion_days_count, "TechQA Milestone At:", self.techqa_milestone_at)
        add_metric_pair(12, "TechQA Milestone Sender:", self.techqa_milestone_sender)

        tk.Label(frame, text="Daily Notification Check (expected 1 start and 1 stop):").grid(
            row=13, column=1, columnspan=4, sticky="w", pady=(10, 4)
        )
        self.daily_listbox = tk.Listbox(frame, exportselection=False, height=5)
        self.daily_listbox.grid(row=14, column=1, columnspan=4, sticky="nsew")

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)
        frame.grid_rowconfigure(14, weight=1)

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
        self.completion_days_count.set(
            "N/A" if stats.completion_days_count is None else str(stats.completion_days_count)
        )
        self.techqa_milestone_at.set(_format_dt(stats.techqa_milestone_at))
        self.techqa_milestone_sender.set(stats.techqa_milestone_sender or "N/A")

    def _reload_aaid_list(self) -> None:
        self.aaid_listbox.delete(0, tk.END)
        self.aaid_keys = sorted(self.stats_by_aaid.keys())
        for key in self.aaid_keys:
            item_stats = self.stats_by_aaid[key]
            display = (
                f"{key}  |  Start: {item_stats.start_notifications_count}"
                f"  Stop: {item_stats.stop_notifications_count}"
            )
            self.aaid_listbox.insert(tk.END, display)

    def on_select_aaid(self, _event=None):
        selected = self.aaid_listbox.curselection()
        if not selected:
            return

        index = selected[0]
        if index < 0 or index >= len(self.aaid_keys):
            return

        key = self.aaid_keys[index]
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
            row_text = (
                f"{date_key} | Start: {counts.start_count} | Stop: {counts.stop_count} | {status}"
            )
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
        except Exception as exc:  # noqa: BLE001 - show user-facing export failure details
            messagebox.showerror("Export Error", str(exc))

    def refresh(self):
        try:
            max_emails = int(self.max_emails.get().strip())
            if max_emails <= 0:
                raise ValueError("max emails must be positive")
        except ValueError:
            messagebox.showerror("Invalid value", "Max Emails must be a positive integer.")
            return

        try:
            start_date, end_date = get_date_range(
                self.range_option.get(),
                self.custom_start_date.get(),
                self.custom_end_date.get(),
            )
        except ValueError:
            messagebox.showerror(
                "Invalid date range",
                "Use Last 1/2/6 months or enter valid custom dates in YYYY-MM-DD format.",
            )
            return

        try:
            messages = read_messages_from_outlook(
                folder_path=self.folder_path.get().strip(),
                max_emails=max_emails,
                subject_contains=self.subject_contains.get(),
                start_date=start_date,
                end_date=end_date,
            )
            self.stats_by_aaid = parse_stats_by_aaid_from_messages(messages)
            self.daily_counts_by_aaid = parse_daily_notification_counts_by_aaid(messages)
        except Exception as exc:  # noqa: BLE001 - show user-facing error from Outlook integration
            messagebox.showerror("Outlook Read Error", str(exc))
            return

        self._reload_aaid_list()

        if not self.aaid_keys:
            self.selected_aaid.set("N/A")
            self._apply_stats_to_view(DashboardStats())
            self.daily_listbox.delete(0, tk.END)
            self.daily_listbox.insert(tk.END, "No AAID data found for selected range.")
            return

        self.aaid_listbox.selection_set(0)
        self.on_select_aaid()


def main():
    root = tk.Tk()
    app = DashboardUI(root)
    app.refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
