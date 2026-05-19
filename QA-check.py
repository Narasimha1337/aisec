import glob
import hashlib
import importlib.util
import logging
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox
from typing import Iterable, Optional


# Logging setup with rotation and retention
APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(APP_DIR, "logs")
LOG_BASENAME = "outlook_qa_dashboard_debug"
LOG_EXT = ".log"
SECURITY_LOG_BASENAME = "outlook_qa_dashboard_security"
DEV_LOG_BASENAME = "outlook_qa_dashboard_dev"
LOG_MAX_SIZE = 1 * 1024 * 1024  # 1 MB
LOG_RETENTION_DAYS = 7


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


SAFE_MODE = _env_flag("OUTLOOK_QA_SAFE_MODE", True)
DEV_MODE = _env_flag("OUTLOOK_QA_DEV_MODE", False)
FEEDBACK_TARGET_URL = os.environ.get(
    "OUTLOOK_QA_FEEDBACK_URL",
    "https://github.com/",
).strip()

UI_BG = "#eef3f8"
UI_PANEL = "#ffffff"
UI_PANEL_ALT = "#f7fafc"
UI_HEADER = "#16324f"
UI_ACCENT = "#5f8dd3"
UI_ACCENT_SOFT = "#dce8f7"
UI_TEXT = "#000000"
UI_MUTED = "#000000"
UI_BORDER = "#d9e2ec"
UI_SUCCESS = "#d8f1df"
UI_WARNING = "#f5e3c6"
UI_INFO = "#dfe8f3"
UI_VIOLET = "#eadcf6"
UI_ROSE = "#f3d9d9"
UI_FONT_FAMILY = "Segoe UI"


def _current_log_path() -> str:
    return os.path.join(LOG_DIR, f"{LOG_BASENAME}{LOG_EXT}")


def _current_security_log_path() -> str:
    return os.path.join(LOG_DIR, f"{SECURITY_LOG_BASENAME}{LOG_EXT}")

def _current_dev_log_path() -> str:
    return os.path.join(LOG_DIR, f"{DEV_LOG_BASENAME}{LOG_EXT}")


def _redact_subject(subject: str) -> str:
    digest = hashlib.sha256(subject.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"subject_sha256={digest} len={len(subject)}"


def _format_subject_for_logging(subject: str) -> str:
    """Return unredacted subject if in DEV_MODE, otherwise redacted."""
    if DEV_MODE:
        return f"subject={subject[:500]}"  # Limit to first 500 chars for dev logs
    return _redact_subject(subject)


def _append_debug_log_line(line: str) -> None:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = _current_log_path()
        rotate_log_if_needed(log_path)
        delete_old_logs()
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except OSError:
        pass


def _append_dev_log_line(line: str) -> None:
    """Append to dev log file with unredacted details."""
    if not DEV_MODE:
        return
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        dev_log_path = _current_dev_log_path()
        rotate_log_if_needed(dev_log_path)
        with open(dev_log_path, "a", encoding="utf-8") as dev_file:
            dev_file.write(line + "\n")
    except OSError:
        pass


def _user_error_message(default_message: str, exc: Optional[Exception] = None) -> str:
    if SAFE_MODE or exc is None:
        return default_message
    return f"{default_message}\n\n{exc}"


def _configure_root_theme(root: tk.Tk) -> None:
    root.configure(bg=UI_BG)
    root.option_add("*Font", f"{{{UI_FONT_FAMILY}}} 10")
    root.option_add("*Menu.Font", f"{{{UI_FONT_FAMILY}}} 10")
    root.option_add("*Menubutton.Font", f"{{{UI_FONT_FAMILY}}} 10")
    root.option_add("*Listbox.Font", f"{{{UI_FONT_FAMILY}}} 10")
    root.option_add("*Checkbutton.Font", f"{{{UI_FONT_FAMILY}}} 10")
    root.option_add("*Radiobutton.Font", f"{{{UI_FONT_FAMILY}}} 10")
    root.option_add("*Foreground", UI_TEXT)
    root.option_add("*Label.Foreground", UI_TEXT)
    root.option_add("*Checkbutton.Foreground", UI_TEXT)
    root.option_add("*Radiobutton.Foreground", UI_TEXT)
    root.option_add("*Menubutton.Foreground", UI_TEXT)
    root.option_add("*Entry.Foreground", UI_TEXT)
    root.option_add("*Text.Foreground", UI_TEXT)
    root.option_add("*Label.Background", UI_BG)
    root.option_add("*Frame.Background", UI_BG)
    root.option_add("*Button.Background", UI_PANEL)
    root.option_add("*Button.Foreground", UI_TEXT)
    root.option_add("*Button.Relief", "flat")
    root.option_add("*Button.BorderWidth", 1)
    root.option_add("*Entry.Relief", "flat")
    root.option_add("*Entry.BorderWidth", 1)
    root.option_add("*Text.Relief", "flat")
    root.option_add("*Text.BorderWidth", 1)

    for font_name in tkfont.names(root=root):
        try:
            tkfont.nametofont(font_name, root=root).configure(family=UI_FONT_FAMILY)
        except tk.TclError:
            pass


def _style_button(button: tk.Button, *, variant: str = "secondary") -> tk.Button:
    base_style = {
        "bg": UI_ACCENT_SOFT,
        "fg": UI_TEXT,
        "activebackground": "#c7daef",
        "activeforeground": UI_TEXT,
        "highlightbackground": "#bfd0e2",
    }
    styles = {
        "primary": base_style,
        "success": base_style,
        "soft": base_style,
        "danger": base_style,
        "ghost": base_style,
        "secondary": base_style,
    }
    config = styles.get(variant, styles["secondary"])
    button.configure(
        bg=config["bg"],
        fg=config["fg"],
        activebackground=config["activebackground"],
        activeforeground=config["activeforeground"],
        highlightbackground=config["highlightbackground"],
        relief="raised",
        bd=1,
        padx=6,
        pady=3,
        cursor="hand2",
        font=(UI_FONT_FAMILY, 9),
        takefocus=True,
    )
    return button


def _new_button(parent: tk.Widget, text: str, command, *, variant: str = "secondary", width: Optional[int] = None) -> tk.Button:
    kwargs = {"text": text, "command": command}
    if width is not None:
        kwargs["width"] = width
    button = tk.Button(parent, **kwargs)
    return _style_button(button, variant=variant)


def _style_entry(entry: tk.Entry) -> tk.Entry:
    entry.configure(
        bg="white",
        fg=UI_TEXT,
        insertbackground=UI_TEXT,
        relief="solid",
        bd=1,
        highlightthickness=1,
        highlightbackground=UI_BORDER,
        highlightcolor=UI_ACCENT,
    )
    return entry


def rotate_log_if_needed(log_path):
    """
    If the log file exceeds LOG_MAX_SIZE, rotate it by renaming with a timestamp.
    """
    if os.path.exists(log_path) and os.path.getsize(log_path) > LOG_MAX_SIZE:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rotated_name = f"{LOG_BASENAME}_{timestamp}{LOG_EXT}"
        rotated_path = os.path.join(LOG_DIR, rotated_name)
        os.rename(log_path, rotated_path)

def delete_old_logs():
    """
    Delete log files older than LOG_RETENTION_DAYS.
    """
    now = time.time()
    os.makedirs(LOG_DIR, exist_ok=True)
    pattern = os.path.join(LOG_DIR, f"{LOG_BASENAME}_*{LOG_EXT}")
    for log_file in glob.glob(pattern):
        try:
            mtime = os.path.getmtime(log_file)
            if (now - mtime) > LOG_RETENTION_DAYS * 86400:
                os.remove(log_file)
        except OSError:
            pass
    # Also check the main log file
    main_log = _current_log_path()
    if os.path.exists(main_log):
        mtime = os.path.getmtime(main_log)
        if (now - mtime) > LOG_RETENTION_DAYS * 86400:
            try:
                os.remove(main_log)
            except OSError:
                pass

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = _current_log_path()
    rotate_log_if_needed(log_path)
    delete_old_logs()
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )


