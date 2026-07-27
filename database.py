"""
===============================================================================
DATABASE.PY
Telegram Directory Bot v2.0
===============================================================================

Handles:
    • PostgreSQL Connection Pool
    • Database Initialization
    • Profile Cache
    • User CRUD
    • Reset Requests
    • Error Handling

Author: ChatGPT
===============================================================================
"""

import os
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional, Tuple

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor


# =============================================================================
# CONFIGURATION
# =============================================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not found.")


# =============================================================================
# LOGGER
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# CONNECTION POOL
# =============================================================================

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL
)


def get_connection():
    """
    Get a database connection from the pool.
    """
    return connection_pool.getconn()


def release_connection(conn):
    """
    Return connection back to the pool.
    """
    if conn:
        connection_pool.putconn(conn)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

@contextmanager
def get_cursor(dictionary: bool = False):
    """
    Context manager for PostgreSQL cursor.

    Automatically:

    - Gets pooled connection
    - Creates cursor
    - Commits transaction
    - Rolls back on exception
    - Closes cursor
    - Releases connection
    """

    conn = get_connection()

    if dictionary:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()

    try:
        yield cursor
        conn.commit()

    except Exception:

        conn.rollback()
        logger.exception("Database transaction failed.")
        raise

    finally:

        cursor.close()
        release_connection(conn)


# =============================================================================
# PROFILE CACHE
# =============================================================================

PROFILE_CACHE: List[Dict] = []


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """
    Creates all required tables if they do not exist.
    """

    logger.info("Initializing database...")

    with get_cursor() as cur:

        # ==========================================================
        # USERS
        # ==========================================================

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(

            telegram_id BIGINT PRIMARY KEY,

            selected_profile_id INTEGER NOT NULL,

            selected_name TEXT NOT NULL,

            selected_bot TEXT NOT NULL,

            selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );
        """)

        logger.info("Users table verified.")

        # ==========================================================
        # RESET REQUESTS
        # ==========================================================

        cur.execute("""

        CREATE TABLE IF NOT EXISTS reset_requests(

            telegram_id BIGINT PRIMARY KEY,

            status TEXT NOT NULL,

            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );

        """)

        logger.info("Reset request table verified.")

        # ==========================================================
        # PROFILES
        # ==========================================================

        cur.execute("""

        CREATE TABLE IF NOT EXISTS profiles(

            id INTEGER PRIMARY KEY,

            name TEXT NOT NULL,

            age INTEGER,

            marital_status TEXT,

            country TEXT,

            about TEXT,

            image TEXT,

            bot_link TEXT NOT NULL,

            is_active BOOLEAN DEFAULT TRUE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );

        """)

        logger.info("Profiles table verified.")

    logger.info("Database initialized successfully.")

# =============================================================================
# PROFILE CACHE FUNCTIONS
# =============================================================================

def load_profiles() -> None:
    """
    Loads all active profiles into memory.

    This function should be called once when the bot starts.
    """

    global PROFILE_CACHE

    logger.info("Loading profile cache...")

    with get_cursor(dictionary=True) as cur:

        cur.execute("""
            SELECT
                id,
                name,
                age,
                marital_status AS status,
                country,
                about,
                image AS photo,
                bot_link AS bot
            FROM profiles
            WHERE is_active = TRUE
            ORDER BY id;
        """)

        PROFILE_CACHE = list(cur.fetchall())

    logger.info("Loaded %d active profiles.", len(PROFILE_CACHE))


def refresh_profiles() -> None:
    """
    Refresh profile cache from PostgreSQL.
    """

    logger.info("Refreshing profile cache...")

    load_profiles()

    logger.info("Profile cache refreshed.")


def get_profiles() -> List[Dict]:
    """
    Returns cached profiles.

    No database query is executed.
    """

    return PROFILE_CACHE


# =============================================================================
# USER FUNCTIONS
# =============================================================================

def save_selection(
    telegram_id: int,
    profile_id: int,
    selected_name: str,
    selected_bot: str
) -> None:
    """
    Save the selected profile for a user.
    """

    logger.info(
        "Saving selection for Telegram ID %s (%s)",
        telegram_id,
        selected_name
    )

    with get_cursor() as cur:

        cur.execute(
            """
            INSERT INTO users(

                telegram_id,
                selected_profile_id,
                selected_name,
                selected_bot

            )

            VALUES (%s,%s,%s,%s)
            """,
            (
                telegram_id,
                profile_id,
                selected_name,
                selected_bot
            )
        )


def user_exists(
    telegram_id: int
) -> bool:
    """
    Returns True if the user has already selected a profile.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT 1
            FROM users
            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )

        return cur.fetchone() is not None


