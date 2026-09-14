"""
================================================================
بوت استضافة بوتات تيليجرام — نسخة الجوال (SQLite)
================================================================
- تستخدم SQLite (مدمجة في بايثون، لا تحتاج تثبيت إضافي).
- مناسبة للتشغيل على Pydroid / Termux / أي كمبيوتر.
- متطلبات: pip install pyTelegramBotAPI
- التشغيل: python3 emrati.py
================================================================
"""

# ============================================================
# 1) الإعدادات — عدّل هذه القيم فقط
# ============================================================
import os

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "8857061529:AAEcz7UIP0hsXTxHKWKsdMIHAlGIyBkc0E4").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID") or "8635274099")
# ── المطوّرون/أدمن متعدد ──
_DEVELOPER_IDS: set[int] = {8635274099, 
8635274099}
if os.environ.get("ADMIN_IDS"):
    for _id in os.environ["ADMIN_IDS"].split(","):
        try: _DEVELOPER_IDS.add(int(_id.strip()))
        except ValueError: pass

DB_PATH = os.environ.get("DB_PATH", "hosting_bot.db")
KEEP_ALIVE_PORT = int(os.environ.get("PORT", "5000"))
PROJECTS_DIR = os.environ.get("PROJECTS_DIR", "hosted_projects")
ADMIN_CONTACT = os.environ.get("ADMIN_CONTACT", "@EM_RT2")
DEVELOPER_USERNAME = os.environ.get("DEVELOPER_USERNAME", "EM_RT2").lstrip("@")

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_SITE_ZIP_SIZE = int(os.environ.get("MAX_SITE_ZIP_SIZE", str(50 * 1024 * 1024)))
NETLIFY_TOKEN = os.environ.get("NETLIFY_TOKEN", "").strip()
NETLIFY_API_BASE = os.environ.get("NETLIFY_API_BASE", "https://api.netlify.com/api/v1").rstrip("/")
NETLIFY_SITE_PREFIX = (os.environ.get("NETLIFY_SITE_PREFIX", "tg-site") or "tg-site").strip()
VERCEL_TOKEN = os.environ.get("VERCEL_TOKEN", "").strip()
VERCEL_API_BASE = os.environ.get("VERCEL_API_BASE", "https://api.vercel.com").rstrip("/")
VERCEL_SITE_PREFIX = (os.environ.get("VERCEL_SITE_PREFIX", "tg-vercel") or "tg-vercel").strip()
MAX_VERCEL_INLINE_BYTES = int(os.environ.get("MAX_VERCEL_INLINE_BYTES", str(3 * 1024 * 1024)))
MAX_FILES_PER_PROJECT = 50
ALLOWED_EXTENSIONS = {
    ".py", ".txt", ".json", ".csv", ".env", ".yaml", ".yml",
    ".ini", ".cfg", ".md", ".html", ".css", ".js", ".sql",
    ".xml", ".log", ".db",
}

# ============================================================
# 2) الاستيرادات
# ============================================================
import logging
import json
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import shlex
import io
import zipfile
import base64
import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

import telebot
from telebot import types
from telebot import apihelper

# ============================================================
# ثوابت أيقونات الأزرار — Custom Emoji IDs
# ============================================================
EMOJI_IDS = [
    "4945049066271671758",  # 0  — admin / dev
    "5965466792527666087",  # 1  — home
    "5373020661574826232",  # 2  — back
    "5967507756691757055",  # 3  — cancel
    "5967301267549068409",  # 4  — users
    "5785167918027250397",  # 5  — list / accounts
    "5857054220179486296",  # 6  — new / add
    "5857339990123486296",  # 7  — upload
    "5881760620117760960",  # 8  — terminal
    "5920209833071482745",  # 9  — sites / web
    "5920415115328362511",  # 10 — deploys
    "5920298756074379058",  # 11 — points
    "5922681088534124293",  # 12 — transfer
    "6001388309853510348",  # 13 — help
    "5999278377104578246",  # 14 — start / play
    "5998940732545571769",  # 15 — stop
    "6003691769533829755",  # 16 — restart
    "5280753674451175517",  # 17 — add file
    "5314299563761222650",  # 18 — log
    "6037182124916740433",  # 19 — files
    "5976317950091598658",  # 20 — install / package
    "5976831692604709621",  # 21 — delete
    "5253743295141538873",  # 22 — ban
    "5254001839287859496",  # 23 — unban
]

STATS_EMOJI     = "5935935761336505948"
BROADCAST_EMOJI = "5902385465390013835"
WELCOME_EMOJIS = [
    "5811975617830197571",
    "5967427591127176971",
    "5285169394752707985",
]

# تعيين E_* من القائمة
E_ADMIN    = EMOJI_IDS[0]
E_DEV      = EMOJI_IDS[0]
E_HOME     = EMOJI_IDS[1]
E_BACK     = EMOJI_IDS[2]
E_CANCEL   = EMOJI_IDS[3]
E_USERS    = EMOJI_IDS[4]
E_ACCOUNTS = EMOJI_IDS[5]
E_LIST     = EMOJI_IDS[5]
E_NEW      = EMOJI_IDS[6]
E_UPLOAD   = EMOJI_IDS[7]
E_TERMINAL = EMOJI_IDS[8]
E_SITES    = EMOJI_IDS[9]
E_DEPLOYS  = EMOJI_IDS[10]
E_POINTS   = EMOJI_IDS[11]
E_TRANSFER = EMOJI_IDS[12]
E_HELP     = EMOJI_IDS[13]
E_START    = EMOJI_IDS[14]
E_STOP     = EMOJI_IDS[15]
E_RESTART  = EMOJI_IDS[16]
E_ADD_FILE = EMOJI_IDS[17]
E_LOG      = EMOJI_IDS[18]
E_FILES    = EMOJI_IDS[19]
E_INSTALL  = EMOJI_IDS[20]
E_DELETE   = EMOJI_IDS[21]
E_BAN      = EMOJI_IDS[22]
E_UNBAN    = EMOJI_IDS[23]

E_STATS     = STATS_EMOJI
E_BROADCAST = BROADCAST_EMOJI

# باقي الثوابت تستخدم أقرب مرادف
E_APPROVE     = EMOJI_IDS[14]   # start → approve
E_REJECT      = EMOJI_IDS[21]   # delete → reject
E_INFO        = EMOJI_IDS[4]    # users → info
E_CHANNEL     = EMOJI_IDS[9]    # sites → channel
E_SHARE       = EMOJI_IDS[12]   # transfer → share
E_GIFT        = EMOJI_IDS[11]   # points → gift
E_MODS        = EMOJI_IDS[0]    # admin → mods
E_PRICE       = EMOJI_IDS[11]   # points → price
E_TOGGLE      = EMOJI_IDS[16]   # restart → toggle
E_CHECK       = EMOJI_IDS[23]   # unban → check
E_SIGNATURE   = EMOJI_IDS[0]    # admin → signature / brand
E_BLOCK_ID    = EMOJI_IDS[22]   # ban → block
E_UNBLOCK_ID  = EMOJI_IDS[23]   # unban → unblock
E_BLOCKED_LST = EMOJI_IDS[4]    # users → blocked list
E_MSG_USER    = EMOJI_IDS[18]   # log → message user
E_WARN        = EMOJI_IDS[9]    # sites → warn

# ============================================================
# صور البوت
# ============================================================
WELCOME_IMAGE     = "https://ibb.co/W4YYm3dz"
MAINTENANCE_IMAGE = "https://ibb.co/8QX4rFc"
BANNED_IMAGE      = "https://ibb.co/TDSWt4hW"

_START_TS = time.time()

# ============================================================
# اقتباسات البوت — تظهر عشوائياً في الرسائل
# ============================================================
import random

QUOTES = [
    ("الخيال أهم من المعرفة، فالمعرفة محدودة أما الخيال فيطوق العالم.", "ألبرت أينشتاين"),
    ("لا تستسلم أبداً، أبداً، أبداً، أبداً.", "ونستون تشرشل"),
    ("يبدو الأمر مستحيلاً دائماً حتى يتحقق.", "نيلسون مانديلا"),
    ("كن التغيير الذي تريد أن تراه في العالم.", "المهاتما غاندي"),
    ("النجاح هو الانتقال من فشل إلى فشل دون أن تفقد حماسك.", "ونستون تشرشل"),
    ("الإنسان يصنع نفسه بنفسه.", "أرسطو"),
    ("ابقَ جائعاً، ابقَ أحمق.", "ستيف جوبز"),
    ("العبقرية هي واحد بالمئة إلهام، وتسعة وتسعون بالمئة تعرُّق.", "توماس إديسون"),
    ("الحياة ما تُعدّ من الأنفاس، بل ما تُعدّ من اللحظات التي تسرق الأنفاس.", "مايا أنجيلو"),
    ("إذا كنت تسير وحدك فستسير بسرعة، وإذا سرت مع غيرك فستذهب بعيداً.", "مثل أفريقي"),
    ("لا تقيس نجاحك بما حققت، بل بما تجاوزت من عقبات.", "بوكر تي واشنطن"),
    ("العقل الذي ينفتح على فكرة جديدة لا يعود إلى حجمه الأصلي أبداً.", "أوليفر وندل هولمز"),
    ("التعليم هو السلاح الأقوى الذي يمكنك استخدامه لتغيير العالم.", "نيلسون مانديلا"),
    ("الظلام لا يطرد الظلام، النور وحده يستطيع ذلك.", "مارتن لوثر كينج"),
    ("حياة واحدة قصيرة جداً لتكون صغيراً.", "بنيامين ديزرائيلي"),
    ("من لا يجد وقتاً للصحة، سيجد وقتاً للمرض.", "إدوارد ستانلي"),
    ("الشجاعة هي أن تعرف الخوف وتمضي قُدُماً رغمه.", "مارك توين"),
    ("أخبرني وسأنسى، علّمني وسأتذكر، أشركني وسأتعلّم.", "بنيامين فرانكلين"),
    ("لا تتمنَّ أن يكون الأمر أسهل، تمنَّ أن تكون أقوى.", "جيم رون"),
    ("إن أردت أن تبني سفينة، فلا تجمع الناس لتوفير الخشب، بل أيقظ فيهم الشوق إلى البحر اللامتناهي.", "أنطوان دو سانت إكزوبيري"),
    ("لا أفشل، أتعلّم فقط أن ألف طريقة لا تصلح.", "توماس إديسون"),
    ("أجمل الأشياء في الحياة لا تُرى ولا تُلمس، بل تُحسّ بالقلب.", "هيلين كيلر"),
    ("الفرصة لا تأتي إليك، بل أنت من يصنعها.", "كريس غروسر"),
    ("نحن ما نفعله باستمرار، إذاً التميز ليس فعلاً بل عادة.", "أرسطو"),
    ("إذا نظرت إلى ما لديك في الحياة ستجد دائماً أن لديك المزيد.", "أوبرا وينفري"),
]

def get_random_quote() -> str:
    text, author = random.choice(QUOTES)
    return f"<blockquote>{text}\n— <i>{author}</i></blockquote>"

# ============================================================
# 3) فحوص أولية
# ============================================================
if not BOT_TOKEN or BOT_TOKEN == "ضع_توكن_بوتك_هنا":
    raise RuntimeError("BOT_TOKEN غير مضبوط — ضع توكن بوتك في متغير البيئة BOT_TOKEN")
if ADMIN_ID == 0:
    raise RuntimeError("ADMIN_ID غير مضبوط — ضع ID حسابك في متغير البيئة ADMIN_ID")

os.makedirs(PROJECTS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("hosting-bot")

# ============================================================
# 4) قاعدة البيانات SQLite
# ============================================================
_db_lock = threading.RLock()
_db_conn: Optional[sqlite3.Connection] = None


def db_init() -> None:
    global _db_conn
    if _db_conn is not None:
        return
    _db_conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
    _db_conn.row_factory = sqlite3.Row
    _db_conn.execute("PRAGMA journal_mode=WAL")
    _db_conn.execute("PRAGMA synchronous=NORMAL")
    _db_conn.execute("PRAGMA foreign_keys=ON")
    _db_conn.execute("PRAGMA busy_timeout=5000")
    log.info("SQLite database opened at %s", DB_PATH)


def _row_to_dict(row) -> Optional[dict]:
    return dict(row) if row is not None else None


def db_fetchone(query: str, params: Iterable[Any] = ()) -> Optional[dict]:
    with _db_lock:
        cur = _db_conn.execute(query, tuple(params))
        row = cur.fetchone()
        cur.close()
    return _row_to_dict(row)


def db_fetchall(query: str, params: Iterable[Any] = ()) -> list:
    with _db_lock:
        cur = _db_conn.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
    return [dict(r) for r in rows]


def db_execute(query: str, params: Iterable[Any] = ()) -> None:
    with _db_lock:
        cur = _db_conn.execute(query, tuple(params))
        cur.close()


def db_execute_returning_id(query: str, params: Iterable[Any] = ()) -> int:
    with _db_lock:
        cur = _db_conn.execute(query, tuple(params))
        rid = cur.lastrowid
        cur.close()
    return rid


# ============================================================
# 5) إنشاء الجداول
# ============================================================
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY,
    first_name   TEXT,
    username     TEXT,
    approved     INTEGER NOT NULL DEFAULT 0,
    banned       INTEGER NOT NULL DEFAULT 0,
    max_bots     INTEGER NOT NULL DEFAULT 5,
    points       INTEGER NOT NULL DEFAULT 0,
    referred_by  INTEGER,
    blocked_bot  INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    main_file       TEXT NOT NULL DEFAULT '',
    approved        INTEGER NOT NULL DEFAULT 0,
    is_running      INTEGER NOT NULL DEFAULT 0,
    last_started_at TIMESTAMP,
    last_stopped_at TIMESTAMP,
    last_error      TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS project_files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    content     BLOB NOT NULL,
    size_bytes  INTEGER NOT NULL,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (project_id, filename)
);

CREATE TABLE IF NOT EXISTS pending_uploads (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL,
    project_id         INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename           TEXT NOT NULL,
    telegram_file_id   TEXT NOT NULL,
    size_bytes         INTEGER NOT NULL,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL,
    event       TEXT NOT NULL,
    message     TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS gift_links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token       TEXT UNIQUE NOT NULL,
    points      INTEGER NOT NULL,
    max_uses    INTEGER NOT NULL,
    used_count  INTEGER NOT NULL DEFAULT 0,
    created_by  INTEGER NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gift_link_uses (
    link_id  INTEGER NOT NULL REFERENCES gift_links(id) ON DELETE CASCADE,
    user_id  INTEGER NOT NULL,
    used_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (link_id, user_id)
);

CREATE TABLE IF NOT EXISTS netlify_sites (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    site_id        TEXT UNIQUE NOT NULL,
    site_name      TEXT NOT NULL,
    site_url       TEXT NOT NULL,
    last_deploy_id TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_deploy_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS moderators (
    user_id    INTEGER PRIMARY KEY,
    added_by   INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deployments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider    TEXT NOT NULL,
    site_id     TEXT,
    deploy_id   TEXT,
    url         TEXT NOT NULL,
    filename    TEXT,
    size_bytes  INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage_daily (
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day       TEXT NOT NULL,
    section   TEXT NOT NULL,
    count     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day, section)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id    INTEGER NOT NULL,
    action      TEXT NOT NULL,
    target_uid  INTEGER,
    project_id  INTEGER,
    provider    TEXT,
    filename    TEXT,
    size_bytes  INTEGER,
    command     TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_user   ON projects (user_id);
CREATE INDEX IF NOT EXISTS idx_files_project   ON project_files (project_id);
CREATE INDEX IF NOT EXISTS idx_pending_project ON pending_uploads (project_id);
CREATE INDEX IF NOT EXISTS idx_logs_project    ON process_logs (project_id);
CREATE INDEX IF NOT EXISTS idx_gift_uses_link  ON gift_link_uses (link_id);
CREATE INDEX IF NOT EXISTS idx_netlify_user    ON netlify_sites (user_id);
CREATE INDEX IF NOT EXISTS idx_deploy_user     ON deployments (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_deploy_provider ON deployments (provider, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_day       ON usage_daily (day, section);
CREATE INDEX IF NOT EXISTS idx_audit_time      ON audit_log (created_at);

CREATE TABLE IF NOT EXISTS force_channels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel     TEXT NOT NULL UNIQUE,
    label       TEXT NOT NULL DEFAULT '',
    ch_type     TEXT NOT NULL DEFAULT 'public',
    invite_link TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def db_create_schema() -> None:
    with _db_lock:
        _db_conn.executescript(SCHEMA_SQL)
    log.info("Database schema is ready")


def db_ensure_columns() -> None:
    cols = [r["name"] for r in db_fetchall("PRAGMA table_info(users)")]
    for col, defn in [
        ("points", "INTEGER NOT NULL DEFAULT 0"),
        ("referred_by", "INTEGER"),
        ("blocked_bot", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        if col not in cols:
            db_execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            log.info("Added column users.%s", col)

    gcols = [r["name"] for r in db_fetchall("PRAGMA table_info(gift_links)")]
    if gcols and "expires_at" not in gcols:
        db_execute("ALTER TABLE gift_links ADD COLUMN expires_at TIMESTAMP")

    fccols = [r["name"] for r in db_fetchall("PRAGMA table_info(force_channels)")]
    if fccols and "invite_link" not in fccols:
        db_execute("ALTER TABLE force_channels ADD COLUMN invite_link TEXT NOT NULL DEFAULT ''")
        log.info("Added column force_channels.invite_link")

    pucols = [r["name"] for r in db_fetchall("PRAGMA table_info(pending_uploads)")]
    if pucols and "status" not in pucols:
        db_execute("ALTER TABLE pending_uploads ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
        log.info("Added column pending_uploads.status")

    # هجرة: نقل force_channel القديم إلى جدول force_channels
    old_ch = (get_setting("force_channel", "") or "").strip()
    if old_ch:
        existing = db_fetchone("SELECT id FROM force_channels WHERE channel=?", (old_ch,))
        if not existing:
            ch_type = "private" if re.match(r"^-?\d+$", old_ch) else "public"
            db_execute(
                "INSERT OR IGNORE INTO force_channels (channel, label, ch_type) VALUES (?,?,?)",
                (old_ch, old_ch, ch_type),
            )
        set_setting("force_channel", "")
        log.info("Migrated legacy force_channel '%s' to force_channels table", old_ch)


# ============================================================
# 5.1) إعدادات
# ============================================================
def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    row = db_fetchone("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: Any) -> None:
    db_execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def get_upload_price() -> int:
    try:
        return max(0, int(get_setting("upload_price", "1") or "1"))
    except Exception:
        return 1


def get_transfer_fee() -> int:
    try:
        return max(0, int(get_setting("transfer_fee", "0") or "0"))
    except Exception:
        return 0


def get_force_channels() -> list:
    return db_fetchall("SELECT id, channel, label, ch_type, invite_link FROM force_channels ORDER BY id")


def get_force_channel() -> str:
    """توافق مع الكود القديم — يُعيد أول قناة أو نص فارغ"""
    rows = get_force_channels()
    return rows[0]["channel"] if rows else ""


def add_force_channel(channel: str, label: str = "", ch_type: str = "public", invite_link: str = "") -> bool:
    try:
        db_execute(
            "INSERT OR IGNORE INTO force_channels (channel, label, ch_type, invite_link) VALUES (?,?,?,?)",
            (channel, label or channel, ch_type, invite_link or ""),
        )
        return True
    except Exception:
        log.exception("add_force_channel failed for %s", channel)
        return False


def del_force_channel(fid: int) -> None:
    db_execute("DELETE FROM force_channels WHERE id=?", (fid,))


def update_force_channel_invite(fid: int, invite_link: str) -> bool:
    try:
        db_execute(
            "UPDATE force_channels SET invite_link=? WHERE id=?",
            (invite_link, fid),
        )
        return True
    except Exception:
        log.exception("update_force_channel_invite failed for id=%s", fid)
        return False


def update_force_channel_label(fid: int, label: str) -> bool:
    try:
        db_execute("UPDATE force_channels SET label=? WHERE id=?", (label, fid))
        return True
    except Exception:
        log.exception("update_force_channel_label failed for id=%s", fid)
        return False


def update_force_channel_id(fid: int, new_channel: str, ch_type: str) -> bool:
    try:
        db_execute(
            "UPDATE force_channels SET channel=?, ch_type=? WHERE id=?",
            (new_channel, ch_type, fid),
        )
        return True
    except Exception:
        log.exception("update_force_channel_id failed for id=%s", fid)
        return False


def is_user_subscribed_all(uid: int):
    """يُعيد (True, []) إذا مشترك في كل القنوات، أو (False, [قنوات ناقصة])"""
    channels = get_force_channels()
    if not channels:
        return True, []
    unsubscribed = [ch for ch in channels if not is_user_subscribed(uid, ch["channel"])]
    return len(unsubscribed) == 0, unsubscribed


def get_section_price(section_key: str, default: int = 0) -> int:
    try:
        return max(0, int(get_setting(f"price_{section_key}", str(default)) or str(default)))
    except Exception:
        return max(0, default)


def is_admin_notify_enabled(key: str, default: bool = True) -> bool:
    v = (get_setting(key, "1" if default else "0") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _today_utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_daily_limit(section: str, default: int) -> int:
    try:
        return max(0, int(get_setting(f"limit_daily_{section}", str(default)) or str(default)))
    except Exception:
        return max(0, default)


def check_and_inc_daily(uid: int, section: str, default_limit: int) -> tuple:
    if is_admin(uid):
        return True, ""
    limit = get_daily_limit(section, default_limit)
    if limit <= 0:
        return True, ""
    day = _today_utc_day()
    row = db_fetchone("SELECT count FROM usage_daily WHERE user_id=? AND day=? AND section=?", (uid, day, section))
    cur = int((row or {}).get("count") or 0)
    if cur >= limit:
        return False, f"❌ وصلت للحد اليومي لقسم {section}: <b>{limit}</b>"
    db_execute(
        "INSERT INTO usage_daily (user_id, day, section, count) VALUES (?,?,?,1) "
        "ON CONFLICT(user_id, day, section) DO UPDATE SET count = count + 1",
        (uid, day, section),
    )
    return True, ""


def is_bot_disabled() -> bool:
    return (get_setting("bot_disabled", "0") or "0") == "1"


def set_bot_disabled(disabled: bool) -> None:
    set_setting("bot_disabled", "1" if disabled else "0")


def normalize_channel(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    # دعم chat_id الرقمي (قنوات خاصة مثل -1001234567890)
    if re.match(r"^-?\d+$", text):
        return text
    if text.startswith("https://t.me/"):
        text = text[len("https://t.me/"):]
    if text.startswith("t.me/"):
        text = text[len("t.me/"):]
    text = text.split("/")[0].split("?")[0]
    if not text:
        return ""
    if not text.startswith("@"):
        text = "@" + text
    return text


# ============================================================
# 5.2) فحص الاشتراك الإجباري في القناة
# ============================================================

# ذاكرة مؤقتة لتجنب إرسال نفس التنبيه أكثر من مرة
_perm_warn_sent: set = set()


def notify_admin_perm_error(channel: str, label: str, error: str) -> None:
    """يُرسل تنبيهاً للأدمن مرة واحدة لكل قناة عند اكتشاف مشكلة صلاحيات."""
    cache_key = f"{channel}"
    if cache_key in _perm_warn_sent:
        return
    _perm_warn_sent.add(cache_key)
    try:
        bot.send_message(
            ADMIN_ID,
            f"⚠️ <b>تنبيه — صلاحيات البوت ناقصة!</b>\n\n"
            f"📢 القناة: <b>{html_escape(label or channel)}</b>\n"
            f"🆔 المعرف: <code>{html_escape(str(channel))}</code>\n\n"
            f"❌ <b>الخطأ:</b>\n<code>{html_escape(error[:300])}</code>\n\n"
            "📌 <b>الحل المطلوب:</b>\n"
            "• اجعل البوت <b>مشرفاً</b> في القناة\n"
            "• امنحه صلاحية <b>Invite Users via Link</b>\n\n"
            "يمكنك فحص جميع القنوات من:\n"
            "<b>لوحة الأدمن ← الاشتراك الإجباري ← 🔍 فحص الصلاحيات</b>",
        )
    except Exception:
        log.exception("notify_admin_perm_error: failed to notify admin for %s", channel)


def check_bot_channel_permissions(channel: str) -> dict:
    """
    يفحص صلاحيات البوت في القناة المحددة.
    يُعيد dict يحتوي على:
      ok        — True إذا كان البوت مشرفاً بالصلاحيات الكاملة
      is_admin  — True إذا كان البوت مشرفاً أو مالكاً
      can_invite — True إذا كان لديه صلاحية Invite Users via Link
      error     — نص الخطأ إن وجد
    """
    result = {"ok": False, "is_admin": False, "can_invite": False, "error": None}
    try:
        bot_id = bot.get_me().id
        member = bot.get_chat_member(channel, bot_id)
        status = getattr(member, "status", "left")
        if status == "creator":
            result.update({"ok": True, "is_admin": True, "can_invite": True})
        elif status == "administrator":
            can_invite = bool(getattr(member, "can_invite_users", False))
            result.update({"is_admin": True, "can_invite": can_invite, "ok": can_invite})
            if not can_invite:
                result["error"] = "البوت مشرف لكن بدون صلاحية Invite Users via Link"
        else:
            result["error"] = f"البوت ليس مشرفاً في القناة (الحالة الحالية: {status})"
    except Exception as exc:
        result["error"] = str(exc)[:300]
    return result


def is_user_subscribed(uid: int, channel: str) -> bool:
    if not channel:
        return True
    try:
        member = bot.get_chat_member(channel, uid)
        return getattr(member, "status", "left") not in ("left", "kicked")
    except Exception as exc:
        err_str = str(exc).lower()
        log.exception("get_chat_member failed for %s in %s", uid, channel)
        # تنبيه الأدمن إذا كان الخطأ ناتجاً عن نقص صلاحيات البوت
        if any(kw in err_str for kw in (
            "not enough rights", "forbidden", "administrator",
            "bot is not", "have no rights", "chat not found",
        )):
            ch_row = db_fetchone("SELECT label FROM force_channels WHERE channel=?", (channel,))
            label = (ch_row or {}).get("label") or channel
            notify_admin_perm_error(channel, label, str(exc)[:300])
        return True


def force_sub_block(chat_id: int, uid: int) -> bool:
    if is_admin(uid):
        return False
    ok, unsubscribed = is_user_subscribed_all(uid)
    if ok:
        return False
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in unsubscribed:
        label = ch["label"] or ch["channel"]
        if ch["ch_type"] == "public":
            join_url = f"https://t.me/{ch['channel'].lstrip('@')}"
            kb.add(types.InlineKeyboardButton(f"📢 اشترك ← {label}", url=join_url, style="primary"))
        else:
            invite_link = (ch.get("invite_link") or "").strip()
            if invite_link:
                kb.add(types.InlineKeyboardButton(f"📢 اشترك ← {label}", url=invite_link, style="primary"))
            else:
                kb.add(types.InlineKeyboardButton(f"🔒 قناة خاصة: {label}", callback_data="noop", style="primary"))
    kb.add(types.InlineKeyboardButton("✅ تحقّق من الاشتراك", callback_data="check_sub", style="success"))
    lines = "\n".join(f"• {ch['label'] or ch['channel']}" for ch in unsubscribed)
    bot.send_message(
        chat_id,
        f"⚠️ <b>للاستمرار يجب الاشتراك في القنوات التالية:</b>\n\n{lines}\n\n"
        "اضغط على زر الاشتراك ثم اضغط <b>تحقّق</b>.",
        reply_markup=kb,
    )
    return True


# ============================================================
# 5.3) روابط هدايا النقاط
# ============================================================
def _new_gift_token() -> str:
    import secrets
    return secrets.token_urlsafe(8)


def process_gift_link(uid: int, token: str) -> None:
    link = db_fetchone("SELECT * FROM gift_links WHERE token=?", (token,))
    if not link:
        try:
            bot.send_message(uid, "❌ رابط الهدية غير صالح.")
        except Exception:
            pass
        return
    expires_at = link.get("expires_at")
    if expires_at:
        try:
            exp = datetime.strptime(str(expires_at).split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                try:
                    bot.send_message(uid, "❌ انتهت صلاحية رابط الهدية.")
                except Exception:
                    pass
                return
        except Exception:
            pass
    used = db_fetchone("SELECT 1 AS x FROM gift_link_uses WHERE link_id=? AND user_id=?", (link["id"], uid))
    if used:
        try:
            bot.send_message(uid, "❌ سبق وأن استخدمت هذا الرابط من قبل.")
        except Exception:
            pass
        return
    with _db_lock:
        link2 = db_fetchone("SELECT used_count, max_uses, points FROM gift_links WHERE id=?", (link["id"],))
        if not link2 or link2["used_count"] >= link2["max_uses"]:
            try:
                bot.send_message(uid, "❌ تم استنفاذ هذا الرابط (وصل للحد الأقصى).")
            except Exception:
                pass
            return
        db_execute("UPDATE gift_links SET used_count = used_count + 1 WHERE id=? AND used_count < max_uses", (link["id"],))
        db_execute("INSERT OR IGNORE INTO gift_link_uses (link_id, user_id) VALUES (?, ?)", (link["id"], uid))
        db_execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE id=?", (link2["points"], uid))
    try:
        bot.send_message(uid, f"🎁 تهانينا! حصلت على <b>{link2['points']}</b> نقطة من رابط الهدية 🎉")
    except Exception:
        pass


# ============================================================
# 6) Netlify
# ============================================================
def netlify_is_configured() -> bool:
    return bool(NETLIFY_TOKEN)


def _slugify_site_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:63] or "tg-site"


def _netlify_request(method: str, path: str, *, body: Optional[bytes] = None,
                     content_type: Optional[str] = None, timeout: int = 60) -> dict:
    if not netlify_is_configured():
        raise RuntimeError("NETLIFY_TOKEN is not set")
    url = f"{NETLIFY_API_BASE}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}", "User-Agent": "tg-hosting-bot/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8", errors="replace")
        except Exception:
            msg = str(e)
        raise RuntimeError(f"Netlify API error ({e.code}): {msg[:400]}")


def netlify_create_site_for_user(uid: int) -> dict:
    base = _slugify_site_name(f"{NETLIFY_SITE_PREFIX}-{uid}-{int(time.time())}")
    payload = json.dumps({"name": base}).encode("utf-8")
    return _netlify_request("POST", "/sites", body=payload, content_type="application/json", timeout=60)


def netlify_deploy_zip(site_id: str, zip_bytes: bytes) -> dict:
    return _netlify_request("POST", f"/sites/{site_id}/deploys", body=zip_bytes,
                            content_type="application/zip", timeout=180)


def _netlify_pick_site_url(site_payload: dict) -> str:
    for k in ("ssl_url", "url", "admin_url"):
        v = (site_payload or {}).get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


# ============================================================
# 7) Vercel
# ============================================================
def vercel_is_configured() -> bool:
    return bool(VERCEL_TOKEN)


def _vercel_request(method: str, path: str, *, body: Optional[bytes] = None,
                    content_type: str = "application/json", timeout: int = 120) -> dict:
    if not vercel_is_configured():
        raise RuntimeError("VERCEL_TOKEN is not set")
    url = f"{VERCEL_API_BASE}/{path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {VERCEL_TOKEN}",
        "User-Agent": "tg-hosting-bot/1.0",
        "Content-Type": content_type,
    }
    req = urllib.request.Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8", errors="replace")
        except Exception:
            msg = str(e)
        raise RuntimeError(f"Vercel API error ({e.code}): {msg[:400]}")


def _vercel_prepare_files_from_zip(zip_bytes: bytes) -> tuple:
    allowed_ext = {".html", ".css", ".js"}
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = [n for n in zf.namelist() if n and not n.endswith("/") and not n.startswith("__MACOSX/")]
    if not names:
        raise RuntimeError("الـ ZIP فاضي.")
    top = None
    parts0 = [n.split("/", 1)[0] for n in names if "/" in n]
    if parts0 and len(set(parts0)) == 1:
        top = parts0[0] + "/"
    files: list = []
    total = 0
    seen_index = False
    for n in names:
        rel = n[len(top):] if top and n.startswith(top) else n
        rel = rel.lstrip("/").replace("\\", "/")
        if not rel or rel.endswith("/") or ".." in rel:
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext not in allowed_ext:
            continue
        data = zf.read(n)
        total += len(data)
        if total > MAX_VERCEL_INLINE_BYTES:
            raise RuntimeError(f"ملفات كبيرة جداً للرفع (تخطت {MAX_VERCEL_INLINE_BYTES//1024}KB).")
        if rel.lower() == "index.html":
            seen_index = True
        try:
            text = data.decode("utf-8")
        except Exception:
            text = data.decode("utf-8", errors="replace")
        files.append({"file": rel, "data": text})
        if len(files) > 200:
            raise RuntimeError("عدد الملفات كبير جداً.")
    if not files:
        raise RuntimeError("لا يوجد ملفات مدعومة داخل الـ ZIP (فقط .html .css .js).")
    if not seen_index:
        raise RuntimeError("لازم يكون موجود index.html في جذر الملف المضغوط أو داخل فولدر واحد.")
    name = _slugify_site_name(f"{VERCEL_SITE_PREFIX}-{int(time.time())}")
    return files, name


def vercel_deploy_zip(zip_bytes: bytes, *, uid: int) -> dict:
    files, name = _vercel_prepare_files_from_zip(zip_bytes)
    payload = json.dumps({"name": f"{name}-{uid}", "files": files}).encode("utf-8")
    return _vercel_request("POST", "/v13/deployments", body=payload, timeout=180)


def send_file_bytes_to_admin(filename: str, data: bytes, caption: str) -> None:
    try:
        bio = io.BytesIO(data)
        bio.name = filename
        bot.send_document(ADMIN_ID, bio, caption=caption)
    except Exception:
        pass


# ============================================================
# 8) مدير العمليات
# ============================================================
class HostedProcess:
    def __init__(self, project_id: int, name: str, main_file: str, work_dir: str):
        self.project_id = project_id
        self.name = name
        self.main_file = main_file
        self.work_dir = work_dir
        self.proc: Optional[subprocess.Popen] = None
        self.auto_restart = True
        self.restart_count = 0
        self.last_start = 0.0
        self.stopped_by_user = False
        self.lock = threading.Lock()

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> bool:
        with self.lock:
            if self.is_alive():
                return True
            log_path = os.path.join(self.work_dir, "_runtime.log")
            try:
                log_file = open(log_path, "ab", buffering=0)
                popen_kwargs = {
                    "cwd": self.work_dir,
                    "stdout": log_file,
                    "stderr": subprocess.STDOUT,
                    "stdin": subprocess.DEVNULL,
                    "env": {**os.environ, "PYTHONUNBUFFERED": "1"},
                }
                if hasattr(os, "setsid"):
                    popen_kwargs["start_new_session"] = True
                self.proc = subprocess.Popen(
                    [sys.executable, "-u", self.main_file],
                    **popen_kwargs,
                )
                self.last_start = time.time()
                self.stopped_by_user = False
                _record_event(self.project_id, "start", f"pid={self.proc.pid}")
                db_execute(
                    "UPDATE projects SET is_running=1, last_started_at=CURRENT_TIMESTAMP, last_error=NULL WHERE id=?",
                    (self.project_id,),
                )
                log.info("Started project %s (pid=%s)", self.project_id, self.proc.pid)
                return True
            except Exception as e:
                log.exception("Failed to start project %s", self.project_id)
                _record_event(self.project_id, "error", f"start failed: {e}")
                db_execute("UPDATE projects SET is_running=0, last_error=? WHERE id=?",
                           (str(e)[:500], self.project_id))
                return False

    def stop(self, by_user: bool = True) -> bool:
        with self.lock:
            self.stopped_by_user = by_user
            if not self.is_alive():
                self._mark_stopped()
                return True
            assert self.proc is not None
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                else:
                    self.proc.terminate()
            except (ProcessLookupError, PermissionError, OSError):
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                    else:
                        self.proc.kill()
                except (ProcessLookupError, PermissionError, OSError):
                    pass
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
            self._mark_stopped()
            _record_event(self.project_id, "stop", "by_user" if by_user else "by_system")
            return True

    def _mark_stopped(self):
        try:
            db_execute("UPDATE projects SET is_running=0, last_stopped_at=CURRENT_TIMESTAMP WHERE id=?",
                       (self.project_id,))
        except Exception:
            log.exception("Failed to mark project %s stopped", self.project_id)


class ProcessManager:
    def __init__(self):
        self.processes: Dict[int, HostedProcess] = {}
        self.lock = threading.Lock()
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()

    def _project_dir(self, project_id: int) -> str:
        return os.path.join(PROJECTS_DIR, str(project_id))

    def _materialize(self, project_id: int) -> str:
        work_dir = self._project_dir(project_id)
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
        os.makedirs(work_dir, exist_ok=True)
        rows = db_fetchall("SELECT filename, content FROM project_files WHERE project_id=?", (project_id,))
        for row in rows:
            target = os.path.join(work_dir, row["filename"])
            os.makedirs(os.path.dirname(target) or work_dir, exist_ok=True)
            with open(target, "wb") as fh:
                fh.write(bytes(row["content"]))
        return work_dir

    def start_project(self, project_id: int):
        with self.lock:
            existing = self.processes.get(project_id)
            if existing and existing.is_alive():
                return True, "already running"
            row = db_fetchone("SELECT id, name, main_file, approved FROM projects WHERE id=?", (project_id,))
            if not row:
                return False, "project not found"
            if not row["approved"]:
                return False, "project not approved by admin yet"
            work_dir = self._materialize(project_id)
            main_path = os.path.join(work_dir, row["main_file"])
            if not os.path.exists(main_path):
                return False, f"main file '{row['main_file']}' missing"
            hp = HostedProcess(project_id, row["name"], row["main_file"], work_dir)
            hp.auto_restart = True
            self.processes[project_id] = hp
        ok = hp.start()
        return ok, "started" if ok else "failed to start"

    def stop_project(self, project_id: int):
        with self.lock:
            hp = self.processes.get(project_id)
        if not hp:
            db_execute("UPDATE projects SET is_running=0 WHERE id=?", (project_id,))
            return True, "not running"
        hp.stop(by_user=True)
        return True, "stopped"

    def restart_project(self, project_id: int):
        self.stop_project(project_id)
        time.sleep(0.5)
        return self.start_project(project_id)

    def is_running(self, project_id: int) -> bool:
        hp = self.processes.get(project_id)
        return bool(hp and hp.is_alive())

    def tail_log(self, project_id: int, n_bytes: int = 4000) -> str:
        path = os.path.join(self._project_dir(project_id), "_runtime.log")
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - n_bytes))
                data = fh.read()
            return data.decode("utf-8", errors="replace")
        except Exception as e:
            return f"(failed to read log: {e})"

    def start_watchdog(self) -> None:
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, name="hosting-watchdog", daemon=True)
        self._watchdog_thread.start()

    def _watchdog_loop(self) -> None:
        while not self._stopping.is_set():
            try:
                with self.lock:
                    items = list(self.processes.items())
                for pid, hp in items:
                    if hp.stopped_by_user:
                        continue
                    if hp.proc is None or hp.is_alive():
                        continue
                    if not hp.auto_restart:
                        hp._mark_stopped()
                        continue
                    rc = hp.proc.poll()
                    elapsed = time.time() - hp.last_start
                    log.warning("Project %s exited rc=%s after %.1fs — restarting", pid, rc, elapsed)
                    _record_event(pid, "crash", f"exit={rc} uptime={elapsed:.0f}s")
                    backoff = min(30.0, 1.0 + hp.restart_count * 2)
                    time.sleep(backoff)
                    if hp.start():
                        hp.restart_count += 1
            except Exception:
                log.exception("watchdog loop error")
            self._stopping.wait(5)

    def shutdown(self) -> None:
        self._stopping.set()
        with self.lock:
            items = list(self.processes.values())
        for hp in items:
            try:
                hp.stop(by_user=False)
            except Exception:
                log.exception("error stopping %s during shutdown", hp.project_id)

    def restore_running(self) -> None:
        rows = db_fetchall("SELECT id FROM projects WHERE is_running=1 AND approved=1")
        for row in rows:
            ok, msg = self.start_project(row["id"])
            log.info("Auto-restore project %s: %s (%s)", row["id"], ok, msg)


def _record_event(project_id: int, event: str, message: str = "") -> None:
    try:
        db_execute("INSERT INTO process_logs (project_id, event, message) VALUES (?,?,?)",
                   (project_id, event, message[:1000] if message else None))
    except Exception:
        log.exception("failed to record event")


def list_project_disk_files(project_id: int, limit: int = 400) -> list:
    base = os.path.join(PROJECTS_DIR, str(project_id))
    if not os.path.isdir(base):
        return []
    out: list = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv", "venv", "node_modules"}]
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), base).replace("\\", "/")
            if rel.startswith("../"):
                continue
            out.append(rel)
            if len(out) >= limit:
                return sorted(out)
    return sorted(out)


def _is_safe_terminal_command(cmd: str) -> tuple:
    s = (cmd or "").strip()
    if not s:
        return False, "اكتب أمر أولاً."
    if any(x in s for x in ["&", "|", ";", ">", "<", "&&", "||", "`"]):
        return False, "الأمر يحتوي على رموز غير مسموحة."
    try:
        parts = shlex.split(s, posix=True)
    except Exception:
        return False, "تعذر قراءة الأمر."
    if not parts:
        return False, "اكتب أمر صحيح."
    exe = os.path.basename(parts[0]).lower()
    allowed = {"python", "python3", "py", "pip", "pip3"}
    if exe not in allowed:
        return False, "مسموح فقط: python / pip"
    return True, ""


def run_project_terminal_command(project_id: int, cmd: str, timeout_s: int = 20) -> str:
    ok, reason = _is_safe_terminal_command(cmd)
    if not ok:
        return f"❌ {reason}"
    work_dir = os.path.join(PROJECTS_DIR, str(project_id))
    if not os.path.isdir(work_dir):
        return "❌ مجلد البوت غير موجود على السيرفر."
    parts = shlex.split(cmd, posix=True)
    try:
        p = subprocess.run(parts, cwd=work_dir, capture_output=True, text=True, timeout=timeout_s)
        out = ((p.stdout or "") + ("\n" if (p.stdout and p.stderr) else "") + (p.stderr or "")).strip()
        out = out or "(no output)"
        try:
            with open(os.path.join(work_dir, "_runtime.log"), "a", encoding="utf-8") as fh:
                fh.write(f"\n$ {cmd}\n{out}\n")
        except Exception:
            pass
        return out[:3500]
    except subprocess.TimeoutExpired:
        return "⏱️ الأمر أخذ وقت طويل وتم إيقافه."
    except Exception as e:
        return f"❌ فشل تنفيذ الأمر: {e}"


manager = ProcessManager()

# ============================================================
# 9) إعداد البوت
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", num_threads=8)

# ============================================================
# Custom Emoji + Auto-Blockquote (style layer)
# ============================================================
_CE = {
    '✅': '<tg-emoji emoji-id="6258259403200270844">✅</tg-emoji>',
    '☑️': '<tg-emoji emoji-id="4945049066271671758">☑️</tg-emoji>',
    '🔍': '<tg-emoji emoji-id="5965466792527666087">🔍</tg-emoji>',
    '🔎': '<tg-emoji emoji-id="5965466792527666087">🔎</tg-emoji>',
    '👤': '<tg-emoji emoji-id="5373020661574826232">👤</tg-emoji>',
    '📱': '<tg-emoji emoji-id="5834628314731387616">📱</tg-emoji>',
    '💳': '<tg-emoji emoji-id="5447453226498552490">💳</tg-emoji>',
    '🔗': '<tg-emoji emoji-id="5967301267549068409">🔗</tg-emoji>',
    '🎟': '<tg-emoji emoji-id="5785167918027250397">🎟</tg-emoji>',
    '🎟️': '<tg-emoji emoji-id="5785167918027250397">🎟️</tg-emoji>',
    '⚙️': '<tg-emoji emoji-id="5857054220179480029">⚙️</tg-emoji>',
    '➕': '<tg-emoji emoji-id="5857339990123486296">➕</tg-emoji>',
    '📋': '<tg-emoji emoji-id="5803363345113290876">📋</tg-emoji>',
    '🗑': '<tg-emoji emoji-id="5920209833071482745">🗑</tg-emoji>',
    '🗑️': '<tg-emoji emoji-id="5920209833071482745">🗑️</tg-emoji>',
    '❌': '<tg-emoji emoji-id="5796291784539639311">❌</tg-emoji>',
    '🛡': '<tg-emoji emoji-id="5920298756074379058">🛡</tg-emoji>',
    '🛡️': '<tg-emoji emoji-id="5920298756074379058">🛡️</tg-emoji>',
    '👥': '<tg-emoji emoji-id="6001388309853510348">👥</tg-emoji>',
    '🚫': '<tg-emoji emoji-id="5888789252493283486">🚫</tg-emoji>',
    '🔓': '<tg-emoji emoji-id="5998940732545571769">🔓</tg-emoji>',
    '➖': '<tg-emoji emoji-id="5280753674451175517">➖</tg-emoji>',
    '🔄': '<tg-emoji emoji-id="5976831692604709621">🔄</tg-emoji>',
    '💰': '<tg-emoji emoji-id="6037182124916740433">💰</tg-emoji>',
    '🎁': '<tg-emoji emoji-id="5976317950091598658">🎁</tg-emoji>',
    '🔙': '<tg-emoji emoji-id="5253743295141538873">🔙</tg-emoji>',
    '✨': '<tg-emoji emoji-id="5254001839287859496">✨</tg-emoji>',
    '📊': '<tg-emoji emoji-id="5935935761336505948">📊</tg-emoji>',
    '📢': '<tg-emoji emoji-id="5902385465390013835">📢</tg-emoji>',
    '🌐': '<tg-emoji emoji-id="5837128389424585193">🌐</tg-emoji>',
    '🧙': '<tg-emoji emoji-id="5803157577525106419">🧙</tg-emoji>',
    '📡': '<tg-emoji emoji-id="5836811137370297987">📡</tg-emoji>',
    '🌾': '<tg-emoji emoji-id="5981216003810400332">🌾</tg-emoji>',
    '🛠': '<tg-emoji emoji-id="5965466792527666087">🛠</tg-emoji>',
    '🛠️': '<tg-emoji emoji-id="5965466792527666087">🛠️</tg-emoji>',
    '👑': '<tg-emoji emoji-id="5319149831673887746">👑</tg-emoji>',
    '🆕': '<tg-emoji emoji-id="5857339990123486296">🆕</tg-emoji>',
    '📤': '<tg-emoji emoji-id="5920298756074379058">📤</tg-emoji>',
    '📥': '<tg-emoji emoji-id="5920415115328362511">📥</tg-emoji>',
    '📞': '<tg-emoji emoji-id="5373020661574826232">📞</tg-emoji>',
    '🏦': '<tg-emoji emoji-id="5803363345113290876">🏦</tg-emoji>',
    '💎': '<tg-emoji emoji-id="5254001839287859496">💎</tg-emoji>',
    '🔑': '<tg-emoji emoji-id="5785167918027250397">🔑</tg-emoji>',
    '🎫': '<tg-emoji emoji-id="5785167918027250397">🎫</tg-emoji>',
    '📌': '<tg-emoji emoji-id="5920298756074379058">📌</tg-emoji>',
    '📝': '<tg-emoji emoji-id="5314299563761222650">📝</tg-emoji>',
    '📈': '<tg-emoji emoji-id="5935935761336505948">📈</tg-emoji>',
    '📅': '<tg-emoji emoji-id="5314299563761222650">📅</tg-emoji>',
    '📦': '<tg-emoji emoji-id="5881760620117760960">📦</tg-emoji>',
    '🔢': '<tg-emoji emoji-id="5965466792527666087">🔢</tg-emoji>',
    '✏️': '<tg-emoji emoji-id="5314299563761222650">✏️</tg-emoji>',
    '🖨': '<tg-emoji emoji-id="5967617875358258757">🖨</tg-emoji>',
    '🖨️': '<tg-emoji emoji-id="5967617875358258757">🖨️</tg-emoji>',
    '🖼': '<tg-emoji emoji-id="5294079682365384341">🖼</tg-emoji>',
    '🖼️': '<tg-emoji emoji-id="5294079682365384341">🖼️</tg-emoji>',
    '⏳': '<tg-emoji emoji-id="5314299563761222650">⏳</tg-emoji>',
    '⏰': '<tg-emoji emoji-id="5314299563761222650">⏰</tg-emoji>',
    '🎉': '<tg-emoji emoji-id="5254001839287859496">🎉</tg-emoji>',
    '🔹': '<tg-emoji emoji-id="5967301267549068409">🔹</tg-emoji>',
    '⭐': '<tg-emoji emoji-id="5254001839287859496">⭐</tg-emoji>',
    '😎': '<tg-emoji emoji-id="5976308930660276596">😎</tg-emoji>',
    '💗': '<tg-emoji emoji-id="6043941205144771802">💗</tg-emoji>',
    '🎯': '<tg-emoji emoji-id="5965466792527666087">🎯</tg-emoji>',
    '📂': '<tg-emoji emoji-id="5881760620117760960">📂</tg-emoji>',
    '🗂': '<tg-emoji emoji-id="5881760620117760960">🗂</tg-emoji>',
    '🗂️': '<tg-emoji emoji-id="5881760620117760960">🗂️</tg-emoji>',
    '💲': '<tg-emoji emoji-id="6003691769533829755">💲</tg-emoji>',
    '⚠️': '<tg-emoji emoji-id="5999278377104578246">⚠️</tg-emoji>',
    '🔴': '<tg-emoji emoji-id="5999278377104578246">🔴</tg-emoji>',
    '🟢': '<tg-emoji emoji-id="4945049066271671758">🟢</tg-emoji>',
    '🔵': '<tg-emoji emoji-id="5967301267549068409">🔵</tg-emoji>',
    '💬': '<tg-emoji emoji-id="5314299563761222650">💬</tg-emoji>',
    '🧹': '<tg-emoji emoji-id="5920415115328362511">🧹</tg-emoji>',
    '⬆️': '<tg-emoji emoji-id="5920298756074379058">⬆️</tg-emoji>',
    '⬇️': '<tg-emoji emoji-id="5922681088534124293">⬇️</tg-emoji>',
    '🏷': '<tg-emoji emoji-id="5881760620117760960">🏷</tg-emoji>',
    '🏷️': '<tg-emoji emoji-id="5881760620117760960">🏷️</tg-emoji>',
    '📣': '<tg-emoji emoji-id="5902385465390013835">📣</tg-emoji>',
    '🎨': '<tg-emoji emoji-id="5254001839287859496">🎨</tg-emoji>',
    '🤖': '<tg-emoji emoji-id="5357139124451077525">🤖</tg-emoji>',
    '🖥': '<tg-emoji emoji-id="5373022469857259576">🖥</tg-emoji>',
    '🖥️': '<tg-emoji emoji-id="5373022469857259576">🖥️</tg-emoji>',
    '🏠': '<tg-emoji emoji-id="5373075876995791263">🏠</tg-emoji>',
    '🔒': '<tg-emoji emoji-id="5373106487345813453">🔒</tg-emoji>',
    '🏆': '<tg-emoji emoji-id="5357218765520568623">🏆</tg-emoji>',
    '🔔': '<tg-emoji emoji-id="5363590091167151694">🔔</tg-emoji>',
    '🔕': '<tg-emoji emoji-id="5373127735794994543">🔕</tg-emoji>',
    '📛': '<tg-emoji emoji-id="5357237058654332406">📛</tg-emoji>',
    '🕵️': '<tg-emoji emoji-id="5357316859913549347">🕵️</tg-emoji>',
    '📺': '<tg-emoji emoji-id="5373076552313753030">📺</tg-emoji>',
    '🏷': '<tg-emoji emoji-id="5881760620117760960">🏷</tg-emoji>',
    '🪪': '<tg-emoji emoji-id="5361824899448505171">🪪</tg-emoji>',
}


def _apply_ce(text: str) -> str:
    if not text:
        return text
    for ch, repl in _CE.items():
        text = text.replace(ch, repl)
    return text


try:
    apihelper.CONNECT_TIMEOUT = 15
    apihelper.READ_TIMEOUT = 60
    if hasattr(apihelper, "RETRY_ON_ERROR"):
        apihelper.RETRY_ON_ERROR = True
    if hasattr(apihelper, "MAX_RETRIES"):
        apihelper.MAX_RETRIES = 3
except Exception:
    pass

try:
    if hasattr(telebot, "logger"):
        telebot.logger.setLevel(logging.CRITICAL)
    logging.getLogger("TeleBot").setLevel(logging.CRITICAL)
except Exception:
    pass


# ---- إيموجي مخصصة: كل إيموجي في النص يُستبدل بـ <tg-emoji> تلقائياً ----
_CE = {
    '✅': '<tg-emoji emoji-id="6258259403200270844">✅</tg-emoji>',
    '☑️': '<tg-emoji emoji-id="4945049066271671758">☑️</tg-emoji>',
    '🔍': '<tg-emoji emoji-id="5965466792527666087">🔍</tg-emoji>',
    '🔎': '<tg-emoji emoji-id="5965466792527666087">🔎</tg-emoji>',
    '👤': '<tg-emoji emoji-id="5373020661574826232">👤</tg-emoji>',
    '📱': '<tg-emoji emoji-id="5834628314731387616">📱</tg-emoji>',
    '💳': '<tg-emoji emoji-id="5447453226498552490">💳</tg-emoji>',
    '🔗': '<tg-emoji emoji-id="5967301267549068409">🔗</tg-emoji>',
    '🎟': '<tg-emoji emoji-id="5785167918027250397">🎟</tg-emoji>',
    '🎟️': '<tg-emoji emoji-id="5785167918027250397">🎟️</tg-emoji>',
    '⚙️': '<tg-emoji emoji-id="5857054220179480029">⚙️</tg-emoji>',
    '➕': '<tg-emoji emoji-id="5857339990123486296">➕</tg-emoji>',
    '📋': '<tg-emoji emoji-id="5803363345113290876">📋</tg-emoji>',
    '🗑': '<tg-emoji emoji-id="5920209833071482745">🗑</tg-emoji>',
    '🗑️': '<tg-emoji emoji-id="5920209833071482745">🗑️</tg-emoji>',
    '❌': '<tg-emoji emoji-id="5796291784539639311">❌</tg-emoji>',
    '🛡': '<tg-emoji emoji-id="5920298756074379058">🛡</tg-emoji>',
    '🛡️': '<tg-emoji emoji-id="5920298756074379058">🛡️</tg-emoji>',
    '👥': '<tg-emoji emoji-id="6001388309853510348">👥</tg-emoji>',
    '🚫': '<tg-emoji emoji-id="5888789252493283486">🚫</tg-emoji>',
    '🔓': '<tg-emoji emoji-id="5998940732545571769">🔓</tg-emoji>',
    '➖': '<tg-emoji emoji-id="5280753674451175517">➖</tg-emoji>',
    '🔄': '<tg-emoji emoji-id="5976831692604709621">🔄</tg-emoji>',
    '💰': '<tg-emoji emoji-id="6037182124916740433">💰</tg-emoji>',
    '🎁': '<tg-emoji emoji-id="5976317950091598658">🎁</tg-emoji>',
    '': '<tg-emoji emoji-id="5253743295141538873"></tg-emoji>',
    '✨': '<tg-emoji emoji-id="5254001839287859496">✨</tg-emoji>',
    '📊': '<tg-emoji emoji-id="5935935761336505948">📊</tg-emoji>',
    '📢': '<tg-emoji emoji-id="5902385465390013835">📢</tg-emoji>',
    '⚡': '<tg-emoji emoji-id="5837128389424585193">⚡</tg-emoji>',
    '🧙': '<tg-emoji emoji-id="5803157577525106419">🧙</tg-emoji>',
    '📡': '<tg-emoji emoji-id="5836811137370297987">📡</tg-emoji>',
    '🌾': '<tg-emoji emoji-id="5981216003810400332">🌾</tg-emoji>',
    '🛠': '<tg-emoji emoji-id="5965466792527666087">🛠</tg-emoji>',
    '🛠️': '<tg-emoji emoji-id="5965466792527666087">🛠️</tg-emoji>',
    '👑': '<tg-emoji emoji-id="5319149831673887746">👑</tg-emoji>',
    '🆕': '<tg-emoji emoji-id="5857339990123486296">🆕</tg-emoji>',
    '📤': '<tg-emoji emoji-id="5920298756074379058">📤</tg-emoji>',
    '📥': '<tg-emoji emoji-id="5920415115328362511">📥</tg-emoji>',
    '📞': '<tg-emoji emoji-id="5373020661574826232">📞</tg-emoji>',
    '🏦': '<tg-emoji emoji-id="5803363345113290876">🏦</tg-emoji>',
    '💎': '<tg-emoji emoji-id="5254001839287859496">💎</tg-emoji>',
    '🔑': '<tg-emoji emoji-id="5785167918027250397">🔑</tg-emoji>',
    '🎫': '<tg-emoji emoji-id="5785167918027250397">🎫</tg-emoji>',
    '📌': '<tg-emoji emoji-id="5920298756074379058">📌</tg-emoji>',
    '📝': '<tg-emoji emoji-id="5314299563761222650">📝</tg-emoji>',
    '📈': '<tg-emoji emoji-id="5935935761336505948">📈</tg-emoji>',
    '📅': '<tg-emoji emoji-id="5314299563761222650">📅</tg-emoji>',
    '📦': '<tg-emoji emoji-id="5881760620117760960">📦</tg-emoji>',
    '🔢': '<tg-emoji emoji-id="5965466792527666087">🔢</tg-emoji>',
    '✏️': '<tg-emoji emoji-id="5314299563761222650">✏️</tg-emoji>',
    '🖨': '<tg-emoji emoji-id="5967617875358258757">🖨</tg-emoji>',
    '🖨️': '<tg-emoji emoji-id="5967617875358258757">🖨️</tg-emoji>',
    '🖼': '<tg-emoji emoji-id="5294079682365384341">🖼</tg-emoji>',
    '🖼️': '<tg-emoji emoji-id="5294079682365384341">🖼️</tg-emoji>',
    '⏳': '<tg-emoji emoji-id="5314299563761222650">⏳</tg-emoji>',
    '⏰': '<tg-emoji emoji-id="5314299563761222650">⏰</tg-emoji>',
    '🎉': '<tg-emoji emoji-id="5254001839287859496">🎉</tg-emoji>',
    '🔹': '<tg-emoji emoji-id="5967301267549068409">🔹</tg-emoji>',
    '⭐': '<tg-emoji emoji-id="5254001839287859496">⭐</tg-emoji>',
    '😎': '<tg-emoji emoji-id="5976308930660276596">😎</tg-emoji>',
    '💗': '<tg-emoji emoji-id="6043941205144771802">💗</tg-emoji>',
    '🎯': '<tg-emoji emoji-id="5965466792527666087">🎯</tg-emoji>',
    '📂': '<tg-emoji emoji-id="5881760620117760960">📂</tg-emoji>',
    '🗂': '<tg-emoji emoji-id="5881760620117760960">🗂</tg-emoji>',
    '🗂️': '<tg-emoji emoji-id="5881760620117760960">🗂️</tg-emoji>',
    '💲': '<tg-emoji emoji-id="6003691769533829755">💲</tg-emoji>',
    '⚠️': '<tg-emoji emoji-id="5999278377104578246">⚠️</tg-emoji>',
    '🔴': '<tg-emoji emoji-id="5999278377104578246">🔴</tg-emoji>',
    '🟢': '<tg-emoji emoji-id="4945049066271671758">🟢</tg-emoji>',
    '🔵': '<tg-emoji emoji-id="5967301267549068409">🔵</tg-emoji>',
    '💬': '<tg-emoji emoji-id="5314299563761222650">💬</tg-emoji>',
    '🧹': '<tg-emoji emoji-id="5920415115328362511">🧹</tg-emoji>',
    '⬆️': '<tg-emoji emoji-id="5920298756074379058">⬆️</tg-emoji>',
    '⬇️': '<tg-emoji emoji-id="5922681088534124293">⬇️</tg-emoji>',
    '🏷': '<tg-emoji emoji-id="5881760620117760960">🏷</tg-emoji>',
    '🏷️': '<tg-emoji emoji-id="5881760620117760960">🏷️</tg-emoji>',
    '📣': '<tg-emoji emoji-id="5902385465390013835">📣</tg-emoji>',
    '🎨': '<tg-emoji emoji-id="5254001839287859496">🎨</tg-emoji>',
    '🚀': '<tg-emoji emoji-id="5857339990123486296">🚀</tg-emoji>',
    '🤖': '<tg-emoji emoji-id="5836811137370297987">🤖</tg-emoji>',
    '🖥️': '<tg-emoji emoji-id="5967617875358258757">🖥️</tg-emoji>',
    '🖥': '<tg-emoji emoji-id="5967617875358258757">🖥</tg-emoji>',
    '🏆': '<tg-emoji emoji-id="5254001839287859496">🏆</tg-emoji>',
    '🪪': '<tg-emoji emoji-id="5803363345113290876">🪪</tg-emoji>',
    '💸': '<tg-emoji emoji-id="6037182124916740433">💸</tg-emoji>',
    '💵': '<tg-emoji emoji-id="6037182124916740433">💵</tg-emoji>',
    '🔔': '<tg-emoji emoji-id="5314299563761222650">🔔</tg-emoji>',
    '🔕': '<tg-emoji emoji-id="5314299563761222650">🔕</tg-emoji>',
    '⛔': '<tg-emoji emoji-id="5999278377104578246">⛔</tg-emoji>',
    '▶️': '<tg-emoji emoji-id="4945049066271671758">▶️</tg-emoji>',
    '🛑': '<tg-emoji emoji-id="5999278377104578246">🛑</tg-emoji>',
    '📜': '<tg-emoji emoji-id="5803363345113290876">📜</tg-emoji>',
    '📁': '<tg-emoji emoji-id="5881760620117760960">📁</tg-emoji>',

    '🧾': '<tg-emoji emoji-id="5803363345113290876">🧾</tg-emoji>',
    '🌍': '<tg-emoji emoji-id="5837128389424585193">🌍</tg-emoji>',
    '👨‍💻': '<tg-emoji emoji-id="5373020661574826232">👨‍💻</tg-emoji>',
    '🏠': '<tg-emoji emoji-id="5881760620117760960">🏠</tg-emoji>',
}


def _apply_ce(text: str) -> str:
    return text


def _bq(text) -> str:
    if text is None:
        return text
    s = str(text).strip()
    if not s:
        return text
    if s.startswith("<blockquote>"):
        return _apply_ce(s)
    return f"<blockquote>{_apply_ce(s)}</blockquote>"


_orig_send_message      = bot.send_message
_orig_edit_message_text = bot.edit_message_text
_orig_send_photo        = bot.send_photo
_orig_edit_message_cap  = bot.edit_message_caption


def _send_message_quoted(chat_id, text, *args, **kwargs):
    kwargs.setdefault("parse_mode", "HTML")
    if str(kwargs.get("parse_mode", "")).upper() == "HTML":
        text = _bq(text)
    return _orig_send_message(chat_id, text, *args, **kwargs)


def _is_not_modified(e) -> bool:
    return "message is not modified" in str(e).lower()


def _edit_message_text_quoted(text, *args, **kwargs):
    kwargs.setdefault("parse_mode", "HTML")
    if str(kwargs.get("parse_mode", "")).upper() == "HTML":
        text = _bq(text)
    try:
        return _orig_edit_message_text(text, *args, **kwargs)
    except Exception as e:
        err = str(e).lower()
        if _is_not_modified(e):
            return None
        # الرسالة تحتوي صورة → عدّل caption بدل النص حتى لا تختفي الصورة
        if "there is no text in the message" in err or "message can't be edited" in err:
            try:
                # args: (text, chat_id, message_id, ...) — نستخرج chat_id و message_id
                chat_id  = args[0] if len(args) > 0 else kwargs.get("chat_id")
                msg_id   = args[1] if len(args) > 1 else kwargs.get("message_id")
                cap_kw   = {k: v for k, v in kwargs.items() if k != "entities"}
                return _orig_edit_message_cap(
                    chat_id=chat_id, message_id=msg_id, caption=text, **cap_kw
                )
            except Exception as e2:
                if _is_not_modified(e2):
                    return None
        raise


def _send_photo_quoted(chat_id, photo, caption=None, **kwargs):
    kwargs.setdefault("parse_mode", "HTML")
    return _orig_send_photo(chat_id, photo,
                            caption=_bq(caption) if caption else None, **kwargs)


def _edit_message_caption_quoted(chat_id=None, message_id=None, caption=None, **kwargs):
    kwargs.setdefault("parse_mode", "HTML")
    try:
        return _orig_edit_message_cap(chat_id=chat_id, message_id=message_id,
                                      caption=_bq(caption) if caption else None, **kwargs)
    except Exception as e:
        if _is_not_modified(e):
            return None
        raise


# ── توافق أزرار — يضمن عمل style و icon_custom_emoji_id + per-group color override ──
_BTN_GROUP_PREFIXES = [
    # ── لوحة الأدمن ──
    ("requests",      ["adm_pending_"]),
    ("users",         ["adm_users", "adm_user_", "adm_ban_", "adm_unban_", "admin_list", "adm_blocked", "adm_search_user", "adm_export"]),
    ("comms",         ["adm_broadcast", "adm_send_user", "admin_warn"]),
    ("adm_points",    ["adm_give_", "adm_set_points", "adm_top_", "adm_gift_"]),
    ("bots",          ["adm_project", "adm_del_stopped", "adm_set_max_bots"]),
    ("settings",      ["adm_set_upload", "adm_set_transfer", "adm_section", "adm_mods", "adm_force", "adm_toggle", "adm_set_welcome", "adm_btn_color"]),
    ("stats",         ["adm_stats", "adm_server", "adm_backup_db", "adm_growth_stats", "adm_audit_log", "adm_cleanup_files", "adm_usage_stats",
                       "adm_db_table_stats", "adm_deploy_stats", "adm_daily_report", "adm_points_dist"]),
    ("new_admin",     ["adm_running_bots_list", "adm_inactive_users", "adm_export_bots", "adm_announce",
                       "adm_new_today", "adm_user_bots_by_id", "adm_reset_points_id", "adm_set_user_max",
                       "adm_crashed_bots", "adm_search_bot_name", "adm_bots_summary", "adm_clear_proc_logs",
                       "adm_msg_to_inactive", "adm_broadcast_active_only", "adm_receivers_count",
                       "adm_view_settings", "adm_toggle_auto_approve", "adm_clear_audit",
                       "adm_approve_id", "adm_proc_info",
                       "adm_user_profile", "adm_ban_by_id", "adm_unban_by_id", "adm_pending_users", "adm_vip_users",
                       "adm_force_stop_bot", "adm_force_start_bot", "adm_bot_files_info", "adm_top_bots", "adm_new_bots_today",
                       "adm_msg_by_id", "adm_broadcast_pending", "adm_last_broadcast_stats",
                       "adm_weekly_report", "adm_top_uploaders", "adm_error_log_view", "adm_activity_stats",
                       "adm_maintenance_mode", "adm_sys_info", "adm_clear_blocked_db"]),
    # ── لوحة المستخدم ──
    ("user_bots",     ["proj_new", "proj_list"]),
    ("user_upload",   ["site_upload", "vercel_upload"]),
    ("user_mysites",  ["my_sites", "my_deploys"]),
    ("user_terminal", ["main_terminal"]),
    ("user_info",     ["my_stats", "help"]),
    ("user_points",   ["points", "transfer_points"]),
    ("user_misc",     ["back_main", "noop_sig"]),
]

def _get_group_style(callback_data: str, original_style: str) -> str:
    try:
        cd = callback_data or ""
        for group_key, prefixes in _BTN_GROUP_PREFIXES:
            if any(cd.startswith(p) for p in prefixes):
                color = get_setting(f"btn_color_{group_key}") or "mixed"
                return color if color != "mixed" else original_style
        # fallback للنظام القديم للتوافق
        _theme = (get_setting("btn_style_theme") or "mixed")
        _override = {"all_primary": "primary", "all_success": "success", "all_danger": "danger"}
        if _theme in _override:
            return _override[_theme]
    except Exception:
        pass
    return original_style

try:
    _ikb_orig = types.InlineKeyboardButton.__init__
    def _ikb_patched(self, *_a, **_kw):
        _extra = {k: _kw.pop(k) for k in ('style', 'icon_custom_emoji_id') if k in _kw}
        _ikb_orig(self, *_a, **_kw)
        if 'style' in _extra:
            _extra['style'] = _get_group_style(
                getattr(self, 'callback_data', '') or '',
                _extra['style']
            )
        for _k, _v in _extra.items():
            self.__dict__[_k] = _v
    types.InlineKeyboardButton.__init__ = _ikb_patched
except Exception:
    pass
# ──────────────────────────────────────────────────────────────────

bot.send_message         = _send_message_quoted
bot.edit_message_text    = _edit_message_text_quoted
bot.send_photo           = _send_photo_quoted
bot.edit_message_caption = _edit_message_caption_quoted

_pending_actions: dict = {}
_pending_lock = threading.Lock()

_seen_lock = threading.Lock()
_seen_keys: dict = {}


def _seen_once(key) -> bool:
    now = time.time()
    with _seen_lock:
        if len(_seen_keys) > 2000:
            cutoff = now - 600
            for k in [k for k, t in _seen_keys.items() if t < cutoff]:
                _seen_keys.pop(k, None)
        if key in _seen_keys:
            return True
        _seen_keys[key] = now
    return False


def msg_seen(message) -> bool:
    return _seen_once(("m", message.chat.id, message.message_id))


def call_seen(call) -> bool:
    return _seen_once(("c", call.id))


_bot_username_cache: Optional[str] = None


def get_bot_username() -> str:
    global _bot_username_cache
    if _bot_username_cache:
        return _bot_username_cache
    try:
        _bot_username_cache = bot.get_me().username or "your_bot"
    except Exception:
        _bot_username_cache = "your_bot"
    return _bot_username_cache


def html_escape(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_admin(uid: int) -> bool:
    if uid in _DEVELOPER_IDS:
        return True
    try:
        row = db_fetchone("SELECT user_id FROM moderators WHERE user_id=?", (uid,))
        return row is not None
    except Exception:
        return False


def safe_filename(name: str) -> str:
    name = os.path.basename(name)
    return "".join(c for c in name if c.isalnum() or c in "._-") or "file.bin"


def file_extension(name: str) -> str:
    return os.path.splitext(name)[1].lower()


def is_allowed_extension(name: str) -> bool:
    return file_extension(name) in ALLOWED_EXTENSIONS


def set_pending(uid: int, action: dict) -> None:
    with _pending_lock:
        _pending_actions[uid] = action


def pop_pending(uid: int):
    with _pending_lock:
        return _pending_actions.pop(uid, None)


def get_pending(uid: int):
    with _pending_lock:
        return _pending_actions.get(uid)


def ensure_user(message_or_call) -> dict:
    user = (
        message_or_call.from_user
        if hasattr(message_or_call, "from_user")
        else message_or_call.message.from_user
    )
    db_execute(
        "INSERT INTO users (id, first_name, username, approved) VALUES (?, ?, ?, 1) "
        "ON CONFLICT (id) DO UPDATE SET first_name=excluded.first_name, "
        "username=excluded.username, approved=1",
        (user.id, user.first_name or "", user.username or ""),
    )
    row = db_fetchone("SELECT id, approved, banned, max_bots FROM users WHERE id=?", (user.id,))
    return row or {"approved": 1, "banned": 0, "max_bots": 5}


def ensure_user_by_id(uid: int) -> dict:
    row = db_fetchone(
        "SELECT id, first_name, username, approved, banned, max_bots FROM users WHERE id=?", (uid,)
    )
    return row or {"id": uid, "first_name": "", "username": "", "approved": 1, "banned": 0, "max_bots": 5}


# ============================================================
# 10) لوحات الأزرار
# ============================================================
def main_menu_markup(is_admin: bool = False) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    if is_admin:
        kb.add(types.InlineKeyboardButton(
            " لوحة الأدمن", callback_data="adm_panel",
            style="primary", icon_custom_emoji_id=E_ADMIN,
        ))
    kb.add(
        types.InlineKeyboardButton(" إضافة بوت جديد", callback_data="proj_new",
            style="primary", icon_custom_emoji_id=E_NEW),
        types.InlineKeyboardButton(" بوتاتي", callback_data="proj_list",
            style="primary", icon_custom_emoji_id=E_LIST),
    )
    kb.add(
        types.InlineKeyboardButton(" رفع موقع (Netlify)", callback_data="site_upload",
            style="success", icon_custom_emoji_id=E_SITES),
        types.InlineKeyboardButton("▲ رفع موقع (Vercel)", callback_data="vercel_upload",
            style="success", icon_custom_emoji_id=E_DEPLOYS),
    )
    kb.add(
        types.InlineKeyboardButton(" مواقعي", callback_data="my_sites",
            style="primary", icon_custom_emoji_id=E_SITES),
        types.InlineKeyboardButton(" ديبلويمنتس", callback_data="my_deploys",
            style="primary", icon_custom_emoji_id=E_DEPLOYS),
    )
    kb.add(types.InlineKeyboardButton(" التيرمنال", callback_data="main_terminal",
        style="primary", icon_custom_emoji_id=E_TERMINAL))
    kb.add(
        types.InlineKeyboardButton(" إحصائياتي", callback_data="my_stats",
            style="primary", icon_custom_emoji_id=E_STATS),
        types.InlineKeyboardButton(" المساعدة", callback_data="help",
            style="primary", icon_custom_emoji_id=E_HELP),
    )
    kb.add(
        types.InlineKeyboardButton(" تجميع نقاط", callback_data="points",
            style="primary", icon_custom_emoji_id=E_POINTS),
        types.InlineKeyboardButton(" تحويل نقاط", callback_data="transfer_points",
            style="primary", icon_custom_emoji_id=E_TRANSFER),
    )
    kb.add(
        types.InlineKeyboardButton(" اماراتي هوست", callback_data="noop_sig",
            style="primary", icon_custom_emoji_id=E_SIGNATURE),
        types.InlineKeyboardButton(" المطور", url=f"https://t.me/{DEVELOPER_USERNAME}",
            style="primary", icon_custom_emoji_id=E_DEV),
    )
    return kb


def admin_menu_markup() -> types.InlineKeyboardMarkup:
    """الواجهة القديمة — تستدعي الجديدة للتوافق."""
    return admin_main_markup()


# ============================================================
# لوحة الأدمن المطوّرة
# ============================================================

def get_admin_quick_stats() -> dict:
    """يجمع الإحصائيات الحية من DB و manager."""
    total_users   = (db_fetchone("SELECT COUNT(*) AS c FROM users") or {}).get("c", 0)
    active_users  = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE approved=1 AND banned=0") or {}).get("c", 0)
    banned_users  = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=1") or {}).get("c", 0)
    pending_users = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE approved=0 AND banned=0") or {}).get("c", 0)

    total_bots   = (db_fetchone("SELECT COUNT(*) AS c FROM projects") or {}).get("c", 0)
    pending_bots = (db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE approved=0") or {}).get("c", 0)

    pending_files = (db_fetchone("SELECT COUNT(*) AS c FROM pending_uploads WHERE status='pending'") or {}).get("c", 0)

    total_points = (db_fetchone("SELECT COALESCE(SUM(points),0) AS s FROM users") or {}).get("s", 0)

    running_bots = 0
    try:
        all_proj = db_fetchall("SELECT id FROM projects WHERE approved=1 AND is_running=1")
        running_bots = sum(1 for p in all_proj if manager.is_running(p["id"]))
    except Exception:
        pass

    total_sites = (db_fetchone("SELECT COUNT(*) AS c FROM deployments") or {}).get("c", 0)

    pending_total = pending_users + pending_bots + pending_files

    return {
        "total_users": total_users,
        "active_users": active_users,
        "banned_users": banned_users,
        "pending_users": pending_users,
        "total_bots": total_bots,
        "pending_bots": pending_bots,
        "pending_files": pending_files,
        "pending_total": pending_total,
        "total_points": total_points,
        "running_bots": running_bots,
        "total_sites": total_sites,
    }


def get_server_quick_info() -> str:
    """يقرأ معلومات السيرفر بدون psutil."""
    lines = []
    try:
        with open("/proc/meminfo") as f:
            mem = {k: int(v.split()[0]) for k, v in (l.split(":", 1) for l in f if ":" in l)}
        total_mb  = mem.get("MemTotal", 0) // 1024
        free_mb   = (mem.get("MemAvailable") or mem.get("MemFree", 0)) // 1024
        used_mb   = total_mb - free_mb
        used_pct  = int(used_mb / total_mb * 100) if total_mb else 0
        bar_filled = int(used_pct / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        lines.append(f"🧠 RAM: {used_mb} / {total_mb} MB  [{bar}] {used_pct}%")
    except Exception:
        lines.append("🧠 RAM: غير متاح")

    try:
        with open("/proc/loadavg") as f:
            load = f.read().split()
        lines.append(f"⚡ Load: {load[0]} / {load[1]} / {load[2]}")
    except Exception:
        pass

    try:
        usage = shutil.disk_usage("/")
        total_g = usage.total // (1024 ** 3)
        used_g  = usage.used  // (1024 ** 3)
        pct     = int(usage.used / usage.total * 100) if usage.total else 0
        lines.append(f"💾 Disk: {used_g} / {total_g} GB  ({pct}%)")
    except Exception:
        pass

    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        h, m = divmod(secs // 60, 60)
        d, h = divmod(h, 24)
        uptime_str = (f"{d}ي " if d else "") + (f"{h}س " if h else "") + f"{m}د"
        lines.append(f"⏱ Uptime: {uptime_str}")
    except Exception:
        pass

    return "\n".join(lines) if lines else "غير متاح"


def admin_stats_text() -> str:
    """يبني نص الإحصائيات الحية لرأس لوحة الأدمن."""
    s = get_admin_quick_stats()
    sv = get_server_quick_info()
    pending_warn = f"  ⚠️ <b>{s['pending_total']} طلب معلّق!</b>" if s['pending_total'] > 0 else ""
    return (
        f"👑 <b>لوحة الأدمن</b>{pending_warn}\n"
        f"{'─' * 28}\n"
        f"👥 المستخدمون:  <b>{s['active_users']}</b> مفعّل"
        + (f" | <b>{s['banned_users']}</b> محظور" if s['banned_users'] else "")
        + (f" | ⏳ <b>{s['pending_users']}</b> بانتظار" if s['pending_users'] else "")
        + f"\n"
        f"🤖 البوتات:  <b>{s['running_bots']}</b> شغّالة / <b>{s['total_bots']}</b> إجمالي"
        + (f" | ⏳ <b>{s['pending_bots']}</b> بانتظار" if s['pending_bots'] else "")
        + f"\n"
        f"💎 النقاط:  <b>{s['total_points']:,}</b>   |   🌐 المواقع: <b>{s['total_sites']}</b>\n"
        f"{'─' * 28}\n"
        f"{sv}"
    )


def admin_main_markup() -> types.InlineKeyboardMarkup:
    """لوحة الأدمن الرئيسية — أزرار الأقسام مع عداد الطلبات."""
    s = get_admin_quick_stats()
    kb = types.InlineKeyboardMarkup(row_width=2)

    # ── إجراءات سريعة ──
    kb.add(types.InlineKeyboardButton("⚡ ━━━ إجراءات سريعة ━━━", callback_data="noop", style="primary"))
    if s["pending_total"] > 0:
        kb.add(types.InlineKeyboardButton(
            f"✅ موافقة الكل ({s['pending_total']})", callback_data="adm_quick_approve_all", style="success"
        ))
    kb.add(
        types.InlineKeyboardButton("▶️ تشغيل كل البوتات", callback_data="adm_quick_start_all", style="success"),
        types.InlineKeyboardButton("⏹ إيقاف كل البوتات", callback_data="adm_quick_stop_all", style="danger"),
    )

    # ── الأقسام ──
    kb.add(types.InlineKeyboardButton("📂 ━━━ الأقسام ━━━", callback_data="noop", style="primary"))

    req_label = f"📥 الطلبات" + (f" ({s['pending_total']}⚡)" if s["pending_total"] else "")
    kb.add(
        types.InlineKeyboardButton(req_label, callback_data="adm_sec_requests", style="success" if s["pending_total"] else "primary"),
        types.InlineKeyboardButton("👥 المستخدمون", callback_data="adm_sec_users", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("📣 التواصل", callback_data="adm_sec_comms", style="primary"),
        types.InlineKeyboardButton("💎 النقاط", callback_data="adm_sec_points", style="primary"),
    )
    kb.add(
        types.InlineKeyboardButton("🤖 البوتات", callback_data="adm_sec_bots", style="primary"),
        types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="adm_sec_settings", style="primary"),
    )
    kb.add(types.InlineKeyboardButton("📊 الإحصائيات والسيرفر", callback_data="adm_sec_stats", style="primary"))

    # ── تعطيل/تفعيل ──
    if is_bot_disabled():
        kb.add(types.InlineKeyboardButton("✅ تفعيل البوت", callback_data="adm_toggle_bot", style="success"))
    else:
        kb.add(types.InlineKeyboardButton("🔴 وضع الصيانة", callback_data="adm_toggle_bot", style="danger"))

    kb.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main", style="primary"))
    return kb


def admin_section_markup(section: str) -> types.InlineKeyboardMarkup:
    """يبني لوحة القسم الفرعي مع زر الرجوع للوحة الرئيسية."""
    kb = types.InlineKeyboardMarkup(row_width=2)

    if section == "requests":
        s = get_admin_quick_stats()
        pending_label = f"⏳ {s['pending_total']} طلب بانتظار المراجعة" if s["pending_total"] else "✨ لا توجد طلبات معلّقة"
        kb.add(types.InlineKeyboardButton(pending_label, callback_data="noop", style="primary"))
        kb.add(
            types.InlineKeyboardButton("👤 طلبات التفعيل", callback_data="adm_pending_users", style="success"),
            types.InlineKeyboardButton("🤖 طلبات البوتات", callback_data="adm_pending_projects", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("📎 ملفات بانتظار المراجعة", callback_data="adm_pending_files", style="primary"))
        if s["pending_total"] > 0:
            kb.add(types.InlineKeyboardButton(
                f"✅ موافقة الكل ({s['pending_total']})", callback_data="adm_quick_approve_all", style="success"
            ))

    elif section == "users":
        kb.add(
            types.InlineKeyboardButton("📋 كل المستخدمين", callback_data="adm_users", style="primary"),
            types.InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="adm_search_user", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🪪 معلومات مستخدم", callback_data="adm_user_info", style="primary"),
            types.InlineKeyboardButton("📤 تصدير المستخدمين", callback_data="adm_export_users", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🚫 حظر مستخدم", callback_data="adm_ban_by_id", style="danger"),
            types.InlineKeyboardButton("✅ رفع حظر مستخدم", callback_data="adm_unban_by_id", style="danger"),
        )
        kb.add(
            types.InlineKeyboardButton("📛 قائمة المحظورين", callback_data="admin_list_blocked", style="primary"),
            types.InlineKeyboardButton("🕵️ كاشف الحظر", callback_data="adm_blocked_users", style="danger"),
        )
        kb.add(types.InlineKeyboardButton("👻 المستخدمون الخاملون", callback_data="adm_inactive_users", style="primary"))
        kb.add(
            types.InlineKeyboardButton("🆕 مستخدمو اليوم", callback_data="adm_new_today", style="primary"),
            types.InlineKeyboardButton("✅ قبول مستخدم بـ ID", callback_data="adm_approve_id", style="success"),
        )
        kb.add(
            types.InlineKeyboardButton("🤖 بوتات مستخدم", callback_data="adm_user_bots_by_id", style="primary"),
            types.InlineKeyboardButton("🔄 تصفير نقاط مستخدم", callback_data="adm_reset_points_id", style="danger"),
        )
        kb.add(types.InlineKeyboardButton("⚙️ حد بوتات مستخدم بعينه", callback_data="adm_set_user_max", style="primary"))
        kb.add(
            types.InlineKeyboardButton("📄 ملف مستخدم", callback_data="adm_user_profile", style="primary"),
            types.InlineKeyboardButton("⏳ منتظرون موافقة", callback_data="adm_pending_users", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🚫 حظر بـ ID", callback_data="adm_ban_by_id", style="danger"),
            types.InlineKeyboardButton("✅ رفع حظر بـ ID", callback_data="adm_unban_by_id", style="success"),
        )
        kb.add(types.InlineKeyboardButton("👑 VIP المستخدمين", callback_data="adm_vip_users", style="primary"))

    elif section == "comms":
        kb.add(
            types.InlineKeyboardButton("📢 إذاعة للمستخدمين", callback_data="adm_broadcast", style="primary"),
            types.InlineKeyboardButton("📺 إذاعة للقنوات", callback_data="adm_broadcast_channel", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("💬 رسالة لمستخدم", callback_data="adm_send_user", style="primary"),
            types.InlineKeyboardButton("⚠️ تحذير لمستخدم", callback_data="admin_warn_user", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("📣 إعلان منسّق", callback_data="adm_announce", style="success"))
        kb.add(
            types.InlineKeyboardButton("💤 رسالة للخاملين", callback_data="adm_msg_to_inactive", style="primary"),
            types.InlineKeyboardButton("✅ إذاعة للمفعّلين فقط", callback_data="adm_broadcast_active_only", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🔢 عداد المستقبلين", callback_data="adm_receivers_count", style="primary"))
        kb.add(
            types.InlineKeyboardButton("💬 رسالة لمستخدم بـ ID", callback_data="adm_msg_by_id", style="primary"),
            types.InlineKeyboardButton("⏳ رسالة للمنتظرين", callback_data="adm_broadcast_pending", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("📊 إحصائيات آخر إذاعة", callback_data="adm_last_broadcast_stats", style="primary"))

    elif section == "points":
        kb.add(
            types.InlineKeyboardButton("🎁 منح نقاط لمستخدم", callback_data="adm_give_points", style="primary"),
            types.InlineKeyboardButton("🔢 تعيين نقاط", callback_data="adm_set_points", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🎯 منح نقاط للكل", callback_data="adm_give_all_points", style="primary"),
            types.InlineKeyboardButton("🏆 أعلى مستخدمين", callback_data="adm_top_users", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🔗 رابط هدية نقاط", callback_data="adm_gift_new", style="primary"))

    elif section == "bots":
        s = get_admin_quick_stats()
        kb.add(
            types.InlineKeyboardButton("📂 كل البوتات", callback_data="adm_projects", style="primary"),
            types.InlineKeyboardButton("🗑 حذف المتوقفة", callback_data="adm_del_stopped", style="danger"),
        )
        kb.add(
            types.InlineKeyboardButton("▶️ تشغيل كل البوتات", callback_data="adm_quick_start_all", style="success"),
            types.InlineKeyboardButton("⏹ إيقاف كل البوتات", callback_data="adm_quick_stop_all", style="danger"),
        )
        kb.add(types.InlineKeyboardButton("🔁 إعادة تشغيل الشغّالة", callback_data="adm_quick_restart_all", style="primary"))
        kb.add(
            types.InlineKeyboardButton("⚡ البوتات الشغّالة الآن", callback_data="adm_running_bots_list", style="success"),
            types.InlineKeyboardButton("📤 تصدير البوتات CSV", callback_data="adm_export_bots", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("⚙️ حد البوتات للمستخدم", callback_data="adm_set_max_bots", style="primary"))
        kb.add(
            types.InlineKeyboardButton("💥 بوتات معطوبة", callback_data="adm_crashed_bots", style="danger"),
            types.InlineKeyboardButton("🔍 بحث بوت بالاسم", callback_data="adm_search_bot_name", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("📋 ملخص البوتات", callback_data="adm_bots_summary", style="primary"),
            types.InlineKeyboardButton("🧹 تنظيف سجلات العمليات", callback_data="adm_clear_proc_logs", style="danger"),
        )
        kb.add(types.InlineKeyboardButton("⚙️ معلومات العمليات الحية", callback_data="adm_proc_info", style="primary"))
        kb.add(
            types.InlineKeyboardButton("▶️ تشغيل بوت بـ ID", callback_data="adm_force_start_bot", style="success"),
            types.InlineKeyboardButton("⏹ إيقاف بوت بـ ID", callback_data="adm_force_stop_bot", style="danger"),
        )
        kb.add(
            types.InlineKeyboardButton("📁 ملفات بوت بـ ID", callback_data="adm_bot_files_info", style="primary"),
            types.InlineKeyboardButton("📦 أكبر البوتات", callback_data="adm_top_bots", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🆕 بوتات اليوم", callback_data="adm_new_bots_today", style="primary"))
        running_label = f"🟢 {s['running_bots']} بوت شغّال حالياً"
        kb.add(types.InlineKeyboardButton(running_label, callback_data="noop", style="primary"))

    elif section == "settings":
        kb.add(
            types.InlineKeyboardButton("💰 سعر رفع البوت", callback_data="adm_set_upload_price", style="success"),
            types.InlineKeyboardButton("💸 عمولة التحويل", callback_data="adm_set_transfer_fee", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🏷 أسعار الأقسام", callback_data="adm_section_prices", style="primary"),
            types.InlineKeyboardButton("🛡 المشرفين", callback_data="adm_mods", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("📢 اشتراك إجباري", callback_data="adm_force_channel", style="primary"),
            types.InlineKeyboardButton("✏️ رسالة الترحيب", callback_data="adm_set_welcome", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🖼 صورة الترحيب", callback_data="adm_set_welcome_img", style="primary"),
            types.InlineKeyboardButton("🚫 صورة الحظر", callback_data="adm_set_banned_img", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🔧 صورة الصيانة", callback_data="adm_set_maint_img", style="primary"),
            types.InlineKeyboardButton("✍️ رسالة الحظر", callback_data="adm_set_banned_txt", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🔧 رسالة الصيانة", callback_data="adm_set_maint_txt", style="primary"))
        notify_on = is_admin_notify_enabled("notify_admin_new_user", True)
        notify_lbl = "🔕 إيقاف إشعار الجدد" if notify_on else "🔔 تشغيل إشعار الجدد"
        kb.add(types.InlineKeyboardButton(notify_lbl, callback_data="adm_toggle_notify", style="primary"))
        kb.add(types.InlineKeyboardButton("🎨 ألوان الأزرار", callback_data="adm_btn_colors", style="primary"))
        kb.add(
            types.InlineKeyboardButton("📋 عرض كل الإعدادات", callback_data="adm_view_settings", style="primary"),
            types.InlineKeyboardButton("🤖 قبول تلقائي للجدد", callback_data="adm_toggle_auto_approve", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🗑 تنظيف سجل التدقيق (30ي+)", callback_data="adm_clear_audit", style="danger"))
        kb.add(
            types.InlineKeyboardButton("🔧 وضع الصيانة", callback_data="adm_maintenance_mode", style="danger"),
            types.InlineKeyboardButton("🖥 معلومات النظام", callback_data="adm_sys_info", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🧹 تنظيف قاعدة المحظورين", callback_data="adm_clear_blocked_db", style="danger"))

    elif section == "stats":
        kb.add(
            types.InlineKeyboardButton("📈 إحصائيات النظام", callback_data="adm_stats", style="primary"),
            types.InlineKeyboardButton("🖥 حالة السيرفر", callback_data="adm_server_status", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("📊 إحصائيات النمو", callback_data="adm_growth_stats", style="primary"),
            types.InlineKeyboardButton("📋 سجل التدقيق", callback_data="adm_audit_log", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("💾 نسخ احتياطي DB", callback_data="adm_backup_db", style="success"),
            types.InlineKeyboardButton("🧹 تنظيف الملفات", callback_data="adm_cleanup_files", style="danger"),
        )
        kb.add(types.InlineKeyboardButton("📊 إحصائيات الاستخدام", callback_data="adm_usage_stats", style="primary"))
        kb.add(
            types.InlineKeyboardButton("🗃 إحصائيات الجداول", callback_data="adm_db_table_stats", style="primary"),
            types.InlineKeyboardButton("🚀 إحصائيات الرفع", callback_data="adm_deploy_stats", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("📅 تقرير يومي الآن", callback_data="adm_daily_report", style="success"),
            types.InlineKeyboardButton("💎 توزيع النقاط", callback_data="adm_points_dist", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("📆 تقرير أسبوعي", callback_data="adm_weekly_report", style="success"),
            types.InlineKeyboardButton("🏆 أكثر المستخدمين رفعاً", callback_data="adm_top_uploaders", style="primary"),
        )
        kb.add(
            types.InlineKeyboardButton("🔴 آخر أخطاء العمليات", callback_data="adm_error_log_view", style="danger"),
            types.InlineKeyboardButton("📈 نشاط اليوم", callback_data="adm_activity_stats", style="primary"),
        )
        kb.add(types.InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="adm_sec_stats", style="primary"))

    kb.add(types.InlineKeyboardButton("🔙 رجوع للوحة الأدمن", callback_data="adm_panel", style="primary"))
    return kb


def show_admin_panel(chat_id: int, msg_id: int = None) -> None:
    """يعرض لوحة الأدمن الرئيسية مع إحصائيات حية."""
    text = admin_stats_text()
    markup = admin_main_markup()
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)


def back_main_kb() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        " رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK,
    ))
    return kb


def back_admin_kb() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        " رجوع للوحة الأدمن", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK,
    ))
    return kb


# ============================================================
# ألوان الأزرار — Per-Group Color Manager
# ============================================================
ADM_COLOR_GROUPS = {
    "requests":   ("📥 الطلبات",),
    "users":      ("👥 المستخدمون",),
    "comms":      ("📣 التواصل",),
    "adm_points": ("💎 النقاط",),
    "bots":       ("🤖 البوتات",),
    "settings":   ("⚙️ الإعدادات",),
    "stats":      ("📊 الإحصائيات",),
}

USER_COLOR_GROUPS = {
    "user_bots":     ("🤖 إضافة بوت & بوتاتي",),
    "user_upload":   ("⬆️ رفع المواقع",),
    "user_mysites":  ("🌐 مواقعي & ديبلويمنتس",),
    "user_terminal": ("💻 التيرمنال",),
    "user_info":     ("📊 إحصائياتي & المساعدة",),
    "user_points":   ("💎 النقاط",),
    "user_misc":     ("🏷 الشعار والمطور",),
}

BTN_COLOR_GROUPS = {**ADM_COLOR_GROUPS, **USER_COLOR_GROUPS}

_COLOR_LABELS = {
    "mixed":   "🌈 أصلي",
    "primary": "🔵 أزرق",
    "success": "🟢 أخضر",
    "danger":  "🔴 أحمر",
}


def get_group_color(group_key: str) -> str:
    return get_setting(f"btn_color_{group_key}") or "mixed"


def btn_colors_groups_menu() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    # ── قسم لوحة الأدمن ──
    kb.add(types.InlineKeyboardButton("👑 ━━━ لوحة الأدمن ━━━", callback_data="noop", style="primary"))
    for key, (label,) in ADM_COLOR_GROUPS.items():
        color = get_group_color(key)
        color_lbl = _COLOR_LABELS.get(color, "🌈 أصلي")
        kb.add(types.InlineKeyboardButton(
            f"{label}  ·  {color_lbl}",
            callback_data=f"adm_btn_color_group:{key}",
            style="primary",
        ))
    # ── قسم لوحة المستخدم ──
    kb.add(types.InlineKeyboardButton("👤 ━━━ لوحة المستخدم ━━━", callback_data="noop", style="primary"))
    for key, (label,) in USER_COLOR_GROUPS.items():
        color = get_group_color(key)
        color_lbl = _COLOR_LABELS.get(color, "🌈 أصلي")
        kb.add(types.InlineKeyboardButton(
            f"{label}  ·  {color_lbl}",
            callback_data=f"adm_btn_color_group:{key}",
            style="primary",
        ))
    kb.add(types.InlineKeyboardButton(
        " رجوع للوحة الأدمن", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK,
    ))
    return kb


def btn_colors_pick_menu(group_key: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    current = get_group_color(group_key)
    for color, clabel in _COLOR_LABELS.items():
        tick = "✅ " if color == current else ""
        style = "success" if color == current else "primary"
        kb.add(types.InlineKeyboardButton(
            f"{tick}{clabel}",
            callback_data=f"adm_btn_color_pick:{group_key}:{color}",
            style=style,
        ))
    kb.add(types.InlineKeyboardButton(
        " رجوع للأقسام", callback_data="adm_btn_colors",
        style="primary", icon_custom_emoji_id=E_BACK,
    ))
    return kb


def show_btn_colors(chat_id: int, msg_id: int = None) -> None:
    text = "🎨 <b>ألوان الأزرار</b>\n\nاختر القسم الذي تريد تغيير لون أزراره:"
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=btn_colors_groups_menu())
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=btn_colors_groups_menu())


def show_btn_color_pick(chat_id: int, group_key: str, msg_id: int = None) -> None:
    label, = BTN_COLOR_GROUPS.get(group_key, ("القسم",))
    current = get_group_color(group_key)
    current_lbl = _COLOR_LABELS.get(current, "🌈 أصلي")
    text = (
        f"🎨 <b>لون أزرار: {label}</b>\n\n"
        f"اللون الحالي: <b>{current_lbl}</b>\n\n"
        "اختر لوناً جديداً:"
    )
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=btn_colors_pick_menu(group_key))
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=btn_colors_pick_menu(group_key))


def cancel_kb() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "❌ إلغاء", callback_data="cancel_operation",
        style="danger", icon_custom_emoji_id=E_CANCEL,
    ))
    return kb


# ============================================================
# 11) القائمة الرئيسية
# ============================================================
def show_main_menu(chat_id: int, uid: int, edit_message_id: Optional[int] = None) -> None:
    user = ensure_user_by_id(uid)
    proj_count = db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE user_id=?", (uid,))["c"]
    running_count = 0
    for p in db_fetchall("SELECT id FROM projects WHERE user_id=?", (uid,)):
        hp = manager.processes.get(p["id"])
        if hp and hp.is_alive():
            running_count += 1
    stopped_count = max(proj_count - running_count, 0)
    points_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
    points = points_row["p"] if points_row else 0
    username = user.get("username") or "NoUser"
    display_name = user.get("first_name") or "اماراتي"
    percent = int((running_count / max(proj_count, 1)) * 100)
    _quote = get_random_quote()
    _DEFAULT_WELCOME = (
        "╭──〔 🚀 اماراتي هيفضل عمها 〕──╮\n\n"
        f"💬 {_quote}\n\n"
        "🖥 أهلاً {name}\n"
        "🖥 اليوزر: @{username}\n"
        "🖥 ID: {uid}\n"
        "🖥 الخطة: 🖥 Free\n\n"
        "┌ 🖥 إحصائيات حسابك\n"
        "├ 🖥 النقاط: {points}\n"
        "├ 🖥 إجمالي البوتات: {proj_count}\n"
        "├ 🖥 تعمل الآن: {running_count}\n"
        "├ 🖥 متوقفة: {stopped_count}\n"
        "└ 🖥 نسبة التشغيل: {percent}%\n\n"
        "┌ 🖥 حالة السيرفر\n"
        "├ 🖥 الحالة: 🖥 Online\n"
        "├ 🖥 Ping: 12ms\n"
        "├ 🖥 CPU : ██ ░ ░ ░ ░ ░ ░ ░ ░ ░ 20%\n"
        "├ 🖥 RAM : ██ ░ ░ ░ ░ ░ ░ ░ ░ 15%\n"
        "└ 🖥 Disk: ██ █ ░ ░ ░ ░ ░ ░ 30%\n\n"
        "🖥 استضافة قوية للبوتات والمشاريع\n"
        "server: EMIRATI-host.net\n"
        "cpu🖥: 5 cores | ram🖥: 32gb | Disk🖥: 256gb ssd\n"
        "╰── @EM_RT2 ──╯\n\n"
        "اختر من القائمة 🖥"
    )
    _custom_welcome = get_setting("welcome_text") or ""
    _tpl = _custom_welcome if _custom_welcome else _DEFAULT_WELCOME
    text = _tpl.format(
        name=html_escape(display_name),
        username=html_escape(username),
        uid=uid,
        points=points,
        proj_count=proj_count,
        running_count=running_count,
        stopped_count=stopped_count,
        percent=percent,
    )
    kb = main_menu_markup(is_admin=is_admin(uid))
    if edit_message_id:
        # حاول تعديل caption الصورة أولاً، ثم النص العادي
        try:
            bot.edit_message_caption(
                caption=text, chat_id=chat_id, message_id=edit_message_id,
                reply_markup=kb, parse_mode="HTML",
            )
            return
        except Exception:
            pass
        try:
            bot.edit_message_text(text, chat_id, edit_message_id, reply_markup=kb)
            return
        except Exception:
            pass
    # إرسال رسالة جديدة مع صورة الترحيب (مخصصة أو افتراضية)
    _welcome_img = get_setting("welcome_image_id") or WELCOME_IMAGE
    try:
        bot.send_photo(chat_id, _welcome_img, caption=text, reply_markup=kb, parse_mode="HTML")
    except Exception as _e1:
        log.warning("send_photo failed: %s", _e1)
        try:
            bot.send_message(chat_id, text, reply_markup=kb)
        except Exception as _e2:
            log.error("send_message also failed: %s", _e2)


# ============================================================
# 12) أوامر /start /admin /cancel
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "main_terminal")
def main_terminal_callback(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🖥️ استخدم التيرمنال من قائمة بوتاتك ← اختر بوت ← زر التيرمنال.")


@bot.message_handler(commands=["start"])
def cmd_start(message):
    log.info("cmd_start received uid=%s msg_id=%s", message.from_user.id, message.message_id)
    if msg_seen(message):
        log.info("msg_seen=True, skipping uid=%s", message.from_user.id)
        return
    uid = message.from_user.id
    log.info("cmd_start processing uid=%s", uid)
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) == 2 else ""
    ref_id = None
    gift_token = None
    if payload.startswith("gift_"):
        gift_token = payload[len("gift_"):]
    elif payload.isdigit():
        try:
            ref_id = int(payload)
            if ref_id == uid:
                ref_id = None
        except Exception:
            ref_id = None

    existing = db_fetchone("SELECT id FROM users WHERE id=?", (uid,))
    is_new_user = existing is None
    user = ensure_user(message)

    try:
        if uid != ADMIN_ID:
            notify_new = is_admin_notify_enabled("notify_admin_new_user", True)
            notify_any = is_admin_notify_enabled("notify_admin_any_start", False)
            if (is_new_user and notify_new) or notify_any:
                name = (getattr(message.from_user, "first_name", None) or "").strip() or "-"
                uname = (getattr(message.from_user, "username", None) or "").strip()
                uname_disp = f"@{uname}" if uname else "-"
                kind = "🆕 مستخدم جديد" if is_new_user else "👋 دخول"
                bot.send_message(
                    ADMIN_ID,
                    f"{kind}\n\nالاسم: <b>{html_escape(name)}</b>\n"
                    f"يوزر: <code>{html_escape(uname_disp)}</code>\n"
                    f"ID: <code>{uid}</code>",
                )
    except Exception:
        pass

    if user.get("banned"):
        _banned_img = get_setting("banned_image_id") or BANNED_IMAGE
        _banned_txt = get_setting("banned_text") or "🚫 <b>لقد تم حظرك من استخدام الاستضافة.</b>"
        try:
            bot.send_photo(uid, _banned_img, caption=_banned_txt, parse_mode="HTML")
        except Exception:
            bot.send_message(uid, _banned_txt, parse_mode="HTML")
        return

    if is_bot_disabled() and not is_admin(uid):
        _maint_img = get_setting("maintenance_image_id") or MAINTENANCE_IMAGE
        _maint_txt = get_setting("maintenance_text") or (
            "⛔ <b>البوت معطل حالياً</b>\n\n"
            "نعتذر، البوت متوقف مؤقتاً عن استقبال الطلبات الجديدة.\n"
            "بوتاتك المستضافة لا تزال تعمل بشكل طبيعي.\n\n"
            "يرجى المحاولة لاحقاً 🙏"
        )
        try:
            bot.send_photo(
                uid, _maint_img,
                caption=_maint_txt,
                parse_mode="HTML",
            )
        except Exception:
            bot.send_message(uid, _maint_txt, parse_mode="HTML")
        return

    if gift_token:
        process_gift_link(uid, gift_token)

    if is_new_user and ref_id:
        ref_exists = db_fetchone("SELECT id FROM users WHERE id=?", (ref_id,))
        if ref_exists:
            db_execute(
                "UPDATE users SET referred_by=? WHERE id=? AND (referred_by IS NULL OR referred_by=0)",
                (ref_id, uid),
            )
            db_execute("UPDATE users SET points = COALESCE(points,0) + 1 WHERE id=?", (ref_id,))
            try:
                bot.send_message(
                    ref_id,
                    "🎉 شخص جديد دخل عبر رابط الإحالة الخاص بك!\n"
                    "⭐ تمت إضافة <b>1 نقطة</b> إلى رصيدك.",
                )
            except Exception:
                pass

    if force_sub_block(uid, uid):
        return

    show_main_menu(uid, uid)


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "👑 لوحة المطور:", reply_markup=admin_menu_markup())


@bot.message_handler(commands=["cancel"])
def cmd_cancel(message):
    if msg_seen(message):
        return
    pop_pending(message.from_user.id)
    bot.send_message(message.chat.id, "✅ تم إلغاء العملية الحالية.")


@bot.message_handler(commands=["add"])
def cmd_add(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "الاستخدام: /add <user_id>")
        return
    try:
        target = int(parts[1])
    except ValueError:
        bot.send_message(message.chat.id, "❌ معرّف غير صالح")
        return
    db_execute("INSERT INTO users (id, approved) VALUES (?, 1) ON CONFLICT (id) DO UPDATE SET approved=1, banned=0", (target,))
    bot.send_message(message.chat.id, f"✅ تم تفعيل {target}")
    try:
        bot.send_message(target, f"🎉 تم تفعيل حسابك. أرسل /start.\n\n💬 {get_random_quote()}")
    except Exception:
        pass


@bot.message_handler(commands=["ban"])
def cmd_ban(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "الاستخدام: /ban <user_id>")
        return
    target = int(parts[1])
    db_execute("UPDATE users SET banned=1 WHERE id=?", (target,))
    for p in db_fetchall("SELECT id FROM projects WHERE user_id=?", (target,)):
        manager.stop_project(p["id"])
    bot.send_message(message.chat.id, f"🚫 تم حظر {target}")


@bot.message_handler(commands=["unban"])
def cmd_unban(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        return
    target = int(parts[1])
    db_execute("UPDATE users SET banned=0 WHERE id=?", (target,))
    bot.send_message(message.chat.id, f"✅ تم رفع الحظر عن {target}")


@bot.message_handler(commands=["limit"])
def cmd_limit(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.send_message(message.chat.id, "الاستخدام: /limit <user_id> <max_bots>")
        return
    target = int(parts[1])
    n = int(parts[2])
    db_execute("UPDATE users SET max_bots=? WHERE id=?", (n, target))
    bot.send_message(message.chat.id, f"✅ تم ضبط الحد {n} للمستخدم {target}")


# ============================================================
# 13) إضافة بوت جديد
# ============================================================
def start_new_project(chat_id: int, uid: int) -> None:
    ok, msg = check_and_inc_daily(uid, "bots", 5)
    if not ok:
        bot.send_message(chat_id, msg, reply_markup=back_main_kb())
        return
    proj_count = db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE user_id=?", (uid,))["c"]
    is_first = proj_count == 0
    price = get_upload_price()
    if not is_first and price > 0:
        pts_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
        pts = pts_row["p"] if pts_row else 0
        if pts < price:
            bot.send_message(
                chat_id,
                "❌ لا تملك نقاطاً كافية لرفع بوت إضافي.\n"
                f"💡 رفع البوت الإضافي يكلف <b>{price}</b> نقطة.\n"
                "🎁 يمكنك تجميع النقاط من قسم «تجميع نقاط».",
                reply_markup=back_main_kb(),
            )
            return
    set_pending(uid, {"type": "new_project_name", "is_first": is_first, "price": price})
    bot.send_message(
        chat_id,
        "✨🔥 ارفع بوتك الاول مجانية على اقوى استضافة 🔥✨\n\n"
        "📛 أرسل اسماً قصيراً للبوت (حروف وأرقام فقط).\n"
        "أو /cancel للإلغاء.",
        reply_markup=back_main_kb(),
    )


# ============================================================
# 14) رفع موقع Netlify
# ============================================================
def start_netlify_upload(chat_id: int, uid: int) -> None:
    if not netlify_is_configured():
        bot.send_message(
            chat_id,
            "⚠️ ميزة رفع المواقع غير مفعّلة حالياً.\n\n"
            "🔧 لتفعيلها: ضع متغير البيئة <code>NETLIFY_TOKEN</code> ثم أعد تشغيل البوت.",
            reply_markup=back_main_kb(),
        )
        return
    ok, msg = check_and_inc_daily(uid, "netlify", 5)
    if not ok:
        bot.send_message(chat_id, msg, reply_markup=back_main_kb())
        return
    price = get_section_price("netlify", 0)
    if price > 0 and not is_admin(uid):
        pts_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
        pts = pts_row["p"] if pts_row else 0
        if pts < price:
            bot.send_message(chat_id, f"❌ لا تملك نقاطاً كافية.\n💡 سعر رفع Netlify: <b>{price}</b> نقطة.",
                             reply_markup=back_main_kb())
            return
        db_execute("UPDATE users SET points = points - ? WHERE id=? AND COALESCE(points,0) >= ?", (price, uid, price))
    set_pending(uid, {"type": "netlify_upload_zip"})
    bot.send_message(
        chat_id,
        "⚡ <b>رفع موقع على Netlify</b>\n\n"
        "📦 ابعت ملف <b>.zip</b> لفولدر فيه ملفات الموقع.\n"
        "📌 لازم يكون جوّه <code>index.html</code>.\n\n"
        f"📏 الحد الأقصى: <b>{MAX_SITE_ZIP_SIZE // (1024 * 1024)}MB</b>\n"
        "/cancel للإلغاء.",
        reply_markup=back_main_kb(),
    )


def show_netlify_upload_menu(chat_id: int, uid: int, message_id: Optional[int] = None) -> None:
    text = (
        "⚡ <b>رفع موقع (Netlify)</b>\n\n"
        "✅ Netlify بيسمح برفع: <b>HTML / CSS / JS فقط</b>.\n\n"
        "📌 المتطلبات:\n"
        "• اجمع ملفات الموقع في فولدر ثم اعمل له <b>.zip</b>\n"
        "• لازم يكون جوّه <code>index.html</code>\n"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(" رفع ملف ZIP", callback_data="site_upload_zip",
        style="success", icon_custom_emoji_id=E_UPLOAD))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK))
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def show_vercel_upload_menu(chat_id: int, uid: int, message_id: Optional[int] = None) -> None:
    text = (
        "▲ <b>الرفع على Vercel</b>\n\n"
        "📌 المتطلبات:\n"
        "• ابعت <b>.zip</b> لفولدر واحد\n"
        "• لازم يكون جوّه <code>index.html</code>\n\n"
        "🧾 المسموح: <code>.html .css .js</code>\n"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("📤 رفع ملف ZIP", callback_data="vercel_upload_zip",
        style="success", icon_custom_emoji_id=E_UPLOAD))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK))
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def _deploy_netlify_zip_async(chat_id: int, uid: int, filename: str, zip_bytes: bytes) -> None:
    try:
        existing = db_fetchone(
            "SELECT site_id, site_name, site_url FROM netlify_sites WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
        )
        if existing:
            site_id = existing["site_id"]
            site_name = existing["site_name"]
            site_url = existing["site_url"]
        else:
            site = netlify_create_site_for_user(uid)
            site_id = (site or {}).get("id") or ""
            site_name = (site or {}).get("name") or _slugify_site_name(f"{NETLIFY_SITE_PREFIX}-{uid}")
            site_url = _netlify_pick_site_url(site) or ""
        if not site_id:
            raise RuntimeError("Netlify returned no site id")
        deploy = netlify_deploy_zip(site_id, zip_bytes)
        deploy_id = (deploy or {}).get("id") or ""
        deploy_ssl = (deploy or {}).get("ssl_url") or (deploy or {}).get("url") or ""
        if deploy_ssl:
            site_url = deploy_ssl
        if not site_url:
            site_url = f"https://{site_name}.netlify.app"
        db_execute(
            "INSERT INTO netlify_sites (user_id, site_id, site_name, site_url, last_deploy_id, last_deploy_at) "
            "VALUES (?,?,?,?,?, CURRENT_TIMESTAMP) ON CONFLICT(site_id) DO UPDATE SET "
            "site_url=excluded.site_url, last_deploy_id=excluded.last_deploy_id, last_deploy_at=CURRENT_TIMESTAMP",
            (uid, site_id, site_name, site_url, deploy_id),
        )
        db_execute(
            "INSERT INTO deployments (user_id, provider, site_id, deploy_id, url, filename, size_bytes) "
            "VALUES (?,?,?,?,?,?,?)",
            (uid, "netlify", site_id, deploy_id, site_url, filename, len(zip_bytes)),
        )
        bot.send_message(
            chat_id,
            "✅ تم رفع الموقع بنجاح!\n\n"
            f"🖥 الرابط: <code>{html_escape(site_url)}</code>\n"
            f"🆔 Site: <code>{html_escape(site_id)}</code>",
            reply_markup=back_main_kb(),
        )
    except Exception as e:
        bot.send_message(chat_id, f"❌ فشل رفع الموقع: <code>{html_escape(str(e)[:350])}</code>",
                         reply_markup=back_main_kb())


# ============================================================
# 15) معالجة الرسائل النصية المعلقة
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "new_project_name",
    content_types=["text"],
)
def receive_project_name(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    is_first = pending.get("is_first", True)
    price = int(pending.get("price", get_upload_price()))
    name = message.text.strip()
    name = "".join(c for c in name if c.isalnum() or c in "_-")[:40]
    if not name:
        bot.send_message(uid, "❌ اسم غير صالح. حاول مرة أخرى أو /cancel.")
        return
    exists = db_fetchone("SELECT id FROM projects WHERE user_id=? AND name=?", (uid, name))
    if exists:
        bot.send_message(uid, "❌ يوجد بوت بنفس الاسم. اختر اسماً آخر.")
        return
    if not is_first and price > 0:
        with _db_lock:
            pts_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
            pts = pts_row["p"] if pts_row else 0
            if pts < price:
                pop_pending(uid)
                bot.send_message(uid, "❌ رصيد النقاط أصبح غير كافٍ. أُلغيت العملية.")
                return
            db_execute("UPDATE users SET points = points - ? WHERE id=? AND COALESCE(points,0) >= ?", (price, uid, price))
    pid = db_execute_returning_id(
        "INSERT INTO projects (user_id, name, main_file, approved) VALUES (?, ?, '', 0)", (uid, name)
    )
    set_pending(uid, {"type": "new_project_main", "project_id": pid})
    bot.send_message(
        uid,
        f"✅ تم إنشاء البوت <b>{html_escape(name)}</b>.\n\n"
        "📤 الآن أرسل ملف البوت الرئيسي (.py).\n"
        "بعد القبول من المطور، يمكنك إضافة ملفات إضافية.\n\n"
        "/cancel للإلغاء.",
    )


# ============================================================
# 16) معالجة الملفات
# ============================================================
@bot.message_handler(content_types=["document"])
def receive_document(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    user = ensure_user_by_id(uid)
    if user["banned"]:
        bot.send_message(uid, "🚫 لقد تم حظرك من استخدام الاستضافة.")
        return

    pending = get_pending(uid)
    doc = message.document
    filename = safe_filename(doc.file_name or "file.bin")
    size = doc.file_size or 0

    # رفع موقع Netlify
    if pending and pending.get("type") == "netlify_upload_zip":
        if size > MAX_SITE_ZIP_SIZE:
            bot.send_message(uid, f"❌ الملف أكبر من {MAX_SITE_ZIP_SIZE // (1024 * 1024)}MB.")
            return
        if not filename.lower().endswith(".zip"):
            bot.send_message(uid, "❌ ارسل ملف <b>.zip</b> فقط.")
            return
        try:
            file_info = bot.get_file(doc.file_id)
            zip_bytes = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.send_message(uid, f"❌ فشل تحميل الملف: {e}")
            return
        send_file_bytes_to_admin(filename, zip_bytes,
                                 f"⚡ رفع موقع (Netlify)\nالمستخدم: {uid}\nالحجم: {len(zip_bytes)//1024} KB")
        try:
            db_execute("INSERT INTO audit_log (actor_id, action, provider, filename, size_bytes) VALUES (?,?,?,?,?)",
                       (uid, "upload_site", "netlify", filename[:300], len(zip_bytes)))
        except Exception:
            pass
        pop_pending(uid)
        bot.send_message(uid, "⏳ جاري رفع الموقع على Netlify... انتظر قليلًا.")
        threading.Thread(target=_deploy_netlify_zip_async,
                         args=(message.chat.id, uid, filename, zip_bytes), daemon=True).start()
        return

    # رفع موقع Vercel
    if pending and pending.get("type") in ("vercel_upload_zip", "vercel_redeploy_zip"):
        if size > MAX_SITE_ZIP_SIZE:
            bot.send_message(uid, f"❌ الملف أكبر من {MAX_SITE_ZIP_SIZE // (1024 * 1024)}MB.")
            return
        if not filename.lower().endswith(".zip"):
            bot.send_message(uid, "❌ ارسل ملف <b>.zip</b> فقط.")
            return
        try:
            file_info = bot.get_file(doc.file_id)
            zip_bytes = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.send_message(uid, f"❌ فشل تحميل الملف: {e}")
            return
        send_file_bytes_to_admin(filename, zip_bytes,
                                 f"▲ رفع موقع (Vercel)\nالمستخدم: {uid}\nالحجم: {len(zip_bytes)//1024} KB")
        try:
            db_execute("INSERT INTO audit_log (actor_id, action, provider, filename, size_bytes) VALUES (?,?,?,?,?)",
                       (uid, "upload_site", "vercel", filename[:300], len(zip_bytes)))
        except Exception:
            pass
        pop_pending(uid)
        bot.send_message(uid, "⏳ جاري رفع الموقع على Vercel... انتظر قليلًا.")

        def _vercel_async():
            try:
                dep = vercel_deploy_zip(zip_bytes, uid=uid)
                url = (dep or {}).get("url") or ""
                full = f"https://{url}" if url and not url.startswith("http") else url
                if not full:
                    full = "(تم إنشاء الديبلوي لكن لم يرجع رابط)"
                dep_id = (dep or {}).get("id") or ""
                db_execute(
                    "INSERT INTO deployments (user_id, provider, site_id, deploy_id, url, filename, size_bytes) VALUES (?,?,?,?,?,?,?)",
                    (uid, "vercel", None, dep_id, full, filename, len(zip_bytes)),
                )
                bot.send_message(message.chat.id, "✅ تم رفع الموقع على Vercel.\n\n"
                                 f"🖥 الرابط: <code>{html_escape(full)}</code>", reply_markup=back_main_kb())
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ فشل رفع Vercel: <code>{html_escape(str(e)[:350])}</code>",
                                 reply_markup=back_main_kb())

        threading.Thread(target=_vercel_async, daemon=True).start()
        return

    if size > MAX_FILE_SIZE:
        bot.send_message(uid, "❌ الملف أكبر من الحد المسموح (50MB).")
        return
    if not is_allowed_extension(filename):
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        bot.send_message(uid, f"❌ صيغة غير مدعومة. المدعوم:\n<code>{allowed}</code>")
        return

    if pending and pending.get("type") == "new_project_main":
        if not filename.endswith(".py"):
            bot.send_message(uid, "❌ الملف الرئيسي يجب أن يكون .py")
            return
        project_id = pending["project_id"]
        db_execute(
            "INSERT INTO pending_uploads (user_id, project_id, filename, telegram_file_id, size_bytes) VALUES (?,?,?,?,?)",
            (uid, project_id, filename, doc.file_id, size),
        )
        db_execute("UPDATE projects SET main_file=? WHERE id=?", (filename, project_id))
        pop_pending(uid)
        proj = db_fetchone("SELECT name FROM projects WHERE id=?", (project_id,))
        bot.send_message(uid, "✅ تم استلام الملف الرئيسي.\n⏳ بانتظار موافقة المطور لتشغيل البوت.")
        # إشعار الأدمن
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton(f" موافقة #{project_id}", callback_data=f"adm_approve_proj_{project_id}",
                style="primary", icon_custom_emoji_id=E_APPROVE),
            types.InlineKeyboardButton(f" رفض #{project_id}", callback_data=f"adm_reject_proj_{project_id}",
                style="primary", icon_custom_emoji_id=E_REJECT),
        )
        caption = (
            f"📥 <b>بوت جديد بانتظار الموافقة</b>\n\n"
            f"الاسم: <b>{html_escape(proj['name'] if proj else '-')}</b>\n"
            f"المالك: <code>{uid}</code>\n"
            f"الملف: <code>{html_escape(filename)}</code>\n"
            f"الحجم: {size:,} بايت"
        )
        try:
            bot.send_document(ADMIN_ID, doc.file_id, caption=caption, reply_markup=kb)
        except Exception:
            try:
                bot.send_message(ADMIN_ID, caption, reply_markup=kb)
            except Exception:
                pass
        _send_file_preview(ADMIN_ID, doc.file_id, filename)
        return

    if pending and pending.get("type") == "add_file":
        project_id = pending["project_id"]
        proj = db_fetchone("SELECT * FROM projects WHERE id=?", (project_id,))
        if not proj or (proj["user_id"] != uid and not is_admin(uid)):
            pop_pending(uid)
            bot.send_message(message.chat.id, "❌ غير مسموح.")
            return
        file_count = db_fetchone("SELECT COUNT(*) AS c FROM project_files WHERE project_id=?", (project_id,))["c"]
        pending_count = db_fetchone("SELECT COUNT(*) AS c FROM pending_uploads WHERE project_id=?", (project_id,))["c"]
        if file_count + pending_count >= MAX_FILES_PER_PROJECT:
            pop_pending(uid)
            bot.send_message(uid, f"❌ وصلت للحد الأقصى من الملفات ({MAX_FILES_PER_PROJECT}).")
            return
        pending_id = db_execute_returning_id(
            "INSERT INTO pending_uploads (user_id, project_id, filename, telegram_file_id, size_bytes) VALUES (?,?,?,?,?)",
            (uid, project_id, filename, doc.file_id, size),
        )
        pop_pending(uid)
        bot.send_message(uid,
            f"✅ تم استلام الملف <code>{html_escape(filename)}</code>.\n"
            f"⏳ بانتظار مراجعة المطور قبل الإضافة.",
            reply_markup=back_main_kb())
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton(f" موافقة الملف #{pending_id}", callback_data=f"adm_approve_file_{pending_id}",
                style="primary", icon_custom_emoji_id=E_APPROVE),
            types.InlineKeyboardButton(f" رفض الملف #{pending_id}", callback_data=f"adm_reject_file_{pending_id}",
                style="primary", icon_custom_emoji_id=E_REJECT),
        )
        try:
            bot.send_document(
                ADMIN_ID,
                doc.file_id,
                caption=(
                    f"📎 <b>ملف جديد بانتظار المراجعة</b>\n\n"
                    f"البوت: <b>{html_escape(proj['name'])}</b> (#{project_id})\n"
                    f"المالك: <code>{uid}</code>\n"
                    f"الملف: <code>{html_escape(filename)}</code>\n"
                    f"الحجم: {size:,} بايت"
                ),
                reply_markup=kb,
            )
        except Exception:
            try:
                bot.send_message(
                    ADMIN_ID,
                    f"📎 <b>ملف جديد بانتظار المراجعة</b>\n\n"
                    f"البوت: <b>{html_escape(proj['name'])}</b> (#{project_id})\n"
                    f"المالك: <code>{uid}</code>\n"
                    f"الملف: <code>{html_escape(filename)}</code>\n"
                    f"الحجم: {size:,} بايت",
                    reply_markup=kb,
                )
            except Exception:
                pass
        _send_file_preview(ADMIN_ID, doc.file_id, filename)
        return

    bot.send_message(uid, "❌ لا أعرف ماذا أفعل بهذا الملف. حدد عملية أولاً.")


# ============================================================
# 17) معالجة الأوامر النصية للمشرف
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "mods_menu",
    content_types=["text"],
)
def receive_mods_input(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pop_pending(uid)
    if not text or text[0] not in ("+", "-"):
        bot.send_message(uid, "❌ صيغة غير صحيحة. مثال: <code>+123456</code> أو <code>-123456</code>",
                         reply_markup=back_admin_kb())
        return
    op = text[0]
    num = text[1:].strip()
    if not num.lstrip("-").isdigit():
        bot.send_message(uid, "❌ أرسل ID رقمي. أو /cancel.", reply_markup=back_admin_kb())
        return
    target = int(num)
    if op == "+":
        db_execute("INSERT OR IGNORE INTO moderators (user_id, added_by) VALUES (?,?)", (target, uid))
        bot.send_message(uid, f"✅ تم إضافة <code>{target}</code> كمشرف.", reply_markup=back_admin_kb())
    else:
        db_execute("DELETE FROM moderators WHERE user_id=?", (target,))
        bot.send_message(uid, f"✅ تم إزالة <code>{target}</code> من المشرفين.", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "set_section_price",
    content_types=["text"],
)
def receive_section_price(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pop_pending(uid)
    parts = text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.send_message(uid, "❌ صيغة خاطئة. مثال: <code>netlify 5</code>", reply_markup=back_admin_kb())
        return
    section = parts[0].lower()
    val = int(parts[1])
    if section not in {"netlify", "vercel", "terminal"}:
        bot.send_message(uid, "❌ قسم غير معروف. (netlify / vercel / terminal)", reply_markup=back_admin_kb())
        return
    set_setting(f"price_{section}", val)
    bot.send_message(uid, f"✅ تم تعيين سعر {section} إلى <b>{val}</b> نقطة.", reply_markup=back_admin_kb())


# ============================================================
# 18) استقبال الأوامر النصية المعلقة (عامة)
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") in ("proj_term_cmd", "proj_getfile"),
    content_types=["text"],
)
def receive_proj_text_pending(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    ptype = pending.get("type")
    pid = pending.get("project_id")
    if not pid:
        pop_pending(uid)
        return
    proj = db_fetchone("SELECT id, user_id, name FROM projects WHERE id=?", (pid,))
    if not proj or (proj["user_id"] != uid and not is_admin(uid)):
        pop_pending(uid)
        bot.send_message(message.chat.id, "❌ غير مسموح.")
        return

    if ptype == "proj_term_cmd":
        cmd = (message.text or "").strip()
        if not cmd:
            bot.send_message(message.chat.id, "اكتب الأمر.")
            return
        ok, msg = check_and_inc_daily(uid, "terminal", 30)
        if not ok:
            bot.send_message(message.chat.id, msg)
            return
        price = get_section_price("terminal", 0)
        if price > 0 and not is_admin(uid):
            pts_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
            pts = pts_row["p"] if pts_row else 0
            if pts < price:
                bot.send_message(message.chat.id, f"❌ لا تملك نقاط كافية.\n💡 سعر أمر التيرمنال: <b>{price}</b> نقطة.")
                return
            db_execute("UPDATE users SET points = points - ? WHERE id=? AND COALESCE(points,0) >= ?", (price, uid, price))
        bot.send_message(message.chat.id, "⏳ جاري التنفيذ…")
        out = run_project_terminal_command(pid, cmd, timeout_s=20)
        try:
            db_execute("INSERT INTO audit_log (actor_id, action, project_id, command) VALUES (?,?,?,?)",
                       (uid, "terminal_cmd", pid, cmd[:500]))
        except Exception:
            pass
        bot.send_message(message.chat.id, f"🖥️ النتيجة:\n<pre>{html_escape(out)}</pre>")
        return

    if ptype == "proj_getfile":
        rel = (message.text or "").strip().replace("\\", "/")
        if not rel or ".." in rel or rel.startswith("/"):
            bot.send_message(message.chat.id, "❌ اسم ملف غير صحيح.")
            return
        base = os.path.join(PROJECTS_DIR, str(pid))
        abs_path = os.path.normpath(os.path.join(base, rel))
        if not abs_path.startswith(os.path.abspath(base)):
            bot.send_message(message.chat.id, "❌ مسار غير مسموح.")
            return
        if not os.path.isfile(abs_path):
            bot.send_message(message.chat.id, "❌ الملف غير موجود.")
            return
        size = os.path.getsize(abs_path)
        if size > MAX_FILE_SIZE:
            bot.send_message(message.chat.id, "❌ الملف أكبر من الحد المسموح للإرسال.")
            return
        try:
            with open(abs_path, "rb") as fh:
                bot.send_document(message.chat.id, fh, caption=f"📄 {rel}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ فشل إرسال الملف: {e}")
        return


# ============================================================
# محرر الكود — استقبال الكود المعدَّل (نص)
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "proj_file_editing",
    content_types=["text"],
)
def receive_edited_file(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    pid = pending.get("project_id")
    filename = pending.get("filename")
    file_row_id = pending.get("file_row_id")

    if not pid or not filename:
        pop_pending(uid)
        return

    proj = db_fetchone("SELECT id, user_id FROM projects WHERE id=?", (pid,))
    if not proj or (proj["user_id"] != uid and not is_admin(uid)):
        pop_pending(uid)
        bot.send_message(message.chat.id, "❌ غير مسموح.")
        return

    new_content = message.text or ""
    content_bytes = new_content.encode("utf-8")

    if len(content_bytes) > MAX_FILE_SIZE:
        bot.send_message(
            message.chat.id,
            f"❌ الملف كبير جداً ({len(content_bytes)//1024} KB).\n"
            "الحد الأقصى للتعديل النصي: 50 MB.",
        )
        return

    # اقرأ النسخة القديمة من DB لحساب الـ diff
    old_row = db_fetchone(
        "SELECT content, size_bytes FROM project_files WHERE id=? AND project_id=?",
        (file_row_id, pid),
    )
    old_bytes = bytes(old_row["content"]) if old_row else b""
    try:
        old_text = old_bytes.decode("utf-8")
    except UnicodeDecodeError:
        old_text = old_bytes.decode("latin-1", errors="replace")

    # احسب الـ diff
    diff_body, added, removed = _build_diff_preview(old_text, new_content)

    # خزّن المحتوى الجديد في pending (base64 لأمان JSON)
    set_pending(uid, {
        "type": "proj_file_confirm",
        "project_id": pid,
        "filename": filename,
        "file_row_id": file_row_id,
        "new_content_b64": base64.b64encode(content_bytes).decode(),
        "new_size": len(content_bytes),
    })

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ حفظ التعديلات", callback_data=f"proj_save_confirm_{pid}", style="success"),
        types.InlineKeyboardButton("❌ تجاهل", callback_data=f"proj_discard_edit_{pid}", style="danger"),
    )

    no_change = (added == 0 and removed == 0)
    summary = (
        "✅ <b>لا يوجد تغيير</b> — المحتوى مطابق للنسخة الحالية."
        if no_change
        else f"➕ <b>{added}</b> سطر مضاف  |  ➖ <b>{removed}</b> سطر محذوف"
    )

    bot.send_message(
        message.chat.id,
        f"🔍 <b>معاينة التغييرات</b>\n"
        f"📄 <code>{html_escape(filename)}</code>\n\n"
        f"{summary}\n\n"
        f"<pre><code>{diff_body}</code></pre>\n\n"
        "هل تريد <b>حفظ</b> هذه التغييرات؟",
        reply_markup=kb,
    )


# ============================================================
# محرر الكود — استقبال ملف مُرسَل (document) كبديل
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "proj_file_editing",
    content_types=["document"],
)
def receive_edited_file_doc(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    pid = pending.get("project_id")
    filename = pending.get("filename")
    file_row_id = pending.get("file_row_id")

    if not pid or not filename:
        pop_pending(uid)
        return

    proj = db_fetchone("SELECT id, user_id FROM projects WHERE id=?", (pid,))
    if not proj or (proj["user_id"] != uid and not is_admin(uid)):
        pop_pending(uid)
        bot.send_message(message.chat.id, "❌ غير مسموح.")
        return

    doc = message.document
    if doc.file_size > MAX_FILE_SIZE:
        bot.send_message(message.chat.id, "❌ الملف أكبر من الحد المسموح (50 MB).")
        return

    try:
        file_info = bot.get_file(doc.file_id)
        content_bytes = bot.download_file(file_info.file_path)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ فشل تحميل الملف: <code>{html_escape(str(e))}</code>")
        return

    # اقرأ النسخة القديمة من DB لحساب الـ diff
    old_row = db_fetchone(
        "SELECT content FROM project_files WHERE id=? AND project_id=?",
        (file_row_id, pid),
    )
    old_bytes = bytes(old_row["content"]) if old_row else b""

    # حاول حساب diff نصي (إذا كان الملف text)
    is_text_file = any(filename.endswith(ext) for ext in TEXT_PREVIEW_EXTENSIONS) or filename.endswith(".py")
    try:
        old_text = old_bytes.decode("utf-8") if is_text_file else None
        new_text = content_bytes.decode("utf-8") if is_text_file else None
    except UnicodeDecodeError:
        old_text = new_text = None

    if old_text is not None and new_text is not None:
        diff_body, added, removed = _build_diff_preview(old_text, new_text)
        no_change = (added == 0 and removed == 0)
        summary = (
            "✅ <b>لا يوجد تغيير</b> — المحتوى مطابق للنسخة الحالية."
            if no_change
            else f"➕ <b>{added}</b> سطر مضاف  |  ➖ <b>{removed}</b> سطر محذوف"
        )
        diff_section = f"\n\n<pre><code>{diff_body}</code></pre>"
    else:
        summary = f"📦 ملف ثنائي أو غير نصي — الحجم الجديد: <b>{len(content_bytes):,} بايت</b>"
        diff_section = ""

    # خزّن المحتوى الجديد في pending
    set_pending(uid, {
        "type": "proj_file_confirm",
        "project_id": pid,
        "filename": filename,
        "file_row_id": file_row_id,
        "new_content_b64": base64.b64encode(content_bytes).decode(),
        "new_size": len(content_bytes),
    })

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ حفظ التعديلات", callback_data=f"proj_save_confirm_{pid}", style="success"),
        types.InlineKeyboardButton("❌ تجاهل", callback_data=f"proj_discard_edit_{pid}", style="danger"),
    )

    bot.send_message(
        message.chat.id,
        f"🔍 <b>معاينة التغييرات</b>\n"
        f"📄 <code>{html_escape(filename)}</code>\n\n"
        f"{summary}{diff_section}\n\n"
        "هل تريد <b>حفظ</b> هذه التغييرات؟",
        reply_markup=kb,
    )


# ============================================================
# 19) إدارة البوتات
# ============================================================
def list_user_projects(chat_id: int, uid: int, message_id: Optional[int] = None) -> None:
    rows = db_fetchall("SELECT id, name, approved, is_running, main_file FROM projects WHERE user_id=? ORDER BY id", (uid,))
    if not rows:
        text = "📭 لا توجد بوتات بعد. اضغط <b>إضافة بوت جديد</b> للبدء."
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(" إضافة بوت جديد", callback_data="proj_new",
            style="primary", icon_custom_emoji_id=E_NEW))
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
            style="primary", icon_custom_emoji_id=E_BACK))
    else:
        text = "📂 <b>بوتاتك:</b>\n\n"
        kb = types.InlineKeyboardMarkup(row_width=1)
        for p in rows:
            running = manager.is_running(p["id"])
            status = "🟢" if running else ("🟡" if not p["approved"] else "🔴")
            kb.add(types.InlineKeyboardButton(f"{status} {p['name']}", callback_data=f"proj_view_{p['id']}",
                style="primary", icon_custom_emoji_id=E_LIST))
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
            style="primary", icon_custom_emoji_id=E_BACK))
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


_STDLIB_MODULES = {
    "os", "sys", "re", "json", "time", "math", "random", "string", "io", "logging",
    "threading", "subprocess", "signal", "shutil", "sqlite3", "pathlib", "typing",
    "datetime", "collections", "contextlib", "functools", "itertools", "asyncio",
    "socket", "http", "urllib", "html", "csv", "hashlib", "base64", "secrets",
    "tempfile", "glob", "argparse", "pickle", "struct", "uuid", "queue", "traceback",
    "platform", "warnings", "copy", "enum", "dataclasses", "abc", "inspect",
    "concurrent", "multiprocessing", "ssl", "email", "xml", "zipfile", "tarfile",
    "gzip", "bz2", "zlib", "ctypes", "operator", "weakref", "gc", "atexit",
}
_PKG_MAP = {
    "telebot": "pyTelegramBotAPI",
    "telegram": "python-telegram-bot",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "discord": "discord.py",
    "magic": "python-magic",
    "Crypto": "pycryptodome",
    "sklearn": "scikit-learn",
}


def _detect_required_packages(work_dir: str) -> list:
    import re as _re
    found = set()
    if not os.path.isdir(work_dir):
        return []
    for root, _dirs, files in os.walk(work_dir):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    src = fh.read()
            except Exception:
                continue
            for m in _re.finditer(r"^\s*(?:import|from)\s+([a-zA-Z_][\w\.]*)", src, _re.MULTILINE):
                top = m.group(1).split(".")[0]
                if top and top not in _STDLIB_MODULES and not top.startswith("_"):
                    found.add(top)
    return [_PKG_MAP.get(n, n) for n in sorted(found)]


def install_project_requirements(chat_id: int, uid: int, project_id: int, msg_id: Optional[int] = None) -> None:
    p = db_fetchone("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        bot.send_message(chat_id, "❌ البوت غير موجود.")
        return
    if p["user_id"] != uid and not is_admin(uid):
        bot.send_message(chat_id, "❌ لا تملك صلاحية على هذا البوت.")
        return
    work_dir = os.path.join(PROJECTS_DIR, str(project_id))
    req_path = os.path.join(work_dir, "requirements.txt")
    bot.send_message(chat_id, "📦 <b>جارِ تحميل المكتبات…</b>\nقد يستغرق هذا من 10 إلى 60 ثانية.")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    source = ""
    if os.path.isfile(req_path):
        cmd += ["-r", req_path]
        source = "requirements.txt"
    else:
        pkgs = _detect_required_packages(work_dir)
        if not pkgs:
            bot.send_message(chat_id, "ℹ️ لم يتم اكتشاف أي مكتبات خارجية.")
            return
        cmd += pkgs
        source = "اكتشاف تلقائي"
    try:
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, timeout=300)
        out = ((result.stdout or "") + "\n" + (result.stderr or "")).strip() or "(لا يوجد إخراج)"
        snippet = out[-3000:]
        if result.returncode == 0:
            bot.send_message(chat_id, f"✅ <b>تم تحميل المكتبات بنجاح</b>\n📋 المصدر: {html_escape(source)}\n\n"
                             f"<pre>{html_escape(snippet)}</pre>")
        else:
            bot.send_message(chat_id, f"⚠️ <b>فشل تحميل بعض المكتبات</b>\n📋 المصدر: {html_escape(source)}\n\n"
                             f"<pre>{html_escape(snippet)}</pre>")
    except subprocess.TimeoutExpired:
        bot.send_message(chat_id, "❌ انتهت المهلة (5 دقائق).")
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطأ أثناء التثبيت: <code>{html_escape(str(e))}</code>")


def view_project(chat_id: int, uid: int, project_id: int, message_id: Optional[int] = None) -> None:
    p = db_fetchone("SELECT * FROM projects WHERE id=? AND user_id=?", (project_id, uid))
    if not p and not is_admin(uid):
        return
    if not p and is_admin(uid):
        p = db_fetchone("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        return
    files = db_fetchall("SELECT filename, size_bytes FROM project_files WHERE project_id=? ORDER BY filename", (project_id,))
    running = manager.is_running(project_id)
    status_lines = [
        f"📛 <b>{html_escape(p['name'])}</b>",
        f"🆔 <code>{p['id']}</code>",
        f"👤 المالك: <code>{p['user_id']}</code>",
        f"⚙️ الحالة: {'🟢 يعمل' if running else '🔴 متوقف'}",
        f"📄 الملف الرئيسي: <code>{html_escape(p['main_file'] or '-')}</code>",
        f"📁 عدد الملفات: {len(files)}",
        f"✅ موافق عليه: {'نعم' if p['approved'] else 'لا'}",
    ]
    if p["last_error"]:
        status_lines.append(f"⚠️ آخر خطأ: <code>{html_escape(p['last_error'][:200])}</code>")
    text = "\n".join(status_lines)
    if files:
        text += "\n\n<b>الملفات:</b>\n"
        for f in files[:20]:
            text += f"• <code>{html_escape(f['filename'])}</code> ({f['size_bytes']//1024} KB)\n"

    kb = types.InlineKeyboardMarkup(row_width=2)
    if p["approved"]:
        if running:
            kb.add(
                types.InlineKeyboardButton(" إيقاف", callback_data=f"proj_stop_{project_id}",
                    style="danger", icon_custom_emoji_id=E_STOP),
                types.InlineKeyboardButton(" إعادة تشغيل", callback_data=f"proj_restart_{project_id}",
                    style="success", icon_custom_emoji_id=E_RESTART),
            )
        else:
            kb.add(types.InlineKeyboardButton("▶️ تشغيل", callback_data=f"proj_start_{project_id}",
                style="success", icon_custom_emoji_id=E_START))
    kb.add(
        types.InlineKeyboardButton(" إضافة ملف", callback_data=f"proj_addfile_{project_id}",
            style="primary", icon_custom_emoji_id=E_ADD_FILE),
        types.InlineKeyboardButton(" السجل", callback_data=f"proj_log_{project_id}",
            style="primary", icon_custom_emoji_id=E_LOG),
    )
    kb.add(
        types.InlineKeyboardButton(" ملفاتي", callback_data=f"proj_files_{project_id}",
            style="primary", icon_custom_emoji_id=E_FILES),
        types.InlineKeyboardButton(" التيرمنال", callback_data=f"proj_term_{project_id}",
            style="primary", icon_custom_emoji_id=E_TERMINAL),
    )
    kb.add(types.InlineKeyboardButton("✏️ محرر الكود", callback_data=f"proj_editor_{project_id}",
        style="primary", icon_custom_emoji_id=E_TERMINAL))
    kb.add(types.InlineKeyboardButton(" تحميل المكتبات", callback_data=f"proj_install_{project_id}",
        style="primary", icon_custom_emoji_id=E_INSTALL))
    kb.add(types.InlineKeyboardButton(" حذف البوت", callback_data=f"proj_del_{project_id}",
        style="danger", icon_custom_emoji_id=E_DELETE))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="proj_list",
        style="primary", icon_custom_emoji_id=E_BACK))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


# ============================================================
# محرر الكود الداخلي
# ============================================================
MAX_EDIT_CHARS = 3800   # أقصى حجم قابل للإرسال/التعديل كرسالة نصية
DIFF_MAX_CHARS = 2800   # حد عرض الـ diff في رسالة واحدة

import difflib

def _build_diff_preview(old_text: str, new_text: str, max_chars: int = DIFF_MAX_CHARS) -> tuple[str, int, int]:
    """
    يبني نص diff مضغوط بين النسختين.
    يُرجع: (diff_text, added_lines, removed_lines)
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff_gen = difflib.unified_diff(old_lines, new_lines, lineterm="", n=2)
    added = removed = 0
    chunks = []
    total = 0

    for line in diff_gen:
        if line.startswith("+++") or line.startswith("---"):
            continue  # نتخطى رأسية الـ diff
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
        safe = html_escape(line.rstrip("\n"))
        entry = safe + "\n"
        if total + len(entry) > max_chars:
            chunks.append("<i>… تم اختصار بقية الفروق</i>")
            break
        chunks.append(entry)
        total += len(entry)

    body = "".join(chunks) if chunks else "✅ لا يوجد فرق — المحتوى متطابق."
    return body, added, removed


def _save_file_to_disk_and_db(project_id: int, filename: str, content_bytes: bytes) -> None:
    """يحفظ الملف في DB وعلى القرص."""
    db_execute(
        "INSERT INTO project_files (project_id, filename, content, size_bytes) VALUES (?,?,?,?) "
        "ON CONFLICT (project_id, filename) DO UPDATE SET content=excluded.content, "
        "size_bytes=excluded.size_bytes, updated_at=CURRENT_TIMESTAMP",
        (project_id, filename, sqlite3.Binary(content_bytes), len(content_bytes)),
    )
    base = os.path.join(PROJECTS_DIR, str(project_id))
    abs_path = os.path.normpath(os.path.join(base, filename))
    if abs_path.startswith(os.path.abspath(base)):
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as fh:
            fh.write(content_bytes)


def show_editor_files(chat_id: int, uid: int, pid: int, msg_id: int = None) -> None:
    """يعرض قائمة ملفات .py كأزرار للتعديل."""
    proj = db_fetchone("SELECT id, user_id, name FROM projects WHERE id=?", (pid,))
    if not proj or (proj["user_id"] != uid and not is_admin(uid)):
        return

    # جلب كل الملفات من DB مرتبة
    rows = db_fetchall(
        "SELECT id, filename, size_bytes FROM project_files WHERE project_id=? ORDER BY filename",
        (pid,),
    )
    py_rows = [r for r in rows if r["filename"].endswith(".py")]
    other_rows = [r for r in rows if not r["filename"].endswith(".py")]
    all_rows = py_rows + other_rows   # ملفات .py أولاً

    if not all_rows:
        text = (
            "✏️ <b>محرر الكود</b>\n\n"
            "📭 لا توجد ملفات في هذا البوت بعد.\n"
            "أضف ملفات أولاً عبر <b>إضافة ملف</b>."
        )
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"proj_view_{pid}", style="primary"))
        if msg_id:
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
                return
            except Exception:
                pass
        bot.send_message(chat_id, text, reply_markup=kb)
        return

    text = (
        f"✏️ <b>محرر الكود — {html_escape(proj['name'])}</b>\n\n"
        f"📄 {len(all_rows)} ملف — اختر الملف الذي تريد تعديله:"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    for r in all_rows[:30]:
        size_kb = r["size_bytes"] // 1024
        icon = "🐍" if r["filename"].endswith(".py") else "📄"
        label = f"{icon} {r['filename']}  ({size_kb} KB)"
        kb.add(types.InlineKeyboardButton(label, callback_data=f"proj_ef_{pid}_{r['id']}", style="primary"))
    if len(all_rows) > 30:
        kb.add(types.InlineKeyboardButton(f"⚠️ +{len(all_rows)-30} ملف إضافي غير معروض", callback_data="noop"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"proj_view_{pid}", style="primary"))

    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


# ============================================================
# 20) صفحات العرض
# ============================================================
def show_user_stats(chat_id: int, uid: int, message_id: int) -> None:
    rows = db_fetchall("SELECT id, is_running FROM projects WHERE user_id=?", (uid,))
    total = len(rows)
    running = sum(1 for r in rows if manager.is_running(r["id"]))
    size_row = db_fetchone(
        "SELECT COALESCE(SUM(pf.size_bytes),0) AS s FROM project_files pf "
        "JOIN projects p ON p.id = pf.project_id WHERE p.user_id=?", (uid,)
    )
    text = (
        "📊 <b>إحصائياتك</b>\n\n"
        f"📦 عدد البوتات: <b>{total}</b>\n"
        f"⚡ التي تعمل الآن: <b>{running}</b>\n"
        f"💾 حجم ملفاتك: <b>{(size_row['s'] or 0)//1024} KB</b>\n"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def show_points(chat_id: int, uid: int, message_id: int) -> None:
    row = db_fetchone("SELECT COALESCE(points,0) AS points FROM users WHERE id=?", (uid,))
    points = row["points"] if row else 0
    refs_count_row = db_fetchone("SELECT COUNT(*) AS c FROM users WHERE referred_by=?", (uid,))
    refs_count = refs_count_row["c"] if refs_count_row else 0
    bot_username = get_bot_username()
    ref_link = f"https://t.me/{bot_username}?start={uid}"
    share_url = f"https://t.me/share/url?url={ref_link}&text=انضم%20إلى%20بوت%20استضافة%20البوتات%20عبر%20رابطي"
    text = (
        "🎁 <b>قسم تجميع النقاط</b>\n\n"
        "مرحباً بك! قم بمشاركة رابط الإحالة الخاص بك وستحصل على "
        "<b>1 نقطة</b> لكل شخص يدخل عبر الرابط 👇\n\n"
        f"🔗 <code>{ref_link}</code>\n\n"
        f"⭐ نقاطك: <b>{points}</b>\n"
        f"👥 عدد من دخل عبر رابطك: <b>{refs_count}</b>"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" مشاركة الرابط", url=share_url,
        style="primary", icon_custom_emoji_id=E_SHARE))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def start_transfer_points(chat_id: int, uid: int, message_id: int) -> None:
    fee = get_transfer_fee()
    set_pending(uid, {"type": "transfer_recipient"})
    text = (
        "💸 <b>قسم تحويل النقاط:</b>\n\n"
        "أرسل <b>ID</b> المستلم 🎁\n\n"
        "⚠️ أقل عدد يمكن تحويله: <b>5</b>\n"
        f"⚠️ عمولة التحويل: <b>{fee}</b> نقطة\n\n"
        "أو /cancel للإلغاء."
    )
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_main_kb())
    except Exception:
        bot.send_message(chat_id, text, reply_markup=back_main_kb())


def show_help(chat_id: int, message_id: int) -> None:
    allowed = " ".join(sorted(ALLOWED_EXTENSIONS))
    text = (
        "🆘 <b>المساعدة</b>\n\n"
        "📌 <b>رفع بوت (Python)</b>\n"
        "• من الرئيسية اضغط: <b>🚀 إضافة بوت جديد</b>\n"
        "• ابعت اسم للبوت (حروف/أرقام)\n"
        "• ابعت الملف الرئيسي: <code>.py</code>\n"
        "• بعد موافقة الأدمن البوت هيشتغل تلقائياً\n\n"
        "📁 <b>إدارة البوت</b>\n"
        "• من <b>📂 بوتاتي</b> اختار البوت\n"
        "• تقدر: تشغيل / إيقاف / إعادة تشغيل\n"
        "• تقدر تشوف: <b>📜 السجل</b> (آخر مخرجات)\n"
        "• تقدر تشوف: <b>📁 ملفاتي</b> + تحميل ملف\n\n"
        f"📦 الملفات المدعومة: <code>{html_escape(allowed)}</code>\n\n"
        "⚡ <b>رفع موقع (Netlify)</b>\n"
        "• يدعم: <b>HTML / CSS / JS فقط</b>\n"
        "• ارفع <b>.zip</b> لفولدر يحتوي على <code>index.html</code>\n\n"
        "▲ <b>رفع موقع (Vercel)</b>\n"
        "• ارفع <b>.zip</b> يحتوي على <code>index.html</code>\n\n"
        "🖥️ <b>التيرمنال</b>\n"
        "• مسموح فقط أوامر <code>python</code> و <code>pip</code>\n\n"
        f"📞 <b>الدعم</b>\n• {html_escape(ADMIN_CONTACT)}"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def show_user_sites(chat_id: int, uid: int, message_id: Optional[int] = None) -> None:
    nsites = db_fetchall(
        "SELECT provider, site_id, site_url, MAX(created_at) AS created_at FROM ("
        "  SELECT 'netlify' AS provider, site_id, site_url, created_at FROM netlify_sites WHERE user_id=?"
        "  UNION ALL "
        "  SELECT provider, site_id, url AS site_url, created_at FROM deployments WHERE user_id=? AND provider='vercel'"
        ") GROUP BY provider, site_id, site_url ORDER BY created_at DESC LIMIT 20",
        (uid, uid),
    )
    text = "🖥 <b>مواقعي</b>\n\n"
    if not nsites:
        text += "لا يوجد مواقع بعد."
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
            style="primary", icon_custom_emoji_id=E_BACK))
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)
        for r in nsites[:10]:
            prov = "Netlify" if r["provider"] == "netlify" else "Vercel"
            label = f"{prov} — {r['site_url']}"
            kb.add(types.InlineKeyboardButton(label[:60],
                                              callback_data=f"site_redeploy_{r['provider']}_{r['site_id'] or 'x'}",
                                              style="primary", icon_custom_emoji_id=E_SITES))
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
            style="primary", icon_custom_emoji_id=E_BACK))
        text += "اختر موقع لإعادة النشر.\n"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def show_user_deployments(chat_id: int, uid: int, message_id: Optional[int] = None) -> None:
    rows = db_fetchall(
        "SELECT provider, url, filename, size_bytes, created_at FROM deployments "
        "WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,)
    )
    text = "🧾 <b>آخر 5 ديبلويمنتس</b>\n\n"
    if not rows:
        text += "لا يوجد ديبلويمنتس بعد."
    else:
        for r in rows:
            prov = "Netlify" if r["provider"] == "netlify" else "Vercel"
            size_kb = int((r.get("size_bytes") or 0) // 1024)
            fn = r.get("filename") or "-"
            text += f"• <b>{prov}</b>\n  رابط: <code>{html_escape(r['url'])}</code>\n  ملف: {html_escape(fn)} ({size_kb} KB)\n\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="back_main",
        style="primary", icon_custom_emoji_id=E_BACK))
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def show_pending_users(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT id, first_name, username FROM users WHERE approved=0 AND banned=0 ORDER BY created_at DESC LIMIT 30"
    )
    if not rows:
        text = "✨ لا توجد طلبات تفعيل."
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
            style="primary", icon_custom_emoji_id=E_BACK))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        return
    text = "⏳ <b>طلبات تفعيل بانتظار:</b>\n\n"
    kb = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        label = f"{r['first_name'] or '-'} (@{r['username'] or '-'}) [{r['id']}]"
        kb.add(types.InlineKeyboardButton(f" تفعيل {label}", callback_data=f"adm_approve_user_{r['id']}",
            style="primary", icon_custom_emoji_id=E_APPROVE))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_pending_projects(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT p.id, p.name, p.user_id, p.main_file FROM projects p WHERE p.approved=0 ORDER BY p.created_at DESC LIMIT 30"
    )
    if not rows:
        text = "✨ لا توجد بوتات بانتظار الموافقة."
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
            style="primary", icon_custom_emoji_id=E_BACK))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        return
    text = "⏳ <b>بوتات بانتظار الموافقة:</b>\n\n"
    kb = types.InlineKeyboardMarkup(row_width=2)
    for r in rows:
        text += f"• #{r['id']} <b>{html_escape(r['name'])}</b> — مالك <code>{r['user_id']}</code>\n"
        kb.add(
            types.InlineKeyboardButton(f" #{r['id']}", callback_data=f"adm_approve_proj_{r['id']}",
                style="primary", icon_custom_emoji_id=E_APPROVE),
            types.InlineKeyboardButton(f" #{r['id']}", callback_data=f"adm_reject_proj_{r['id']}",
                style="primary", icon_custom_emoji_id=E_REJECT),
        )
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_pending_files(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT pu.id, pu.filename, pu.size_bytes, pu.user_id, pu.project_id, p.name AS proj_name "
        "FROM pending_uploads pu "
        "LEFT JOIN projects p ON p.id = pu.project_id "
        "WHERE pu.project_id IS NOT NULL "
        "ORDER BY pu.created_at ASC LIMIT 30"
    )
    if not rows:
        text = "✨ لا توجد ملفات بانتظار المراجعة."
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
            style="primary", icon_custom_emoji_id=E_BACK))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        return
    text = f"📎 <b>ملفات بانتظار المراجعة ({len(rows)}):</b>\n\n"
    kb = types.InlineKeyboardMarkup(row_width=2)
    for r in rows:
        size_kb = round(r["size_bytes"] / 1024, 1)
        text += (
            f"• <code>{html_escape(r['filename'])}</code> ({size_kb} KB)\n"
            f"  البوت: <b>{html_escape(r['proj_name'] or '-')}</b> — مالك <code>{r['user_id']}</code>\n\n"
        )
        kb.add(
            types.InlineKeyboardButton(f" قبول #{r['id']}", callback_data=f"adm_approve_file_{r['id']}",
                style="primary", icon_custom_emoji_id=E_APPROVE),
            types.InlineKeyboardButton(f" رفض #{r['id']}", callback_data=f"adm_reject_file_{r['id']}",
                style="primary", icon_custom_emoji_id=E_REJECT),
        )
        kb.add(
            types.InlineKeyboardButton(f"👁 معاينة #{r['id']}", callback_data=f"adm_preview_file_{r['id']}",
                style="primary"),
        )
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_all_users(chat_id: int, message_id: int) -> None:
    rows = db_fetchall("SELECT id, first_name, username, approved, banned FROM users ORDER BY created_at DESC LIMIT 50")
    text = "👥 <b>المستخدمون (آخر 50):</b>\n\n"
    for r in rows:
        s = "🟢" if r["approved"] and not r["banned"] else ("🚫" if r["banned"] else "🟡")
        text += f"{s} <code>{r['id']}</code> {html_escape(r['first_name'] or '')} (@{r['username'] or '-'})\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_all_projects(chat_id: int, message_id: int) -> None:
    rows = db_fetchall("SELECT id, user_id, name, approved, is_running FROM projects ORDER BY id DESC LIMIT 50")
    text = "🤖 <b>كل البوتات (آخر 50):</b>\n\n"
    kb = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        running = manager.is_running(r["id"])
        s = "🟢" if running else ("🟡" if not r["approved"] else "🔴")
        kb.add(types.InlineKeyboardButton(f"{s} #{r['id']} {r['name']} — {r['user_id']}", callback_data=f"proj_view_{r['id']}",
            style="primary", icon_custom_emoji_id=E_LIST))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_admin_stats(chat_id: int, message_id: int) -> None:
    counts = db_fetchone(
        "SELECT "
        "(SELECT COUNT(*) FROM users) AS users_total, "
        "(SELECT COUNT(*) FROM users WHERE approved=1) AS users_approved, "
        "(SELECT COUNT(*) FROM users WHERE banned=1) AS users_banned, "
        "(SELECT COUNT(*) FROM projects) AS projects_total, "
        "(SELECT COUNT(*) FROM projects WHERE approved=1) AS projects_approved, "
        "(SELECT COALESCE(SUM(size_bytes),0) FROM project_files) AS total_bytes"
    )
    running = sum(1 for hp in manager.processes.values() if hp.is_alive())
    text = (
        "📈 <b>إحصائيات النظام</b>\n\n"
        f"👥 المستخدمون: {counts['users_total']} (مفعّل {counts['users_approved']}، محظور {counts['users_banned']})\n"
        f"🤖 البوتات: {counts['projects_total']} (موافق عليها {counts['projects_approved']})\n"
        f"⚡ تعمل الآن: <b>{running}</b>\n"
        f"💾 إجمالي ملفات التخزين: {counts['total_bytes']//1024} KB\n"
        f"⏰ الوقت: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" حالة السيرفر", callback_data="adm_server_status",
        style="primary", icon_custom_emoji_id=E_TERMINAL))
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_server_status(chat_id: int, message_id: int) -> None:
    uptime = int(time.time() - _START_TS)
    try:
        du = shutil.disk_usage(os.path.dirname(DB_PATH) or ".")
        disk_line = f"💾 Disk: {du.used//(1024**3)}GB / {du.total//(1024**3)}GB"
    except Exception:
        disk_line = "💾 Disk: (غير متاح)"
    text = (
        "🖥️ <b>حالة السيرفر</b>\n\n"
        f"⏱️ Uptime: <b>{uptime}</b> ثانية\n"
        f"🐍 Python: <code>{html_escape(sys.version.split()[0])}</code>\n"
        f"🧭 Platform: <code>{html_escape(sys.platform)}</code>\n"
        f"{disk_line}\n"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_stats",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def adm_send_backup(chat_id: int) -> None:
    """يرسل نسخة احتياطية من قاعدة البيانات للأدمن."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = f"/tmp/hosting_bot_backup_{ts}.db"
        import shutil as _sh
        _sh.copy2(DB_PATH, backup_path)
        size_kb = os.path.getsize(backup_path) // 1024
        caption = (
            f"💾 <b>نسخة احتياطية من قاعدة البيانات</b>\n"
            f"📅 التاريخ: <code>{ts}</code>\n"
            f"📦 الحجم: <b>{size_kb} KB</b>"
        )
        with open(backup_path, "rb") as f:
            bot.send_document(chat_id, f, caption=caption, visible_file_name=f"db_backup_{ts}.db")
        os.remove(backup_path)
    except Exception as e:
        bot.send_message(chat_id, f"❌ فشل إنشاء النسخة الاحتياطية:\n<code>{html_escape(str(e))}</code>")


def adm_show_growth_stats(chat_id: int, message_id: int) -> None:
    """يعرض إحصائيات نمو المستخدمين والبوتات خلال آخر 7 أيام."""
    lines = ["📊 <b>إحصائيات النمو — آخر 7 أيام</b>\n"]
    for i in range(6, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        u = (db_fetchone(
            "SELECT COUNT(*) AS c FROM users WHERE date(created_at)=?", (d,)) or {}).get("c", 0)
        p = (db_fetchone(
            "SELECT COUNT(*) AS c FROM projects WHERE date(created_at)=?", (d,)) or {}).get("c", 0)
        bar_u = "▓" * min(u, 10) + "░" * max(0, 10 - min(u, 10))
        day_label = "اليوم" if i == 0 else f"قبل {i}ي"
        lines.append(f"📅 <b>{d}</b>  ({day_label})\n   👥 {bar_u} {u} مستخدم  |  🤖 {p} بوت")
    text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_audit_log(chat_id: int, message_id: int) -> None:
    """يعرض آخر 20 حدث في سجل التدقيق."""
    rows = db_fetchall(
        "SELECT actor_id, action, target_uid, project_id, created_at "
        "FROM audit_log ORDER BY id DESC LIMIT 20"
    )
    if not rows:
        text = "📋 <b>سجل التدقيق</b>\n\nلا توجد سجلات حتى الآن."
    else:
        lines = ["📋 <b>سجل التدقيق — آخر 20 حدث</b>\n"]
        for r in rows:
            ts = str(r.get("created_at", ""))[:16]
            actor = r.get("actor_id", "?")
            action = html_escape(str(r.get("action", "")))
            target = f" ← {r['target_uid']}" if r.get("target_uid") else ""
            proj = f" [بوت#{r['project_id']}]" if r.get("project_id") else ""
            lines.append(f"<code>{ts}</code>  <b>{action}</b>{target}{proj}\n  👤 {actor}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_cleanup_stopped_files(chat_id: int) -> None:
    """يحذف مجلدات المشاريع المتوقفة والمحذوفة من الـ DB لتحرير مساحة."""
    try:
        active_ids = {str(r["id"]) for r in db_fetchall("SELECT id FROM projects")}
        removed = 0
        freed_bytes = 0
        if os.path.isdir(PROJECTS_DIR):
            for folder in os.listdir(PROJECTS_DIR):
                folder_path = os.path.join(PROJECTS_DIR, folder)
                if os.path.isdir(folder_path) and folder not in active_ids:
                    try:
                        size = sum(
                            os.path.getsize(os.path.join(dp, f))
                            for dp, _, fnames in os.walk(folder_path)
                            for f in fnames
                        )
                        shutil.rmtree(folder_path)
                        freed_bytes += size
                        removed += 1
                    except Exception:
                        pass
        freed_kb = freed_bytes // 1024
        bot.send_message(
            chat_id,
            f"🧹 <b>تم التنظيف</b>\n\n"
            f"🗂 مجلدات محذوفة: <b>{removed}</b>\n"
            f"💾 مساحة محرَّرة: <b>{freed_kb} KB</b>",
            reply_markup=back_admin_kb()
        )
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطأ أثناء التنظيف:\n<code>{html_escape(str(e))}</code>")


def adm_show_running_bots(chat_id: int, message_id: int) -> None:
    """يعرض قائمة البوتات الشغّالة حالياً مع معلومات صاحبها."""
    rows = db_fetchall(
        "SELECT p.id, p.name, p.user_id, u.first_name, u.username "
        "FROM projects p LEFT JOIN users u ON u.id=p.user_id "
        "WHERE p.approved=1 ORDER BY p.id DESC"
    )
    running_rows = [r for r in rows if manager.is_running(r["id"])]
    if not running_rows:
        text = "⚡ <b>البوتات الشغّالة الآن</b>\n\n😴 لا يوجد أي بوت شغّال حالياً."
    else:
        lines = [f"⚡ <b>البوتات الشغّالة الآن</b>  —  <b>{len(running_rows)}</b> بوت\n"]
        for r in running_rows:
            name = html_escape(r.get("name") or f"#{r['id']}")
            owner = html_escape(r.get("first_name") or "")
            uname = f"@{r['username']}" if r.get("username") else f"<code>{r['user_id']}</code>"
            lines.append(f"🟢 <b>{name}</b>  │  {owner} ({uname})")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="adm_running_bots_list", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_bots", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_export_bots_csv(chat_id: int) -> None:
    """يصدّر جميع البوتات إلى ملف CSV ويرسله للأدمن."""
    try:
        rows = db_fetchall(
            "SELECT p.id, p.name, p.main_file, p.approved, p.is_running, p.created_at, "
            "u.id AS uid, u.first_name, u.username "
            "FROM projects p LEFT JOIN users u ON u.id=p.user_id ORDER BY p.id DESC"
        )
        buf = io.StringIO()
        buf.write("id,name,main_file,approved,is_running,created_at,owner_id,owner_name,owner_username\n")
        for r in rows:
            running = "1" if manager.is_running(r["id"]) else "0"
            buf.write(
                f"{r['id']},{r.get('name','')},{r.get('main_file','')},{r['approved']},"
                f"{running},{r.get('created_at','')},{r.get('uid','')},"
                f"{r.get('first_name','')},{r.get('username','')}\n"
            )
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        data = buf.getvalue().encode("utf-8")
        bio = io.BytesIO(data)
        bio.name = f"bots_export_{ts}.csv"
        bot.send_document(
            chat_id, bio,
            caption=f"📤 <b>تصدير البوتات</b>\n📅 {ts}\n🤖 إجمالي: <b>{len(rows)}</b> بوت"
        )
    except Exception as e:
        bot.send_message(chat_id, f"❌ فشل التصدير:\n<code>{html_escape(str(e))}</code>")


def adm_show_inactive_users(chat_id: int, message_id: int) -> None:
    """يعرض المستخدمين الذين لم يتفاعلوا منذ 30+ يوماً."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    rows = db_fetchall(
        "SELECT id, first_name, username, created_at FROM users "
        "WHERE approved=1 AND banned=0 "
        "AND id NOT IN (SELECT DISTINCT user_id FROM usage_daily WHERE day >= ?) "
        "AND date(created_at) <= ? "
        "ORDER BY created_at ASC LIMIT 40",
        (cutoff, cutoff)
    )
    if not rows:
        text = "👻 <b>المستخدمون الخاملون</b>\n\n✅ لا يوجد مستخدمون خاملون منذ 30 يوماً."
    else:
        lines = [f"👻 <b>المستخدمون الخاملون</b> (30+ يوم)\n<i>إجمالي: {len(rows)} مستخدم</i>\n"]
        for r in rows:
            name = html_escape(r.get("first_name") or "-")
            uname = f"@{r['username']}" if r.get("username") else f"<code>{r['id']}</code>"
            joined = str(r.get("created_at", ""))[:10]
            lines.append(f"💤 {name} ({uname})  │  انضم: {joined}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_users", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_usage_stats(chat_id: int, message_id: int) -> None:
    """يعرض إحصائيات الاستخدام من جدول usage_daily (أكثر الأقسام استخداماً)."""
    rows = db_fetchall(
        "SELECT section, SUM(count) AS total "
        "FROM usage_daily GROUP BY section ORDER BY total DESC LIMIT 15"
    )
    top_users = db_fetchall(
        "SELECT user_id, SUM(count) AS total FROM usage_daily "
        "GROUP BY user_id ORDER BY total DESC LIMIT 5"
    )
    if not rows:
        text = "📊 <b>إحصائيات الاستخدام</b>\n\nلا توجد بيانات بعد."
    else:
        total_all = sum(r["total"] for r in rows)
        lines = [f"📊 <b>إحصائيات الاستخدام</b>  —  إجمالي: <b>{total_all:,}</b> عملية\n"]
        lines.append("<b>🏆 أكثر الأقسام استخداماً:</b>")
        for r in rows:
            pct = int(r["total"] / total_all * 100) if total_all else 0
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            lines.append(f"  <code>{html_escape(r['section']):<18}</code> {bar} {r['total']:,}")
        if top_users:
            lines.append("\n<b>👥 أكثر المستخدمين نشاطاً:</b>")
            for r in top_users:
                uid = r["user_id"]
                u = db_fetchone("SELECT first_name, username FROM users WHERE id=?", (uid,)) or {}
                name = html_escape(u.get("first_name") or str(uid))
                lines.append(f"  • {name}  —  <b>{r['total']:,}</b> عملية")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_start_announce(chat_id: int, uid: int) -> None:
    """يبدأ تدفق إرسال إعلان منسّق لجميع المستخدمين."""
    set_pending(uid, {"type": "adm_announce"})
    bot.send_message(
        chat_id,
        "📣 <b>إعلان منسّق</b>\n\n"
        "أرسل نص الإعلان الآن.\n"
        "يمكنك استخدام HTML: <code>&lt;b&gt;عريض&lt;/b&gt;</code>، <code>&lt;i&gt;مائل&lt;/i&gt;</code>، <code>&lt;code&gt;كود&lt;/code&gt;</code>\n\n"
        "سيُرسَل للجميع بالتنسيق:\n"
        "━━━━━━━━━━━━━━\n"
        "📣 <b>إعلان من الإدارة</b>\n"
        "نص إعلانك هنا\n"
        "━━━━━━━━━━━━━━\n\n"
        "أو /cancel للإلغاء.",
        reply_markup=back_admin_kb()
    )


# ============================================================
# ➕ ميزات الأدمن الجديدة (20 ميزة)
# ============================================================

def adm_new_today(chat_id: int, message_id: int) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = db_fetchall(
        "SELECT id, first_name, username, approved FROM users WHERE date(created_at)=? ORDER BY id DESC",
        (today,)
    )
    if not rows:
        text = f"🆕 <b>مستخدمو اليوم</b> — {today}\n\n😶 لم ينضم أحد اليوم."
    else:
        lines = [f"🆕 <b>مستخدمو اليوم</b> — {today}\nإجمالي: <b>{len(rows)}</b>\n"]
        for r in rows:
            st = "✅" if r["approved"] else "⏳"
            name = html_escape(r.get("first_name") or "-")
            uname = f"@{r['username']}" if r.get("username") else f"<code>{r['id']}</code>"
            lines.append(f"{st} {name} ({uname})")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_users", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_start_user_bots_by_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_user_bots_by_id"})
    bot.send_message(chat_id, "🤖 أرسل <b>ID المستخدم</b> لعرض بوتاته:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_user_bots(chat_id: int, message_id: int, target_uid: int) -> None:
    u = db_fetchone("SELECT first_name, username FROM users WHERE id=?", (target_uid,))
    rows = db_fetchall("SELECT id, name, approved, is_running FROM projects WHERE user_id=? ORDER BY id DESC", (target_uid,))
    uname_str = f"@{u['username']}" if u and u.get("username") else f"<code>{target_uid}</code>"
    name_str = html_escape((u or {}).get("first_name") or str(target_uid))
    if not rows:
        text = f"🤖 <b>بوتات {name_str}</b> ({uname_str})\n\nلا توجد بوتات."
    else:
        lines = [f"🤖 <b>بوتات {name_str}</b> ({uname_str}) — {len(rows)} بوت\n"]
        for r in rows:
            running = manager.is_running(r["id"])
            st = "🟢" if running else ("🟡" if not r["approved"] else "🔴")
            lines.append(f"{st} #{r['id']} — {html_escape(r['name'] or '-')}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_users", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_start_reset_points(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_reset_points_id"})
    bot.send_message(chat_id, "🔄 أرسل <b>ID المستخدم</b> لتصفير نقاطه:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_start_set_user_max(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_set_user_max_step1"})
    bot.send_message(chat_id, "⚙️ أرسل <b>ID المستخدم</b> لضبط حد البوتات له:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_crashed_bots(chat_id: int, message_id: int) -> None:
    rows = db_fetchall("SELECT id, name, user_id FROM projects WHERE approved=1 AND is_running=1")
    crashed = [r for r in rows if not manager.is_running(r["id"])]
    if not crashed:
        text = "💥 <b>البوتات المعطوبة</b>\n\n✅ لا توجد بوتات معطوبة!"
    else:
        lines = [f"💥 <b>البوتات المعطوبة</b> — {len(crashed)} بوت\n<i>(مُعلَّمة شغّالة في DB لكنها متوقفة)</i>\n"]
        for r in crashed:
            lines.append(f"🔴 #{r['id']} — {html_escape(r['name'] or '-')}  │  👤 {r['user_id']}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="adm_crashed_bots", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_bots", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_start_search_bot(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_search_bot_name"})
    bot.send_message(chat_id, "🔍 أرسل <b>اسم البوت</b> أو جزء منه للبحث:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_bots_summary(chat_id: int, message_id: int) -> None:
    c = db_fetchone(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN approved=1 THEN 1 ELSE 0 END) AS approved, "
        "SUM(CASE WHEN approved=0 THEN 1 ELSE 0 END) AS pending, "
        "SUM(CASE WHEN is_running=1 THEN 1 ELSE 0 END) AS db_running "
        "FROM projects"
    ) or {}
    actual_running = sum(1 for hp in manager.processes.values() if hp.is_alive())
    files_c = (db_fetchone("SELECT COUNT(*) AS c FROM project_files") or {}).get("c", 0)
    files_sz = (db_fetchone("SELECT COALESCE(SUM(size_bytes),0) AS s FROM project_files") or {}).get("s", 0)
    text = (
        "📋 <b>ملخص البوتات</b>\n\n"
        f"📦 الإجمالي: <b>{c.get('total',0)}</b>\n"
        f"✅ موافق عليها: <b>{c.get('approved',0)}</b>\n"
        f"⏳ بانتظار موافقة: <b>{c.get('pending',0)}</b>\n"
        f"🟢 تعمل فعلاً: <b>{actual_running}</b>\n"
        f"🔴 متوقفة: <b>{(c.get('approved',0) or 0) - actual_running}</b>\n"
        f"📁 إجمالي الملفات: <b>{files_c:,}</b>\n"
        f"💾 مساحة الملفات: <b>{files_sz//1024:,} KB</b>"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_bots", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_clear_process_logs(chat_id: int) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    c = (db_fetchone("SELECT COUNT(*) AS c FROM process_logs WHERE date(created_at)<?", (cutoff,)) or {}).get("c", 0)
    db_execute("DELETE FROM process_logs WHERE date(created_at)<?", (cutoff,))
    bot.send_message(chat_id, f"🧹 <b>تنظيف سجلات العمليات</b>\n\n✅ حُذف <b>{c:,}</b> سجل (أقدم من 7 أيام).", reply_markup=back_admin_kb())


def adm_start_msg_inactive(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_msg_to_inactive"})
    bot.send_message(
        chat_id,
        "💤 <b>رسالة للمستخدمين الخاملين</b>\n\n"
        "أرسل نص الرسالة الآن — ستُرسَل لكل من لم يستخدم البوت منذ 30+ يوم.\n"
        "/cancel للإلغاء.",
        reply_markup=back_admin_kb()
    )


def adm_start_broadcast_active(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_broadcast_active"})
    bot.send_message(
        chat_id,
        "✅ <b>إذاعة للمفعّلين فقط</b>\n\n"
        "أرسل الرسالة الآن — ستصل فقط للمستخدمين المفعَّلين غير المحظورين.\n"
        "/cancel للإلغاء.",
        reply_markup=back_admin_kb()
    )


def adm_show_receivers_count(chat_id: int, message_id: int) -> None:
    all_u  = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=0") or {}).get("c", 0)
    active = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=0 AND approved=1") or {}).get("c", 0)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    inactive = (db_fetchone(
        "SELECT COUNT(*) AS c FROM users WHERE approved=1 AND banned=0 "
        "AND id NOT IN (SELECT DISTINCT user_id FROM usage_daily WHERE day>=?) "
        "AND date(created_at)<=?", (cutoff, cutoff)
    ) or {}).get("c", 0)
    text = (
        "🔢 <b>عداد المستقبلين</b>\n\n"
        f"📢 إذاعة عادية (كل غير المحظورين): <b>{all_u:,}</b>\n"
        f"✅ إذاعة للمفعّلين فقط: <b>{active:,}</b>\n"
        f"💤 رسالة الخاملين (30+ي): <b>{inactive:,}</b>"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_comms", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_db_table_stats(chat_id: int, message_id: int) -> None:
    tables = ["users", "projects", "project_files", "pending_uploads",
              "process_logs", "settings", "gift_links", "netlify_sites",
              "deployments", "usage_daily", "audit_log", "force_channels", "moderators"]
    lines = ["🗃 <b>إحصائيات جداول قاعدة البيانات</b>\n"]
    for t in tables:
        try:
            c = (db_fetchone(f"SELECT COUNT(*) AS c FROM {t}") or {}).get("c", 0)
            lines.append(f"  <code>{t:<20}</code> {c:>8,} سجل")
        except Exception:
            lines.append(f"  <code>{t:<20}</code>  —")
    try:
        sz = os.path.getsize(DB_PATH) // 1024
        lines.append(f"\n💾 حجم الـ DB: <b>{sz:,} KB</b>")
    except Exception:
        pass
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text("\n".join(lines), chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


def adm_show_deploy_stats(chat_id: int, message_id: int) -> None:
    netlify_c = (db_fetchone("SELECT COUNT(*) AS c FROM netlify_sites") or {}).get("c", 0)
    vercel_c  = (db_fetchone("SELECT COUNT(*) AS c FROM deployments WHERE provider='vercel'") or {}).get("c", 0)
    netlify_u = (db_fetchone("SELECT COUNT(DISTINCT user_id) AS c FROM netlify_sites") or {}).get("c", 0)
    vercel_u  = (db_fetchone("SELECT COUNT(DISTINCT user_id) AS c FROM deployments WHERE provider='vercel'") or {}).get("c", 0)
    total_sz  = (db_fetchone("SELECT COALESCE(SUM(size_bytes),0) AS s FROM deployments") or {}).get("s", 0)
    recent = db_fetchall(
        "SELECT provider, filename, url, created_at FROM deployments ORDER BY id DESC LIMIT 5"
    )
    lines = [
        "🚀 <b>إحصائيات الرفع (Deploy)</b>\n",
        f"🌐 Netlify:  <b>{netlify_c}</b> موقع  │  {netlify_u} مستخدم",
        f"▲ Vercel:   <b>{vercel_c}</b> نشر    │  {vercel_u} مستخدم",
        f"💾 إجمالي الحجم: <b>{total_sz//1024:,} KB</b>",
    ]
    if recent:
        lines.append("\n<b>📋 آخر 5 نشرات:</b>")
        for r in recent:
            ts = str(r.get("created_at",""))[:10]
            lines.append(f"  {r['provider']} │ {html_escape(r.get('filename',''))} │ {ts}")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text("\n".join(lines), chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


def adm_send_daily_report(chat_id: int) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    new_u   = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE date(created_at)=?", (today,)) or {}).get("c", 0)
    new_p   = (db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE date(created_at)=?", (today,)) or {}).get("c", 0)
    total_u = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=0") or {}).get("c", 0)
    active  = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE approved=1 AND banned=0") or {}).get("c", 0)
    running = sum(1 for hp in manager.processes.values() if hp.is_alive())
    total_p = (db_fetchone("SELECT COUNT(*) AS c FROM projects") or {}).get("c", 0)
    deploys_today = (db_fetchone("SELECT COUNT(*) AS c FROM deployments WHERE date(created_at)=?", (today,)) or {}).get("c", 0)
    sv = get_server_quick_info()
    text = (
        f"📅 <b>التقرير اليومي — {today}</b>\n"
        f"{'━'*28}\n"
        f"👥 مستخدمون جدد اليوم: <b>{new_u}</b>\n"
        f"🤖 بوتات جديدة اليوم: <b>{new_p}</b>\n"
        f"🚀 نشرات اليوم: <b>{deploys_today}</b>\n"
        f"{'─'*28}\n"
        f"👥 إجمالي المستخدمين: <b>{total_u}</b>  (مفعّل {active})\n"
        f"🤖 إجمالي البوتات: <b>{total_p}</b>  (شغّال {running})\n"
        f"{'─'*28}\n"
        f"🖥 <b>السيرفر:</b>\n{sv}"
    )
    bot.send_message(chat_id, text, reply_markup=back_admin_kb())


def adm_show_points_dist(chat_id: int, message_id: int) -> None:
    stats = db_fetchone(
        "SELECT COUNT(*) AS total, COALESCE(SUM(points),0) AS s, "
        "COALESCE(AVG(points),0) AS avg, COALESCE(MAX(points),0) AS mx, "
        "SUM(CASE WHEN points=0 THEN 1 ELSE 0 END) AS zero_c "
        "FROM users WHERE banned=0"
    ) or {}
    top5 = db_fetchall(
        "SELECT first_name, username, COALESCE(points,0) AS points "
        "FROM users WHERE banned=0 ORDER BY points DESC LIMIT 5"
    )
    lines = [
        "💎 <b>توزيع النقاط</b>\n",
        f"📊 إجمالي النقاط: <b>{int(stats.get('s',0)):,}</b>",
        f"📈 المتوسط: <b>{int(stats.get('avg',0)):,}</b>",
        f"🏆 الأعلى: <b>{int(stats.get('mx',0)):,}</b>",
        f"😶 مستخدمون بصفر نقطة: <b>{stats.get('zero_c',0)}</b> / {stats.get('total',0)}",
    ]
    if top5:
        lines.append("\n<b>🥇 أعلى 5 نقاطاً:</b>")
        for i, r in enumerate(top5, 1):
            n = html_escape(r.get("first_name") or "-")
            lines.append(f"  {i}. {n} — <b>{int(r['points']):,}</b> نقطة")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text("\n".join(lines), chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


def adm_show_all_settings(chat_id: int, message_id: int) -> None:
    keys = [
        ("upload_price", "💰 سعر الرفع"),
        ("transfer_fee", "💸 عمولة التحويل"),
        ("bot_disabled", "🔴 البوت معطّل"),
        ("auto_approve", "✅ قبول تلقائي"),
        ("welcome_text", "✏️ نص الترحيب"),
        ("notify_admin_new_user", "🔔 إشعار الجدد"),
        ("btn_style_theme", "🎨 ثيم الأزرار"),
    ]
    lines = ["📋 <b>كل الإعدادات الحالية</b>\n"]
    for k, label in keys:
        v = get_setting(k, "—") or "—"
        if len(v) > 40:
            v = v[:37] + "…"
        lines.append(f"  {label}: <code>{html_escape(v)}</code>")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_settings", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text("\n".join(lines), chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


def adm_toggle_auto_approve_fn(chat_id: int, message_id: int) -> None:
    current = (get_setting("auto_approve", "0") or "0") == "1"
    new_val = "0" if current else "1"
    set_setting("auto_approve", new_val)
    state = "✅ مفعّل" if new_val == "1" else "❌ معطّل"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تبديل مرة أخرى", callback_data="adm_toggle_auto_approve", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_settings", style="primary", icon_custom_emoji_id=E_BACK))
    text = f"🤖 <b>القبول التلقائي للمستخدمين الجدد</b>\n\nالحالة الآن: <b>{state}</b>"
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_clear_old_audit(chat_id: int) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    c = (db_fetchone("SELECT COUNT(*) AS c FROM audit_log WHERE date(created_at)<?", (cutoff,)) or {}).get("c", 0)
    db_execute("DELETE FROM audit_log WHERE date(created_at)<?", (cutoff,))
    bot.send_message(chat_id, f"🗑 <b>تنظيف سجل التدقيق</b>\n\n✅ حُذف <b>{c:,}</b> سجل (أقدم من 30 يوم).", reply_markup=back_admin_kb())


def adm_start_approve_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_approve_id"})
    bot.send_message(chat_id, "✅ أرسل <b>ID المستخدم</b> لتفعيله:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_proc_info(chat_id: int, message_id: int) -> None:
    rows = db_fetchall("SELECT id, name, user_id FROM projects WHERE approved=1")
    running_rows = [(r, manager.processes.get(r["id"])) for r in rows if manager.is_running(r["id"])]
    if not running_rows:
        text = "⚙️ <b>معلومات العمليات الحية</b>\n\n😴 لا توجد عمليات نشطة."
    else:
        lines = [f"⚙️ <b>معلومات العمليات الحية</b> — {len(running_rows)} بوت\n"]
        for r, hp in running_rows:
            pid = getattr(hp, "pid", None) or (getattr(hp, "process", None) and getattr(hp.process, "pid", None))
            alive = "✅" if hp and hp.is_alive() else "❌"
            lines.append(f"{alive} <b>{html_escape(r['name'] or '-')}</b>  │  PID: <code>{pid or '?'}</code>  │  👤 {r['user_id']}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="adm_proc_info", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_bots", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


# ── مساعد: هل الإعداد auto_approve مفعّل ──
def is_auto_approve() -> bool:
    return (get_setting("auto_approve", "0") or "0") == "1"


# ============================================================
# ➕ ميزات الأدمن الجديدة — الدفعة الثالثة (20 ميزة)
# ============================================================

# ── Users ──
def adm_show_user_profile(chat_id: int, message_id: int | None, target: int) -> None:
    u = db_fetchone(
        "SELECT id, first_name, last_name, username, approved, banned, "
        "COALESCE(points,0) AS points, COALESCE(max_bots,0) AS max_bots, "
        "created_at FROM users WHERE id=?", (target,)
    )
    if not u:
        text = f"❌ المستخدم <code>{target}</code> غير موجود في قاعدة البيانات."
    else:
        bots_c = (db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE user_id=?", (target,)) or {}).get("c", 0)
        running_c = sum(1 for pid, hp in manager.processes.items()
                        if hp.is_alive() and
                        (db_fetchone("SELECT user_id FROM projects WHERE id=?", (pid,)) or {}).get("user_id") == target)
        deploys_c = (db_fetchone("SELECT COUNT(*) AS c FROM deployments WHERE user_id=?", (target,)) or {}).get("c", 0)
        name = html_escape((u.get("first_name") or "") + " " + (u.get("last_name") or "")).strip()
        uname = f"@{u['username']}" if u.get("username") else "—"
        status = "✅ مفعّل" if u["approved"] else "⏳ منتظر"
        if u["banned"]: status = "🚫 محظور"
        text = (
            f"📄 <b>ملف مستخدم</b>\n\n"
            f"👤 الاسم: <b>{name or '—'}</b>\n"
            f"🆔 ID: <code>{u['id']}</code>\n"
            f"📛 يوزر: {uname}\n"
            f"⚡ الحالة: {status}\n"
            f"💎 النقاط: <b>{int(u['points']):,}</b>\n"
            f"🤖 البوتات: <b>{bots_c}</b>  (شغّال: {running_c})\n"
            f"🚀 النشرات: <b>{deploys_c}</b>\n"
            f"⚙️ حد البوتات: <b>{u['max_bots'] or 'الافتراضي'}</b>\n"
            f"📅 تاريخ التسجيل: {str(u.get('created_at',''))[:10]}"
        )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_users", style="primary", icon_custom_emoji_id=E_BACK))
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def adm_start_user_profile(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_user_profile"})
    bot.send_message(chat_id, "📄 أرسل <b>ID المستخدم</b> لعرض ملفه الكامل:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_pending_users(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT id, first_name, username, created_at FROM users WHERE approved=0 AND banned=0 ORDER BY id DESC LIMIT 30"
    )
    if not rows:
        text = "⏳ <b>المستخدمون المنتظرون موافقة</b>\n\n✅ لا أحد في قائمة الانتظار!"
    else:
        lines = [f"⏳ <b>المنتظرون موافقة</b> — {len(rows)}\n"]
        for r in rows:
            name = html_escape(r.get("first_name") or "-")
            uname = f"@{r['username']}" if r.get("username") else f"<code>{r['id']}</code>"
            dt = str(r.get("created_at",""))[:10]
            lines.append(f"  👤 {name} ({uname}) │ {dt}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_users", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_start_ban_by_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_ban_by_id"})
    bot.send_message(chat_id, "🚫 أرسل <b>ID المستخدم</b> لحظره:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_start_unban_by_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_unban_by_id"})
    bot.send_message(chat_id, "✅ أرسل <b>ID المستخدم</b> لرفع حظره:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_vip_users(chat_id: int, message_id: int) -> None:
    top_pts = db_fetchall(
        "SELECT id, first_name, username, COALESCE(points,0) AS points "
        "FROM users WHERE banned=0 AND approved=1 ORDER BY points DESC LIMIT 10"
    )
    top_bots = db_fetchall(
        "SELECT user_id, COUNT(*) AS c FROM projects GROUP BY user_id ORDER BY c DESC LIMIT 5"
    )
    lines = ["👑 <b>VIP المستخدمين</b>\n\n🏆 <b>أعلى نقاطاً:</b>"]
    for i, r in enumerate(top_pts, 1):
        name = html_escape(r.get("first_name") or "-")
        uname = f"@{r['username']}" if r.get("username") else f"<code>{r['id']}</code>"
        lines.append(f"  {i}. {name} ({uname}) — <b>{int(r['points']):,}</b> نقطة")
    lines.append("\n🤖 <b>أكثر بوتات:</b>")
    for r in top_bots:
        u = db_fetchone("SELECT first_name, username FROM users WHERE id=?", (r["user_id"],)) or {}
        name = html_escape(u.get("first_name") or str(r["user_id"]))
        lines.append(f"  {name} — <b>{r['c']}</b> بوت")
    text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_users", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


# ── Bots ──
def adm_start_force_stop_bot(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_force_stop_bot"})
    bot.send_message(chat_id, "⏹ أرسل <b>ID البوت</b> لإيقافه:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_start_force_start_bot(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_force_start_bot"})
    bot.send_message(chat_id, "▶️ أرسل <b>ID البوت</b> لتشغيله:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_start_bot_files_info(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_bot_files_info"})
    bot.send_message(chat_id, "📁 أرسل <b>ID البوت</b> لعرض ملفاته:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_show_top_bots(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT p.id, p.name, p.user_id, COUNT(f.id) AS fc, COALESCE(SUM(f.size_bytes),0) AS sz "
        "FROM projects p LEFT JOIN project_files f ON f.project_id=p.id "
        "GROUP BY p.id ORDER BY sz DESC LIMIT 15"
    )
    if not rows:
        text = "📦 <b>أكبر البوتات حجماً</b>\n\nلا يوجد بيانات."
    else:
        lines = ["📦 <b>أكبر البوتات حجماً</b>\n"]
        for i, r in enumerate(rows, 1):
            running = "🟢" if manager.is_running(r["id"]) else "🔴"
            sz_kb = r["sz"] // 1024
            lines.append(f"{running} {i}. #{r['id']} {html_escape(r['name'] or '-')} │ {r['fc']} ملف │ {sz_kb:,} KB")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_bots", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_new_bots_today(chat_id: int, message_id: int) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = db_fetchall(
        "SELECT id, name, user_id, approved FROM projects WHERE date(created_at)=? ORDER BY id DESC",
        (today,)
    )
    if not rows:
        text = f"🆕 <b>بوتات اليوم</b> — {today}\n\n😶 لم يُضَف أي بوت اليوم."
    else:
        lines = [f"🆕 <b>بوتات اليوم</b> — {today}\nالإجمالي: <b>{len(rows)}</b>\n"]
        for r in rows:
            st = "✅" if r["approved"] else "⏳"
            lines.append(f"{st} #{r['id']} {html_escape(r['name'] or '-')} │ 👤 {r['user_id']}")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_bots", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


# ── Comms ──
def adm_start_msg_by_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_msg_by_id_step1"})
    bot.send_message(chat_id, "💬 أرسل <b>ID المستخدم</b> لإرسال رسالة له:\n/cancel للإلغاء.", reply_markup=back_admin_kb())


def adm_start_broadcast_pending(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "adm_broadcast_pending"})
    bot.send_message(
        chat_id,
        "⏳ <b>رسالة للمنتظرين الموافقة</b>\n\n"
        "أرسل الرسالة الآن — ستصل لكل من لم يُفعَّل بعد.\n"
        "/cancel للإلغاء.",
        reply_markup=back_admin_kb()
    )


def adm_show_last_broadcast_stats(chat_id: int, message_id: int) -> None:
    row = db_fetchone(
        "SELECT action, created_at FROM audit_log WHERE action LIKE 'broadcast%' ORDER BY id DESC LIMIT 1"
    )
    total_u  = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=0") or {}).get("c", 0)
    active_u = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=0 AND approved=1") or {}).get("c", 0)
    blocked  = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE blocked_bot=1") or {}).get("c", 0)
    text = (
        "📊 <b>إحصائيات الإذاعات</b>\n\n"
        f"👥 إجمالي المستخدمين (غير محظورين): <b>{total_u:,}</b>\n"
        f"✅ مفعَّلون: <b>{active_u:,}</b>\n"
        f"🚫 حظروا البوت: <b>{blocked:,}</b>\n"
    )
    if row:
        text += f"\n📋 آخر إذاعة: <code>{row['action']}</code>\n🕐 التاريخ: {str(row.get('created_at',''))[:16]}"
    else:
        text += "\n📋 لا يوجد سجل إذاعة سابق."
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_comms", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


# ── Stats ──
def adm_send_weekly_report(chat_id: int) -> None:
    today = datetime.now(timezone.utc)
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    new_u   = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE date(created_at)>=?", (week_ago,)) or {}).get("c", 0)
    new_p   = (db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE date(created_at)>=?", (week_ago,)) or {}).get("c", 0)
    deploys = (db_fetchone("SELECT COUNT(*) AS c FROM deployments WHERE date(created_at)>=?", (week_ago,)) or {}).get("c", 0)
    total_u = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE banned=0") or {}).get("c", 0)
    total_p = (db_fetchone("SELECT COUNT(*) AS c FROM projects") or {}).get("c", 0)
    running = sum(1 for hp in manager.processes.values() if hp.is_alive())
    sv = get_server_quick_info()
    text = (
        f"📆 <b>التقرير الأسبوعي</b>\n"
        f"من {week_ago} → {today_str}\n"
        f"{'━'*28}\n"
        f"👥 مستخدمون جدد هذا الأسبوع: <b>{new_u}</b>\n"
        f"🤖 بوتات جديدة: <b>{new_p}</b>\n"
        f"🚀 نشرات: <b>{deploys}</b>\n"
        f"{'─'*28}\n"
        f"👥 إجمالي المستخدمين: <b>{total_u}</b>\n"
        f"🤖 إجمالي البوتات: <b>{total_p}</b>  (شغّال {running})\n"
        f"{'─'*28}\n"
        f"🖥 <b>السيرفر:</b>\n{sv}"
    )
    bot.send_message(chat_id, text, reply_markup=back_admin_kb())


def adm_show_top_uploaders(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT user_id, COUNT(*) AS c, COALESCE(SUM(size_bytes),0) AS sz "
        "FROM deployments GROUP BY user_id ORDER BY c DESC LIMIT 15"
    )
    if not rows:
        text = "🏆 <b>أكثر المستخدمين رفعاً</b>\n\nلا يوجد بيانات رفع بعد."
    else:
        lines = ["🏆 <b>أكثر المستخدمين رفعاً</b>\n"]
        for i, r in enumerate(rows, 1):
            u = db_fetchone("SELECT first_name, username FROM users WHERE id=?", (r["user_id"],)) or {}
            name = html_escape(u.get("first_name") or str(r["user_id"]))
            uname = f"@{u['username']}" if u.get("username") else f"<code>{r['user_id']}</code>"
            lines.append(f"  {i}. {name} ({uname}) │ <b>{r['c']}</b> رفعة │ {r['sz']//1024:,} KB")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_error_log(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT project_id, event, message, created_at FROM process_logs "
        "WHERE event='error' ORDER BY id DESC LIMIT 20"
    )
    if not rows:
        text = "🔴 <b>آخر أخطاء العمليات</b>\n\n✅ لا أخطاء مسجّلة!"
    else:
        lines = [f"🔴 <b>آخر أخطاء العمليات</b> — {len(rows)} خطأ\n"]
        for r in rows:
            ts = str(r.get("created_at",""))[:16]
            msg = html_escape(str(r.get("message",""))[:80])
            lines.append(f"  🤖 #{r['project_id']} │ {ts}\n  <code>{msg}</code>")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="adm_error_log_view", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_activity_stats(chat_id: int, message_id: int) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = db_fetchall(
        "SELECT section, SUM(count) AS total FROM usage_daily WHERE day=? GROUP BY section ORDER BY total DESC",
        (today,)
    )
    total_active = (db_fetchone(
        "SELECT COUNT(DISTINCT user_id) AS c FROM usage_daily WHERE day=?", (today,)
    ) or {}).get("c", 0)
    if not rows:
        text = f"📈 <b>نشاط اليوم</b> — {today}\n\n😶 لا نشاط مسجّل اليوم."
    else:
        lines = [f"📈 <b>نشاط اليوم</b> — {today}\n👤 مستخدمون نشطون: <b>{total_active}</b>\n"]
        for r in rows:
            lines.append(f"  📌 {html_escape(r['section'] or '-')}: <b>{int(r['total']):,}</b> طلب")
        text = "\n".join(lines)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="adm_activity_stats", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_stats", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


# ── System / Settings ──
def adm_toggle_maintenance(chat_id: int, message_id: int) -> None:
    current = (get_setting("bot_disabled", "0") or "0") == "1"
    new_val = "0" if current else "1"
    set_setting("bot_disabled", new_val)
    state = "🔴 البوت في وضع الصيانة الآن" if new_val == "1" else "🟢 البوت يعمل بشكل طبيعي"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تبديل مرة أخرى", callback_data="adm_maintenance_mode", style="danger"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_settings", style="primary", icon_custom_emoji_id=E_BACK))
    text = f"🔧 <b>وضع الصيانة</b>\n\n{state}"
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_show_sys_info(chat_id: int, message_id: int) -> None:
    import sys, platform
    py_ver = sys.version.split()[0]
    platform_str = platform.platform()
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=0.3)
        mem_used = mem.used // (1024**2)
        mem_total = mem.total // (1024**2)
        disk = psutil.disk_usage("/")
        disk_used = disk.used // (1024**3)
        disk_total = disk.total // (1024**3)
        sv_block = (
            f"🧠 RAM: <b>{mem_used} / {mem_total} MB</b> ({mem.percent}%)\n"
            f"🖥 CPU: <b>{cpu_pct}%</b>\n"
            f"💾 Disk: <b>{disk_used} / {disk_total} GB</b> ({disk.percent}%)"
        )
    except ImportError:
        sv_block = "⚠️ psutil غير متاح"
    db_sz = 0
    try:
        db_sz = os.path.getsize(DB_PATH) // 1024
    except Exception:
        pass
    text = (
        "🖥 <b>معلومات النظام</b>\n\n"
        f"🐍 Python: <code>{py_ver}</code>\n"
        f"🖥 Platform: <code>{platform_str[:60]}</code>\n"
        f"💾 حجم DB: <b>{db_sz:,} KB</b>\n"
        f"🤖 بوتات شغّالة: <b>{sum(1 for hp in manager.processes.values() if hp.is_alive())}</b>\n"
        f"{'─'*28}\n"
        f"{sv_block}"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="adm_sys_info", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_sec_settings", style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def adm_clear_blocked_db(chat_id: int) -> None:
    c = (db_fetchone("SELECT COUNT(*) AS c FROM users WHERE blocked_bot=1") or {}).get("c", 0)
    db_execute("UPDATE users SET blocked_bot=0 WHERE blocked_bot=1")
    bot.send_message(
        chat_id,
        f"🧹 <b>تنظيف قاعدة المحظورين</b>\n\n"
        f"✅ تمّ إعادة تعيين علامة blocked_bot لـ <b>{c:,}</b> مستخدم.\n"
        f"<i>ملاحظة: هذا لا يرفع الحظر الفعلي، فقط يعيد تعيين الـ flag.</i>",
        reply_markup=back_admin_kb()
    )


def show_top_users(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT id, first_name, username, COALESCE(points,0) AS points "
        "FROM users WHERE banned=0 ORDER BY points DESC LIMIT 20"
    )
    text = "🏆 <b>أعلى 20 مستخدم نقاطاً</b>\n\n"
    for i, r in enumerate(rows, 1):
        name = html_escape(r.get("first_name") or "-")
        uname = f"@{r['username']}" if r.get("username") else f"<code>{r['id']}</code>"
        text += f"{i}. {name} ({uname}) — <b>{r['points']}</b> نقطة\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)


def show_blocked_users_report(chat_id: int, uid: int) -> None:
    def _scan():
        rows = db_fetchall("SELECT id FROM users WHERE banned=0")
        blocked = []
        for r in rows:
            try:
                bot.send_chat_action(r["id"], "typing")
                db_execute("UPDATE users SET blocked_bot=0 WHERE id=?", (r["id"],))
            except Exception as e:
                err = str(e).lower()
                if "blocked" in err or "deactivated" in err or "not found" in err or "forbidden" in err:
                    blocked.append(r["id"])
                    db_execute("UPDATE users SET blocked_bot=1 WHERE id=?", (r["id"],))
            time.sleep(0.08)
        total = len(rows)
        b_count = len(blocked)
        ids_text = "\n".join(f"• <code>{x}</code>" for x in blocked[:50])
        more_txt = f"\n… و{b_count-50} أكثر" if b_count > 50 else ""
        msg = (
            f"🔍 <b>نتيجة الفحص</b>\n\n"
            f"👥 إجمالي الفحص: <b>{total}</b>\n"
            f"🚫 حظروا البوت: <b>{b_count}</b>\n\n"
        )
        if blocked:
            msg += f"<b>القائمة:</b>\n{ids_text}{more_txt}"
        try:
            bot.send_message(uid, msg, reply_markup=back_admin_kb())
        except Exception:
            pass
    threading.Thread(target=_scan, daemon=True).start()
    bot.send_message(chat_id, "🔍 جارِ الفحص… ستصلك النتيجة قريباً.", reply_markup=back_admin_kb())


def export_users_file(chat_id: int) -> None:
    rows = db_fetchall(
        "SELECT id, first_name, username, approved, banned, COALESCE(points,0) AS points, "
        "COALESCE(blocked_bot,0) AS blocked_bot, created_at FROM users ORDER BY id"
    )
    lines = ["id,first_name,username,approved,banned,points,blocked_bot,created_at"]
    for r in rows:
        lines.append(",".join([
            str(r["id"]),
            (r.get("first_name") or "").replace(",", " "),
            (r.get("username") or ""),
            str(r["approved"]), str(r["banned"]), str(r["points"]),
            str(r.get("blocked_bot") or 0), str(r.get("created_at") or ""),
        ]))
    csv_bytes = "\n".join(lines).encode("utf-8")
    bio = io.BytesIO(csv_bytes)
    bio.name = f"users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    bot.send_document(chat_id, bio, caption=f"📤 قائمة المستخدمين — {len(rows)} مستخدم", reply_markup=back_admin_kb())


# ============================================================
# 21) إعدادات الأدمن
# ============================================================
def start_set_upload_price(chat_id: int, uid: int) -> None:
    cur = get_upload_price()
    set_pending(uid, {"type": "set_upload_price"})
    bot.send_message(chat_id, f"💰 <b>تعديل سعر رفع البوت</b>\n\nالسعر الحالي: <b>{cur}</b> نقطة\n\n"
                     "أرسل العدد الجديد (0 = مجاني).\nأو /cancel للإلغاء.", reply_markup=back_admin_kb())


def start_set_transfer_fee(chat_id: int, uid: int) -> None:
    cur = get_transfer_fee()
    set_pending(uid, {"type": "set_transfer_fee"})
    bot.send_message(chat_id, f"💸 <b>تعديل عمولة التحويل</b>\n\nالعمولة الحالية: <b>{cur}</b> نقطة\n\n"
                     "أرسل العدد الجديد (0 = بدون عمولة).\nأو /cancel للإلغاء.", reply_markup=back_admin_kb())


def show_force_channels_panel(chat_id: int, uid: int, msg_id: int = None) -> None:
    channels = get_force_channels()
    count = len(channels)
    text = (
        "📢 <b>إدارة الاشتراك الإجباري</b>\n\n"
        f"📋 عدد القنوات المفعّلة: <b>{count}</b>\n\n"
        "اختر العملية المطلوبة:"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("➕ إضافة قناة", callback_data="adm_fc_add", style="primary"))
    kb.add(types.InlineKeyboardButton(f"📋 عرض القنوات ({count})", callback_data="adm_fc_list", style="primary"))
    kb.add(types.InlineKeyboardButton("🔍 فحص الصلاحيات", callback_data="adm_fc_check", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع للوحة", callback_data="adm_panel", style="primary"))
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def show_force_channels_list(chat_id: int, msg_id: int = None) -> None:
    channels = get_force_channels()
    kb = types.InlineKeyboardMarkup(row_width=2)
    if not channels:
        text = "📋 <b>قنوات الاشتراك الإجباري</b>\n\nلا توجد قنوات مضافة بعد."
    else:
        lines = []
        for ch in channels:
            icon = "🔒" if ch["ch_type"] == "private" else "📢"
            label = html_escape(ch["label"] or ch["channel"])
            invite_link = (ch.get("invite_link") or "").strip()
            if ch["ch_type"] == "private" and invite_link:
                lines.append(f"{icon} {label}\n   ↳ <code>{html_escape(ch['channel'])}</code> | <a href='{html_escape(invite_link)}'>رابط الدعوة</a>")
            elif ch["ch_type"] == "private":
                lines.append(f"{icon} {label}\n   ↳ <code>{html_escape(ch['channel'])}</code> | ⚠️ بدون رابط دعوة")
            else:
                lines.append(f"{icon} {label}")
            # زرّا تعديل + حذف جنباً لجنب
            kb.add(
                types.InlineKeyboardButton(
                    f"✏️ تعديل {icon} {ch['label'] or ch['channel']}",
                    callback_data=f"adm_fc_edit_{ch['id']}", style="primary"),
                types.InlineKeyboardButton(
                    f"🗑 حذف",
                    callback_data=f"adm_fc_del_{ch['id']}", style="primary"),
            )
        text = "📋 <b>قنوات الاشتراك الإجباري:</b>\n\n" + "\n".join(lines)
    kb.add(types.InlineKeyboardButton("➕ إضافة قناة", callback_data="adm_fc_add", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="adm_force_channel", style="primary"))
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def show_fc_edit_panel(chat_id: int, fid: int, msg_id: int = None) -> None:
    """لوحة تعديل قناة واحدة — تعديل الاسم أو الرابط أو الـ ID."""
    ch = db_fetchone("SELECT * FROM force_channels WHERE id=?", (fid,))
    if not ch:
        show_force_channels_list(chat_id, msg_id)
        return
    icon = "🔒" if ch["ch_type"] == "private" else "📢"
    invite_link = (ch.get("invite_link") or "").strip()
    text = (
        f"✏️ <b>تعديل القناة</b>\n\n"
        f"{icon} <b>الاسم:</b> {html_escape(ch['label'] or ch['channel'])}\n"
        f"🆔 <b>الـ ID:</b> <code>{html_escape(ch['channel'])}</code>\n"
        f"🔗 <b>الرابط:</b> {html_escape(invite_link) if invite_link else '—'}\n\n"
        "اختر ما تريد تعديله:"
    )
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"adm_fc_ename_{fid}", style="primary"))
    kb.add(types.InlineKeyboardButton("🔗 تعديل الرابط", callback_data=f"adm_fc_elink_{fid}", style="primary"))
    kb.add(types.InlineKeyboardButton("🆔 تعديل الـ ID", callback_data=f"adm_fc_eid_{fid}", style="primary"))
    kb.add(types.InlineKeyboardButton("🗑 حذف القناة", callback_data=f"adm_fc_del_{fid}", style="primary"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="adm_fc_list", style="primary"))
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=kb)


def _fc_wizard_cancel_kb() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="adm_force_channel", style="primary"))
    return kb


def _fc_wizard_next_kb(callback: str, label: str = "التالي ▶️") -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(label, callback_data=callback, style="primary"),
        types.InlineKeyboardButton("❌ إلغاء", callback_data="adm_force_channel", style="primary"),
    )
    return kb


def show_fc_wizard_step1(chat_id: int, uid: int) -> None:
    """الخطوة 1: اطلب رابط الدعوة."""
    pop_pending(uid)
    set_pending(uid, {"type": "fc_wiz_step1"})
    bot.send_message(
        chat_id,
        "📢 <b>إضافة قناة — الخطوة 1 من 3</b>\n\n"
        "🔗 <b>أرسل رابط الدعوة (Invite Link)</b> للقناة:\n\n"
        "مثال:\n"
        "<code>https://t.me/+AbCdEfGhIjKl</code>\n"
        "أو <code>https://t.me/joinchat/AbCdEfGhIjKl</code>\n\n"
        "⚠️ يجب أن يكون البوت <b>مشرفاً</b> في القناة.",
        reply_markup=_fc_wizard_cancel_kb(),
    )


def show_fc_add_type(chat_id: int, msg_id: int = None) -> None:
    """نقطة دخول قديمة — الآن تبدأ الـ Wizard مباشرة."""
    show_fc_wizard_step1(chat_id, chat_id)


# اسم قديم للتوافق مع زر adm_force_channel القديم
def start_set_force_channel(chat_id: int, uid: int) -> None:
    show_force_channels_panel(chat_id, uid)


def start_ban_by_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "admin_ban_user"})
    bot.send_message(chat_id, "🚫 <b>حظر مستخدم</b>\n\nأرسل <b>ID</b> المستخدم المراد حظره.\nأو /cancel.",
                     reply_markup=back_admin_kb())


def start_unban_by_id(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "admin_unban_user"})
    bot.send_message(chat_id, "✅ <b>رفع حظر مستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\nأو /cancel.",
                     reply_markup=back_admin_kb())


def start_user_info(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "admin_user_info"})
    bot.send_message(chat_id, "🪪 <b>معلومات مستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\nأو /cancel.",
                     reply_markup=back_admin_kb())


def start_search_user(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "search_user"})
    bot.send_message(
        chat_id,
        "🔍 <b>بحث عن مستخدم</b>\n\n"
        "أرسل <b>ID</b> الرقمي أو <b>@username</b>.\nأو /cancel.",
        reply_markup=back_admin_kb(),
    )


def show_list_blocked_from_db(chat_id: int, message_id: int) -> None:
    rows = db_fetchall(
        "SELECT id, first_name, username FROM users WHERE banned=1 ORDER BY id DESC LIMIT 40"
    )
    if not rows:
        text = "✅ لا يوجد مستخدمون محظورون في قاعدة البيانات."
    else:
        text = f"🚫 <b>المحظورون ({len(rows)}):</b>\n\n"
        for r in rows:
            name = html_escape(r.get("first_name") or "-")
            uname = f"@{r['username']}" if r.get("username") else "-"
            text += f"• <code>{r['id']}</code> — {name} ({uname})\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(" رجوع", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=kb)


def start_create_gift_link(chat_id: int, uid: int) -> None:
    set_pending(uid, {"type": "gift_points"})
    bot.send_message(chat_id, "🎁 <b>إنشاء رابط هدية نقاط</b>\n\n🔢 <b>الخطوة 1/3:</b> أرسل عدد النقاط لكل مستخدم.\nأو /cancel للإلغاء.",
                     reply_markup=back_admin_kb())


# ============================================================
# 21.5) معاينة محتوى الملف للأدمن
# ============================================================
TEXT_PREVIEW_EXTENSIONS = {
    ".py", ".txt", ".json", ".csv", ".yaml", ".yml",
    ".ini", ".cfg", ".md", ".html", ".css", ".js",
    ".xml", ".log", ".sql", ".env",
}
MAX_PREVIEW_CHARS = 3500

# كاش صفحات المعاينة: cache_key -> {"pages": [...], "filename": str, "total_lines": int}
_file_preview_cache: Dict[str, dict] = {}


def _file_cache_key(telegram_file_id: str) -> str:
    return hashlib.md5(telegram_file_id.encode()).hexdigest()[:12]


def _build_preview_pages(content: str) -> list:
    """تقسّم المحتوى إلى صفحات بحجم MAX_PREVIEW_CHARS كل صفحة."""
    lines = content.splitlines()
    pages = []
    current_lines = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > MAX_PREVIEW_CHARS and current_lines:
            pages.append("\n".join(current_lines))
            current_lines = [line]
            current_len = line_len
        else:
            current_lines.append(line)
            current_len += line_len
    if current_lines:
        pages.append("\n".join(current_lines))
    return pages if pages else [""]


def _make_preview_keyboard(cache_key: str, page: int, total_pages: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    if page > 0:
        buttons.append(types.InlineKeyboardButton(
            "◀️ السابق", callback_data=f"fpg_{cache_key}_{page - 1}"
        ))
    buttons.append(types.InlineKeyboardButton(
        f"📄 {page + 1} / {total_pages}", callback_data="noop"
    ))
    if page < total_pages - 1:
        buttons.append(types.InlineKeyboardButton(
            "التالي ▶️", callback_data=f"fpg_{cache_key}_{page + 1}"
        ))
    kb.add(*buttons)
    return kb


def _send_file_preview(chat_id: int, telegram_file_id: str, filename: str) -> None:
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in TEXT_PREVIEW_EXTENSIONS:
        return
    try:
        file_info = bot.get_file(telegram_file_id)
        raw = bot.download_file(file_info.file_path)
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1", errors="replace")

        pages = _build_preview_pages(content)
        total_lines = len(content.splitlines())
        cache_key = _file_cache_key(telegram_file_id)
        _file_preview_cache[cache_key] = {
            "pages": pages,
            "filename": filename,
            "total_lines": total_lines,
        }

        page = 0
        total_pages = len(pages)
        header = (
            f"📄 <b>محتوى الملف:</b> <code>{html_escape(filename)}</code>\n"
            f"<i>({total_lines} سطر — صفحة {page + 1} من {total_pages})</i>"
        )
        markup = _make_preview_keyboard(cache_key, page, total_pages) if total_pages > 1 else None
        bot.send_message(
            chat_id,
            f"{header}\n\n<pre><code>{html_escape(pages[page])}</code></pre>",
            reply_markup=markup,
        )
    except Exception as e:
        log.warning("_send_file_preview failed for %s: %s", filename, e)


# ============================================================
# 22) الموافقة على البوت
# ============================================================
def approve_project(project_id: int) -> None:
    p = db_fetchone("SELECT * FROM projects WHERE id=?", (project_id,))
    if not p:
        return
    pending = db_fetchone("SELECT * FROM pending_uploads WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,))
    if pending:
        try:
            file_info = bot.get_file(pending["telegram_file_id"])
            data = bot.download_file(file_info.file_path)
            db_execute(
                "INSERT INTO project_files (project_id, filename, content, size_bytes) VALUES (?,?,?,?) "
                "ON CONFLICT (project_id, filename) DO UPDATE SET content=excluded.content, "
                "size_bytes=excluded.size_bytes, updated_at=CURRENT_TIMESTAMP",
                (project_id, pending["filename"], sqlite3.Binary(data), len(data)),
            )
            db_execute("DELETE FROM pending_uploads WHERE id=?", (pending["id"],))
        except Exception as e:
            log.exception("download for project %s failed", project_id)
            db_execute("UPDATE projects SET last_error=? WHERE id=?", (f"download failed: {e}", project_id))
            try:
                bot.send_message(p["user_id"], f"❌ فشل تحميل ملف البوت: {e}")
            except Exception:
                pass
            return
    db_execute("UPDATE projects SET approved=1 WHERE id=?", (project_id,))
    try:
        bot.send_message(p["user_id"], f"🎉 تمت الموافقة على بوت <b>{html_escape(p['name'])}</b> وبدء تشغيله.\n\n💬 {get_random_quote()}")
    except Exception:
        pass
    ok, msg = manager.start_project(project_id)
    log.info("Approved project %s — start=%s (%s)", project_id, ok, msg)


# ============================================================
# 23) معالجات الرسائل النصية للأدمن
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "set_upload_price",
    content_types=["text"],
)
def receive_set_upload_price(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.isdigit():
        bot.send_message(uid, "❌ أرسل رقماً صحيحاً ≥ 0. أو /cancel.", reply_markup=back_admin_kb())
        return
    set_setting("upload_price", int(text))
    pop_pending(uid)
    bot.send_message(uid, f"✅ تم تحديث سعر رفع البوت إلى <b>{text}</b> نقطة.", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "set_transfer_fee",
    content_types=["text"],
)
def receive_set_transfer_fee(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.isdigit():
        bot.send_message(uid, "❌ أرسل رقماً صحيحاً ≥ 0. أو /cancel.", reply_markup=back_admin_kb())
        return
    set_setting("transfer_fee", int(text))
    pop_pending(uid)
    bot.send_message(uid, f"✅ تم تحديث عمولة التحويل إلى <b>{text}</b> نقطة.", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_welcome",
    content_types=["text"],
)
def receive_set_welcome(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pop_pending(uid)
    if text == "-":
        set_setting("welcome_text", "")
        bot.send_message(uid, "✅ تم إعادة رسالة الترحيب إلى الافتراضية.", reply_markup=back_admin_kb())
    else:
        set_setting("welcome_text", text)
        # معاينة
        preview = text.replace("{name}", "اماراتي")
        bot.send_message(uid,
            f"✅ <b>تم تحديث رسالة الترحيب</b>\n\n<b>معاينة:</b>\n{preview}",
            reply_markup=back_admin_kb()
        )


# ── استقبال نص "-" لإعادة صورة الترحيب الافتراضية ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_welcome_img",
    content_types=["text"],
)
def receive_set_welcome_img_text(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if text == "-":
        pop_pending(uid)
        set_setting("welcome_image_id", "")
        bot.send_message(uid, "✅ تمت إعادة صورة الترحيب إلى الافتراضية.", reply_markup=back_admin_kb())
    else:
        bot.send_message(uid, "⚠️ أرسل صورة مباشرةً، أو أرسل <code>-</code> لإعادة الصورة الافتراضية.", reply_markup=back_admin_kb())


# ── استقبال الصورة الجديدة ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_welcome_img",
    content_types=["photo"],
)
def receive_set_welcome_img_photo(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pop_pending(uid)
    # نأخذ أكبر حجم للصورة (آخر عنصر في القائمة)
    file_id = message.photo[-1].file_id
    set_setting("welcome_image_id", file_id)
    bot.send_message(
        uid,
        "✅ <b>تم تحديث صورة الترحيب!</b>\n\nستظهر الصورة الجديدة للمستخدمين عند الضغط على /start.",
        reply_markup=back_admin_kb(),
    )


# ── صورة الحظر: نص ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_banned_img",
    content_types=["text"],
)
def receive_set_banned_img_text(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    if (message.text or "").strip() == "-":
        pop_pending(uid)
        set_setting("banned_image_id", "")
        bot.send_message(uid, "✅ تمت إعادة صورة الحظر إلى الافتراضية.", reply_markup=back_admin_kb())
    else:
        bot.send_message(uid, "⚠️ أرسل صورة مباشرةً، أو أرسل <code>-</code> لإعادة الافتراضية.", reply_markup=back_admin_kb())


# ── صورة الحظر: صورة ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_banned_img",
    content_types=["photo"],
)
def receive_set_banned_img_photo(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pop_pending(uid)
    set_setting("banned_image_id", message.photo[-1].file_id)
    bot.send_message(uid, "✅ <b>تم تحديث صورة الحظر!</b>", reply_markup=back_admin_kb())


# ── صورة الصيانة: نص ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_maint_img",
    content_types=["text"],
)
def receive_set_maint_img_text(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    if (message.text or "").strip() == "-":
        pop_pending(uid)
        set_setting("maintenance_image_id", "")
        bot.send_message(uid, "✅ تمت إعادة صورة الصيانة إلى الافتراضية.", reply_markup=back_admin_kb())
    else:
        bot.send_message(uid, "⚠️ أرسل صورة مباشرةً، أو أرسل <code>-</code> لإعادة الافتراضية.", reply_markup=back_admin_kb())


# ── صورة الصيانة: صورة ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_maint_img",
    content_types=["photo"],
)
def receive_set_maint_img_photo(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pop_pending(uid)
    set_setting("maintenance_image_id", message.photo[-1].file_id)
    bot.send_message(uid, "✅ <b>تم تحديث صورة الصيانة!</b>", reply_markup=back_admin_kb())


# ── رسالة الحظر: نص ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_banned_txt",
    content_types=["text"],
)
def receive_set_banned_txt(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pop_pending(uid)
    if text == "-":
        set_setting("banned_text", "")
        bot.send_message(uid, "✅ تمت إعادة رسالة الحظر إلى الافتراضية.", reply_markup=back_admin_kb())
    else:
        set_setting("banned_text", text)
        bot.send_message(uid, f"✅ <b>تم تحديث رسالة الحظر.</b>\n\n<b>معاينة:</b>\n{text}", reply_markup=back_admin_kb())


# ── رسالة الصيانة: نص ──
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_maint_txt",
    content_types=["text"],
)
def receive_set_maint_txt(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pop_pending(uid)
    if text == "-":
        set_setting("maintenance_text", "")
        bot.send_message(uid, "✅ تمت إعادة رسالة الصيانة إلى الافتراضية.", reply_markup=back_admin_kb())
    else:
        set_setting("maintenance_text", text)
        bot.send_message(uid, f"✅ <b>تم تحديث رسالة الصيانة.</b>\n\n<b>معاينة:</b>\n{text}", reply_markup=back_admin_kb())


# ============================================================
# Wizard — الخطوة 1: استقبال رابط الدعوة
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_wiz_step1",
    content_types=["text"],
)
def receive_fc_wiz_step1(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()

    valid = (
        text.startswith("https://t.me/+")
        or text.startswith("https://t.me/joinchat/")
        or re.match(r"^@[\w]{4,}$", text)  # يقبل @username أيضاً
    )
    if not valid:
        bot.send_message(
            uid,
            "❌ <b>رابط غير صالح.</b>\n\n"
            "يجب أن يكون رابط دعوة:\n"
            "<code>https://t.me/+AbCdEfGhIjKl</code>\n"
            "أو يوزرنيم عام: <code>@channel_name</code>\n\n"
            "أرسل الرابط مجدداً أو اضغط إلغاء.",
            reply_markup=_fc_wizard_cancel_kb(),
        )
        return

    set_pending(uid, {"type": "fc_wiz_step1", "link": text})
    bot.send_message(
        uid,
        f"✅ <b>تم استلام الرابط:</b>\n<code>{html_escape(text)}</code>\n\n"
        "📢 <b>الخطوة 1 من 3 مكتملة.</b>\n"
        "اضغط <b>التالي</b> للمتابعة.",
        reply_markup=_fc_wizard_next_kb("fc_wiz_to2"),
    )


# ============================================================
# Wizard — الخطوة 2: استقبال الـ ID
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_wiz_step2",
    content_types=["text"],
)
def receive_fc_wiz_step2(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()

    # يقبل رقم مثل -1001234567890 أو @username
    is_numeric = re.match(r"^-?\d{5,}$", text)
    is_username = re.match(r"^@[\w]{4,}$", text)

    if not is_numeric and not is_username:
        bot.send_message(
            uid,
            "❌ <b>الـ ID غير صالح.</b>\n\n"
            "أرسل رقم القناة (Chat ID):\n"
            "مثال: <code>-1001234567890</code>\n"
            "أو اليوزرنيم: <code>@channel_name</code>\n\n"
            "أرسل الـ ID مجدداً أو اضغط إلغاء.",
            reply_markup=_fc_wizard_cancel_kb(),
        )
        return

    pending = get_pending(uid)
    pending["type"] = "fc_wiz_step2"
    pending["channel_id"] = text
    set_pending(uid, pending)

    bot.send_message(
        uid,
        f"✅ <b>تم استلام الـ ID:</b>\n<code>{html_escape(text)}</code>\n\n"
        "📢 <b>الخطوة 2 من 3 مكتملة.</b>\n"
        "اضغط <b>التالي</b> للمتابعة.",
        reply_markup=_fc_wizard_next_kb("fc_wiz_to3"),
    )


# ============================================================
# Wizard — الخطوة 3: استقبال الاسم وحفظ القناة
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_wiz_step3",
    content_types=["text"],
)
def receive_fc_wiz_step3(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    name = (message.text or "").strip()

    if not name or len(name) < 2:
        bot.send_message(
            uid,
            "❌ الاسم قصير جداً. أرسل اسماً مناسباً للقناة.",
            reply_markup=_fc_wizard_cancel_kb(),
        )
        return

    pending = get_pending(uid)
    link = pending.get("link", "")
    channel_id = pending.get("channel_id", "")
    pop_pending(uid)

    # تحديد نوع القناة
    is_private = re.match(r"^-?\d+$", channel_id)
    if is_private:
        add_force_channel(channel_id, name, "private", link)
    else:
        # قناة عامة — @username
        ch = normalize_channel(channel_id)
        add_force_channel(ch, name, "public", link)

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🔙 العودة للوحة", callback_data="adm_force_channel", style="primary"))

    bot.send_message(
        uid,
        f"🎉 <b>تمت إضافة القناة بنجاح!</b>\n\n"
        f"📛 الاسم: <b>{html_escape(name)}</b>\n"
        f"🆔 الـ ID: <code>{html_escape(channel_id)}</code>\n"
        f"🔗 الرابط: {html_escape(link) if link else '—'}\n\n"
        "⏳ جارٍ فحص صلاحيات البوت في القناة...",
        reply_markup=kb,
    )

    # فحص فوري للصلاحيات
    check_id = channel_id if is_private else normalize_channel(channel_id)
    perm = check_bot_channel_permissions(check_id)
    if perm["ok"]:
        bot.send_message(uid, "✅ <b>الصلاحيات سليمة</b> — البوت مشرف وجاهز للعمل.")
    else:
        bot.send_message(
            uid,
            f"⚠️ <b>تنبيه صلاحيات!</b>\n\n"
            f"❌ {html_escape(perm['error'] or 'خطأ غير محدد')}\n\n"
            "📌 <b>الحل:</b> اجعل البوت مشرفاً في القناة\n"
            "ومنحه صلاحية <b>Invite Users via Link</b>.",
        )


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_update_invite",
    content_types=["text"],
)
def receive_fc_update_invite(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pending = get_pending(uid) or {}
    fid = pending.get("fid")

    if not (text.startswith("https://t.me/+") or text.startswith("https://t.me/joinchat/")):
        bot.send_message(uid,
                         "❌ رابط الدعوة غير صالح.\n"
                         "يجب أن يبدأ بـ <code>https://t.me/+</code> أو <code>https://t.me/joinchat/</code>\n\n"
                         "أرسل الرابط الصحيح أو /cancel.",
                         reply_markup=back_admin_kb())
        return

    ok = update_force_channel_invite(fid, text)
    pop_pending(uid)
    if ok:
        bot.send_message(uid,
                         f"✅ تم تحديث رابط الدعوة بنجاح!\n"
                         f"🔗 الرابط الجديد: {html_escape(text)}",
                         reply_markup=back_admin_kb())
    else:
        bot.send_message(uid,
                         "❌ فشل تحديث الرابط.",
                         reply_markup=back_admin_kb())


# ============================================================
# تعديل القناة — استقبال الاسم الجديد
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_edit_name",
    content_types=["text"],
)
def receive_fc_edit_name(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    name = (message.text or "").strip()
    pending = get_pending(uid) or {}
    fid = pending.get("fid")
    if not name or len(name) < 2:
        bot.send_message(uid, "❌ الاسم قصير جداً. أرسل اسماً مناسباً أو /cancel.",
                         reply_markup=_fc_wizard_cancel_kb())
        return
    ok = update_force_channel_label(fid, name)
    pop_pending(uid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🔙 رجوع للقناة", callback_data=f"adm_fc_edit_{fid}", style="primary"))
    if ok:
        bot.send_message(uid, f"✅ <b>تم تحديث الاسم بنجاح!</b>\n✏️ الاسم الجديد: <b>{html_escape(name)}</b>",
                         reply_markup=kb)
    else:
        bot.send_message(uid, "❌ فشل تحديث الاسم.", reply_markup=kb)


# ============================================================
# تعديل القناة — استقبال الرابط الجديد
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_edit_link",
    content_types=["text"],
)
def receive_fc_edit_link(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    link = (message.text or "").strip()
    pending = get_pending(uid) or {}
    fid = pending.get("fid")
    valid = (
        link.startswith("https://t.me/+")
        or link.startswith("https://t.me/joinchat/")
        or link == "-"
    )
    if not valid:
        bot.send_message(
            uid,
            "❌ رابط غير صالح.\n"
            "يجب أن يبدأ بـ <code>https://t.me/+</code> أو <code>https://t.me/joinchat/</code>\n"
            "أو أرسل <code>-</code> لحذف الرابط الحالي.\n\nأو /cancel.",
            reply_markup=_fc_wizard_cancel_kb(),
        )
        return
    ok = update_force_channel_invite(fid, "" if link == "-" else link)
    pop_pending(uid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🔙 رجوع للقناة", callback_data=f"adm_fc_edit_{fid}", style="primary"))
    if ok:
        disp = "تم حذف الرابط" if link == "-" else f"🔗 الرابط الجديد: {html_escape(link)}"
        bot.send_message(uid, f"✅ <b>تم تحديث الرابط بنجاح!</b>\n{disp}", reply_markup=kb)
    else:
        bot.send_message(uid, "❌ فشل تحديث الرابط.", reply_markup=kb)


# ============================================================
# تعديل القناة — استقبال الـ ID الجديد
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "fc_edit_id",
    content_types=["text"],
)
def receive_fc_edit_id(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    pending = get_pending(uid) or {}
    fid = pending.get("fid")
    is_numeric = re.match(r"^-?\d{5,}$", text)
    is_username = re.match(r"^@[\w]{4,}$", text)
    if not is_numeric and not is_username:
        bot.send_message(
            uid,
            "❌ الـ ID غير صالح.\n"
            "مثال رقمي: <code>-1001234567890</code>\n"
            "أو يوزرنيم: <code>@channel_name</code>\n\nأو /cancel.",
            reply_markup=_fc_wizard_cancel_kb(),
        )
        return
    ch_type = "private" if is_numeric else "public"
    ok = update_force_channel_id(fid, text, ch_type)
    pop_pending(uid)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("🔙 رجوع للقناة", callback_data=f"adm_fc_edit_{fid}", style="primary"))
    if ok:
        bot.send_message(uid, f"✅ <b>تم تحديث الـ ID بنجاح!</b>\n🆔 الجديد: <code>{html_escape(text)}</code>",
                         reply_markup=kb)
    else:
        bot.send_message(uid, "❌ فشل تحديث الـ ID.", reply_markup=kb)


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "admin_ban_user",
    content_types=["text"],
)
def receive_admin_ban_user(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        bot.send_message(uid, "❌ أرسل id رقمي صالح. أو /cancel.", reply_markup=back_admin_kb())
        return
    target = int(text)
    if target == uid:
        bot.send_message(uid, "❌ لا يمكنك حظر نفسك.", reply_markup=back_admin_kb())
        return
    db_execute("INSERT INTO users (id, banned) VALUES (?, 1) ON CONFLICT(id) DO UPDATE SET banned=1", (target,))
    for p in db_fetchall("SELECT id FROM projects WHERE user_id=?", (target,)):
        manager.stop_project(p["id"])
    pop_pending(uid)
    bot.send_message(uid, f"🚫 تم حظر المستخدم <code>{target}</code>.", reply_markup=back_admin_kb())
    try:
        bot.send_message(target, "🚫 لقد تم حظرك من استخدام البوت.")
    except Exception:
        pass


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "admin_unban_user",
    content_types=["text"],
)
def receive_admin_unban_user(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        bot.send_message(uid, "❌ أرسل id رقمي صالح. أو /cancel.", reply_markup=back_admin_kb())
        return
    target = int(text)
    db_execute("UPDATE users SET banned=0 WHERE id=?", (target,))
    pop_pending(uid)
    bot.send_message(uid, f"✅ تم رفع الحظر عن <code>{target}</code>.", reply_markup=back_admin_kb())
    try:
        bot.send_message(target, "🎉 تم رفع الحظر عنك. أرسل /start للبدء.")
    except Exception:
        pass


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "admin_user_info",
    content_types=["text"],
)
def receive_admin_user_info(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip().lstrip("@")
    if not text.lstrip("-").isdigit():
        bot.send_message(uid, "❌ أرسل id رقمي صالح. أو /cancel.", reply_markup=back_admin_kb())
        return
    target = int(text)
    row = db_fetchone(
        "SELECT id, first_name, username, approved, banned, max_bots, "
        "COALESCE(points,0) AS points, created_at, referred_by FROM users WHERE id=?", (target,)
    )
    if not row:
        pop_pending(uid)
        bot.send_message(uid, f"❌ لا يوجد مستخدم بهذا الـ id: <code>{target}</code>", reply_markup=back_admin_kb())
        return
    proj_total = db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE user_id=?", (target,))["c"]
    proj_approved = db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE user_id=? AND approved=1", (target,))["c"]
    running_count = 0
    project_lines = []
    for p in db_fetchall("SELECT id, name, approved FROM projects WHERE user_id=? ORDER BY id ASC", (target,)):
        hp = manager.processes.get(p["id"])
        is_run = bool(hp and hp.is_alive())
        if is_run:
            running_count += 1
        status = "🟢 يعمل" if is_run else ("🟡 معتمد" if p["approved"] else "🔴 بانتظار الموافقة")
        project_lines.append(f"   ▫️ <code>#{p['id']}</code> — <b>{html_escape(p['name'])}</b> — {status}")
    referrals_count = db_fetchone("SELECT COUNT(*) AS c FROM users WHERE referred_by=?", (target,))["c"]
    fname = (row.get("first_name") or "").strip() or "—"
    uname = (row.get("username") or "").strip()
    uname_disp = f"@{uname}" if uname else "—"
    status_parts = []
    if row.get("banned"):
        status_parts.append("🚫 محظور")
    status_parts.append("✅ مفعّل" if row.get("approved") else "⏳ بانتظار التفعيل")
    info = (
        "🪪 <b>معلومات المستخدم الكاملة</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>الاسم:</b> {html_escape(fname)}\n"
        f"🔖 <b>اليوزر:</b> {html_escape(uname_disp)}\n"
        f"🆔 <b>الايدي:</b> <code>{target}</code>\n"
        f"📅 <b>تاريخ الدخول:</b> <code>{html_escape(str(row.get('created_at') or '—'))}</code>\n"
        f"⚙️ <b>الحالة:</b> {' | '.join(status_parts)}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💎 <b>النقاط:</b> <b>{row.get('points') or 0}</b>\n"
        f"📦 <b>الحد الأقصى للبوتات:</b> <b>{row.get('max_bots') or 0}</b>\n"
        f"🤖 <b>عدد البوتات الكلي:</b> <b>{proj_total}</b>\n"
        f"✅ <b>البوتات المعتمدة:</b> <b>{proj_approved}</b>\n"
        f"🔋 <b>البوتات النشطة الآن:</b> <b>{running_count}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <b>عدد الإحالات:</b> <b>{referrals_count}</b>\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    if project_lines:
        info += "\n📋 <b>قائمة بوتاته:</b>\n" + "\n".join(project_lines)
    else:
        info += "\n📋 <b>قائمة بوتاته:</b> لا يوجد"
    pop_pending(uid)
    bot.send_message(uid, info, reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "gift_points",
    content_types=["text"],
)
def receive_gift_points(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        bot.send_message(uid, "❌ أرسل عدد نقاط صحيح موجب (> 0). أو /cancel.", reply_markup=back_admin_kb())
        return
    points = int(text)
    set_pending(uid, {"type": "gift_uses", "points": points})
    bot.send_message(uid, f"✅ النقاط: <b>{points}</b>\n\n🔢 <b>الخطوة 2/3:</b> أرسل عدد المستخدمين الذين يمكنهم استخدام الرابط.\nأو /cancel.",
                     reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "gift_uses",
    content_types=["text"],
)
def receive_gift_uses(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    points = int(pending.get("points", 0))
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        bot.send_message(uid, "❌ أرسل عدد مستخدمين صحيح موجب (> 0). أو /cancel.", reply_markup=back_admin_kb())
        return
    max_uses = int(text)
    set_pending(uid, {"type": "gift_days", "points": points, "max_uses": max_uses})
    bot.send_message(uid, f"✅ عدد المستخدمين: <b>{max_uses}</b>\n\n⏳ <b>الخطوة 3/3:</b> أرسل مدة صلاحية الرابط بالأيام (0 = دائم).\nأو /cancel.",
                     reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "gift_days",
    content_types=["text"],
)
def receive_gift_days(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    points = int(pending.get("points", 0))
    max_uses = int(pending.get("max_uses", 0))
    text = (message.text or "").strip()
    if not text.isdigit():
        bot.send_message(uid, "❌ أرسل عدد أيام صحيح ≥ 0. أو /cancel.", reply_markup=back_admin_kb())
        return
    days = int(text)
    expires_at = None
    if days > 0:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    token = _new_gift_token()
    while db_fetchone("SELECT 1 AS x FROM gift_links WHERE token=?", (token,)):
        token = _new_gift_token()
    db_execute("INSERT INTO gift_links (token, points, max_uses, created_by, expires_at) VALUES (?, ?, ?, ?, ?)",
               (token, points, max_uses, uid, expires_at))
    pop_pending(uid)
    try:
        bot_username = bot.get_me().username or ""
    except Exception:
        bot_username = ""
    link = f"https://t.me/{bot_username}?start=gift_{token}" if bot_username else f"start=gift_{token}"
    expiry_line = (f"⏳ ينتهي في: <b>{html_escape(expires_at)}</b> (UTC)\n" if expires_at
                   else "⏳ المدة: <b>دائم</b>\n")
    bot.send_message(uid,
                     "✅ <b>تم إنشاء رابط الهدية</b>\n\n"
                     f"🎁 النقاط لكل مستخدم: <b>{points}</b>\n"
                     f"👥 الحد الأقصى: <b>{max_uses}</b>\n"
                     f"{expiry_line}\n"
                     f"🔗 <code>{link}</code>",
                     reply_markup=back_admin_kb())


# ============================================================
# 24) الإذاعة
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "broadcast",
    content_types=["text", "photo", "video", "document", "animation"],
)
def receive_broadcast(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    pop_pending(message.from_user.id)
    rows = db_fetchall("SELECT id FROM users WHERE banned=0")
    ok = 0
    fail = 0
    blocked = 0
    bot.send_message(message.chat.id, f"📤 جارِ الإرسال إلى {len(rows)} مستخدم…")
    for r in rows:
        try:
            bot.copy_message(r["id"], message.chat.id, message.message_id)
            ok += 1
            time.sleep(0.04)
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
                db_execute("UPDATE users SET blocked_bot=1 WHERE id=?", (r["id"],))
            fail += 1
    bot.send_message(message.chat.id,
                     f"✅ انتهت الإذاعة\n\n📨 نجح: <b>{ok}</b>\n❌ فشل: <b>{fail - blocked}</b>\n🚫 حظروا البوت: <b>{blocked}</b>",
                     reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_announce",
    content_types=["text"],
)
def receive_adm_announce(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    pop_pending(message.from_user.id)
    text_body = (message.text or "").strip()
    if not text_body:
        bot.send_message(message.chat.id, "❌ النص فارغ. يُرجى المحاولة مجدداً.", reply_markup=back_admin_kb())
        return
    announce_text = (
        "━━━━━━━━━━━━━━━━━\n"
        "📣 <b>إعلان من الإدارة</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        f"{text_body}\n\n"
        "━━━━━━━━━━━━━━━━━"
    )
    rows = db_fetchall("SELECT id FROM users WHERE banned=0 AND approved=1")
    ok = fail = blocked = 0
    bot.send_message(message.chat.id, f"📤 جارٍ إرسال الإعلان إلى {len(rows)} مستخدم…")
    for r in rows:
        try:
            bot.send_message(r["id"], announce_text)
            ok += 1
            time.sleep(0.05)
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
                db_execute("UPDATE users SET blocked_bot=1 WHERE id=?", (r["id"],))
            fail += 1
    bot.send_message(
        message.chat.id,
        f"✅ <b>انتهى الإعلان</b>\n\n📨 نجح: <b>{ok}</b>\n❌ فشل: <b>{fail - blocked}</b>\n🚫 حظروا البوت: <b>{blocked}</b>",
        reply_markup=back_admin_kb()
    )


# ── معالجات الرسائل للـ 20 ميزة الجديدة ──

@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_user_bots_by_id",
    content_types=["text"],
)
def receive_user_bots_by_id(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        target = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    adm_show_user_bots(message.chat.id, None, target)


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_reset_points_id",
    content_types=["text"],
)
def receive_reset_points_id(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        target = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    u = db_fetchone("SELECT first_name FROM users WHERE id=?", (target,))
    if not u:
        bot.send_message(message.chat.id, f"❌ المستخدم <code>{target}</code> غير موجود.", reply_markup=back_admin_kb())
        return
    db_execute("UPDATE users SET points=0 WHERE id=?", (target,))
    name = html_escape(u.get("first_name") or str(target))
    bot.send_message(message.chat.id, f"✅ تمّ تصفير نقاط <b>{name}</b> (<code>{target}</code>) إلى 0.", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_user_max_step1",
    content_types=["text"],
)
def receive_set_user_max_step1(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    try:
        target = int((message.text or "").strip())
    except ValueError:
        pop_pending(message.from_user.id)
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    u = db_fetchone("SELECT first_name FROM users WHERE id=?", (target,))
    if not u:
        pop_pending(message.from_user.id)
        bot.send_message(message.chat.id, f"❌ المستخدم <code>{target}</code> غير موجود.", reply_markup=back_admin_kb())
        return
    set_pending(message.from_user.id, {"type": "adm_set_user_max_step2", "target": target})
    bot.send_message(message.chat.id, f"⚙️ مستخدم: <b>{html_escape(u.get('first_name') or str(target))}</b>\nأرسل الآن <b>حد البوتات الجديد</b> (رقم):", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_set_user_max_step2",
    content_types=["text"],
)
def receive_set_user_max_step2(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pending = get_pending(message.from_user.id)
    pop_pending(message.from_user.id)
    target = pending.get("target")
    try:
        new_max = int((message.text or "").strip())
        if new_max < 0: raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال رقم صحيح غير سالب.", reply_markup=back_admin_kb())
        return
    db_execute("UPDATE users SET max_bots=? WHERE id=?", (new_max, target))
    bot.send_message(message.chat.id, f"✅ تمّ تعيين حد البوتات للمستخدم <code>{target}</code> إلى <b>{new_max}</b>.", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_search_bot_name",
    content_types=["text"],
)
def receive_search_bot_name(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    query = (message.text or "").strip()
    if not query:
        bot.send_message(message.chat.id, "❌ نص البحث فارغ.", reply_markup=back_admin_kb())
        return
    rows = db_fetchall(
        "SELECT id, name, user_id, approved, is_running FROM projects WHERE name LIKE ? ORDER BY id DESC LIMIT 20",
        (f"%{query}%",)
    )
    if not rows:
        text = f"🔍 <b>بحث: «{html_escape(query)}»</b>\n\n😕 لا نتائج."
    else:
        lines = [f"🔍 <b>بحث: «{html_escape(query)}»</b> — {len(rows)} نتيجة\n"]
        for r in rows:
            running = manager.is_running(r["id"])
            st = "🟢" if running else ("🟡" if not r["approved"] else "🔴")
            lines.append(f"{st} #{r['id']} {html_escape(r['name'] or '-')}  │  👤 {r['user_id']}")
        text = "\n".join(lines)
    bot.send_message(message.chat.id, text, reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_msg_to_inactive",
    content_types=["text", "photo", "video", "document", "animation"],
)
def receive_msg_inactive(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    rows = db_fetchall(
        "SELECT id FROM users WHERE approved=1 AND banned=0 "
        "AND id NOT IN (SELECT DISTINCT user_id FROM usage_daily WHERE day>=?) "
        "AND date(created_at)<=?", (cutoff, cutoff)
    )
    ok = fail = blocked = 0
    bot.send_message(message.chat.id, f"📤 جارٍ إرسال رسالة إلى {len(rows)} مستخدم خامل…")
    for r in rows:
        try:
            bot.copy_message(r["id"], message.chat.id, message.message_id)
            ok += 1
            time.sleep(0.05)
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
            fail += 1
    bot.send_message(message.chat.id,
        f"✅ <b>انتهى إرسال رسالة الخاملين</b>\n\n📨 نجح: <b>{ok}</b>\n❌ فشل: <b>{fail - blocked}</b>\n🚫 حظروا: <b>{blocked}</b>",
        reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_broadcast_active",
    content_types=["text", "photo", "video", "document", "animation"],
)
def receive_broadcast_active(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    rows = db_fetchall("SELECT id FROM users WHERE banned=0 AND approved=1")
    ok = fail = blocked = 0
    bot.send_message(message.chat.id, f"📤 جارٍ الإذاعة إلى {len(rows)} مستخدم مفعَّل…")
    for r in rows:
        try:
            bot.copy_message(r["id"], message.chat.id, message.message_id)
            ok += 1
            time.sleep(0.04)
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
                db_execute("UPDATE users SET blocked_bot=1 WHERE id=?", (r["id"],))
            fail += 1
    bot.send_message(message.chat.id,
        f"✅ <b>انتهت الإذاعة للمفعّلين</b>\n\n📨 نجح: <b>{ok}</b>\n❌ فشل: <b>{fail - blocked}</b>\n🚫 حظروا: <b>{blocked}</b>",
        reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_approve_id",
    content_types=["text"],
)
def receive_approve_id(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        target = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    u = db_fetchone("SELECT first_name, approved FROM users WHERE id=?", (target,))
    if not u:
        bot.send_message(message.chat.id, f"❌ المستخدم <code>{target}</code> غير موجود.", reply_markup=back_admin_kb())
        return
    if u.get("approved"):
        bot.send_message(message.chat.id, f"ℹ️ المستخدم <code>{target}</code> مفعَّل مسبقاً.", reply_markup=back_admin_kb())
        return
    db_execute("UPDATE users SET approved=1 WHERE id=?", (target,))
    name = html_escape(u.get("first_name") or str(target))
    bot.send_message(message.chat.id, f"✅ تمّ تفعيل <b>{name}</b> (<code>{target}</code>).", reply_markup=back_admin_kb())
    try:
        bot.send_message(target, "🎉 تمّ قبول طلبك! يمكنك الآن استخدام البوت.")
    except Exception:
        pass


# ── message handlers — الدفعة الثالثة ──

@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_user_profile",
    content_types=["text"],
)
def receive_user_profile(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        target = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    adm_show_user_profile(message.chat.id, None, target)


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_ban_by_id",
    content_types=["text"],
)
def receive_ban_by_id(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        target = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    u = db_fetchone("SELECT first_name, banned FROM users WHERE id=?", (target,))
    if not u:
        bot.send_message(message.chat.id, f"❌ المستخدم <code>{target}</code> غير موجود.", reply_markup=back_admin_kb())
        return
    if u.get("banned"):
        bot.send_message(message.chat.id, f"ℹ️ المستخدم <code>{target}</code> محظور مسبقاً.", reply_markup=back_admin_kb())
        return
    db_execute("UPDATE users SET banned=1 WHERE id=?", (target,))
    name = html_escape(u.get("first_name") or str(target))
    bot.send_message(message.chat.id, f"🚫 تمّ حظر <b>{name}</b> (<code>{target}</code>).", reply_markup=back_admin_kb())
    try:
        bot.send_message(target, "🚫 تمّ حظرك من استخدام البوت.")
    except Exception:
        pass


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_unban_by_id",
    content_types=["text"],
)
def receive_unban_by_id(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        target = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    u = db_fetchone("SELECT first_name, banned FROM users WHERE id=?", (target,))
    if not u:
        bot.send_message(message.chat.id, f"❌ المستخدم <code>{target}</code> غير موجود.", reply_markup=back_admin_kb())
        return
    if not u.get("banned"):
        bot.send_message(message.chat.id, f"ℹ️ المستخدم <code>{target}</code> غير محظور أصلاً.", reply_markup=back_admin_kb())
        return
    db_execute("UPDATE users SET banned=0 WHERE id=?", (target,))
    name = html_escape(u.get("first_name") or str(target))
    bot.send_message(message.chat.id, f"✅ تمّ رفع حظر <b>{name}</b> (<code>{target}</code>).", reply_markup=back_admin_kb())
    try:
        bot.send_message(target, "✅ تمّ رفع الحظر عنك، يمكنك استخدام البوت مجدداً.")
    except Exception:
        pass


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_force_stop_bot",
    content_types=["text"],
)
def receive_force_stop_bot(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        pid = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    p = db_fetchone("SELECT name FROM projects WHERE id=?", (pid,))
    if not p:
        bot.send_message(message.chat.id, f"❌ البوت #{pid} غير موجود.", reply_markup=back_admin_kb())
        return
    if not manager.is_running(pid):
        bot.send_message(message.chat.id, f"ℹ️ البوت #{pid} متوقف مسبقاً.", reply_markup=back_admin_kb())
        return
    manager.stop(pid)
    db_execute("UPDATE projects SET is_running=0 WHERE id=?", (pid,))
    bot.send_message(message.chat.id, f"⏹ تمّ إيقاف البوت <b>{html_escape(p.get('name') or str(pid))}</b> (#{pid}).", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_force_start_bot",
    content_types=["text"],
)
def receive_force_start_bot(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        pid = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    p = db_fetchone("SELECT name, approved FROM projects WHERE id=?", (pid,))
    if not p:
        bot.send_message(message.chat.id, f"❌ البوت #{pid} غير موجود.", reply_markup=back_admin_kb())
        return
    if not p.get("approved"):
        bot.send_message(message.chat.id, f"❌ البوت #{pid} لم يُوافَق عليه بعد.", reply_markup=back_admin_kb())
        return
    if manager.is_running(pid):
        bot.send_message(message.chat.id, f"ℹ️ البوت #{pid} يعمل مسبقاً.", reply_markup=back_admin_kb())
        return
    manager.start(pid)
    db_execute("UPDATE projects SET is_running=1 WHERE id=?", (pid,))
    bot.send_message(message.chat.id, f"▶️ تمّ تشغيل البوت <b>{html_escape(p.get('name') or str(pid))}</b> (#{pid}).", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_bot_files_info",
    content_types=["text"],
)
def receive_bot_files_info(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    try:
        pid = int((message.text or "").strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    p = db_fetchone("SELECT name, user_id FROM projects WHERE id=?", (pid,))
    if not p:
        bot.send_message(message.chat.id, f"❌ البوت #{pid} غير موجود.", reply_markup=back_admin_kb())
        return
    rows = db_fetchall(
        "SELECT filename, size_bytes, uploaded_at FROM project_files WHERE project_id=? ORDER BY id DESC",
        (pid,)
    )
    total_sz = sum(r.get("size_bytes", 0) or 0 for r in rows)
    name = html_escape(p.get("name") or str(pid))
    if not rows:
        text = f"📁 <b>ملفات البوت {name}</b> (#{pid})\n\nلا توجد ملفات."
    else:
        lines = [f"📁 <b>ملفات البوت {name}</b> (#{pid}) — {len(rows)} ملف │ {total_sz//1024:,} KB\n"]
        for r in rows:
            sz = (r.get("size_bytes") or 0) // 1024
            dt = str(r.get("uploaded_at",""))[:10]
            lines.append(f"  📄 {html_escape(r.get('filename') or '-')} │ {sz:,} KB │ {dt}")
        text = "\n".join(lines)
    bot.send_message(message.chat.id, text, reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_msg_by_id_step1",
    content_types=["text"],
)
def receive_msg_by_id_step1(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    try:
        target = int((message.text or "").strip())
    except ValueError:
        pop_pending(message.from_user.id)
        bot.send_message(message.chat.id, "❌ يجب إرسال ID رقمي صحيح.", reply_markup=back_admin_kb())
        return
    u = db_fetchone("SELECT first_name FROM users WHERE id=?", (target,))
    if not u:
        pop_pending(message.from_user.id)
        bot.send_message(message.chat.id, f"❌ المستخدم <code>{target}</code> غير موجود.", reply_markup=back_admin_kb())
        return
    set_pending(message.from_user.id, {"type": "adm_msg_by_id_step2", "target": target})
    bot.send_message(
        message.chat.id,
        f"💬 سيُرسَل إلى: <b>{html_escape(u.get('first_name') or str(target))}</b> (<code>{target}</code>)\n"
        "أرسل الرسالة الآن (نص أو صورة أو أي محتوى):\n/cancel للإلغاء.",
        reply_markup=back_admin_kb()
    )


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_msg_by_id_step2",
    content_types=["text", "photo", "video", "document", "animation", "sticker"],
)
def receive_msg_by_id_step2(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pending = get_pending(message.from_user.id)
    pop_pending(message.from_user.id)
    target = pending.get("target")
    try:
        bot.copy_message(target, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, f"✅ تمّ إرسال الرسالة إلى <code>{target}</code>.", reply_markup=back_admin_kb())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ فشل الإرسال: {html_escape(str(e))}", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "adm_broadcast_pending",
    content_types=["text", "photo", "video", "document", "animation"],
)
def receive_broadcast_pending(message):
    if msg_seen(message): return
    if not is_admin(message.from_user.id): return
    pop_pending(message.from_user.id)
    rows = db_fetchall("SELECT id FROM users WHERE approved=0 AND banned=0")
    ok = fail = blocked = 0
    bot.send_message(message.chat.id, f"📤 جارٍ إرسال رسالة إلى {len(rows)} مستخدم منتظر…")
    for r in rows:
        try:
            bot.copy_message(r["id"], message.chat.id, message.message_id)
            ok += 1
            time.sleep(0.05)
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
            fail += 1
    bot.send_message(
        message.chat.id,
        f"✅ <b>انتهى إرسال رسالة المنتظرين</b>\n\n📨 نجح: <b>{ok}</b>\n❌ فشل: <b>{fail - blocked}</b>\n🚫 حظروا: <b>{blocked}</b>",
        reply_markup=back_admin_kb()
    )


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "broadcast_channel_list",
    content_types=["text"],
)
def receive_broadcast_channel_list(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    channels_raw = (message.text or "").strip()
    set_pending(message.from_user.id, {"type": "broadcast_channel_msg", "channels": channels_raw})
    bot.send_message(message.chat.id, "✅ تم حفظ القنوات.\n\nأرسل الرسالة اللي تبيها تُذاع.\n/cancel للإلغاء.",
                     reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "broadcast_channel_msg",
    content_types=["text", "photo", "video", "document", "animation"],
)
def receive_broadcast_channel_msg(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    pending = get_pending(message.from_user.id) or {}
    channels_raw = pending.get("channels", "")
    pop_pending(message.from_user.id)
    channels = [c.strip() for c in channels_raw.split(",") if c.strip()]
    if not channels:
        bot.send_message(message.chat.id, "❌ لا توجد قنوات.", reply_markup=back_admin_kb())
        return
    ok = 0
    fail_list = []
    for ch in channels:
        try:
            bot.copy_message(ch, message.chat.id, message.message_id)
            ok += 1
            time.sleep(0.3)
        except Exception as e:
            fail_list.append(f"{ch}: {str(e)[:60]}")
    result = f"✅ تم الإرسال إلى {ok}/{len(channels)} قناة"
    if fail_list:
        result += "\n\n❌ الفاشلة:\n" + "\n".join(fail_list)
    bot.send_message(message.chat.id, result, reply_markup=back_admin_kb())


# ============================================================
# 25) رسالة لمستخدم بعينه
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "send_user_id",
    content_types=["text"],
)
def receive_send_user_id(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        bot.send_message(message.from_user.id, "❌ أرسل id رقمي صحيح. أو /cancel.", reply_markup=back_admin_kb())
        return
    target = int(text)
    set_pending(message.from_user.id, {"type": "send_user_msg", "target_uid": target})
    bot.send_message(message.chat.id, f"✅ ID: <code>{target}</code>\n\nأرسل الرسالة الآن.\n/cancel للإلغاء.",
                     reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "send_user_msg",
    content_types=["text", "photo", "video", "document", "animation"],
)
def receive_send_user_msg(message):
    if msg_seen(message):
        return
    if not is_admin(message.from_user.id):
        return
    pending = get_pending(message.from_user.id) or {}
    target = pending.get("target_uid")
    pop_pending(message.from_user.id)
    if not target:
        bot.send_message(message.chat.id, "❌ لم يُحدَّد المستخدم.", reply_markup=back_admin_kb())
        return
    try:
        bot.copy_message(target, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, f"✅ تم إرسال الرسالة إلى <code>{target}</code>.", reply_markup=back_admin_kb())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ فشل الإرسال: {str(e)[:100]}", reply_markup=back_admin_kb())


# ============================================================
# 25b) بحث عن مستخدم
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "search_user",
    content_types=["text"],
)
def receive_search_user(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pop_pending(uid)
    query = (message.text or "").strip()
    if query.startswith("@"):
        row = db_fetchone("SELECT * FROM users WHERE username=?", (query.lstrip("@"),))
    elif query.lstrip("-").isdigit():
        row = db_fetchone("SELECT * FROM users WHERE id=?", (int(query),))
    else:
        bot.send_message(uid, "❌ أرسل ID رقمي أو @username. أو /cancel.", reply_markup=back_admin_kb())
        return
    if not row:
        bot.send_message(uid, f"❌ لم يُعثر على مستخدم: <code>{html_escape(query)}</code>", reply_markup=back_admin_kb())
        return
    status = "🚫 محظور" if row["banned"] else ("✅ مفعّل" if row["approved"] else "🟡 غير مفعّل")
    pts = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (row["id"],))
    bots_count = db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE user_id=?", (row["id"],))
    text = (
        f"🔍 <b>نتيجة البحث</b>\n\n"
        f"🪪 ID: <code>{row['id']}</code>\n"
        f"👤 الاسم: {html_escape(row.get('first_name') or '-')}\n"
        f"📛 Username: @{row.get('username') or '-'}\n"
        f"📊 الحالة: {status}\n"
        f"⭐ النقاط: <b>{pts['p'] if pts else 0}</b>\n"
        f"🤖 عدد البوتات: <b>{bots_count['c'] if bots_count else 0}</b>\n"
        f"📅 تاريخ التسجيل: {row.get('created_at') or '-'}"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(" حظر", callback_data=f"adm_ban_user_{row['id']}",
            style="danger", icon_custom_emoji_id=E_BAN),
        types.InlineKeyboardButton(" رفع حظر", callback_data=f"adm_unban_user_{row['id']}",
            style="danger", icon_custom_emoji_id=E_UNBAN),
    )
    kb.add(types.InlineKeyboardButton(" رجوع للوحة الأدمن", callback_data="adm_panel",
        style="primary", icon_custom_emoji_id=E_BACK))
    bot.send_message(uid, text, reply_markup=kb)


# ============================================================
# 25c) منح نقاط للكل
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "give_all_points_input",
    content_types=["text"],
)
def receive_give_all_points(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pop_pending(uid)
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        bot.send_message(uid, "❌ أرسل رقماً صحيحاً. أو /cancel.", reply_markup=back_admin_kb())
        return
    amount = int(text)
    if amount == 0:
        bot.send_message(uid, "❌ القيمة لا يمكن أن تكون 0.", reply_markup=back_admin_kb())
        return
    db_execute(
        "UPDATE users SET points = MAX(0, COALESCE(points,0) + ?) WHERE approved=1 AND banned=0",
        (amount,),
    )
    count_row = db_fetchone("SELECT COUNT(*) AS c FROM users WHERE approved=1 AND banned=0")
    count = count_row["c"] if count_row else 0
    action = "إضافة" if amount > 0 else "خصم"
    bot.send_message(
        uid,
        f"✅ <b>تم {action} <code>{abs(amount)}</code> نقطة لـ <b>{count}</b> مستخدم.</b>",
        reply_markup=back_admin_kb(),
    )


# ============================================================
# 25d) تحذير مستخدم
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "warn_user_id",
    content_types=["text"],
)
def receive_warn_user_id(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        bot.send_message(uid, "❌ أرسل ID رقمي صحيح. أو /cancel.", reply_markup=back_admin_kb())
        return
    target = int(text)
    set_pending(uid, {"type": "warn_user_msg", "target_uid": target})
    bot.send_message(
        uid,
        f"✅ ID: <code>{target}</code>\n\nأرسل نص التحذير الآن.\n/cancel للإلغاء.",
        reply_markup=back_admin_kb(),
    )


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "warn_user_msg",
    content_types=["text"],
)
def receive_warn_user_msg(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    target = pending.get("target_uid")
    pop_pending(uid)
    if not target:
        bot.send_message(uid, "❌ لم يُحدَّد المستخدم.", reply_markup=back_admin_kb())
        return
    warn_text = (message.text or "").strip()
    try:
        bot.send_message(
            target,
            f"⚠️ <b>تحذير من الإدارة</b>\n\n{html_escape(warn_text)}",
        )
        bot.send_message(uid, f"✅ تم إرسال التحذير إلى <code>{target}</code>.", reply_markup=back_admin_kb())
    except Exception as e:
        bot.send_message(uid, f"❌ فشل الإرسال: {str(e)[:100]}", reply_markup=back_admin_kb())


# ============================================================
# 26) منح نقاط / تعيين نقاط / حد البوتات
# ============================================================
@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "give_points_input",
    content_types=["text"],
)
def receive_give_points_input(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    step = pending.get("step", "id")
    text = (message.text or "").strip()
    if step == "id":
        if not text.lstrip("-").isdigit():
            bot.send_message(uid, "❌ أرسل id رقمي. أو /cancel.", reply_markup=back_admin_kb())
            return
        set_pending(uid, {"type": "give_points_input", "step": "amount", "target": int(text)})
        bot.send_message(uid, f"✅ المستخدم: <code>{text}</code>\n\nأرسل عدد النقاط (موجب=إضافة، سالب=خصم).\nأو /cancel.",
                         reply_markup=back_admin_kb())
    elif step == "amount":
        if not text.lstrip("-").isdigit():
            bot.send_message(uid, "❌ أرسل رقماً. أو /cancel.", reply_markup=back_admin_kb())
            return
        target = pending.get("target")
        amount = int(text)
        db_execute("UPDATE users SET points = MAX(0, COALESCE(points,0) + ?) WHERE id=?", (amount, target))
        pop_pending(uid)
        sign = "+" if amount >= 0 else ""
        bot.send_message(uid, f"✅ تم: {sign}{amount} نقطة للمستخدم <code>{target}</code>.", reply_markup=back_admin_kb())
        try:
            verb = "إضافة" if amount >= 0 else "خصم"
            bot.send_message(target, f"💎 تم {verb} <b>{abs(amount)}</b> نقطة من المطور.")
        except Exception:
            pass


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "set_points_input",
    content_types=["text"],
)
def receive_set_points_input(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    step = pending.get("step", "id")
    text = (message.text or "").strip()
    if step == "id":
        if not text.lstrip("-").isdigit():
            bot.send_message(uid, "❌ أرسل id. أو /cancel.", reply_markup=back_admin_kb())
            return
        set_pending(uid, {"type": "set_points_input", "step": "amount", "target": int(text)})
        bot.send_message(uid, f"✅ المستخدم: <code>{text}</code>\n\nأرسل القيمة الجديدة للنقاط.\nأو /cancel.",
                         reply_markup=back_admin_kb())
    elif step == "amount":
        if not text.isdigit():
            bot.send_message(uid, "❌ أرسل رقماً ≥ 0. أو /cancel.", reply_markup=back_admin_kb())
            return
        target = pending.get("target")
        db_execute("UPDATE users SET points=? WHERE id=?", (int(text), target))
        pop_pending(uid)
        bot.send_message(uid, f"✅ تم تعيين نقاط <code>{target}</code> إلى <b>{text}</b>.", reply_markup=back_admin_kb())


@bot.message_handler(
    func=lambda m: is_admin(m.from_user.id) and get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "set_max_bots_input",
    content_types=["text"],
)
def receive_set_max_bots_input(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    step = pending.get("step", "id")
    text = (message.text or "").strip()
    if step == "id":
        if not text.lstrip("-").isdigit():
            bot.send_message(uid, "❌ أرسل id. أو /cancel.", reply_markup=back_admin_kb())
            return
        set_pending(uid, {"type": "set_max_bots_input", "step": "amount", "target": int(text)})
        bot.send_message(uid, f"✅ المستخدم: <code>{text}</code>\n\nأرسل الحد الجديد للبوتات.\nأو /cancel.",
                         reply_markup=back_admin_kb())
    elif step == "amount":
        if not text.isdigit():
            bot.send_message(uid, "❌ أرسل رقماً ≥ 0. أو /cancel.", reply_markup=back_admin_kb())
            return
        target = pending.get("target")
        db_execute("UPDATE users SET max_bots=? WHERE id=?", (int(text), target))
        pop_pending(uid)
        bot.send_message(uid, f"✅ تم تعيين حد البوتات لـ<code>{target}</code> إلى <b>{text}</b>.",
                         reply_markup=back_admin_kb())


# ============================================================
# 27) تحويل النقاط
# ============================================================
@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "transfer_recipient",
    content_types=["text"],
)
def receive_transfer_recipient(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        bot.send_message(uid, "❌ يرجى إرسال <b>ID</b> رقمي صالح. أو /cancel للإلغاء.")
        return
    recipient_id = int(text)
    if recipient_id == uid:
        bot.send_message(uid, "❌ لا يمكنك التحويل لنفسك.")
        return
    recipient = db_fetchone("SELECT id, banned FROM users WHERE id=?", (recipient_id,))
    if not recipient:
        bot.send_message(uid, "❌ المستخدم غير موجود. تأكد من أنه بدأ البوت من قبل.\nأو /cancel.")
        return
    if recipient.get("banned"):
        bot.send_message(uid, "❌ لا يمكن التحويل إلى مستخدم محظور.")
        return
    set_pending(uid, {"type": "transfer_amount", "recipient_id": recipient_id})
    bot.send_message(uid, "❄️ ارسل عدد النقاط المراد تحويلها:")


@bot.message_handler(
    func=lambda m: get_pending(m.from_user.id) is not None
    and get_pending(m.from_user.id).get("type") == "transfer_amount",
    content_types=["text"],
)
def receive_transfer_amount(message):
    if msg_seen(message):
        return
    uid = message.from_user.id
    pending = get_pending(uid) or {}
    recipient_id = pending.get("recipient_id")
    if not recipient_id:
        pop_pending(uid)
        bot.send_message(uid, "❌ انتهت جلسة التحويل. ابدأ من جديد.")
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        bot.send_message(uid, "❌ يرجى إرسال عدد صحيح موجب. أو /cancel.")
        return
    amount = int(text)
    if amount < 5:
        bot.send_message(uid, "❌ أقل عدد يمكن تحويله هو <b>5</b> نقاط.")
        return
    fee = get_transfer_fee()
    total_deduct = amount + fee
    with _db_lock:
        sender_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
        sender_pts = sender_row["p"] if sender_row else 0
        if sender_pts < total_deduct:
            pop_pending(uid)
            bot.send_message(uid, f"❌ رصيدك ({sender_pts}) غير كافٍ.\nالمطلوب: {amount} + عمولة {fee} = <b>{total_deduct}</b> نقطة.")
            return
        db_execute("UPDATE users SET points = points - ? WHERE id=? AND COALESCE(points,0) >= ?",
                   (total_deduct, uid, total_deduct))
        db_execute("UPDATE users SET points = COALESCE(points,0) + ? WHERE id=?", (amount, recipient_id))
    pop_pending(uid)
    sender_msg = f"🎁 تم إرسال <b>{amount}</b> نقطة إلى المستخدم <code>{recipient_id}</code> بنجاح 🎁"
    if fee > 0:
        sender_msg += f"\n💸 (تم خصم {fee} نقطة عمولة، الإجمالي {total_deduct})"
    bot.send_message(uid, sender_msg, reply_markup=back_main_kb())
    try:
        bot.send_message(recipient_id, f"🎉 تهانينا، تم استلام <b>{amount}</b> نقطة من المستخدم <code>{uid}</code> 🎁")
    except Exception:
        pass


# ============================================================
# 28) موجّه الأزرار الرئيسي
# ============================================================
@bot.callback_query_handler(func=lambda c: True)
def on_callback(call):
    if call_seen(call):
        return
    uid = call.from_user.id
    user = ensure_user(call)
    if user.get("banned"):
        bot.answer_callback_query(call.id, "🚫 محظور", show_alert=True)
        return
    if is_bot_disabled() and not is_admin(uid):
        bot.answer_callback_query(call.id, "⛔ البوت معطل حالياً", show_alert=True)
        return
    data = call.data or ""
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    # تنقل بين صفحات معاينة الملف
    if data.startswith("fpg_"):
        parts = data.split("_")
        if len(parts) == 3:
            _, cache_key, page_str = parts
            page = int(page_str)
            cached = _file_preview_cache.get(cache_key)
            if not cached:
                bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية المعاينة، يرجى إعادة فتح الملف.", show_alert=True)
                return
            pages = cached["pages"]
            total_pages = len(pages)
            total_lines = cached["total_lines"]
            filename = cached["filename"]
            if page < 0 or page >= total_pages:
                bot.answer_callback_query(call.id, "❌ صفحة غير موجودة")
                return
            header = (
                f"📄 <b>محتوى الملف:</b> <code>{html_escape(filename)}</code>\n"
                f"<i>({total_lines} سطر — صفحة {page + 1} من {total_pages})</i>"
            )
            markup = _make_preview_keyboard(cache_key, page, total_pages)
            try:
                bot.edit_message_text(
                    f"{header}\n\n<pre><code>{html_escape(pages[page])}</code></pre>",
                    chat_id=chat_id,
                    message_id=msg_id,
                    reply_markup=markup,
                )
                bot.answer_callback_query(call.id, f"صفحة {page + 1} من {total_pages}")
            except Exception as e:
                bot.answer_callback_query(call.id, "⚠️ حدث خطأ")
                log.warning("fpg edit_message_text failed: %s", e)
        return

    if data == "noop":
        bot.answer_callback_query(call.id)
        return

    # زر التحقق من الاشتراك
    if data == "check_sub":
        ok, unsubscribed = is_user_subscribed_all(uid)
        if ok:
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ تم التحقق")
            if is_admin(uid):
                bot.send_message(chat_id, "👑 أهلاً بالمطور.", reply_markup=admin_menu_markup())
            else:
                show_main_menu(chat_id, uid)
        else:
            names = ", ".join(ch["label"] or ch["channel"] for ch in unsubscribed)
            bot.answer_callback_query(call.id, f"❌ لم تشترك بعد في: {names}", show_alert=True)
        return

    # فحص الاشتراك الإجباري
    if not is_admin(uid):
        ok, _ = is_user_subscribed_all(uid)
        if not ok:
            bot.answer_callback_query(call.id, "⚠️ يجب الاشتراك في القنوات أولاً", show_alert=True)
            force_sub_block(chat_id, uid)
            return

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    try:
        if data == "back_main":
            pop_pending(uid)
            show_main_menu(chat_id, uid, msg_id)

        elif data in ("noop_sig", "noop"):
            pass  # أزرار زخرفية لا تفعل شيئاً

        elif data == "cancel_operation":
            pop_pending(uid)
            show_main_menu(chat_id, uid, msg_id)

        elif data == "adm_panel":
            if not is_admin(uid):
                return
            pop_pending(uid)
            show_admin_panel(chat_id, msg_id)

        # ── أقسام لوحة الأدمن ──
        elif data == "adm_sec_requests":
            if not is_admin(uid): return
            s = get_admin_quick_stats()
            pending_warn = f"  ⚠️ {s['pending_total']} طلب معلّق" if s["pending_total"] else ""
            text = f"📥 <b>الطلبات</b>{pending_warn}"
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=admin_section_markup("requests"))
            except Exception:
                bot.send_message(chat_id, text, reply_markup=admin_section_markup("requests"))

        elif data == "adm_sec_users":
            if not is_admin(uid): return
            s = get_admin_quick_stats()
            text = f"👥 <b>المستخدمون</b>  |  إجمالي: <b>{s['total_users']}</b>  |  محظور: <b>{s['banned_users']}</b>"
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=admin_section_markup("users"))
            except Exception:
                bot.send_message(chat_id, text, reply_markup=admin_section_markup("users"))

        elif data == "adm_sec_comms":
            if not is_admin(uid): return
            try:
                bot.edit_message_text("📣 <b>التواصل</b>", chat_id, msg_id, reply_markup=admin_section_markup("comms"))
            except Exception:
                bot.send_message(chat_id, "📣 <b>التواصل</b>", reply_markup=admin_section_markup("comms"))

        elif data == "adm_sec_points":
            if not is_admin(uid): return
            s = get_admin_quick_stats()
            text = f"💎 <b>النقاط</b>  |  إجمالي النقاط: <b>{s['total_points']:,}</b>"
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=admin_section_markup("points"))
            except Exception:
                bot.send_message(chat_id, text, reply_markup=admin_section_markup("points"))

        elif data == "adm_sec_bots":
            if not is_admin(uid): return
            s = get_admin_quick_stats()
            text = f"🤖 <b>البوتات</b>  |  شغّالة: <b>{s['running_bots']}</b> / إجمالي: <b>{s['total_bots']}</b>"
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=admin_section_markup("bots"))
            except Exception:
                bot.send_message(chat_id, text, reply_markup=admin_section_markup("bots"))

        elif data == "adm_sec_settings":
            if not is_admin(uid): return
            try:
                bot.edit_message_text("⚙️ <b>الإعدادات</b>", chat_id, msg_id, reply_markup=admin_section_markup("settings"))
            except Exception:
                bot.send_message(chat_id, "⚙️ <b>الإعدادات</b>", reply_markup=admin_section_markup("settings"))

        elif data == "adm_sec_stats":
            if not is_admin(uid): return
            sv = get_server_quick_info()
            text = f"📊 <b>الإحصائيات والسيرفر</b>\n\n{sv}"
            try:
                bot.edit_message_text(text, chat_id, msg_id, reply_markup=admin_section_markup("stats"))
            except Exception:
                bot.send_message(chat_id, text, reply_markup=admin_section_markup("stats"))

        # ── إجراءات سريعة ──
        elif data == "adm_quick_approve_all":
            if not is_admin(uid): return
            # قبول جميع طلبات التفعيل والبوتات المعلّقة
            pending_u = db_fetchall("SELECT id FROM users WHERE approved=0 AND banned=0")
            pending_p = db_fetchall("SELECT id FROM projects WHERE approved=0")
            count_u = len(pending_u)
            count_p = len(pending_p)
            for r in pending_u:
                db_execute("UPDATE users SET approved=1 WHERE id=?", (r["id"],))
                try:
                    bot.send_message(r["id"], "✅ <b>تم تفعيل حسابك!</b>\nيمكنك الآن استخدام البوت.")
                except Exception:
                    pass
            for r in pending_p:
                db_execute("UPDATE projects SET approved=1 WHERE id=?", (r["id"],))
                proj = db_fetchone("SELECT user_id, name FROM projects WHERE id=?", (r["id"],))
                if proj:
                    try:
                        bot.send_message(proj["user_id"],
                                         f"✅ <b>تم قبول بوتك</b> «{html_escape(proj['name'])}» !")
                    except Exception:
                        pass
            msg_txt = (
                f"✅ <b>تمت الموافقة على الكل</b>\n\n"
                f"👤 {count_u} مستخدم مُفعَّل\n"
                f"🤖 {count_p} بوت مُقبَل"
            )
            bot.answer_callback_query(call.id, f"✅ {count_u + count_p} طلب تمت الموافقة عليه")
            show_admin_panel(chat_id, msg_id)
            if count_u + count_p > 0:
                bot.send_message(chat_id, msg_txt)

        elif data == "adm_quick_start_all":
            if not is_admin(uid): return
            rows = db_fetchall("SELECT id FROM projects WHERE approved=1")
            started = 0
            for r in rows:
                if not manager.is_running(r["id"]):
                    try:
                        manager.start_project(r["id"])
                        started += 1
                    except Exception:
                        pass
            bot.answer_callback_query(call.id, f"▶️ تم تشغيل {started} بوت")
            show_admin_panel(chat_id, msg_id)

        elif data == "adm_quick_stop_all":
            if not is_admin(uid): return
            rows = db_fetchall("SELECT id FROM projects WHERE approved=1")
            stopped = 0
            for r in rows:
                if manager.is_running(r["id"]):
                    try:
                        manager.stop_project(r["id"])
                        stopped += 1
                    except Exception:
                        pass
            bot.answer_callback_query(call.id, f"⏹ تم إيقاف {stopped} بوت")
            show_admin_panel(chat_id, msg_id)

        elif data == "adm_quick_restart_all":
            if not is_admin(uid): return
            rows = db_fetchall("SELECT id FROM projects WHERE approved=1 AND is_running=1")
            restarted = 0
            for r in rows:
                try:
                    if manager.is_running(r["id"]):
                        manager.stop_project(r["id"])
                    time.sleep(0.3)
                    manager.start_project(r["id"])
                    restarted += 1
                except Exception:
                    pass
            bot.answer_callback_query(call.id, f"🔁 تم إعادة تشغيل {restarted} بوت")
            show_admin_panel(chat_id, msg_id)

        elif data == "proj_new":
            start_new_project(chat_id, uid)

        elif data == "site_upload":
            pop_pending(uid)
            show_netlify_upload_menu(chat_id, uid, msg_id)

        elif data == "site_upload_zip":
            pop_pending(uid)
            start_netlify_upload(chat_id, uid)

        elif data == "vercel_upload":
            pop_pending(uid)
            show_vercel_upload_menu(chat_id, uid, msg_id)

        elif data == "vercel_upload_zip":
            pop_pending(uid)
            if not vercel_is_configured():
                bot.send_message(chat_id, "⚠️ ميزة رفع Vercel غير مفعّلة.\n🔧 فعّلها بإضافة <code>VERCEL_TOKEN</code>.",
                                 reply_markup=back_main_kb())
                return
            ok, msg = check_and_inc_daily(uid, "vercel", 5)
            if not ok:
                bot.send_message(chat_id, msg, reply_markup=back_main_kb())
                return
            price = get_section_price("vercel", 0)
            if price > 0 and not is_admin(uid):
                pts_row = db_fetchone("SELECT COALESCE(points,0) AS p FROM users WHERE id=?", (uid,))
                pts = pts_row["p"] if pts_row else 0
                if pts < price:
                    bot.send_message(chat_id, f"❌ لا تملك نقاطاً كافية.\n💡 سعر رفع Vercel: <b>{price}</b> نقطة.",
                                     reply_markup=back_main_kb())
                    return
                db_execute("UPDATE users SET points = points - ? WHERE id=? AND COALESCE(points,0) >= ?",
                           (price, uid, price))
            set_pending(uid, {"type": "vercel_upload_zip"})
            bot.send_message(chat_id, "▲ <b>رفع موقع على Vercel</b>\n\n📌 ابعت ملف <b>.zip</b> فيه <code>index.html</code>.\n/cancel للإلغاء.",
                             reply_markup=back_main_kb())

        elif data == "proj_list":
            list_user_projects(chat_id, uid, msg_id)

        elif data == "my_stats":
            show_user_stats(chat_id, uid, msg_id)

        elif data == "help":
            show_help(chat_id, msg_id)

        elif data == "my_sites":
            show_user_sites(chat_id, uid, msg_id)

        elif data == "my_deploys":
            show_user_deployments(chat_id, uid, msg_id)

        elif data.startswith("site_redeploy_"):
            parts = data.split("_", 3)
            if len(parts) < 4:
                return
            provider = parts[2]
            site_id = parts[3]
            if provider == "netlify":
                set_pending(uid, {"type": "netlify_upload_zip", "redeploy": True, "site_id": site_id})
                bot.send_message(chat_id, "📤 ابعت ZIP جديد لإعادة نشر موقع Netlify.\n/cancel للإلغاء.")
            else:
                set_pending(uid, {"type": "vercel_redeploy_zip", "redeploy": True, "site_name": site_id})
                bot.send_message(chat_id, "📤 ابعت ZIP جديد لإعادة نشر موقع Vercel.\n/cancel للإلغاء.")

        elif data == "points":
            show_points(chat_id, uid, msg_id)

        elif data == "transfer_points":
            start_transfer_points(chat_id, uid, msg_id)

        elif data.startswith("proj_view_"):
            view_project(chat_id, uid, int(data.split("_")[-1]), msg_id)

        elif data.startswith("proj_start_"):
            pid = int(data.split("_")[-1])
            ok, msg = manager.start_project(pid)
            view_project(chat_id, uid, pid, msg_id)

        elif data.startswith("proj_stop_"):
            pid = int(data.split("_")[-1])
            manager.stop_project(pid)
            view_project(chat_id, uid, pid, msg_id)

        elif data.startswith("proj_restart_"):
            pid = int(data.split("_")[-1])
            manager.restart_project(pid)
            view_project(chat_id, uid, pid, msg_id)

        elif data.startswith("proj_editor_"):
            # فتح محرر الكود — قائمة الملفات
            pid = int(data.split("_")[-1])
            show_editor_files(chat_id, uid, pid, msg_id)

        elif data.startswith("proj_save_confirm_"):
            # المستخدم أكّد حفظ التعديلات بعد رؤية الـ diff
            pid = int(data.split("_")[-1])
            pending = get_pending(uid) or {}
            if pending.get("type") != "proj_file_confirm" or pending.get("project_id") != pid:
                bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية التعديل، حدّد الملف مرة أخرى.")
                show_editor_files(chat_id, uid, pid, msg_id)
                return
            filename    = pending["filename"]
            file_row_id = pending["file_row_id"]
            try:
                content_bytes = base64.b64decode(pending["new_content_b64"])
            except Exception as e:
                bot.answer_callback_query(call.id, "❌ خطأ في البيانات")
                bot.send_message(chat_id, f"❌ فشل استعادة المحتوى: <code>{html_escape(str(e))}</code>")
                pop_pending(uid)
                return
            try:
                _save_file_to_disk_and_db(pid, filename, content_bytes)
            except Exception as e:
                bot.answer_callback_query(call.id, "❌ فشل الحفظ")
                bot.send_message(chat_id, f"❌ فشل حفظ الملف: <code>{html_escape(str(e))}</code>")
                pop_pending(uid)
                return
            pop_pending(uid)
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("✏️ تعديل مرة ثانية", callback_data=f"proj_ef_{pid}_{file_row_id}", style="primary"),
                types.InlineKeyboardButton("📁 قائمة الملفات", callback_data=f"proj_editor_{pid}", style="primary"),
            )
            kb.add(types.InlineKeyboardButton("🔙 لوحة البوت", callback_data=f"proj_view_{pid}", style="primary"))
            try:
                bot.edit_message_text(
                    f"✅ <b>تم حفظ التعديلات بنجاح!</b>\n\n"
                    f"📄 الملف: <code>{html_escape(filename)}</code>\n"
                    f"📦 الحجم: <b>{len(content_bytes):,} بايت</b>\n\n"
                    "⚠️ أعد تشغيل البوت لتفعيل التغييرات.",
                    chat_id, msg_id, reply_markup=kb,
                )
            except Exception:
                bot.send_message(
                    chat_id,
                    f"✅ <b>تم حفظ التعديلات بنجاح!</b>\n\n"
                    f"📄 الملف: <code>{html_escape(filename)}</code>\n"
                    f"📦 الحجم: <b>{len(content_bytes):,} بايت</b>\n\n"
                    "⚠️ أعد تشغيل البوت لتفعيل التغييرات.",
                    reply_markup=kb,
                )
            bot.answer_callback_query(call.id, "✅ تم الحفظ!")

        elif data.startswith("proj_discard_edit_"):
            # المستخدم ألغى التعديلات
            pid = int(data.split("_")[-1])
            pending = get_pending(uid) or {}
            filename = pending.get("filename", "")
            file_row_id = pending.get("file_row_id")
            pop_pending(uid)
            kb = types.InlineKeyboardMarkup(row_width=2)
            if file_row_id:
                kb.add(types.InlineKeyboardButton("✏️ تعديل مرة أخرى", callback_data=f"proj_ef_{pid}_{file_row_id}", style="primary"))
            kb.add(types.InlineKeyboardButton("📁 قائمة الملفات", callback_data=f"proj_editor_{pid}", style="primary"))
            kb.add(types.InlineKeyboardButton("🔙 لوحة البوت", callback_data=f"proj_view_{pid}", style="primary"))
            try:
                bot.edit_message_text(
                    f"🗑 <b>تم تجاهل التعديلات</b>\n\n"
                    f"📄 الملف: <code>{html_escape(filename)}</code>\n"
                    "لم يتم تغيير أي شيء.",
                    chat_id, msg_id, reply_markup=kb,
                )
            except Exception:
                bot.send_message(
                    chat_id,
                    f"🗑 <b>تم تجاهل التعديلات</b>\n\nلم يتم تغيير أي شيء.",
                    reply_markup=kb,
                )
            bot.answer_callback_query(call.id, "🗑 تم التجاهل")

        elif data.startswith("proj_ef_"):
            # المستخدم اختار ملفاً للتعديل — proj_ef_{pid}_{file_row_id}
            parts = data.split("_")
            pid = int(parts[2])
            file_row_id = int(parts[3])
            proj = db_fetchone("SELECT id, user_id FROM projects WHERE id=?", (pid,))
            if not proj or (proj["user_id"] != uid and not is_admin(uid)):
                bot.answer_callback_query(call.id, "❌ غير مسموح")
                return
            row = db_fetchone("SELECT id, filename, content, size_bytes FROM project_files WHERE id=? AND project_id=?",
                              (file_row_id, pid))
            if not row:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود")
                show_editor_files(chat_id, uid, pid, msg_id)
                return

            filename = row["filename"]
            size = row["size_bytes"]

            # ضبط pending أولاً
            pop_pending(uid)
            set_pending(uid, {
                "type": "proj_file_editing",
                "project_id": pid,
                "filename": filename,
                "file_row_id": file_row_id,
            })

            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("📁 قائمة الملفات", callback_data=f"proj_editor_{pid}", style="primary"),
                types.InlineKeyboardButton("❌ إلغاء", callback_data=f"proj_view_{pid}", style="primary"),
            )

            # إذا كان الملف نصياً وصغيراً — أرسل المحتوى للتعديل المباشر
            is_text = any(filename.endswith(ext) for ext in TEXT_PREVIEW_EXTENSIONS) or filename.endswith(".py")
            if is_text and size <= MAX_EDIT_CHARS * 2:
                try:
                    raw = bytes(row["content"])
                    try:
                        content_str = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        content_str = raw.decode("latin-1", errors="replace")

                    lines = content_str.splitlines()
                    line_count = len(lines)
                    bot.answer_callback_query(call.id, f"📄 {filename}")
                    bot.send_message(
                        chat_id,
                        f"✏️ <b>محرر الكود</b>\n"
                        f"📄 <code>{html_escape(filename)}</code>\n"
                        f"<i>({line_count} سطر — {size:,} بايت)</i>\n\n"
                        "📋 <b>المحتوى الحالي:</b>",
                        reply_markup=kb,
                    )
                    # إرسال المحتوى في رسالة منفصلة بصيغة code block
                    preview = content_str[:MAX_EDIT_CHARS]
                    truncated = size > MAX_EDIT_CHARS
                    suffix = f"\n\n<i>… تم عرض {MAX_EDIT_CHARS} حرف من {size:,}</i>" if truncated else ""
                    bot.send_message(
                        chat_id,
                        f"<pre><code>{html_escape(preview)}</code></pre>{suffix}",
                    )
                    bot.send_message(
                        chat_id,
                        "✏️ <b>أرسل الآن النص الجديد الكامل للملف</b> (نسخ ← تعديل ← إرسال)\n"
                        "أو أرسل الملف كـ <b>Document</b> إذا كان كبيراً\n"
                        "أو /cancel للإلغاء.",
                        reply_markup=kb,
                    )
                except Exception as e:
                    bot.send_message(chat_id, f"❌ فشل قراءة الملف: <code>{html_escape(str(e))}</code>")
                    pop_pending(uid)
            else:
                # ملف كبير أو ثنائي — أرسله كمرفق
                bot.answer_callback_query(call.id, f"📦 {filename}")
                try:
                    raw = bytes(row["content"])
                    bio = io.BytesIO(raw)
                    bio.name = filename
                    bot.send_document(chat_id, bio, caption=f"📄 <code>{html_escape(filename)}</code>")
                except Exception as e:
                    bot.send_message(chat_id, f"❌ فشل إرسال الملف: <code>{html_escape(str(e))}</code>")
                bot.send_message(
                    chat_id,
                    f"📦 الملف <code>{html_escape(filename)}</code> كبير ({size//1024} KB)\n\n"
                    "📤 <b>أرسل النسخة المعدَّلة كـ Document</b>\n"
                    "أو /cancel للإلغاء.",
                    reply_markup=kb,
                )

        elif data.startswith("proj_addfile_"):
            pid = int(data.split("_")[-1])
            set_pending(uid, {"type": "add_file", "project_id": pid})
            bot.send_message(chat_id, "📎 أرسل الملف الذي تريد إضافته (txt, json, csv, ...)\n/cancel للإلغاء.")

        elif data.startswith("proj_log_"):
            pid = int(data.split("_")[-1])
            log_text = manager.tail_log(pid, 3500) or "(لا يوجد سجل بعد)"
            bot.send_message(chat_id, f"📜 آخر مخرجات البوت:\n<pre>{html_escape(log_text[-3500:])}</pre>")

        elif data.startswith("proj_files_"):
            pid = int(data.split("_")[-1])
            proj = db_fetchone("SELECT id, user_id, name FROM projects WHERE id=?", (pid,))
            if not proj or (proj["user_id"] != uid and not is_admin(uid)):
                return
            files = list_project_disk_files(pid, limit=450)
            if not files:
                bot.send_message(chat_id, "📁 لا توجد ملفات على السيرفر لهذا البوت بعد.")
                return
            preview = "\n".join(f"• <code>{html_escape(f)}</code>" for f in files[:200])
            more = "" if len(files) <= 200 else f"\n\n… وتم إخفاء {len(files)-200} ملف إضافي."
            bot.send_message(chat_id, f"📁 <b>ملفات البوت:</b>\n{preview}{more}")
            set_pending(uid, {"type": "proj_getfile", "project_id": pid})
            bot.send_message(chat_id, "📤 لو عايز تحمل ملف: ابعت اسم الملف بالظبط\nأو /cancel للإلغاء.")

        elif data.startswith("proj_term_"):
            pid = int(data.split("_")[-1])
            proj = db_fetchone("SELECT id, user_id FROM projects WHERE id=?", (pid,))
            if not proj or (proj["user_id"] != uid and not is_admin(uid)):
                return
            set_pending(uid, {"type": "proj_term_cmd", "project_id": pid})
            bot.send_message(chat_id,
                             "🖥️ <b>تيرمنال البوت</b>\n\n"
                             "✅ مسموح فقط: <code>python</code> و <code>pip</code>\n"
                             "مثال: <code>pip install requests</code>\n\n/cancel للإلغاء.")

        elif data.startswith("proj_install_"):
            pid = int(data.split("_")[-1])
            install_project_requirements(chat_id, uid, pid, msg_id)

        elif data.startswith("proj_del_"):
            pid = int(data.split("_")[-1])
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton(" نعم احذف", callback_data=f"proj_delconfirm_{pid}",
                    style="danger", icon_custom_emoji_id=E_DELETE),
                types.InlineKeyboardButton(" تراجع", callback_data=f"proj_view_{pid}",
                    style="primary", icon_custom_emoji_id=E_BACK),
            )
            bot.edit_message_text("⚠️ هل أنت متأكد من حذف البوت وكل ملفاته؟", chat_id, msg_id, reply_markup=kb)

        elif data.startswith("proj_delconfirm_"):
            pid = int(data.split("_")[-1])
            manager.stop_project(pid)
            db_execute("DELETE FROM projects WHERE id=? AND (user_id=? OR ?=?)", (pid, uid, uid, ADMIN_ID))
            list_user_projects(chat_id, uid, msg_id)

        # ---- أوامر الأدمن ----
        elif data.startswith("adm_") and not is_admin(uid):
            pass

        elif data == "adm_pending_users":
            show_pending_users(chat_id, msg_id)

        elif data == "adm_pending_projects":
            show_pending_projects(chat_id, msg_id)

        elif data == "adm_pending_files":
            show_pending_files(chat_id, msg_id)

        elif data.startswith("adm_preview_file_"):
            pending_id = int(data.split("_")[-1])
            pu = db_fetchone("SELECT * FROM pending_uploads WHERE id=?", (pending_id,))
            if not pu:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود.")
            else:
                bot.answer_callback_query(call.id, "⏳ جاري تحميل المعاينة…")
                _send_file_preview(chat_id, pu["telegram_file_id"], pu["filename"])

        elif data == "adm_users":
            show_all_users(chat_id, msg_id)

        elif data == "adm_projects":
            show_all_projects(chat_id, msg_id)

        elif data == "adm_stats":
            show_admin_stats(chat_id, msg_id)

        elif data == "adm_server_status":
            if not is_admin(uid):
                return
            show_server_status(chat_id, msg_id)

        elif data == "adm_backup_db":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ إنشاء النسخة الاحتياطية…")
            threading.Thread(target=adm_send_backup, args=(chat_id,), daemon=True).start()

        elif data == "adm_growth_stats":
            if not is_admin(uid): return
            adm_show_growth_stats(chat_id, msg_id)

        elif data == "adm_audit_log":
            if not is_admin(uid): return
            adm_show_audit_log(chat_id, msg_id)

        elif data == "adm_cleanup_files":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ التنظيف…")
            threading.Thread(target=adm_cleanup_stopped_files, args=(chat_id,), daemon=True).start()

        elif data == "adm_running_bots_list":
            if not is_admin(uid): return
            adm_show_running_bots(chat_id, msg_id)

        elif data == "adm_export_bots":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ التصدير…")
            threading.Thread(target=adm_export_bots_csv, args=(chat_id,), daemon=True).start()

        elif data == "adm_inactive_users":
            if not is_admin(uid): return
            adm_show_inactive_users(chat_id, msg_id)

        elif data == "adm_usage_stats":
            if not is_admin(uid): return
            adm_show_usage_stats(chat_id, msg_id)

        elif data == "adm_announce":
            if not is_admin(uid): return
            adm_start_announce(chat_id, uid)

        # ── الـ 20 ميزة الجديدة ──
        elif data == "adm_new_today":
            if not is_admin(uid): return
            adm_new_today(chat_id, msg_id)

        elif data == "adm_user_bots_by_id":
            if not is_admin(uid): return
            adm_start_user_bots_by_id(chat_id, uid)

        elif data == "adm_reset_points_id":
            if not is_admin(uid): return
            adm_start_reset_points(chat_id, uid)

        elif data == "adm_set_user_max":
            if not is_admin(uid): return
            adm_start_set_user_max(chat_id, uid)

        elif data == "adm_crashed_bots":
            if not is_admin(uid): return
            adm_show_crashed_bots(chat_id, msg_id)

        elif data == "adm_search_bot_name":
            if not is_admin(uid): return
            adm_start_search_bot(chat_id, uid)

        elif data == "adm_bots_summary":
            if not is_admin(uid): return
            adm_show_bots_summary(chat_id, msg_id)

        elif data == "adm_clear_proc_logs":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ التنظيف…")
            threading.Thread(target=adm_clear_process_logs, args=(chat_id,), daemon=True).start()

        elif data == "adm_msg_to_inactive":
            if not is_admin(uid): return
            adm_start_msg_inactive(chat_id, uid)

        elif data == "adm_broadcast_active_only":
            if not is_admin(uid): return
            adm_start_broadcast_active(chat_id, uid)

        elif data == "adm_receivers_count":
            if not is_admin(uid): return
            adm_show_receivers_count(chat_id, msg_id)

        elif data == "adm_db_table_stats":
            if not is_admin(uid): return
            adm_show_db_table_stats(chat_id, msg_id)

        elif data == "adm_deploy_stats":
            if not is_admin(uid): return
            adm_show_deploy_stats(chat_id, msg_id)

        elif data == "adm_daily_report":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ توليد التقرير…")
            threading.Thread(target=adm_send_daily_report, args=(chat_id,), daemon=True).start()

        elif data == "adm_points_dist":
            if not is_admin(uid): return
            adm_show_points_dist(chat_id, msg_id)

        elif data == "adm_view_settings":
            if not is_admin(uid): return
            adm_show_all_settings(chat_id, msg_id)

        elif data == "adm_toggle_auto_approve":
            if not is_admin(uid): return
            adm_toggle_auto_approve_fn(chat_id, msg_id)

        elif data == "adm_clear_audit":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ التنظيف…")
            threading.Thread(target=adm_clear_old_audit, args=(chat_id,), daemon=True).start()

        elif data == "adm_approve_id":
            if not is_admin(uid): return
            adm_start_approve_id(chat_id, uid)

        elif data == "adm_proc_info":
            if not is_admin(uid): return
            adm_show_proc_info(chat_id, msg_id)

        # ── الدفعة الثالثة — 20 ميزة ──
        elif data == "adm_user_profile":
            if not is_admin(uid): return
            adm_start_user_profile(chat_id, uid)

        elif data == "adm_pending_users":
            if not is_admin(uid): return
            adm_show_pending_users(chat_id, msg_id)

        elif data == "adm_ban_by_id":
            if not is_admin(uid): return
            adm_start_ban_by_id(chat_id, uid)

        elif data == "adm_unban_by_id":
            if not is_admin(uid): return
            adm_start_unban_by_id(chat_id, uid)

        elif data == "adm_vip_users":
            if not is_admin(uid): return
            adm_show_vip_users(chat_id, msg_id)

        elif data == "adm_force_stop_bot":
            if not is_admin(uid): return
            adm_start_force_stop_bot(chat_id, uid)

        elif data == "adm_force_start_bot":
            if not is_admin(uid): return
            adm_start_force_start_bot(chat_id, uid)

        elif data == "adm_bot_files_info":
            if not is_admin(uid): return
            adm_start_bot_files_info(chat_id, uid)

        elif data == "adm_top_bots":
            if not is_admin(uid): return
            adm_show_top_bots(chat_id, msg_id)

        elif data == "adm_new_bots_today":
            if not is_admin(uid): return
            adm_show_new_bots_today(chat_id, msg_id)

        elif data == "adm_msg_by_id":
            if not is_admin(uid): return
            adm_start_msg_by_id(chat_id, uid)

        elif data == "adm_broadcast_pending":
            if not is_admin(uid): return
            adm_start_broadcast_pending(chat_id, uid)

        elif data == "adm_last_broadcast_stats":
            if not is_admin(uid): return
            adm_show_last_broadcast_stats(chat_id, msg_id)

        elif data == "adm_weekly_report":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ توليد التقرير الأسبوعي…")
            threading.Thread(target=adm_send_weekly_report, args=(chat_id,), daemon=True).start()

        elif data == "adm_top_uploaders":
            if not is_admin(uid): return
            adm_show_top_uploaders(chat_id, msg_id)

        elif data == "adm_error_log_view":
            if not is_admin(uid): return
            adm_show_error_log(chat_id, msg_id)

        elif data == "adm_activity_stats":
            if not is_admin(uid): return
            adm_show_activity_stats(chat_id, msg_id)

        elif data == "adm_maintenance_mode":
            if not is_admin(uid): return
            adm_toggle_maintenance(chat_id, msg_id)

        elif data == "adm_sys_info":
            if not is_admin(uid): return
            adm_show_sys_info(chat_id, msg_id)

        elif data == "adm_clear_blocked_db":
            if not is_admin(uid): return
            bot.answer_callback_query(call.id, "⏳ جارٍ التنظيف…")
            threading.Thread(target=adm_clear_blocked_db, args=(chat_id,), daemon=True).start()

        elif data == "adm_broadcast":
            set_pending(uid, {"type": "broadcast"})
            bot.send_message(chat_id, "📢 أرسل نص الإذاعة الآن، أو /cancel.", reply_markup=back_admin_kb())

        elif data == "adm_broadcast_channel":
            set_pending(uid, {"type": "broadcast_channel_list"})
            bot.send_message(
                chat_id,
                "📺 <b>إذاعة للقنوات</b>\n\nأرسل أسماء القنوات مفصولة بفاصلة:\n"
                "مثال: <code>@channel1, @channel2</code>\n\n"
                "⚠️ يجب أن يكون البوت مشرفاً في كل قناة.\n/cancel للإلغاء.",
                reply_markup=back_admin_kb(),
            )

        elif data == "adm_blocked_users":
            show_blocked_users_report(chat_id, uid)

        elif data == "adm_top_users":
            show_top_users(chat_id, msg_id)

        elif data == "adm_export_users":
            export_users_file(chat_id)

        elif data == "adm_gift_new":
            start_create_gift_link(chat_id, uid)

        elif data == "adm_force_channel":
            show_force_channels_panel(chat_id, uid, msg_id)

        elif data == "adm_fc_list":
            show_force_channels_list(chat_id, msg_id)

        elif data == "adm_fc_check":
            channels = get_force_channels()
            if not channels:
                bot.answer_callback_query(call.id, "لا توجد قنوات مضافة.")
            else:
                bot.answer_callback_query(call.id, "⏳ جارٍ الفحص...")
                lines = ["🔍 <b>تقرير صلاحيات البوت في القنوات:</b>\n"]
                all_ok = True
                for ch in channels:
                    lbl = html_escape(ch["label"] or ch["channel"])
                    perm = check_bot_channel_permissions(ch["channel"])
                    if perm["ok"]:
                        lines.append(f"✅ <b>{lbl}</b> — صلاحيات سليمة")
                    else:
                        all_ok = False
                        err = html_escape(perm["error"] or "خطأ غير محدد")
                        lines.append(
                            f"❌ <b>{lbl}</b>\n"
                            f"   <code>{html_escape(str(ch['channel']))}</code>\n"
                            f"   ↳ {err}"
                        )
                        # تنبيه الأدمن وإعادة تهيئة كاش التحذير لهذه القناة لإعادة الإرسال
                        _perm_warn_sent.discard(str(ch["channel"]))
                        notify_admin_perm_error(str(ch["channel"]), ch["label"] or ch["channel"], perm["error"] or "خطأ غير محدد")
                if all_ok:
                    lines.append("\n🎉 جميع القنوات تعمل بشكل صحيح!")
                else:
                    lines.append(
                        "\n📌 <b>الحل:</b> اجعل البوت مشرفاً في القنوات المعطوبة\n"
                        "ومنحه صلاحية <b>Invite Users via Link</b>."
                    )
                bot.send_message(chat_id, "\n".join(lines), reply_markup=back_admin_kb())

        elif data == "adm_fc_add":
            show_fc_wizard_step1(chat_id, uid)

        elif data == "fc_wiz_to2":
            # التالي من الخطوة 1 إلى 2 — اطلب الـ ID
            pending = get_pending(uid) or {}
            if not pending.get("link"):
                bot.answer_callback_query(call.id, "⚠️ انتهت الجلسة، أعد المحاولة.", show_alert=True)
                show_force_channels_panel(chat_id, uid, msg_id)
                return
            pending["type"] = "fc_wiz_step2"
            set_pending(uid, pending)
            bot.answer_callback_query(call.id, "✅ تم الانتقال للخطوة 2")
            bot.send_message(
                chat_id,
                "📢 <b>إضافة قناة — الخطوة 2 من 3</b>\n\n"
                "🆔 <b>أرسل الـ ID (Chat ID)</b> للقناة:\n\n"
                "مثال قناة خاصة:\n<code>-1001234567890</code>\n"
                "أو يوزرنيم قناة عامة:\n<code>@channel_name</code>",
                reply_markup=_fc_wizard_cancel_kb(),
            )

        elif data == "fc_wiz_to3":
            # التالي من الخطوة 2 إلى 3 — اطلب الاسم
            pending = get_pending(uid) or {}
            if not pending.get("channel_id"):
                bot.answer_callback_query(call.id, "⚠️ انتهت الجلسة، أعد المحاولة.", show_alert=True)
                show_force_channels_panel(chat_id, uid, msg_id)
                return
            pending["type"] = "fc_wiz_step3"
            set_pending(uid, pending)
            bot.answer_callback_query(call.id, "✅ تم الانتقال للخطوة 3")
            bot.send_message(
                chat_id,
                "📢 <b>إضافة قناة — الخطوة 3 من 3</b>\n\n"
                "✏️ <b>أرسل اسم القناة</b> الذي سيظهر للمستخدمين:",
                reply_markup=_fc_wizard_cancel_kb(),
            )

        elif data.startswith("adm_fc_upd_"):
            # تحديث رابط (مسار قديم للتوافق)
            try:
                fid = int(data.split("_")[-1])
            except Exception:
                fid = None
            if fid:
                pop_pending(uid)
                set_pending(uid, {"type": "fc_edit_link", "fid": fid})
                ch_row = db_fetchone("SELECT label, channel FROM force_channels WHERE id=?", (fid,))
                lbl = html_escape((ch_row or {}).get("label") or (ch_row or {}).get("channel") or "")
                bot.send_message(chat_id,
                                 f"🔗 <b>تعديل رابط الدعوة</b>\n\n"
                                 f"القناة: <b>{lbl}</b>\n\n"
                                 "أرسل الرابط الجديد:\n"
                                 "<code>https://t.me/+AbCdEfGhIjKl</code>\n"
                                 "أو أرسل <code>-</code> لحذف الرابط.\n\nأو /cancel.",
                                 reply_markup=_fc_wizard_cancel_kb())
            else:
                show_force_channels_list(chat_id, msg_id)

        elif data.startswith("adm_fc_edit_"):
            # لوحة تعديل القناة
            try:
                fid = int(data.split("_")[-1])
            except Exception:
                fid = None
            if fid:
                bot.answer_callback_query(call.id)
                show_fc_edit_panel(chat_id, fid, msg_id)
            else:
                show_force_channels_list(chat_id, msg_id)

        elif data.startswith("adm_fc_ename_"):
            # تعديل الاسم
            try:
                fid = int(data.split("_")[-1])
            except Exception:
                fid = None
            if fid:
                pop_pending(uid)
                set_pending(uid, {"type": "fc_edit_name", "fid": fid})
                ch = db_fetchone("SELECT label, channel FROM force_channels WHERE id=?", (fid,))
                current = html_escape((ch or {}).get("label") or (ch or {}).get("channel") or "")
                bot.send_message(chat_id,
                                 f"✏️ <b>تعديل اسم القناة</b>\n\n"
                                 f"الاسم الحالي: <b>{current}</b>\n\n"
                                 "أرسل الاسم الجديد أو /cancel.",
                                 reply_markup=_fc_wizard_cancel_kb())
            else:
                show_force_channels_list(chat_id, msg_id)

        elif data.startswith("adm_fc_elink_"):
            # تعديل الرابط
            try:
                fid = int(data.split("_")[-1])
            except Exception:
                fid = None
            if fid:
                pop_pending(uid)
                set_pending(uid, {"type": "fc_edit_link", "fid": fid})
                ch = db_fetchone("SELECT invite_link FROM force_channels WHERE id=?", (fid,))
                current = html_escape((ch or {}).get("invite_link") or "—")
                bot.send_message(chat_id,
                                 f"🔗 <b>تعديل رابط الدعوة</b>\n\n"
                                 f"الرابط الحالي: <code>{current}</code>\n\n"
                                 "أرسل الرابط الجديد:\n"
                                 "<code>https://t.me/+AbCdEfGhIjKl</code>\n"
                                 "أو أرسل <code>-</code> لحذف الرابط.\n\nأو /cancel.",
                                 reply_markup=_fc_wizard_cancel_kb())
            else:
                show_force_channels_list(chat_id, msg_id)

        elif data.startswith("adm_fc_eid_"):
            # تعديل الـ ID
            try:
                fid = int(data.split("_")[-1])
            except Exception:
                fid = None
            if fid:
                pop_pending(uid)
                set_pending(uid, {"type": "fc_edit_id", "fid": fid})
                ch = db_fetchone("SELECT channel FROM force_channels WHERE id=?", (fid,))
                current = html_escape((ch or {}).get("channel") or "")
                bot.send_message(chat_id,
                                 f"🆔 <b>تعديل الـ ID</b>\n\n"
                                 f"الـ ID الحالي: <code>{current}</code>\n\n"
                                 "أرسل الـ ID الجديد:\n"
                                 "مثال رقمي: <code>-1001234567890</code>\n"
                                 "أو يوزرنيم: <code>@channel_name</code>\n\nأو /cancel.",
                                 reply_markup=_fc_wizard_cancel_kb())
            else:
                show_force_channels_list(chat_id, msg_id)

        elif data.startswith("adm_fc_del_"):
            try:
                fid = int(data.split("_")[-1])
                del_force_channel(fid)
                bot.answer_callback_query(call.id, "🗑 تم حذف القناة")
            except Exception:
                pass
            show_force_channels_list(chat_id, msg_id)

        elif data == "adm_set_upload_price":
            start_set_upload_price(chat_id, uid)

        elif data == "adm_set_transfer_fee":
            start_set_transfer_fee(chat_id, uid)

        elif data == "adm_ban_by_id":
            start_ban_by_id(chat_id, uid)

        elif data == "adm_unban_by_id":
            start_unban_by_id(chat_id, uid)

        elif data == "adm_user_info":
            start_user_info(chat_id, uid)

        elif data == "adm_toggle_bot":
            new_state = not is_bot_disabled()
            set_bot_disabled(new_state)
            try:
                bot.edit_message_text("👑 لوحة المطور:", chat_id, msg_id, reply_markup=admin_menu_markup())
            except Exception:
                pass

        elif data == "adm_mods":
            if not is_admin(uid):
                return
            set_pending(uid, {"type": "mods_menu"})
            bot.send_message(
                chat_id,
                "🛡️ <b>المشرفين</b>\n\n"
                "أرسل ID لإضافة/حذف مشرف.\n"
                "صيغة الإضافة: <code>+123456789</code>\n"
                "صيغة الحذف: <code>-123456789</code>\n"
                "/cancel للإلغاء.",
                reply_markup=back_admin_kb(),
            )

        elif data == "adm_section_prices":
            if not is_admin(uid):
                return
            set_pending(uid, {"type": "set_section_price"})
            bot.send_message(
                chat_id,
                "💵 <b>أسعار الأقسام</b>\n\nاكتب بالشكل:\n"
                "<code>netlify 5</code>\n<code>vercel 5</code>\n<code>terminal 1</code>\n\n"
                "0 = مجاني.\n/cancel للإلغاء.",
                reply_markup=back_admin_kb(),
            )

        elif data == "adm_give_points":
            set_pending(uid, {"type": "give_points_input", "step": "id"})
            bot.send_message(chat_id, "💰 <b>منح نقاط لمستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\n/cancel للإلغاء.",
                             reply_markup=back_admin_kb())

        elif data == "adm_set_points":
            set_pending(uid, {"type": "set_points_input", "step": "id"})
            bot.send_message(chat_id, "⭐ <b>تعيين نقاط مستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\n/cancel للإلغاء.",
                             reply_markup=back_admin_kb())

        elif data == "adm_set_max_bots":
            set_pending(uid, {"type": "set_max_bots_input", "step": "id"})
            bot.send_message(chat_id, "🤖 <b>تعديل حد البوتات لمستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\n/cancel للإلغاء.",
                             reply_markup=back_admin_kb())

        elif data == "adm_send_user":
            set_pending(uid, {"type": "send_user_id"})
            bot.send_message(chat_id, "📩 <b>إرسال رسالة لمستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\n/cancel للإلغاء.",
                             reply_markup=back_admin_kb())

        elif data == "adm_set_welcome":
            if not is_admin(uid):
                return
            current_welcome = get_setting("welcome_text") or ""
            preview = current_welcome[:200] + ("…" if len(current_welcome) > 200 else "") if current_welcome else "_(لم يُضبط بعد)_"
            pop_pending(uid)
            set_pending(uid, {"type": "adm_set_welcome"})
            bot.edit_message_text(
                f"✏️ <b>تغيير رسالة الترحيب</b>\n\n"
                f"الرسالة الحالية:\n<code>{html_escape(preview)}</code>\n\n"
                "أرسل النص الجديد لرسالة الترحيب.\n"
                "يمكنك استخدام <code>{name}</code> لاسم المستخدم.\n"
                "أرسل <code>-</code> لإعادة النص الافتراضي.",
                chat_id, msg_id, reply_markup=back_admin_kb(),
            )

        elif data == "adm_set_welcome_img":
            if not is_admin(uid):
                return
            pop_pending(uid)
            set_pending(uid, {"type": "adm_set_welcome_img"})
            has_custom = bool(get_setting("welcome_image_id"))
            status_txt = "✅ يوجد صورة مخصصة حالياً." if has_custom else "ℹ️ لا توجد صورة مخصصة، يُستخدم الافتراضي."
            _img_kb = types.InlineKeyboardMarkup()
            if has_custom or True:  # دائماً نعرض زرار المعاينة
                _img_kb.add(types.InlineKeyboardButton(
                    "🖼 معاينة الصورة الحالية", callback_data="adm_preview_welcome_img", style="primary",
                ))
            _img_kb.add(types.InlineKeyboardButton(
                " رجوع للوحة الأدمن", callback_data="adm_panel",
                style="primary", icon_custom_emoji_id=E_BACK,
            ))
            bot.edit_message_text(
                f"🖼 <b>تغيير صورة الترحيب</b>\n\n"
                f"{status_txt}\n\n"
                "أرسل الصورة الجديدة التي تريدها كصورة ترحيب.\n"
                "أرسل <code>-</code> لإعادة الصورة الافتراضية.",
                chat_id, msg_id, reply_markup=_img_kb,
            )

        elif data == "adm_preview_welcome_img":
            if not is_admin(uid):
                return
            _img = get_setting("welcome_image_id") or WELCOME_IMAGE
            _src = "مخصصة" if get_setting("welcome_image_id") else "افتراضية"
            try:
                bot.send_photo(
                    chat_id, _img,
                    caption=f"🖼 <b>صورة الترحيب الحالية</b> ({_src})",
                    parse_mode="HTML",
                    reply_markup=back_admin_kb(),
                )
            except Exception:
                bot.send_message(chat_id, "⚠️ تعذّر تحميل الصورة الحالية.", reply_markup=back_admin_kb())

        elif data == "adm_set_banned_img":
            if not is_admin(uid):
                return
            pop_pending(uid)
            set_pending(uid, {"type": "adm_set_banned_img"})
            has_custom = bool(get_setting("banned_image_id"))
            status_txt = "✅ يوجد صورة مخصصة حالياً." if has_custom else "ℹ️ لا توجد صورة مخصصة، يُستخدم الافتراضي."
            _bkb = types.InlineKeyboardMarkup()
            _bkb.add(types.InlineKeyboardButton("🖼 معاينة الصورة الحالية", callback_data="adm_preview_banned_img", style="primary"))
            _bkb.add(types.InlineKeyboardButton(" رجوع للوحة الأدمن", callback_data="adm_panel", style="primary", icon_custom_emoji_id=E_BACK))
            bot.edit_message_text(
                f"🚫 <b>تغيير صورة الحظر</b>\n\n{status_txt}\n\n"
                "أرسل الصورة الجديدة لصورة الحظر.\n"
                "أرسل <code>-</code> لإعادة الصورة الافتراضية.",
                chat_id, msg_id, reply_markup=_bkb,
            )

        elif data == "adm_preview_banned_img":
            if not is_admin(uid):
                return
            _img = get_setting("banned_image_id") or BANNED_IMAGE
            _src = "مخصصة" if get_setting("banned_image_id") else "افتراضية"
            try:
                bot.send_photo(chat_id, _img, caption=f"🚫 <b>صورة الحظر الحالية</b> ({_src})", parse_mode="HTML", reply_markup=back_admin_kb())
            except Exception:
                bot.send_message(chat_id, "⚠️ تعذّر تحميل الصورة الحالية.", reply_markup=back_admin_kb())

        elif data == "adm_set_maint_img":
            if not is_admin(uid):
                return
            pop_pending(uid)
            set_pending(uid, {"type": "adm_set_maint_img"})
            has_custom = bool(get_setting("maintenance_image_id"))
            status_txt = "✅ يوجد صورة مخصصة حالياً." if has_custom else "ℹ️ لا توجد صورة مخصصة، يُستخدم الافتراضي."
            _mkb = types.InlineKeyboardMarkup()
            _mkb.add(types.InlineKeyboardButton("🖼 معاينة الصورة الحالية", callback_data="adm_preview_maint_img", style="primary"))
            _mkb.add(types.InlineKeyboardButton(" رجوع للوحة الأدمن", callback_data="adm_panel", style="primary", icon_custom_emoji_id=E_BACK))
            bot.edit_message_text(
                f"🔧 <b>تغيير صورة الصيانة</b>\n\n{status_txt}\n\n"
                "أرسل الصورة الجديدة لصورة الصيانة.\n"
                "أرسل <code>-</code> لإعادة الصورة الافتراضية.",
                chat_id, msg_id, reply_markup=_mkb,
            )

        elif data == "adm_preview_maint_img":
            if not is_admin(uid):
                return
            _img = get_setting("maintenance_image_id") or MAINTENANCE_IMAGE
            _src = "مخصصة" if get_setting("maintenance_image_id") else "افتراضية"
            try:
                bot.send_photo(chat_id, _img, caption=f"🔧 <b>صورة الصيانة الحالية</b> ({_src})", parse_mode="HTML", reply_markup=back_admin_kb())
            except Exception:
                bot.send_message(chat_id, "⚠️ تعذّر تحميل الصورة الحالية.", reply_markup=back_admin_kb())

        elif data == "adm_set_banned_txt":
            if not is_admin(uid):
                return
            pop_pending(uid)
            set_pending(uid, {"type": "adm_set_banned_txt"})
            current = get_setting("banned_text") or "_(الافتراضي)_"
            preview = current[:200] + ("…" if len(current) > 200 else "")
            bot.edit_message_text(
                f"✍️ <b>رسالة الحظر</b>\n\nالنص الحالي:\n<code>{html_escape(preview)}</code>\n\n"
                "أرسل النص الجديد (يدعم HTML).\n"
                "أرسل <code>-</code> لإعادة النص الافتراضي.",
                chat_id, msg_id, reply_markup=back_admin_kb(),
            )

        elif data == "adm_set_maint_txt":
            if not is_admin(uid):
                return
            pop_pending(uid)
            set_pending(uid, {"type": "adm_set_maint_txt"})
            current = get_setting("maintenance_text") or "_(الافتراضي)_"
            preview = current[:200] + ("…" if len(current) > 200 else "")
            bot.edit_message_text(
                f"🔧 <b>رسالة الصيانة</b>\n\nالنص الحالي:\n<code>{html_escape(preview)}</code>\n\n"
                "أرسل النص الجديد (يدعم HTML).\n"
                "أرسل <code>-</code> لإعادة النص الافتراضي.",
                chat_id, msg_id, reply_markup=back_admin_kb(),
            )

        elif data == "adm_toggle_notify":
            current = is_admin_notify_enabled("notify_admin_new_user", True)
            set_setting("notify_admin_new_user", "0" if current else "1")
            try:
                bot.edit_message_text("👑 لوحة المطور:", chat_id, msg_id, reply_markup=admin_menu_markup())
            except Exception:
                pass

        elif data == "adm_btn_colors":
            show_btn_colors(chat_id, msg_id)

        elif data.startswith("adm_btn_color_group:"):
            group_key = data.split(":", 1)[1]
            if group_key in BTN_COLOR_GROUPS:
                show_btn_color_pick(chat_id, group_key, msg_id)

        elif data.startswith("adm_btn_color_pick:"):
            parts = data.split(":", 2)
            if len(parts) == 3:
                _, group_key, color = parts
                if group_key in BTN_COLOR_GROUPS and color in _COLOR_LABELS:
                    set_setting(f"btn_color_{group_key}", color)
                    label, = BTN_COLOR_GROUPS[group_key]
                    color_lbl = _COLOR_LABELS[color]
                    bot.answer_callback_query(call.id, f"✅ {label}: {color_lbl}", show_alert=False)
                show_btn_color_pick(chat_id, group_key, msg_id)

        elif data == "adm_search_user":
            start_search_user(chat_id, uid)

        elif data == "adm_give_all_points":
            set_pending(uid, {"type": "give_all_points_input"})
            count_row = db_fetchone("SELECT COUNT(*) AS c FROM users WHERE approved=1 AND banned=0")
            count = count_row["c"] if count_row else 0
            bot.send_message(
                chat_id,
                f"🎁 <b>منح نقاط لكل المستخدمين</b>\n\n"
                f"👥 عدد المستخدمين المؤهلين: <b>{count}</b>\n\n"
                "أرسل عدد النقاط (موجب=إضافة، سالب=خصم).\n/cancel للإلغاء.",
                reply_markup=back_admin_kb(),
            )

        elif data == "admin_warn_user":
            set_pending(uid, {"type": "warn_user_id"})
            bot.send_message(
                chat_id,
                "⚠️ <b>تحذير مستخدم</b>\n\nأرسل <b>ID</b> المستخدم.\nأو /cancel.",
                reply_markup=back_admin_kb(),
            )

        elif data == "admin_list_blocked":
            show_list_blocked_from_db(chat_id, msg_id)

        elif data == "adm_del_stopped":
            stopped = db_fetchone("SELECT COUNT(*) AS c FROM projects WHERE is_running=0 AND approved=1")
            count = stopped["c"] if stopped else 0
            kb_confirm = types.InlineKeyboardMarkup()
            kb_confirm.add(
                types.InlineKeyboardButton(" نعم احذف الكل", callback_data="adm_del_stopped_confirm",
                    style="danger", icon_custom_emoji_id=E_DELETE),
                types.InlineKeyboardButton(" تراجع", callback_data="adm_panel",
                    style="primary", icon_custom_emoji_id=E_BACK),
            )
            bot.edit_message_text(f"⚠️ هل أنت متأكد من حذف <b>{count}</b> بوت متوقف وكل ملفاته؟",
                                  chat_id, msg_id, reply_markup=kb_confirm)

        elif data == "adm_del_stopped_confirm":
            rows = db_fetchall("SELECT id FROM projects WHERE is_running=0 AND approved=1")
            deleted = 0
            for r in rows:
                manager.stop_project(r["id"])
                db_execute("DELETE FROM projects WHERE id=?", (r["id"],))
                deleted += 1
            try:
                bot.edit_message_text(f"✅ تم حذف <b>{deleted}</b> بوت متوقف.", chat_id, msg_id,
                                      reply_markup=back_admin_kb())
            except Exception:
                pass

        elif data.startswith("adm_approve_user_"):
            target = int(data.split("_")[-1])
            db_execute("UPDATE users SET approved=1, banned=0 WHERE id=?", (target,))
            try:
                bot.send_message(target, f"🎉 تم تفعيل حسابك. أرسل /start للبدء.\n\n💬 {get_random_quote()}")
            except Exception:
                pass

        elif data.startswith("adm_ban_user_"):
            target = int(data.split("_")[-1])
            db_execute("UPDATE users SET banned=1 WHERE id=?", (target,))
            for p in db_fetchall("SELECT id FROM projects WHERE user_id=?", (target,)):
                manager.stop_project(p["id"])

        elif data.startswith("adm_unban_user_"):
            target = int(data.split("_")[-1])
            db_execute("UPDATE users SET banned=0 WHERE id=?", (target,))

        elif data.startswith("adm_approve_proj_"):
            pid = int(data.split("_")[-1])
            approve_project(pid)
            try:
                bot.edit_message_text(f"✅ تمت الموافقة على البوت #{pid}", chat_id, msg_id)
            except Exception:
                pass

        elif data.startswith("adm_reject_proj_"):
            pid = int(data.split("_")[-1])
            row = db_fetchone("SELECT user_id, name FROM projects WHERE id=?", (pid,))
            if row:
                try:
                    bot.send_message(row["user_id"], f"❌ تم رفض البوت <b>{html_escape(row['name'])}</b> من المطور.")
                except Exception:
                    pass
            db_execute("DELETE FROM projects WHERE id=?", (pid,))
            try:
                bot.edit_message_text(f"❌ تم رفض البوت #{pid}", chat_id, msg_id)
            except Exception:
                pass

        elif data.startswith("adm_approve_file_"):
            pending_id = int(data.split("_")[-1])
            pu = db_fetchone("SELECT * FROM pending_uploads WHERE id=?", (pending_id,))
            if not pu:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود أو تمت معالجته مسبقاً.")
            else:
                try:
                    file_info = bot.get_file(pu["telegram_file_id"])
                    file_data = bot.download_file(file_info.file_path)
                    db_execute(
                        "INSERT INTO project_files (project_id, filename, content, size_bytes) VALUES (?,?,?,?) "
                        "ON CONFLICT (project_id, filename) DO UPDATE SET content=excluded.content, "
                        "size_bytes=excluded.size_bytes, updated_at=CURRENT_TIMESTAMP",
                        (pu["project_id"], pu["filename"], sqlite3.Binary(file_data), len(file_data)),
                    )
                    db_execute("DELETE FROM pending_uploads WHERE id=?", (pending_id,))
                    proj = db_fetchone("SELECT name FROM projects WHERE id=?", (pu["project_id"],))
                    try:
                        bot.send_message(
                            pu["user_id"],
                            f"✅ تمت الموافقة على ملف <code>{html_escape(pu['filename'])}</code> "
                            f"وإضافته للبوت <b>{html_escape((proj or {}).get('name', ''))}</b>.",
                        )
                    except Exception:
                        pass
                    try:
                        bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=msg_id,
                            caption=f"✅ تمت الموافقة على الملف <code>{html_escape(pu['filename'])}</code> #{pending_id}",
                        )
                    except Exception:
                        try:
                            bot.edit_message_text(
                                f"✅ تمت الموافقة على الملف <code>{html_escape(pu['filename'])}</code> #{pending_id}",
                                chat_id, msg_id,
                            )
                        except Exception:
                            pass
                except Exception as e:
                    log.exception("approve_file failed for pending_id=%s", pending_id)
                    bot.answer_callback_query(call.id, f"❌ فشل تحميل الملف: {str(e)[:100]}")

        elif data.startswith("adm_reject_file_"):
            pending_id = int(data.split("_")[-1])
            pu = db_fetchone("SELECT * FROM pending_uploads WHERE id=?", (pending_id,))
            if not pu:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود أو تمت معالجته مسبقاً.")
            else:
                db_execute("DELETE FROM pending_uploads WHERE id=?", (pending_id,))
                try:
                    bot.send_message(
                        pu["user_id"],
                        f"❌ تم رفض الملف <code>{html_escape(pu['filename'])}</code> من المطور.",
                    )
                except Exception:
                    pass
                try:
                    bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=msg_id,
                        caption=f"❌ تم رفض الملف <code>{html_escape(pu['filename'])}</code> #{pending_id}",
                    )
                except Exception:
                    try:
                        bot.edit_message_text(
                            f"❌ تم رفض الملف <code>{html_escape(pu['filename'])}</code> #{pending_id}",
                            chat_id, msg_id,
                        )
                    except Exception:
                        pass

    except Exception as e:
        log.exception("callback error: %s", data)
        try:
            bot.send_message(chat_id, f"❌ خطأ: {str(e)[:200]}")
        except Exception:
            pass


# ============================================================
# 29) Fallback للرسائل النصية
# ============================================================
@bot.message_handler(
    func=lambda m: not (m.text or "").startswith("/"),
    content_types=["text"],
)
def fallback(message):
    if msg_seen(message):
        return
    if get_pending(message.from_user.id):
        return
    show_main_menu(message.chat.id, message.from_user.id)


# ============================================================
# 30) نقطة التشغيل
# ============================================================
def graceful_shutdown(signum, frame):
    log.warning("Received signal %s, shutting down…", signum)
    try:
        manager.shutdown()
    finally:
        sys.exit(0)


def run_polling():
    try:
        bot.remove_webhook()
    except Exception:
        pass
    while True:
        try:
            log.info("Starting Telegram polling…")
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=False,
                allowed_updates=["message", "callback_query"],
                logger_level=logging.WARNING,
            )
        except Exception:
            log.exception("Polling crashed; restarting in 5s")
            time.sleep(5)


def main():
    log.info("Opening SQLite database…")
    db_init()
    db_create_schema()
    db_ensure_columns()

    db_execute("UPDATE projects SET is_running=0")

    log.info("Starting watchdog…")
    manager.start_watchdog()

    log.info("Restoring previously-running projects…")
    try:
        manager.restore_running()
    except Exception:
        log.exception("restore_running failed")

    try:
        signal.signal(signal.SIGTERM, graceful_shutdown)
        signal.signal(signal.SIGINT, graceful_shutdown)
    except Exception:
        pass

    log.info("Hosting bot is up. Admin id=%s", ADMIN_ID)
    run_polling()


if __name__ == "__main__":
    main()