def setup_security_logging():
    """Setup separate security logger for pentest/attack detection."""
    os.makedirs(LOG_DIR, exist_ok=True)
    sec_log_path = _current_security_log_path()
    rotate_log_if_needed(sec_log_path)
    
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.WARNING)
    
    # Remove existing handlers to avoid duplicates
    security_logger.handlers.clear()
    
    handler = logging.FileHandler(sec_log_path, encoding="utf-8")
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter("%(asctime)s [SECURITY] %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)
    return security_logger


def setup_dev_logging():
    """Setup dev mode logger for detailed unredacted debugging."""
    if not DEV_MODE:
        return None
    
    os.makedirs(LOG_DIR, exist_ok=True)
    dev_log_path = _current_dev_log_path()
    rotate_log_if_needed(dev_log_path)
    
    dev_logger = logging.getLogger("dev")
    dev_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    dev_logger.handlers.clear()
    
    handler = logging.FileHandler(dev_log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [DEV] %(message)s")
    handler.setFormatter(formatter)
    dev_logger.addHandler(handler)
    return dev_logger


setup_logging()
SECURITY_LOGGER = setup_security_logging()
DEV_LOGGER = setup_dev_logging()

# Log dev mode status at startup
if DEV_MODE:
    _append_dev_log_line(f"[{datetime.now().isoformat()}] DEV_MODE ENABLED - Unredacted logging active")
    logging.info("[DEV_MODE] Development mode enabled - detailed logging in logs/outlook_qa_dashboard_dev.log")


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
ALL_MAILBOXES_OPTION = "All Mailboxes"
RUNTIME_DEPENDENCIES: list[tuple[str, str]] = [
    ("pywin32", "win32com"),
    ("openpyxl", "openpyxl"),
]


# Security/Pentest Detection Patterns
SQL_INJECTION_PATTERNS = re.compile(
    r"(\b(SELECT|UNION|DROP|DELETE|INSERT|UPDATE|EXEC|EXECUTE|ALTER|CREATE)\b|'|--|;|\/\*|\*\/|xp_)",
    re.IGNORECASE
)
COMMAND_INJECTION_PATTERNS = re.compile(r"([|&;`$()\\]|>|<|&&|\|\|)")
PATH_TRAVERSAL_PATTERNS = re.compile(r"(\.\.\/|\.\.\\|\.\.%2[fF]|\.\.%5[cC])")
XSS_PATTERNS = re.compile(r"(<script|<img|<iframe|<object|<embed|javascript:|onerror=|onload=)", re.IGNORECASE)
SUSPICIOUS_LENGTH_THRESHOLD = 10000  # Emails with subjects > 10KB might be attack attempts


def _detect_pentest_attempt(text: str, field_name: str = "input") -> Optional[str]:
    """Detect common pentest/attack patterns. Returns threat description or None."""
    if not text or not isinstance(text, str):
        return None
    
    # Limit check: extremely long inputs might be buffer overflow attempts
    if len(text) > SUSPICIOUS_LENGTH_THRESHOLD:
        return f"Extremely long {field_name} ({len(text)} chars, threshold: {SUSPICIOUS_LENGTH_THRESHOLD})"
    
    # SQL Injection detection
    if SQL_INJECTION_PATTERNS.search(text):
        return f"SQL injection pattern detected in {field_name}"
    
    # Command Injection detection
    if COMMAND_INJECTION_PATTERNS.search(text):
        return f"Command injection pattern detected in {field_name}"
    
    # Path Traversal detection
    if PATH_TRAVERSAL_PATTERNS.search(text):
        return f"Path traversal pattern detected in {field_name}"
    
    # XSS detection
    if XSS_PATTERNS.search(text):
        return f"XSS/Script injection pattern detected in {field_name}"
    
    return None


def _log_security_event(threat: str, context: dict = None) -> None:
    """Log security event to separate security log file."""
    context_str = " | ".join(f"{k}={v}" for k, v in (context or {}).items())
    log_msg = f"{threat}" + (f" | {context_str}" if context_str else "")
    SECURITY_LOGGER.warning(log_msg)
    logging.info(f"[SECURITY] {log_msg}")  # Also log to main log


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
    is_test_run: bool = False  # True if minimal test: exactly 1 START + 1 STOP
    has_techqa_overlap: bool = False  # True if TechQA started during testing


@dataclass
class DailyNotificationCounts:
    start_count: int = 0
    stop_count: int = 0
    raw_start_count: int = 0
    raw_stop_count: int = 0
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None


class OutlookFolderNotFoundError(Exception):
    pass


class OutlookNotFoundError(Exception):
    pass


def _is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _ensure_runtime_dependencies() -> None:
    missing_packages = [
        package_name
        for package_name, module_name in RUNTIME_DEPENDENCIES
        if not _is_module_available(module_name)
    ]
    if not missing_packages:
        return

    package_list = ", ".join(missing_packages)
    raise RuntimeError(
        "Missing required Python packages: "
        f"{package_list}. Install them before running: "
        f"{sys.executable} -m pip install {' '.join(missing_packages)}"
    )


def _find_outlook_executable() -> Optional[str]:
    try:
        import winreg
    except ImportError:
        return None

    app_path_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE"),
    ]

    for root, key_path in app_path_keys:
        try:
            with winreg.OpenKey(root, key_path) as key:
                value, _ = winreg.QueryValueEx(key, None)
                if value and os.path.isfile(value):
                    return value
        except OSError:
            continue

    candidate_paths = [
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft Office", "root", "Office16", "OUTLOOK.EXE"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft Office", "root", "Office16", "OUTLOOK.EXE"),
    ]
    for path in candidate_paths:
        if path and os.path.isfile(path):
            return path

    return None


def _is_suspicious_executable_path(exe_path: str) -> bool:
    normalized = os.path.normcase(os.path.abspath(exe_path))
    basename = os.path.basename(normalized).lower()
    if basename != "outlook.exe":
        return True

    temp_roots = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    ]
    for root in temp_roots:
        if root:
            root_norm = os.path.normcase(os.path.abspath(root))
            if normalized.startswith(root_norm + os.sep):
                return True

    return False