def get_selection(
    telegram_id: int
) -> Optional[Tuple[str, str]]:
    """
    Returns:

        (
            selected_name,
            selected_bot
        )

    or None.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT

                selected_name,
                selected_bot

            FROM users

            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )

        row = cur.fetchone()

        if row is None:
            return None

        return row


def reset_selection(
    telegram_id: int
) -> None:
    """
    Deletes the selected profile.

    Called after admin approval.
    """

    logger.info(
        "Resetting profile selection for %s",
        telegram_id
    )

    with get_cursor() as cur:

        cur.execute(
            """
            DELETE
            FROM users
            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )

# =============================================================================
# RESET REQUEST FUNCTIONS
# =============================================================================

def has_pending_request(
    telegram_id: int
) -> bool:
    """
    Returns True if user already has
    a pending reset request.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT status
            FROM reset_requests
            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )

        row = cur.fetchone()

        return (
            row is not None
            and row[0] == "PENDING"
        )


def create_reset_request(
    telegram_id: int
) -> None:
    """
    Creates or updates
    a reset request.
    """

    logger.info(
        "Creating reset request for %s",
        telegram_id
    )

    with get_cursor() as cur:

        cur.execute(
            """
            INSERT INTO reset_requests(

                telegram_id,
                status

            )

            VALUES(

                %s,
                'PENDING'

            )

            ON CONFLICT(telegram_id)

            DO UPDATE SET

                status='PENDING',
                requested_at=CURRENT_TIMESTAMP
            """,
            (telegram_id,)
        )


def approve_request(
    telegram_id: int
) -> None:
    """
    Marks request as approved.
    """

    logger.info(
        "Approved reset request %s",
        telegram_id
    )

    with get_cursor() as cur:

        cur.execute(
            """
            UPDATE reset_requests

            SET status='APPROVED'

            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )


def reject_request(
    telegram_id: int
) -> None:
    """
    Marks request as rejected.
    """

    logger.info(
        "Rejected reset request %s",
        telegram_id
    )

    with get_cursor() as cur:

        cur.execute(
            """
            UPDATE reset_requests

            SET status='REJECTED'

            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )


def delete_request(
    telegram_id: int
) -> None:
    """
    Deletes request after
    approval/rejection.
    """

    logger.info(
        "Deleting reset request %s",
        telegram_id
    )

    with get_cursor() as cur:

        cur.execute(
            """
            DELETE
            FROM reset_requests
            WHERE telegram_id=%s
            """,
            (telegram_id,)
        )


# =============================================================================
# SHUTDOWN
# =============================================================================

def close_pool() -> None:
    """
    Close all PostgreSQL connections.

    Call this only when the bot
    is shutting down.
    """

    logger.info("Closing PostgreSQL connection pool.")

    if connection_pool:
        connection_pool.closeall()


# =============================================================================
# DATABASE STATS
# =============================================================================

def get_database_stats() -> dict:
    """
    Returns basic database statistics.
    Useful for admin commands.
    """

    with get_cursor() as cur:

        cur.execute("SELECT COUNT(*) FROM users")
        users = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM profiles
            WHERE is_active=TRUE
        """)
        profiles = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM reset_requests
            WHERE status='PENDING'
        """)
        pending = cur.fetchone()[0]

    return {
        "users": users,
        "profiles": profiles,
        "pending_requests": pending
    }


# =============================================================================
# END OF FILE
# =============================================================================
