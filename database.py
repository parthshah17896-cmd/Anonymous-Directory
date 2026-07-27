"""
===============================================================================
database.py
Telegram Directory Bot v2.0
===============================================================================

PostgreSQL Database Layer

Features
--------
✓ Connection Pool
✓ Automatic Transactions
✓ Context Manager
✓ Schema Initialization
✓ Profile Cache
✓ Railway Compatible
===============================================================================
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, List, Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from config import config
from logger import logger


# =============================================================================
# CONNECTION POOL
# =============================================================================

_connection_pool: Optional[pool.SimpleConnectionPool] = None


def initialize_pool() -> None:
    """
    Creates the PostgreSQL connection pool.
    """

    global _connection_pool

    if _connection_pool is not None:
        return

    logger.info("Creating PostgreSQL connection pool...")

    _connection_pool = pool.SimpleConnectionPool(
        minconn=config.DB_POOL_MIN,
        maxconn=config.DB_POOL_MAX,
        dsn=config.DATABASE_URL,
    )

    logger.info("Connection pool created.")


def close_pool() -> None:
    """
    Close every database connection.
    """

    global _connection_pool

    if _connection_pool:

        logger.info("Closing PostgreSQL connection pool...")

        _connection_pool.closeall()

        _connection_pool = None


def get_connection():

    if _connection_pool is None:
        initialize_pool()

    return _connection_pool.getconn()


def release_connection(connection):

    if _connection_pool:
        _connection_pool.putconn(connection)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

@contextmanager
def get_cursor(dictionary: bool = False):
    """
    Database cursor context manager.

    Automatically:

    • gets pooled connection
    • commits
    • rollback on failure
    • closes cursor
    • returns connection
    """

    connection = get_connection()

    cursor = (
        connection.cursor(cursor_factory=RealDictCursor)
        if dictionary
        else connection.cursor()
    )

    try:

        yield cursor

        connection.commit()

    except Exception:

        connection.rollback()

        logger.exception("Database transaction failed.")

        raise

    finally:

        cursor.close()

        release_connection(connection)


# =============================================================================
# PROFILE CACHE
# =============================================================================

PROFILE_CACHE: List[Dict] = []


def clear_cache():

    global PROFILE_CACHE

    PROFILE_CACHE.clear()


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db() -> None:
    """
    Creates all database tables.
    Safe to execute multiple times.
    """

    logger.info("Initializing database...")

    with get_cursor() as cur:

        # ---------------------------------------------------------------------
        # USERS
        # ---------------------------------------------------------------------

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users(

            telegram_id BIGINT PRIMARY KEY,

            selected_profile_id INTEGER NOT NULL,

            selected_name TEXT NOT NULL,

            selected_bot TEXT NOT NULL,

            selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );
        """)

        # ---------------------------------------------------------------------
        # RESET REQUESTS
        # ---------------------------------------------------------------------

        cur.execute("""
        CREATE TABLE IF NOT EXISTS reset_requests(

            telegram_id BIGINT PRIMARY KEY,

            status TEXT NOT NULL,

            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );
        """)

        # ---------------------------------------------------------------------
        # PROFILES
        # ---------------------------------------------------------------------

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

        # ---------------------------------------------------------------------
        # INDEXES
        # ---------------------------------------------------------------------

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_profile
        ON users(selected_profile_id);
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reset_status
        ON reset_requests(status);
        """)

    logger.info("Database initialized successfully.")

# =============================================================================
# PROFILE CACHE FUNCTIONS
# =============================================================================

def load_profiles() -> None:
    """
    Load all active profiles from the database into memory.
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

        PROFILE_CACHE = [dict(row) for row in cur.fetchall()]

    logger.info("Loaded %d profiles.", len(PROFILE_CACHE))


def refresh_profiles() -> None:
    """
    Refresh the in-memory profile cache.
    """

    clear_cache()
    load_profiles()


def get_profiles() -> List[Dict]:
    """
    Return all cached profiles.
    """

    return PROFILE_CACHE.copy()


def get_profile_by_id(profile_id: int) -> Optional[Dict]:
    """
    Get a profile from cache by ID.
    """

    for profile in PROFILE_CACHE:
        if profile["id"] == profile_id:
            return profile

    return None


# =============================================================================
# PROFILE CRUD
# =============================================================================

def add_profile(
    profile_id: int,
    name: str,
    age: int,
    marital_status: str,
    country: str,
    about: str,
    image: str,
    bot_link: str,
) -> None:
    """
    Add a new profile.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            INSERT INTO profiles(

                id,
                name,
                age,
                marital_status,
                country,
                about,
                image,
                bot_link

            )

            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                profile_id,
                name,
                age,
                marital_status,
                country,
                about,
                image,
                bot_link,
            ),
        )

    refresh_profiles()

    logger.info("Profile '%s' added.", name)


def update_profile(
    profile_id: int,
    name: str,
    age: int,
    marital_status: str,
    country: str,
    about: str,
    image: str,
    bot_link: str,
    is_active: bool = True,
) -> None:
    """
    Update an existing profile.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            UPDATE profiles
            SET
                name=%s,
                age=%s,
                marital_status=%s,
                country=%s,
                about=%s,
                image=%s,
                bot_link=%s,
                is_active=%s
            WHERE id=%s
            """,
            (
                name,
                age,
                marital_status,
                country,
                about,
                image,
                bot_link,
                is_active,
                profile_id,
            ),
        )

    refresh_profiles()

    logger.info("Profile ID %s updated.", profile_id)


def delete_profile(profile_id: int) -> None:
    """
    Soft delete a profile by marking it inactive.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            UPDATE profiles
            SET is_active = FALSE
            WHERE id = %s
            """,
            (profile_id,),
        )

    refresh_profiles()

    logger.info("Profile ID %s deactivated.", profile_id)


def profile_exists(profile_id: int) -> bool:
    """
    Check whether a profile exists.
    """

    with get_cursor() as cur:

        cur.execute(
            """
            SELECT 1
            FROM profiles
            WHERE id = %s
            """,
            (profile_id,),
        )

        return cur.fetchone() is not None
        