def _get_powershell_executable() -> Optional[str]:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidates = [
        os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
        os.path.join(system_root, "Sysnative", "WindowsPowerShell", "v1.0", "powershell.exe"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def _is_trusted_outlook_executable(exe_path: str) -> bool:
    """
    Best-effort signature check for Outlook executable.
    Returns False only on explicit trust failures; returns True if verification
    cannot be performed to avoid over-restricting normal environments.
    """
    escaped_path = exe_path.replace("'", "''")
    ps_command = (
        f"$sig = Get-AuthenticodeSignature -FilePath '{escaped_path}'; "
        "Write-Output ($sig.Status.ToString()); "
        "if ($sig.SignerCertificate) { Write-Output ($sig.SignerCertificate.Subject) }"
    )

    powershell_exe = _get_powershell_executable()
    if not powershell_exe:
        return True

    try:
        result = subprocess.run(
            [
                powershell_exe,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps_command,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return True

    if result.returncode != 0:
        return True

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return True

    status = lines[0].upper()
    signer_subject = lines[1].upper() if len(lines) > 1 else ""

    explicit_fail_statuses = {
        "NOTSIGNED",
        "NOTTRUSTED",
        "HASHMISMATCH",
        "REVOKED",
        "EXPIRED",
        "UNKNOWNERROR",
    }
    if status in explicit_fail_statuses:
        return False

    if status == "VALID" and "MICROSOFT" not in signer_subject:
        return False

    return True


def _get_outlook_namespace():
    import win32com.client  # Local import so tests can run without Outlook dependency.
    import pythoncom

    pythoncom.CoInitialize()

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        return outlook.GetNamespace("MAPI")
    except Exception as initial_exc:
        last_exc = initial_exc

    # If Outlook is installed but not running, try launching it first.
    try:
        outlook_exe = _find_outlook_executable()
        if not outlook_exe:
            raise OSError("Outlook executable not found")
        if SAFE_MODE and _is_suspicious_executable_path(outlook_exe):
            raise OSError("Potentially unsafe Outlook executable path")
        if SAFE_MODE and not _is_trusted_outlook_executable(outlook_exe):
            raise OSError("Outlook executable failed trust validation")
        os.startfile(outlook_exe)
    except OSError as launch_exc:
        raise OutlookNotFoundError("Outlook not found.") from launch_exc

    # Give Outlook a few seconds to initialize COM and MAPI.
    for _ in range(8):
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            return outlook.GetNamespace("MAPI")
        except Exception as retry_exc:
            last_exc = retry_exc
            time.sleep(1)

    raise OutlookNotFoundError("Outlook not found.") from last_exc


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


def _same_person(left: Optional[str], right: Optional[str]) -> bool:
    if left is None or right is None:
        return False
    return _sender_dedupe_key(left) == _sender_dedupe_key(right)


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

    # Count business days only (Mon-Fri) to avoid inflating completion duration
    # with weekends when comparing QA start/stop timelines.
    count = 0
    current = start_day
    while current <= end_day:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


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

    # DEV_MODE: Log full unredacted details for tracing
    if DEV_MODE:
        _append_dev_log_line(
            f"[APPLY_STATS] Subject={subject_text[:500]} | Sender={sender_name} | "
            f"is_start={is_start} is_stop={is_stop} is_bracket_start={is_bracket_start} "
            f"is_bracket_stop={is_bracket_stop} is_notification={is_notification_type} is_pentest={is_pentest}"
        )

    # DEBUG: Log parser signal details and keep subjects redacted by default.
    if hasattr(stats, '_log_debug'):
        stats._log_debug(
            f"Processing subject: {_format_subject_for_logging(subject_text)} | "
            f"is_pentest={is_pentest} "
            f"is_bracket_start={is_bracket_start} "
            f"is_bracket_stop={is_bracket_stop} "
            f"is_start={is_start} is_stop={is_stop} "
            f"is_notification_type={is_notification_type}"
        )

    # Only count if [PENTEST] is present in subject
    if is_pentest and (is_bracket_start or (is_notification_type and is_start)):
        stats.raw_start_notifications_count += 1
        stats.start_notifications_count += 1
        previous_first_start = stats.first_start_notification_at
        stats.first_start_notification_at = _earliest(stats.first_start_notification_at, event_time)
    if is_pentest and (is_bracket_stop or (is_notification_type and is_stop)):
        stats.raw_stop_notifications_count += 1
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


def parse_stats_by_aaid_from_messages(
    messages: Iterable[tuple[str, object]],
    filter_aaid: Optional[set[str]] = None,
    debug_enabled: bool = False,
) -> dict[str, DashboardStats]:
    message_list = list(messages)
    stats_by_aaid: dict[str, DashboardStats] = {}
    
    # Track all start notifications by AAID to capture sender of earliest one
    start_notifications_by_aaid: dict[str, list[tuple[Optional[datetime], Optional[str]]]] = {}
    unique_start_sender_day_by_aaid: dict[str, set[tuple[str, str]]] = {}
    unique_stop_sender_day_by_aaid: dict[str, set[tuple[str, str]]] = {}

    # First pass: collect stats and track start notifications
    for msg in message_list:
        subject, received_time, sender_name, _body_text = _unpack_message(msg)
        if not subject:
            continue

        # Security: Check for pentest/attack patterns
        subject_threat = _detect_pentest_attempt(subject, "email_subject")
        if subject_threat:
            _log_security_event(subject_threat, {"aaid": extract_aaid(subject), "sender": sender_name})
        
        sender_threat = _detect_pentest_attempt(sender_name or "", "sender_name")
        if sender_threat:
            _log_security_event(sender_threat, {"sender": sender_name})

        event_time = _to_datetime(received_time)
        aaid = extract_aaid(subject)
        # DEBUG: Keep logs non-sensitive while still signaling parse activity.
        if debug_enabled:
            _append_debug_log_line(
                f"[{datetime.now().isoformat()}] [PARSE] { _format_subject_for_logging(subject) }"
            )
            # DEV_MODE: Log full details with sender and timestamp
            if DEV_MODE:
                _append_dev_log_line(
                    f"[{datetime.now().isoformat()}] [PARSE] AAID={aaid} | "
                    f"Sender={sender_name} | Subject={subject[:500]}"
                )
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
        lowered = subject.lower()
        if "automatic reply" in lowered or "autoreply" in lowered or "auto-reply" in lowered:
            continue

        is_start = _is_start(subject)
        is_stop = _is_stop(subject)
        is_bracket_start = "[START]" in subject.upper()
        is_bracket_stop = "[STOP]" in subject.upper()
        is_notification_type = _is_notification(subject)
        is_pentest = "[PENTEST]" in subject.upper()

        if event_time is not None and is_pentest:
            date_key = event_time.strftime("%Y-%m-%d")
            sender_key = _sender_dedupe_key(sender_name)
            if is_bracket_start or (is_notification_type and is_start):
                start_unique = unique_start_sender_day_by_aaid.setdefault(aaid, set())
                start_unique.add((date_key, sender_key))
            if is_bracket_stop or (is_notification_type and is_stop):
                stop_unique = unique_stop_sender_day_by_aaid.setdefault(aaid, set())
                stop_unique.add((date_key, sender_key))

        if is_bracket_start or (is_notification_type and is_start):
            if aaid not in start_notifications_by_aaid:
                start_notifications_by_aaid[aaid] = []
            start_notifications_by_aaid[aaid].append((event_time, sender_name))

    for aaid, stats in stats_by_aaid.items():
        stats.start_notifications_count = len(unique_start_sender_day_by_aaid.get(aaid, set()))
        stats.stop_notifications_count = len(unique_stop_sender_day_by_aaid.get(aaid, set()))
    
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
            and _same_person(sender_name, tester_name)
        ):
            stats.techqa_milestone_at = event_time

        if (
            _is_techqa(subject)
            and stats.techqa_person is None
            and sender_name is not None
            and not _same_person(sender_name, tester_name)
            and not _same_person(sender_name, stats.finalqa_person)
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
            and _same_person(sender_name, stats.techqa_person)
        ):
            stats.techqa_stop = event_time

        if (
            _is_finalqa(subject)
            and stats.finalqa_person is None
            and sender_name is not None
            and not _same_person(sender_name, tester_name)
            and not _same_person(sender_name, stats.techqa_person)
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
        
        # Flag if TechQA started during or before testing was completed
        if stats.techqa_milestone_at and stats.last_stop_notification_at:
            if stats.techqa_milestone_at <= stats.last_stop_notification_at:
                stats.has_techqa_overlap = True

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
            # Track the first start time
            if day_counts.start_time is None:
                day_counts.start_time = event_time
            start_seen = seen_daily_start_senders.setdefault(sender_bucket_key, set())
            if sender_key not in start_seen:
                start_seen.add(sender_key)
                day_counts.start_count += 1
        if is_bracket_stop or (is_notification_type and is_stop):
            day_counts.raw_stop_count += 1
            # Track the last stop time
            if day_counts.stop_time is None or event_time > day_counts.stop_time:
                day_counts.stop_time = event_time
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
        # Only count AAIDs that have at least one START or STOP notification (exclude QA-only)
        has_any_start_or_stop = stats.start_notifications_count > 0 or stats.stop_notifications_count > 0
        if has_any_start_or_stop:
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
    # Security: Check for path traversal attempts
    traversal_threat = _detect_pentest_attempt(folder_path, "folder_path")
    if traversal_threat:
        _log_security_event(traversal_threat, {"folder_path": folder_path})
    
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


def _read_messages_from_folder(
    namespace,
    folder_path: str,
    max_emails: int,
    subject_contains: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    debug_enabled: bool = False,
) -> list[tuple[str, object, Optional[str], str]]:
    folder = get_outlook_folder(namespace, folder_path)

    items = folder.Items
    items.Sort("[ReceivedTime]", True)

    results: list[tuple[str, object, Optional[str], str]] = []
    # Parse comma-separated keywords for subject filter (supports: "AA123, BB456, CC789")
    keywords = [kw.strip().lower() for kw in subject_contains.strip().split(",") if kw.strip()]
    normalized_start = _normalize_for_comparison(start_date)
    normalized_end = _normalize_for_comparison(end_date)
    count = 0


    if debug_enabled:
        _append_debug_log_line(
            f"[{datetime.now().isoformat()}] [FILTER] "
            f"keywords_count={len(keywords)} date_range={normalized_start}->{normalized_end}"
        )

    # Strict subject match: read [PENTEST] thread emails plus any TechQA / Final QA
    # related messages (these keywords drive the dashboard's QA milestones).
    # If custom keywords are provided, also require matching those keywords (AND logic).
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

        # Must match strict keywords ([PENTEST], Tech QA, Final QA)
        if not pentest_event_re.search(subject):
            continue

        # If custom keywords provided, also require matching (AND condition)
        if keywords and not any(kw in subject.lower() for kw in keywords):
            skipped_by_filter_count += 1
            continue

        matched_subject_count += 1

        received_time = _to_datetime(getattr(item, "ReceivedTime", None))
        normalized_received = _normalize_for_comparison(received_time)

        if normalized_end and normalized_received and normalized_received > normalized_end:
            skipped_by_date_count += 1
            continue
        if normalized_start and normalized_received and normalized_received < normalized_start:
            # Items are sorted by newest first, so we can stop once we pass lower bound.
            skipped_by_date_count += 1
            break

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

    if debug_enabled:
        _append_debug_log_line(
            f"[{datetime.now().isoformat()}] [SUMMARY] "
            f"matched={matched_subject_count} skipped_date={skipped_by_date_count} "
            f"skipped_filter={skipped_by_filter_count} kept={len(results)}"
        )

    return results


def read_messages_from_outlook(
    folder_path: str,
    max_emails: int,
    subject_contains: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    debug_enabled: bool = False,
) -> list[tuple[str, object, Optional[str], str]]:
    namespace = _get_outlook_namespace()
    return _read_messages_from_folder(
        namespace=namespace,
        folder_path=folder_path,
        max_emails=max_emails,
        subject_contains=subject_contains,
        start_date=start_date,
        end_date=end_date,
        debug_enabled=debug_enabled,
    )


def read_messages_from_all_mailboxes(
    mailbox_names: list[str],
    folder_path: str,
    max_emails: int,
    subject_contains: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    debug_enabled: bool = False,
) -> list[tuple[str, object, Optional[str], str]]:
    namespace = _get_outlook_namespace()
    aggregated: list[tuple[str, object, Optional[str], str]] = []
    relative_folder = (folder_path or "Inbox").strip("/")
    if not relative_folder:
        relative_folder = "Inbox"

    for mailbox in mailbox_names:
        if mailbox in {ALL_MAILBOXES_OPTION, "Default Mailbox"}:
            continue
        if mailbox.lower().startswith("online archive"):
            continue

        mailbox_relative = relative_folder
        prefix = f"{mailbox}/"
        if mailbox_relative.lower().startswith(prefix.lower()):
            mailbox_relative = mailbox_relative[len(prefix):].strip("/")
            if not mailbox_relative:
                mailbox_relative = "Inbox"

        full_folder_path = f"{mailbox}/{mailbox_relative}"
        remaining = max(max_emails - len(aggregated), 0)
        if remaining <= 0:
            break
        try:
            aggregated.extend(
                _read_messages_from_folder(
                    namespace=namespace,
                    folder_path=full_folder_path,
                    max_emails=remaining,
                    subject_contains=subject_contains,
                    start_date=start_date,
                    end_date=end_date,
                    debug_enabled=debug_enabled,
                )
            )
        except OutlookFolderNotFoundError:
            # If a mailbox doesn't have the requested folder path, continue others.
            continue

    return aggregated


class DashboardUI:
    def _set_sort_mode(self, mode):
        self.aaid_sort_mode = mode
        self._refresh_sort_button_labels()
        self._reload_aaid_list(reset_page=True)

    def _toggle_sort_mode(self, metric: str) -> None:
        if metric == "start":
            next_mode = "start_desc" if self.aaid_sort_mode == "start_asc" else "start_asc"
        elif metric == "stop":
            next_mode = "stop_desc" if self.aaid_sort_mode == "stop_asc" else "stop_asc"
        else:
            return
        self._set_sort_mode(next_mode)

    def _refresh_sort_button_labels(self) -> None:
        if hasattr(self, "start_sort_btn"):
            if self.aaid_sort_mode == "start_asc":
                self.start_sort_btn.configure(text="Start ↑")
            elif self.aaid_sort_mode == "start_desc":
                self.start_sort_btn.configure(text="Start ↓")
            else:
                self.start_sort_btn.configure(text="Start ↕")

        if hasattr(self, "stop_sort_btn"):
            if self.aaid_sort_mode == "stop_asc":
                self.stop_sort_btn.configure(text="Stop ↑")
            elif self.aaid_sort_mode == "stop_desc":
                self.stop_sort_btn.configure(text="Stop ↓")
            else:
                self.stop_sort_btn.configure(text="Stop ↕")

    def _is_qa_only_aaid(self, stats: DashboardStats) -> bool:
        has_notifications = stats.start_notifications_count > 0 or stats.stop_notifications_count > 0
        has_qa_signals = any(
            value is not None
            for value in (
                stats.techqa_start,
                stats.techqa_stop,
                stats.finalqa_start,
                stats.finalqa_stop,
                stats.techqa_milestone_at,
                stats.techqa_person,
                stats.finalqa_person,
            )
        )
        return (not has_notifications) and has_qa_signals

    def _datetime_sort_value(self, value: Optional[datetime]) -> Optional[int]:
        if value is None:
            return None
        return (
            value.toordinal() * 86400
            + value.hour * 3600
            + value.minute * 60
            + value.second
        )

    def _qa_start_proxy(self, stats: DashboardStats) -> Optional[datetime]:
        candidates = [
            stats.techqa_start,
            stats.techqa_milestone_at,
            stats.finalqa_start,
        ]
        available = [dt for dt in candidates if dt is not None]
        if not available:
            return None
        return min(available)

    def _qa_stop_proxy(self, stats: DashboardStats) -> Optional[datetime]:
        candidates = [
            stats.techqa_stop,
            stats.finalqa_stop,
            stats.finalqa_start,
        ]
        available = [dt for dt in candidates if dt is not None]
        if not available:
            return None
        return max(available)

    def _matches_notification_filter(self, stats: DashboardStats) -> bool:
        mode = self.notification_filter_mode.get()
        missing_start = stats.start_notifications_count == 0
        missing_stop = stats.stop_notifications_count == 0
        has_any_start_or_stop = stats.start_notifications_count > 0 or stats.stop_notifications_count > 0

        # Exclude QA-only AAIDs (no START or STOP) from START/STOP filters
        if mode in ["Missing Start", "Missing Stop", "Missing Start and Stop"]:
            if not has_any_start_or_stop:
                return False

        if mode == "Missing Start":
            return missing_start
        if mode == "Missing Stop":
            return missing_stop
        if mode == "Missing Start and Stop":
            return missing_start and missing_stop
        if mode == "Complete (Start + Stop)":
            return (not missing_start) and (not missing_stop)
        return True

    def __init__(self, root: tk.Tk):
        self.root = root
        _configure_root_theme(self.root)
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
        self.range_option = tk.StringVar(value="Last 3 Months")
        self.custom_start_date = tk.StringVar(value="")
        self.custom_end_date = tk.StringVar(value="")
        self.aaid_filter = tk.StringVar(value="")
        self.notification_filter_mode = tk.StringVar(value="All Apps")
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
        self.is_test_run = tk.StringVar(value="N/A")
        self.has_techqa_overlap = tk.StringVar(value="N/A")
        self.aaid_keys: list[str] = []
        self.current_page_keys: list[str] = []
        self.stats_by_aaid: dict[str, DashboardStats] = {}
        self.daily_counts_by_aaid: dict[str, dict[str, DailyNotificationCounts]] = {}
        self._aaid_search_after_id: Optional[str] = None
        self.aaid_page_size = 50
        self.aaid_current_page = 0
        self.aaid_total_pages = 0
        self.aaid_page_info = tk.StringVar(value="Total: 0 | Page: 0/0")
        self.aaid_sort_mode = "start_desc"
        self._mailbox_init_in_progress = False

        self.status_var = tk.StringVar(value="Ready.")
        status_row = tk.Frame(self.root, bg=UI_BG)
        status_row.pack(fill="x", padx=12, pady=(0, 4))
        self.status_label = tk.Label(
            status_row,
            textvariable=self.status_var,
            anchor="w",
            fg=UI_TEXT,
            bg=UI_BG,
            font=(UI_FONT_FAMILY, 10),
        )
        self.status_label.pack(side="left", fill="x", expand=True)


        def _add_status_link(text: str, command, *, pad_right: int = 0) -> None:
            link = tk.Label(
                status_row,
                text=text,
                bg=UI_BG,
                fg=UI_MUTED,
                cursor="hand2",
                font=(UI_FONT_FAMILY, 10, "underline"),
                padx=4,
                pady=1,
            )
            link.pack(side="right", padx=(0, pad_right))
            link.bind("<Button-1>", lambda _event: command())
            link.bind("<Enter>", lambda _event, lbl=link: lbl.configure(fg=UI_TEXT))
            link.bind("<Leave>", lambda _event, lbl=link: lbl.configure(fg=UI_MUTED))

        _add_status_link("Help", self._open_help_dialog)
        _add_status_link("Feedback", self._open_feedback_link, pad_right=8)

        # Add Enable Debug Logs checkbox before the links (to the right side)
        debug_chk = tk.Checkbutton(
            status_row,
            text="Enable Debug Logs",
            variable=self.debug_enabled,
            bg=UI_BG,
            font=(UI_FONT_FAMILY, 10),
            padx=4,
            pady=1,
            highlightthickness=0,
            activebackground=UI_BG,
            selectcolor=UI_BG,
            bd=0,
        )
        debug_chk.pack(side="right", padx=(0, 8))

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

        self._build()
        self.root.after(50, self._init_mailboxes_async)
        self._auto_adjust_max_emails()
        self._update_stat_date_range_preview()

    def _log_debug(self, message: str) -> None:
        if not self.debug_enabled.get():
            return
        _append_debug_log_line(
            f"[{datetime.now().isoformat()}] {_safe_log_text(message, max_len=2000)}"
        )

    def _open_feedback_link(self) -> None:
        if not FEEDBACK_TARGET_URL:
            self.status_var.set("Feedback URL is not configured.")
            messagebox.showinfo(
                "No feedback URL",
                "Set OUTLOOK_QA_FEEDBACK_URL to open feedback directly.",
            )
            return

        if webbrowser.open(FEEDBACK_TARGET_URL):
            self.status_var.set("Opened feedback URL.")
        else:
            self.status_var.set("Unable to open feedback URL.")

    def _open_help_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Help / Kick Start Guide")
        dialog.grab_set()
        dialog.geometry("980x720")
        dialog.minsize(900, 640)
        dialog.resizable(True, True)

        background = "#f4f7fb"
        header_bg = "#17324d"
        accent_bg = "#dfe9f5"
        card_bg = "#ffffff"
        header_text = "#f6fbff"
        body_text = "#2a3a4d"

        dialog.configure(bg=background)

        container = tk.Frame(dialog, bg=background, padx=12, pady=12)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(2, weight=1)
        container.grid_columnconfigure(0, weight=1)

        header = tk.Frame(container, bg=header_bg, padx=18, pady=14)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="Outlook QA Dashboard",
            bg=header_bg,
            fg=header_text,
            font=(UI_FONT_FAMILY, 10),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="Kick Start Guide",
            bg=header_bg,
            fg=header_text,
            font=(UI_FONT_FAMILY, 10),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        banner = tk.Frame(container, bg=accent_bg, padx=14, pady=8)
        banner.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        banner.grid_columnconfigure(0, weight=1)
        tk.Label(
            banner,
            text="Use this page to learn the workflow quickly: pick a mailbox, refresh data, review the AAID list, then export or report issues.",
            bg=accent_bg,
            fg=UI_TEXT,
            justify="left",
            wraplength=900,
            font=(UI_FONT_FAMILY, 10),
        ).grid(row=0, column=0, sticky="w")

        body = tk.Frame(container, bg=background)
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        scroll_container = tk.Frame(body, bg=background)
        scroll_container.grid(row=0, column=0, sticky="nsew")
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_container, bg=background, highlightthickness=0)
        v_scroll = tk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")

        content = tk.Frame(canvas, bg=background)
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def _sync_scroll_region(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_content_width(event) -> None:
            canvas.itemconfigure(content_window, width=event.width)

        content.bind("<Configure>", _sync_scroll_region)
        canvas.bind("<Configure>", _sync_content_width)

        guide_col = tk.Frame(content, bg=background)
        guide_col.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        guide_col.grid_columnconfigure(0, weight=1)
        guide_col.grid_columnconfigure(1, weight=1)

        def _on_mousewheel(event) -> None:
            delta = -1 * int(event.delta / 120)
            canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _cleanup_and_close() -> None:
            canvas.unbind_all("<MouseWheel>")
            dialog.destroy()

        def add_card(parent: tk.Widget, title: str, lines: list[str], accent: str) -> None:
            card = tk.Frame(parent, bg=card_bg, bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e2ec")
            card.grid_propagate(True)
            title_bar = tk.Frame(card, bg=accent, padx=12, pady=8)
            title_bar.pack(fill="x")
            tk.Label(
                title_bar,
                text=title,
                bg=accent,
                fg=UI_TEXT,
                font=(UI_FONT_FAMILY, 10),
            ).pack(anchor="w")

            content = tk.Frame(card, bg=card_bg, padx=12, pady=10)
            content.pack(fill="both", expand=True)
            for line in lines:
                tk.Label(
                    content,
                    text=line,
                    bg=card_bg,
                    fg=body_text,
                    anchor="w",
                    justify="left",
                    wraplength=420,
                    font=(UI_FONT_FAMILY, 10),
                ).pack(anchor="w", fill="x", pady=2)

            return card

        help_sections = [
            (
                "1. Start here",
                [
                    "- Make sure Outlook desktop is open and signed in.",
                    "- Choose the correct mailbox and folder path.",
                    "- Click Refresh after selecting the date range.",
                ],
                "#c7d8ff",
            ),
            (
                "2. Main inputs",
                [
                    "- Mailbox picks the Outlook root mailbox.",
                    "- Outlook Folder uses / separators, for example Inbox or Mailbox/Inbox/Project.",
                    "- Max Emails caps how many messages are scanned.",
                    "- Subject Contains narrows the message set.",
                    "- Date Range supports presets or Custom Range.",
                ],
                "#d8f1df",
            ),
            (
                "3. What Refresh does",
                [
                    "- Reads Outlook messages from the selected folder.",
                    "- Groups messages by AAID and calculates Start and Stop counts.",
                    "- Detects TechQA and Final QA timeline events.",
                    "- Updates the list, details panel, daily check, and statistics.",
                ],
                "#f5e3c6",
            ),
            (
                "4. How to read the results",
                [
                    "- Select an AAID to see counts, timestamps, and QA milestones.",
                    "- Daily Notification Check shows whether each day has exactly 1 Start and 1 Stop.",
                    "- Rows marked ALERT need attention because the counts are not balanced.",
                ],
                "#dfe8f3",
            ),
            (
                "5. Useful filters",
                [
                    "- Show filters Missing Start, Missing Stop, or complete records.",
                    "- Sort by changes the AAID order by Start or Stop counts.",
                    "- Application [AAID] lets you type one or more AAIDs separated by commas.",
                ],
                "#eadcf6",
            ),
            (
                "6. Export and support",
                [
                    "- Export to Excel saves the current results to .xlsx.",
                    f"- Feedback opens {FEEDBACK_TARGET_URL or 'the issue tracker'}.",
                    "- Use it for bugs, feature requests, or tester notes.",
                ],
                "#f3d9d9",
            ),
            (
                "7. Tips",
                [
                    "- If no results appear, verify the folder path and date range.",
                    "- If Outlook is not found, confirm the desktop client is installed and signed in.",
                    "- Use Debug Logs only when you need trace output.",
                ],
                "#d7ece7",
            ),
        ]

        for idx, (title, lines, accent) in enumerate(help_sections):
            row_idx = idx // 2
            col_idx = idx % 2
            card = add_card(guide_col, title, lines, accent)
            if idx == len(help_sections) - 1 and len(help_sections) % 2 == 1:
                card.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=2, pady=(0, 10))
            else:
                card.grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=(0, 10))

        # Bottom spacer keeps last card clear from the viewport edge.
        guide_col.grid_rowconfigure((len(help_sections) + 1) // 2, minsize=10)

        scroll_container.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

        dialog.protocol("WM_DELETE_WINDOW", _cleanup_and_close)

    def _init_mailboxes_async(self) -> None:
        if self._mailbox_init_in_progress:
            return
        self._mailbox_init_in_progress = True
        self.status_var.set("Initializing Outlook mailboxes...")
        thread = threading.Thread(target=self._init_mailboxes_worker, daemon=True)
        thread.start()

    def _init_mailboxes_worker(self) -> None:
        try:
            namespace = _get_outlook_namespace()
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

            def update_success_ui() -> None:
                if mailbox_names:
                    self.mailbox_names = [ALL_MAILBOXES_OPTION] + mailbox_names
                else:
                    self.mailbox_names = ["Default Mailbox"]
                self.selected_mailbox.set(self.mailbox_names[0])
                self._refresh_mailbox_dropdown()
                self._mailbox_init_in_progress = False
                self.status_var.set("Ready.")

            self.root.after(0, update_success_ui)
        except OutlookNotFoundError:
            def update_not_found_ui() -> None:
                self.mailbox_names = ["Default Mailbox"]
                self.selected_mailbox.set("Default Mailbox")
                self._refresh_mailbox_dropdown()
                self._mailbox_init_in_progress = False
                self.status_var.set("")
                messagebox.showerror("Outlook Not Found", "Outlook not found.")

            self.root.after(0, update_not_found_ui)
        except Exception:
            def update_fallback_ui() -> None:
                self.mailbox_names = ["Default Mailbox"]
                self.selected_mailbox.set("Default Mailbox")
                self._refresh_mailbox_dropdown()
                self._mailbox_init_in_progress = False
                self.status_var.set("Ready.")

            self.root.after(0, update_fallback_ui)

    def _toggle_custom_dates(self):
        if self.range_option.get() == "Custom Range":
            self.custom_dates_label.grid()
            self.custom_dates_row.grid()
        else:
            self.custom_dates_label.grid_remove()
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
        shell = tk.Frame(self.root, bg=UI_BG, padx=8, pady=4)
        shell.pack(fill="both", expand=True)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        frame = tk.Frame(shell, bg=UI_BG)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_rowconfigure(7, weight=1)

        def make_card(parent: tk.Widget, title: str, *, row: int, column: int, rowspan: int = 1, columnspan: int = 1, padx=(0, 0), pady=(0, 0), min_header: bool = False) -> tuple[tk.Frame, tk.Frame]:
            outer = tk.Frame(parent, bg=UI_PANEL, bd=1, relief="solid", highlightthickness=1, highlightbackground=UI_BORDER)
            outer.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky="nsew", padx=padx, pady=pady)
            outer.grid_columnconfigure(0, weight=1)
            header_height = 6 if min_header else 7
            header = tk.Frame(outer, bg=UI_ACCENT_SOFT, padx=8, pady=header_height)
            header.grid(row=0, column=0, sticky="ew")
            tk.Label(header, text=title, bg=UI_ACCENT_SOFT, fg=UI_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            body = tk.Frame(outer, bg=UI_PANEL, padx=6, pady=4)
            body.grid(row=1, column=0, sticky="nsew")
            return outer, body

        # Statistics panel styled as a card, matching AAID Details
        stats_outer = tk.Frame(frame, bg=UI_PANEL, bd=1, relief="solid", highlightthickness=1, highlightbackground=UI_BORDER)
        stats_outer.grid(row=0, column=4, rowspan=7, sticky="nsew", padx=(16, 0), pady=(1, 4))
        stats_outer.grid_columnconfigure(0, weight=1)
        stats_header = tk.Frame(stats_outer, bg=UI_ACCENT_SOFT, padx=8, pady=7)
        stats_header.grid(row=0, column=0, sticky="ew")
        tk.Label(stats_header, text="Statistics", bg=UI_ACCENT_SOFT, fg=UI_TEXT, font=(UI_FONT_FAMILY, 10, "bold")).pack(anchor="w")
        stats_body = tk.Frame(stats_outer, bg=UI_PANEL, padx=6, pady=4)
        stats_body.grid(row=1, column=0, sticky="nsew")
        self._build_statistics_panel(stats_body)

        # Sorting controls for AAID results
        import tkinter.ttk as ttk

        # Custom style for Combobox to match button style
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Custom.TCombobox",
            fieldbackground=UI_ACCENT_SOFT,
            background=UI_ACCENT_SOFT,
            foreground=UI_TEXT,
            bordercolor=UI_BORDER,
            borderwidth=1,
            relief="raised",
            padding=2,
            font=(UI_FONT_FAMILY, 9),
            arrowcolor=UI_TEXT,
        )
        style.map(
            "Custom.TCombobox",
            fieldbackground=[('readonly', UI_ACCENT_SOFT)],
            background=[('readonly', UI_ACCENT_SOFT)],
            foreground=[('readonly', UI_TEXT)],
        )

        control_col_width = 240

        tk.Label(frame, text="Mailbox:").grid(row=0, column=0, sticky="w", pady=(1, 1))
        mailbox_row = tk.Frame(frame, bg=UI_BG)
        mailbox_row.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(1, 1))
        mailbox_row.grid_propagate(False)
        mailbox_row.configure(width=control_col_width)
        mailbox_options = self.mailbox_names if self.mailbox_names else ["Default Mailbox"]
        self.mailbox_menu_cb = ttk.Combobox(
            mailbox_row,
            textvariable=self.selected_mailbox,
            values=mailbox_options,
            state="readonly",
            style="Custom.TCombobox",
            width=25,
        )
        self.mailbox_menu_cb.pack(side="left", fill="x", expand=True)
        # Debug logs checkbox removed from mailbox row (now only in status row)

    # _reload_mailboxes removed; mailboxes now load automatically at startup

        tk.Label(frame, text="Outlook Folder (use /):").grid(row=1, column=0, sticky="w")
        folder_entry = tk.Entry(frame, textvariable=self.folder_path, width=25)
        _style_entry(folder_entry)
        folder_entry.grid(row=1, column=1, sticky="ew", pady=2)

        tk.Label(frame, text="Max Emails:").grid(row=2, column=0, sticky="w")
        max_entry = tk.Entry(frame, textvariable=self.max_emails, width=25)
        _style_entry(max_entry)
        max_entry.grid(row=2, column=1, sticky="ew", pady=2)

        tk.Label(frame, text="Subject Contains (optional):").grid(row=3, column=0, sticky="w")
        subject_frame = tk.Frame(frame, bg=UI_BG)
        subject_frame.grid(row=3, column=1, sticky="ew", pady=2)
        subject_entry = tk.Entry(subject_frame, textvariable=self.subject_contains, width=25)
        _style_entry(subject_entry)
        subject_entry.pack(side="left", fill="x", expand=True)

        tk.Label(frame, text="Date Range:").grid(row=4, column=0, sticky="w")
        self.range_menu_cb = ttk.Combobox(
            frame,
            textvariable=self.range_option,
            values=[
                "Last 1 Week",
                "Last 1 Month",
                "Last 3 Months",
                "Last 6 Months",
                "Custom Range",
            ],
            state="readonly",
            style="Custom.TCombobox",
            width=25,
        )
        self.range_menu_cb.grid(row=4, column=1, sticky="ew", pady=2)
        self.range_menu_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_range_option_changed())

        self.custom_dates_label = tk.Label(frame, text="Custom Date (YYYY-MM-DD):")
        self.custom_dates_label.grid(row=5, column=0, sticky="w", pady=2)

        self.custom_dates_row = tk.Frame(frame, bg=UI_BG, width=control_col_width)
        self.custom_dates_row.grid(row=5, column=1, columnspan=2, sticky="ew", pady=2)
        self.custom_dates_row.grid_propagate(False)

        # Try to use tkcalendar.DateEntry for date picking, fallback to Entry if unavailable
        try:
            from tkcalendar import DateEntry
            self.custom_start_entry = DateEntry(
                self.custom_dates_row,
                textvariable=self.custom_start_date,
                width=12,
                date_pattern="yyyy-mm-dd",
                background=UI_PANEL,
                foreground=UI_TEXT,
                borderwidth=1,
                font=(UI_FONT_FAMILY, 9),
            )
            self.custom_start_entry.pack(side="left", padx=(0, 10))
            self.custom_end_entry = DateEntry(
                self.custom_dates_row,
                textvariable=self.custom_end_date,
                width=12,
                date_pattern="yyyy-mm-dd",
                background=UI_PANEL,
                foreground=UI_TEXT,
                borderwidth=1,
                font=(UI_FONT_FAMILY, 9),
            )
            self.custom_end_entry.pack(side="left", padx=(4, 0))
            # Bind date selection event
            self.custom_start_entry.bind("<<DateEntrySelected>>", self._on_custom_date_changed)
            self.custom_end_entry.bind("<<DateEntrySelected>>", self._on_custom_date_changed)
        except ImportError:
            self.custom_start_entry = tk.Entry(self.custom_dates_row, textvariable=self.custom_start_date, width=14)
            _style_entry(self.custom_start_entry)
            self.custom_start_entry.pack(side="left", padx=(0, 10))
            self.custom_end_entry = tk.Entry(self.custom_dates_row, textvariable=self.custom_end_date, width=14)
            _style_entry(self.custom_end_entry)
            self.custom_end_entry.pack(side="left", padx=(4, 0))
            self.custom_start_entry.bind("<KeyRelease>", self._on_custom_date_changed)
            self.custom_end_entry.bind("<KeyRelease>", self._on_custom_date_changed)

        self.custom_dates_label.grid_remove()
        self.custom_dates_row.grid_remove()

        button_frame = tk.Frame(frame, bg=UI_BG)
        button_frame.grid(row=6, column=1, sticky="w", pady=4)
        _new_button(button_frame, "Refresh", self.refresh, variant="primary").grid(row=0, column=0, padx=(0, 6))
        _new_button(button_frame, "Export to Excel", self.export_excel, variant="success").grid(row=0, column=1)

        results_frame = tk.Frame(frame, bg=UI_BG)
        results_frame.grid(row=7, column=0, columnspan=5, sticky="nsew", pady=(0, 6))
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=0)
        results_frame.grid_columnconfigure(1, weight=1)

        left_outer, left_panel = make_card(results_frame, "AAID Results", row=0, column=0, padx=(0, 8), pady=(8, 0))
        left_outer.grid_rowconfigure(1, weight=1)
        left_panel.grid_rowconfigure(2, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        top_row = tk.Frame(left_panel, bg=UI_PANEL)
        top_row.grid(row=0, column=0, sticky="ew", pady=(1, 0))
        top_row.grid_columnconfigure(0, weight=1)
        tk.Label(top_row, text="Application [AAID]:", bg=UI_PANEL, fg=UI_TEXT, font=(UI_FONT_FAMILY, 10)).grid(row=0, column=0, sticky="w")

        sort_frame = tk.Frame(top_row, bg=UI_PANEL)
        sort_frame.grid(row=0, column=1, sticky="e")
        tk.Label(sort_frame, text="Sort by:", bg=UI_PANEL, fg=UI_TEXT, font=(UI_FONT_FAMILY, 10)).pack(side="left")
        self.start_sort_btn = _new_button(
            sort_frame,
            "Start ↕",
            lambda: self._toggle_sort_mode("start"),
            variant="soft",
        )
        self.start_sort_btn.pack(side="left", padx=1)
        self.stop_sort_btn = _new_button(
            sort_frame,
            "Stop ↕",
            lambda: self._toggle_sort_mode("stop"),
            variant="soft",
        )
        self.stop_sort_btn.pack(side="left", padx=1)
        self._refresh_sort_button_labels()

        filter_row = tk.Frame(left_panel, bg=UI_PANEL)
        filter_row.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        filter_row.grid_columnconfigure(0, weight=0)
        filter_row.grid_columnconfigure(1, weight=0)

        aaid_entry = tk.Entry(filter_row, textvariable=self.aaid_filter, width=34)
        _style_entry(aaid_entry)
        aaid_entry.grid(row=0, column=0, sticky="w")
        aaid_entry.bind("<KeyRelease>", self._on_aaid_filter_change)

        show_frame = tk.Frame(filter_row, bg=UI_PANEL)
        show_frame.grid(row=0, column=1, sticky="w", padx=(6, 0))
        tk.Label(show_frame, text="Show:", bg=UI_PANEL, fg=UI_TEXT, font=(UI_FONT_FAMILY, 10)).pack(side="left", padx=(0, 2))

        self.notification_filter_mode_cb = ttk.Combobox(
            show_frame,
            textvariable=self.notification_filter_mode,
            values=[
                "All Apps",
                "Missing Start",
                "Missing Stop",
                "Missing Start and Stop",
                "Complete (Start + Stop)",
            ],
            state="readonly",
            style="Custom.TCombobox",
            width=18,
        )
        self.notification_filter_mode_cb.pack(side="left")
        self.notification_filter_mode_cb.bind("<<ComboboxSelected>>", lambda _e: self._reload_aaid_list(reset_page=True))

        aaid_list_frame = tk.Frame(left_panel)
        aaid_list_frame.grid(row=2, column=0, sticky="nsew")
        aaid_list_frame.grid_rowconfigure(0, weight=1)
        aaid_list_frame.grid_columnconfigure(0, weight=1)
        self.aaid_listbox = tk.Listbox(
            aaid_list_frame,
            exportselection=False,
            height=8,
            justify="center",
            bg="white",
            fg=UI_TEXT,
            selectbackground="#cfe1f5",
            selectforeground=UI_TEXT,
            activestyle="none",
            highlightthickness=1,
            highlightbackground=UI_BORDER,
            highlightcolor=UI_ACCENT,
        )
        self.aaid_listbox.grid(row=0, column=0, sticky="nsew")
        aaid_scrollbar = tk.Scrollbar(aaid_list_frame, orient="vertical", command=self.aaid_listbox.yview)
        aaid_scrollbar.grid(row=0, column=1, sticky="ns")
        self.aaid_listbox.configure(yscrollcommand=aaid_scrollbar.set)
        self.aaid_listbox.bind("<<ListboxSelect>>", self.on_select_aaid)

        pager_frame = tk.Frame(left_panel, bg=UI_PANEL)
        pager_frame.grid(row=3, column=0, sticky="w", pady=(2, 0))
        self.prev_page_btn = _new_button(pager_frame, "Prev", self._go_prev_page, variant="ghost", width=6)
        self.prev_page_btn.grid(row=0, column=0, padx=(0, 6))
        self.next_page_btn = _new_button(pager_frame, "Next", self._go_next_page, variant="ghost", width=6)
        self.next_page_btn.grid(row=0, column=1, padx=(0, 8))
        tk.Label(pager_frame, textvariable=self.aaid_page_info).grid(row=0, column=2, sticky="w")

        detail_outer, detail_panel = make_card(results_frame, "AAID Details", row=0, column=1, padx=(0, 0), pady=(8, 0))
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
            tk.Label(
                detail_panel,
                text=left_label,
                bg=UI_PANEL,
                fg=UI_TEXT,
                font=(UI_FONT_FAMILY, 10),
            ).grid(row=row_idx, column=0, sticky="w", pady=(top_pad, bottom_pad))
            tk.Label(
                detail_panel,
                textvariable=left_var,
                anchor="w",
                bg=UI_PANEL,
                fg=UI_TEXT,
                font=(UI_FONT_FAMILY, 10),
            ).grid(row=row_idx, column=1, sticky="ew", pady=(top_pad, bottom_pad))
            if right_label is not None and right_var is not None:
                tk.Label(
                    detail_panel,
                    text=right_label,
                    bg=UI_PANEL,
                    fg=UI_TEXT,
                    font=(UI_FONT_FAMILY, 10),
                ).grid(
                    row=row_idx,
                    column=2,
                    sticky="w",
                    pady=(top_pad, bottom_pad),
                    padx=(24, 0),
                )
                tk.Label(
                    detail_panel,
                    textvariable=right_var,
                    anchor="w",
                    bg=UI_PANEL,
                    fg=UI_TEXT,
                    font=(UI_FONT_FAMILY, 10),
                ).grid(
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

        tk.Label(detail_panel, text="Daily Notification Check (expected 1 start and 1 stop):", bg=UI_PANEL).grid(
            row=15, column=0, columnspan=4, sticky="w", pady=(6, 2)
        )

        daily_outer = tk.Frame(
            detail_panel,
            bg=UI_PANEL,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=UI_BORDER,
        )
        daily_outer.grid(row=16, column=0, columnspan=4, sticky="nsew", pady=(0, 6))
        daily_outer.grid_rowconfigure(0, weight=1)
        daily_outer.grid_columnconfigure(0, weight=1)

        daily_inner = tk.Frame(daily_outer, bg=UI_PANEL, padx=1, pady=1)
        daily_inner.grid(row=0, column=0, sticky="nsew")
        daily_inner.grid_rowconfigure(0, weight=1)
        daily_inner.grid_rowconfigure(1, weight=0, minsize=18)
        daily_inner.grid_columnconfigure(0, weight=1)

        self.daily_listbox = tk.Listbox(
            daily_inner,
            exportselection=False,
            height=10,
            bg="white",
            fg=UI_TEXT,
            bd=0,
            highlightthickness=0,
            activestyle="none",
            selectbackground="#cfe1f5",
            selectforeground=UI_TEXT,
            xscrollcommand=lambda *args: daily_h_scroll.set(*args),
            yscrollcommand=lambda *args: daily_v_scroll.set(*args),
        )
        self.daily_listbox.grid(row=0, column=0, sticky="nsew")

        daily_v_scroll = tk.Scrollbar(
            daily_inner,
            orient="vertical",
            command=self.daily_listbox.yview,
            bd=1,
            relief="solid",
            highlightthickness=0,
            background="#c7cfda",
            activebackground="#aeb8c7",
            troughcolor="#eef2f7",
            width=16,
        )
        daily_v_scroll.grid(row=0, column=1, sticky="ns")
        daily_h_scroll = tk.Scrollbar(
            daily_inner,
            orient="horizontal",
            command=self.daily_listbox.xview,
            bd=1,
            relief="solid",
            highlightthickness=0,
            background="#c7cfda",
            activebackground="#aeb8c7",
            troughcolor="#eef2f7",
            width=18,
        )
        daily_h_scroll.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        self.daily_listbox.configure(xscrollcommand=daily_h_scroll.set, yscrollcommand=daily_v_scroll.set)

        detail_panel.grid_rowconfigure(16, weight=1, minsize=90)

        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=0, minsize=control_col_width)
        frame.grid_columnconfigure(2, weight=0, minsize=10)
        frame.grid_columnconfigure(3, weight=0, minsize=10)
        frame.grid_columnconfigure(4, weight=1)

    def _refresh_mailbox_dropdown(self) -> None:
        if not hasattr(self, "mailbox_menu_cb"):
            return
        options = self.mailbox_names if self.mailbox_names else ["Default Mailbox"]
        self.mailbox_menu_cb["values"] = options
        if self.selected_mailbox.get() not in options:
            self.selected_mailbox.set(options[0])

    def _build_statistics_panel(self, parent: tk.Frame) -> None:
        parent.configure(bg=UI_PANEL)
        # Single ordered list keeps all metrics visible and aligned.
        parent.grid_columnconfigure(2, weight=1)

        def add_stat_row(row_idx: int, label: str, value_var) -> None:
            tk.Label(
                parent,
                text=label,
                font=(UI_FONT_FAMILY, 10),
                bg=UI_PANEL,
                fg=UI_TEXT,
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="w", pady=(0, 1), padx=(0, 2))
            tk.Label(
                parent,
                text=":",
                font=(UI_FONT_FAMILY, 10),
                bg=UI_PANEL,
                fg=UI_TEXT,
            ).grid(row=row_idx, column=1, sticky="w", pady=(0, 1), padx=(0, 5))
            tk.Label(
                parent,
                textvariable=value_var,
                font=(UI_FONT_FAMILY, 10),
                fg=UI_TEXT,
                bg=UI_PANEL,
                anchor="w",
            ).grid(row=row_idx, column=2, sticky="w", pady=(0, 1), padx=(0, 0))

        add_stat_row(0, "Date Range", self.stat_date_range)
        add_stat_row(1, "Total Applications", self.stat_total_apps)
        add_stat_row(2, "Avg TechQA Duration", self.stat_avg_techqa)
        add_stat_row(3, "Avg Final QA Duration", self.stat_avg_finalqa)
        add_stat_row(4, "Avg QA Completion", self.stat_avg_totalqa)
        add_stat_row(5, "Missing Start Notifications", self.stat_missing_start)
        add_stat_row(6, "Missing Stop Notifications", self.stat_missing_stop)

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
                fg=UI_TEXT,
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
        self.is_test_run.set("Yes" if stats.is_test_run else "No")
        self.has_techqa_overlap.set("Yes" if stats.has_techqa_overlap else "No")

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
        mode = self.aaid_sort_mode if hasattr(self, 'aaid_sort_mode') else "start_desc"
        all_keys = [
            key
            for key, stats in self.stats_by_aaid.items()
            if self._matches_notification_filter(stats)
        ]

        def group_key(aaid_key: str) -> int:
            stats = self.stats_by_aaid[aaid_key]
            has_notifications = stats.start_notifications_count > 0 or stats.stop_notifications_count > 0
            if has_notifications:
                return 0
            if self._is_qa_only_aaid(stats):
                return 1
            return 2

        if mode == "start_asc":
            value_key = lambda k: (self.stats_by_aaid[k].start_notifications_count, k)
            notification_keys = sorted((k for k in all_keys if group_key(k) == 0), key=value_key)
        elif mode == "start_desc":
            value_key = lambda k: (self.stats_by_aaid[k].start_notifications_count, k)
            notification_keys = sorted((k for k in all_keys if group_key(k) == 0), key=value_key, reverse=True)
        elif mode == "stop_asc":
            value_key = lambda k: (self.stats_by_aaid[k].stop_notifications_count, k)
            notification_keys = sorted((k for k in all_keys if group_key(k) == 0), key=value_key)
        elif mode == "stop_desc":
            value_key = lambda k: (self.stats_by_aaid[k].stop_notifications_count, k)
            notification_keys = sorted((k for k in all_keys if group_key(k) == 0), key=value_key, reverse=True)
        else:
            notification_keys = sorted((k for k in all_keys if group_key(k) == 0))

        qa_only_candidates = [k for k in all_keys if group_key(k) == 1]
        if mode == "start_asc":
            qa_only_keys = sorted(
                qa_only_candidates,
                key=lambda k: (
                    self._qa_start_proxy(self.stats_by_aaid[k]) is None,
                    self._datetime_sort_value(self._qa_start_proxy(self.stats_by_aaid[k])) or 0,
                    k,
                ),
            )
        elif mode == "start_desc":
            qa_only_keys = sorted(
                qa_only_candidates,
                key=lambda k: (
                    self._qa_start_proxy(self.stats_by_aaid[k]) is None,
                    -(self._datetime_sort_value(self._qa_start_proxy(self.stats_by_aaid[k])) or 0),
                    k,
                ),
            )
        elif mode == "stop_asc":
            qa_only_keys = sorted(
                qa_only_candidates,
                key=lambda k: (
                    self._qa_stop_proxy(self.stats_by_aaid[k]) is None,
                    self._datetime_sort_value(self._qa_stop_proxy(self.stats_by_aaid[k])) or 0,
                    k,
                ),
            )
        elif mode == "stop_desc":
            qa_only_keys = sorted(
                qa_only_candidates,
                key=lambda k: (
                    self._qa_stop_proxy(self.stats_by_aaid[k]) is None,
                    -(self._datetime_sort_value(self._qa_stop_proxy(self.stats_by_aaid[k])) or 0),
                    k,
                ),
            )
        else:
            qa_only_keys = sorted(qa_only_candidates)

        other_keys = sorted((k for k in all_keys if group_key(k) == 2))
        self.aaid_keys = notification_keys + qa_only_keys + other_keys
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
            flags = []
            if item_stats.is_test_run:
                flags.append("[TEST]")
            if item_stats.has_techqa_overlap:
                flags.append("[TechQA Overlap]")
            flags_str = " ".join(flags)
            
            if self._is_qa_only_aaid(item_stats):
                display = f"QA - {key}"
            else:
                display = f"{key}  |  Start: {item_stats.start_notifications_count}  Stop: {item_stats.stop_notifications_count}"
            
            if flags_str:
                display += f"  {flags_str}"
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
        
        # Show techqa overlap flags at the top
        stats = self.stats_by_aaid.get(aaid)
        if stats:
            flags = []
            if stats.has_techqa_overlap:
                flags.append("[TechQA Overlap]")
            if flags:
                self.daily_listbox.insert(tk.END, " ".join(flags))
                self.daily_listbox.itemconfig(0, fg=UI_TEXT)
        
        daily_counts = self.daily_counts_by_aaid.get(aaid, {})
        if not daily_counts:
            self.daily_listbox.insert(tk.END, "No notification entries for this AAID in selected range.")
            return

        sorted_dates = sorted(daily_counts.keys(), reverse=True)
        for date_key in sorted_dates:
            counts = daily_counts[date_key]
            # Daily notifications are valid only when there is exactly 1 start and 1 stop.
            is_alert = counts.start_count != 1 or counts.stop_count != 1
            status = "ALERT" if is_alert else "OK"
            # Show breakdown only if there are multiple raw notifications
            start_text = (
                str(counts.start_count)
                if counts.raw_start_count <= 1
                else f"{counts.start_count}({counts.raw_start_count})"
            )
            stop_text = (
                str(counts.stop_count)
                if counts.raw_stop_count <= 1
                else f"{counts.stop_count}({counts.raw_stop_count})"
            )
            # Include timestamps if available
            start_time_str = counts.start_time.strftime("%H:%M:%S") if counts.start_time else "N/A"
            stop_time_str = counts.stop_time.strftime("%H:%M:%S") if counts.stop_time else "N/A"
            row_text = f"{date_key} | Start: {start_text} @ {start_time_str} | Stop: {stop_text} @ {stop_time_str} | {status}"
            self.daily_listbox.insert(tk.END, row_text)
            row_index = self.daily_listbox.size() - 1
            if is_alert:
                self.daily_listbox.itemconfig(row_index, fg="#c62828")

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
            messagebox.showerror(
                "Export Error",
                _user_error_message("Failed to export results.", exc),
            )

    def refresh(self):
        # Initialize mailboxes asynchronously so the UI thread does not block.
        if not self.mailbox_names or self.mailbox_names == ["Default Mailbox"]:
            self._init_mailboxes_async()
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
                # Security: Check filter input for suspicious patterns
                filter_threat = _detect_pentest_attempt(aaid_filter_str, "aaid_filter")
                if filter_threat:
                    _log_security_event(filter_threat, {"filter": aaid_filter_str})
                
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
            # Security: Check subject filter for suspicious patterns
            if subject_contains:
                subject_threat = _detect_pentest_attempt(subject_contains, "subject_filter")
                if subject_threat:
                    _log_security_event(subject_threat, {"subject_filter": subject_contains})

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
                debug_enabled = self.debug_enabled.get()
                logging.getLogger().setLevel(logging.DEBUG if debug_enabled else logging.INFO)
                selected_mailbox = self.selected_mailbox.get().strip()
                if selected_mailbox == ALL_MAILBOXES_OPTION:
                    messages = read_messages_from_all_mailboxes(
                        mailbox_names=self.mailbox_names,
                        folder_path=self.folder_path.get().strip(),
                        max_emails=max_emails,
                        subject_contains=subject_contains,
                        start_date=start_date,
                        end_date=end_date,
                        debug_enabled=debug_enabled,
                    )
                else:
                    folder_path = self._get_full_folder_path()
                    messages = read_messages_from_outlook(
                        folder_path=folder_path,
                        max_emails=max_emails,
                        subject_contains=subject_contains,
                        start_date=start_date,
                        end_date=end_date,
                        debug_enabled=debug_enabled,
                    )
                self._log_debug(f"Total messages fetched: {len(messages)}")
                for msg in messages:
                    subject = msg[0] if msg else ""
                    self._log_debug(f"[MESSAGE_TO_PARSE] {_redact_subject(str(subject))}")
                stats_by_aaid = parse_stats_by_aaid_from_messages(
                    messages,
                    filter_aaid=filter_aaid,
                    debug_enabled=debug_enabled,
                )
                daily_counts_by_aaid = parse_daily_notification_counts_by_aaid(messages, filter_aaid=filter_aaid)
                trend_stats = compute_missing_notification_trends(messages, filter_aaid=filter_aaid)
            except OutlookNotFoundError:
                self.root.after(0, lambda: self.status_var.set(""))
                self.root.after(0, lambda: messagebox.showerror("Outlook Not Found", "Outlook not found."))
                return
            except Exception as exc:
                self.root.after(0, lambda: self.status_var.set(""))
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Outlook Read Error",
                        _user_error_message("Failed to read Outlook data.", exc),
                    ),
                )
                import traceback

                self._log_debug(f"Outlook Read Error: {exc}\n{traceback.format_exc()}")
                return

            def update_ui():
                self.stats_by_aaid = stats_by_aaid
                self.daily_counts_by_aaid = daily_counts_by_aaid
                self.trend_stats = trend_stats
                # Clear old details before loading new data to prevent stale results
                self.selected_aaid.set("N/A")
                self._apply_stats_to_view(DashboardStats())
                self.daily_listbox.delete(0, tk.END)
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
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Thread Error",
                    _user_error_message("An unexpected error occurred while processing."),
                ),
            )
            self._log_debug(f"Thread Error: {exc}")

    def _get_full_folder_path(self):
        mailbox = self.selected_mailbox.get().strip()
        folder = self.folder_path.get().strip()
        if (
            not mailbox
            or mailbox.lower() == "default mailbox"
            or mailbox == ALL_MAILBOXES_OPTION
        ):
            return folder or "Inbox"
        if folder.lower().startswith(mailbox.lower() + "/"):
            folder = folder[len(mailbox) + 1:]
        folder = folder.strip("/")
        if not folder:
            folder = "Inbox"
        return f"{mailbox}/{folder}"


def main():
    try:
        try:
            _ensure_runtime_dependencies()
        except Exception as dependency_exc:  # noqa: BLE001
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Dependency Error",
                _user_error_message("Required Python packages are missing.", dependency_exc),
            )
            root.destroy()
            return

        root = tk.Tk()
        app = DashboardUI(root)
        app.refresh()
        root.mainloop()
    except Exception as exc:
        import traceback
        traceback_text = traceback.format_exc()

        if SAFE_MODE:
            error_message = "[FATAL ERROR] Application terminated unexpectedly."
        else:
            error_message = f"[FATAL ERROR] {exc}\n{traceback_text}"

        print(error_message)
        log_path = _current_log_path()
        try:
            rotate_log_if_needed(log_path)
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(error_message + "\n")
                # Preserve traceback in logs even when SAFE_MODE hides it from console.
                if SAFE_MODE:
                    log_file.write(f"[FATAL TRACEBACK]\n{traceback_text}\n")
        except OSError:
            pass

        try:
            messagebox.showerror(
                "Fatal Error",
                f"Application terminated unexpectedly.\nSee logs for details:\n{log_path}",
            )
        except Exception:
            pass


if __name__ == '__main__':
    main()
