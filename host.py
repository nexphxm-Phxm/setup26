# -*- coding: utf-8 -*-
"""
🚀 ADVANCED BOT HOSTING SYSTEM V3.1 🚀
Modern Dashboard | Enhanced Security | Advanced Admin Controls
Creator: @abbsydurov
Channel: https://t.me/DEviNePORTaL
Features: Save & Update Bot Source Files
"""

import os
import sys
import threading
import time
import subprocess
import sqlite3
import zipfile
import re
import shutil
import io
import psutil
import asyncio
import logging
import atexit
import socket
import json
import html
import random
import string
import hashlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urlparse

# ===== ENVIRONMENT CONFIGURATION =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8585334842:AAHqGfyEIlMndh8qP3lfc4JKRYgcr8rNGPM")
OWNER_ID = int(os.environ.get("OWNER_ID", "5157557268"))
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1004414969225"))
OWNER_USERNAME = "@abbsydurov"
CHANNEL_LINK = "https://t.me/DEviNePORTaL"

# ===== SYSTEM CONSTANTS =====
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PID_FILE = os.path.join(BASE_DIR, "hosting_bot.pid")
DB_PATH = os.path.join(BASE_DIR, "hosting.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "projects")
LOG_DIR = os.path.join(BASE_DIR, "logs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SOURCE_BACKUP_DIR = os.path.join(BASE_DIR, "source_backups")

# Create directories
for directory in [UPLOAD_DIR, LOG_DIR, TEMP_DIR, BACKUP_DIR, CONFIG_DIR, SOURCE_BACKUP_DIR]:
    os.makedirs(directory, exist_ok=True)

# ===== ENUMS =====
class ProjectStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"
    DEPLOYING = "deploying"
    DELETED = "deleted"
    UPDATING = "updating"

class UserRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    PREMIUM = "premium"
    USER = "user"
    BANNED = "banned"

class ProjectType(Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEB = "web"
    API = "api"
    OTHER = "other"

# ===== DATA CLASSES =====
@dataclass
class User:
    user_id: int
    username: str = ""
    role: UserRole = UserRole.USER
    file_limit: int = 0
    total_projects: int = 0
    max_concurrent: int = 3
    created_at: datetime = None
    last_active: datetime = None
    free_trial_used: bool = False
    free_trial_expiry: datetime = None
    is_banned: bool = False

@dataclass
class Project:
    id: int
    user_id: int
    name: str
    main_file: str
    framework: str
    project_type: str
    port: int = None
    status: ProjectStatus = ProjectStatus.STOPPED
    auto_restart: bool = True
    deps_installed: bool = False
    hosting_type: str = "zip"
    git_url: str = None
    created_at: datetime = None
    last_started: datetime = None
    webhook_url: str = None
    resource_usage: Dict = None
    is_free_trial: bool = False
    free_trial_expiry: datetime = None
    pid: int = None
    cpu_usage: float = 0
    memory_usage: float = 0
    restart_count: int = 0
    last_restart: datetime = None
    error_log: str = ""
    start_count: int = 0
    source_hash: str = None  # For tracking source changes
    version: str = "1.0.0"  # Version tracking
    last_updated: datetime = None

# ===== DATABASE MANAGER =====
class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        with self.get_connection() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    role TEXT DEFAULT 'user',
                    file_limit INTEGER DEFAULT 0,
                    total_projects INTEGER DEFAULT 0,
                    max_concurrent INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    free_trial_used BOOLEAN DEFAULT 0,
                    free_trial_expiry TIMESTAMP,
                    is_banned BOOLEAN DEFAULT 0,
                    backup_count INTEGER DEFAULT 0,
                    api_key TEXT
                )
            """)
            
            # Projects table with new columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT UNIQUE,
                    main_file TEXT,
                    framework TEXT,
                    project_type TEXT,
                    port INTEGER,
                    status TEXT DEFAULT 'stopped',
                    auto_restart BOOLEAN DEFAULT 1,
                    deps_installed BOOLEAN DEFAULT 0,
                    hosting_type TEXT DEFAULT 'zip',
                    git_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_started TIMESTAMP,
                    webhook_url TEXT,
                    resource_usage TEXT DEFAULT '{}',
                    is_free_trial BOOLEAN DEFAULT 0,
                    free_trial_expiry TIMESTAMP,
                    pid INTEGER,
                    cpu_usage REAL DEFAULT 0,
                    memory_usage REAL DEFAULT 0,
                    restart_count INTEGER DEFAULT 0,
                    last_restart TIMESTAMP,
                    error_log TEXT DEFAULT '',
                    start_count INTEGER DEFAULT 0,
                    source_hash TEXT,
                    version TEXT DEFAULT '1.0.0',
                    last_updated TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Check and add new columns if they don't exist
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'source_hash' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN source_hash TEXT")
            if 'version' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN version TEXT DEFAULT '1.0.0'")
            if 'last_updated' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN last_updated TIMESTAMP")
            
            # Admins table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    permissions TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # System logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    user_id INTEGER,
                    log_level TEXT,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # Backups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    backup_path TEXT,
                    size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # Source updates table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    old_version TEXT,
                    new_version TEXT,
                    update_path TEXT,
                    size INTEGER,
                    updated_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # Insert owner
            conn.execute("""
                INSERT OR REPLACE INTO users (user_id, username, role, file_limit) 
                VALUES (?, ?, 'owner', -1)
            """, (OWNER_ID, OWNER_USERNAME))
            
            conn.commit()
    
    def get_user(self, user_id: int) -> Optional[User]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return User(
                    user_id=row['user_id'],
                    username=row['username'] or "",
                    role=UserRole(row['role']),
                    file_limit=row['file_limit'],
                    total_projects=row['total_projects'],
                    max_concurrent=row['max_concurrent'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_active=datetime.fromisoformat(row['last_active']) if row['last_active'] else None,
                    free_trial_used=bool(row['free_trial_used']),
                    free_trial_expiry=datetime.fromisoformat(row['free_trial_expiry']) if row['free_trial_expiry'] else None,
                    is_banned=bool(row['is_banned'])
                )
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                return User(
                    user_id=row['user_id'],
                    username=row['username'] or "",
                    role=UserRole(row['role']),
                    file_limit=row['file_limit'],
                    total_projects=row['total_projects'],
                    max_concurrent=row['max_concurrent'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_active=datetime.fromisoformat(row['last_active']) if row['last_active'] else None,
                    free_trial_used=bool(row['free_trial_used']),
                    free_trial_expiry=datetime.fromisoformat(row['free_trial_expiry']) if row['free_trial_expiry'] else None,
                    is_banned=bool(row['is_banned'])
                )
        return None
    
    def create_user(self, user_id: int, username: str = "") -> User:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO users (user_id, username, role, file_limit)
                VALUES (?, ?, 'user', 0)
            """, (user_id, username))
            conn.commit()
        return self.get_user(user_id)
    
    def update_user(self, user: User):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE users SET 
                    username = ?,
                    role = ?,
                    file_limit = ?,
                    total_projects = ?,
                    max_concurrent = ?,
                    last_active = CURRENT_TIMESTAMP,
                    free_trial_used = ?,
                    free_trial_expiry = ?,
                    is_banned = ?
                WHERE user_id = ?
            """, (
                user.username,
                user.role.value,
                user.file_limit,
                user.total_projects,
                user.max_concurrent,
                1 if user.free_trial_used else 0,
                user.free_trial_expiry.isoformat() if user.free_trial_expiry else None,
                1 if user.is_banned else 0,
                user.user_id
            ))
            conn.commit()
    
    def get_project(self, project_id: int) -> Optional[Project]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if row:
                return Project(
                    id=row['id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    main_file=row['main_file'],
                    framework=row['framework'],
                    project_type=row['project_type'],
                    port=row['port'],
                    status=ProjectStatus(row['status']),
                    auto_restart=bool(row['auto_restart']),
                    deps_installed=bool(row['deps_installed']),
                    hosting_type=row['hosting_type'],
                    git_url=row['git_url'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_started=datetime.fromisoformat(row['last_started']) if row['last_started'] else None,
                    webhook_url=row['webhook_url'],
                    resource_usage=json.loads(row['resource_usage']) if row['resource_usage'] else {},
                    is_free_trial=bool(row['is_free_trial']),
                    free_trial_expiry=datetime.fromisoformat(row['free_trial_expiry']) if row['free_trial_expiry'] else None,
                    pid=row['pid'],
                    cpu_usage=row['cpu_usage'] or 0,
                    memory_usage=row['memory_usage'] or 0,
                    restart_count=row['restart_count'] or 0,
                    last_restart=datetime.fromisoformat(row['last_restart']) if row['last_restart'] else None,
                    error_log=row['error_log'] or "",
                    start_count=row['start_count'] or 0,
                    source_hash=row['source_hash'],
                    version=row['version'] or "1.0.0",
                    last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else None
                )
        return None
    
    def get_user_projects(self, user_id: int) -> List[Project]:
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC
            """, (user_id,)).fetchall()
            projects = []
            for row in rows:
                projects.append(Project(
                    id=row['id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    main_file=row['main_file'],
                    framework=row['framework'],
                    project_type=row['project_type'],
                    port=row['port'],
                    status=ProjectStatus(row['status']),
                    auto_restart=bool(row['auto_restart']),
                    deps_installed=bool(row['deps_installed']),
                    hosting_type=row['hosting_type'],
                    git_url=row['git_url'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_started=datetime.fromisoformat(row['last_started']) if row['last_started'] else None,
                    webhook_url=row['webhook_url'],
                    resource_usage=json.loads(row['resource_usage']) if row['resource_usage'] else {},
                    is_free_trial=bool(row['is_free_trial']),
                    free_trial_expiry=datetime.fromisoformat(row['free_trial_expiry']) if row['free_trial_expiry'] else None,
                    pid=row['pid'],
                    cpu_usage=row['cpu_usage'] or 0,
                    memory_usage=row['memory_usage'] or 0,
                    restart_count=row['restart_count'] or 0,
                    last_restart=datetime.fromisoformat(row['last_restart']) if row['last_restart'] else None,
                    error_log=row['error_log'] or "",
                    start_count=row['start_count'] or 0,
                    source_hash=row['source_hash'],
                    version=row['version'] or "1.0.0",
                    last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else None
                ))
            return projects
    
    def get_all_projects(self) -> List[Project]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
            projects = []
            for row in rows:
                projects.append(Project(
                    id=row['id'],
                    user_id=row['user_id'],
                    name=row['name'],
                    main_file=row['main_file'],
                    framework=row['framework'],
                    project_type=row['project_type'],
                    port=row['port'],
                    status=ProjectStatus(row['status']),
                    auto_restart=bool(row['auto_restart']),
                    deps_installed=bool(row['deps_installed']),
                    hosting_type=row['hosting_type'],
                    git_url=row['git_url'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    last_started=datetime.fromisoformat(row['last_started']) if row['last_started'] else None,
                    webhook_url=row['webhook_url'],
                    resource_usage=json.loads(row['resource_usage']) if row['resource_usage'] else {},
                    is_free_trial=bool(row['is_free_trial']),
                    free_trial_expiry=datetime.fromisoformat(row['free_trial_expiry']) if row['free_trial_expiry'] else None,
                    pid=row['pid'],
                    cpu_usage=row['cpu_usage'] or 0,
                    memory_usage=row['memory_usage'] or 0,
                    restart_count=row['restart_count'] or 0,
                    last_restart=datetime.fromisoformat(row['last_restart']) if row['last_restart'] else None,
                    error_log=row['error_log'] or "",
                    start_count=row['start_count'] or 0,
                    source_hash=row['source_hash'],
                    version=row['version'] or "1.0.0",
                    last_updated=datetime.fromisoformat(row['last_updated']) if row['last_updated'] else None
                ))
            return projects
    
    def create_project(self, project: Project) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO projects (
                    user_id, name, main_file, framework, project_type,
                    port, status, auto_restart, hosting_type,
                    is_free_trial, free_trial_expiry, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.user_id,
                project.name,
                project.main_file,
                project.framework,
                project.project_type,
                project.port,
                project.status.value,
                1 if project.auto_restart else 0,
                project.hosting_type,
                1 if project.is_free_trial else 0,
                project.free_trial_expiry.isoformat() if project.free_trial_expiry else None,
                project.version
            ))
            project_id = cursor.lastrowid
            conn.commit()
            return project_id
    
    def update_project(self, project: Project):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE projects SET
                    main_file = ?,
                    framework = ?,
                    project_type = ?,
                    port = ?,
                    status = ?,
                    auto_restart = ?,
                    deps_installed = ?,
                    git_url = ?,
                    last_started = ?,
                    webhook_url = ?,
                    resource_usage = ?,
                    pid = ?,
                    cpu_usage = ?,
                    memory_usage = ?,
                    restart_count = ?,
                    last_restart = ?,
                    error_log = ?,
                    start_count = ?,
                    source_hash = ?,
                    version = ?,
                    last_updated = ?
                WHERE id = ?
            """, (
                project.main_file,
                project.framework,
                project.project_type,
                project.port,
                project.status.value,
                1 if project.auto_restart else 0,
                1 if project.deps_installed else 0,
                project.git_url,
                project.last_started.isoformat() if project.last_started else None,
                project.webhook_url,
                json.dumps(project.resource_usage) if project.resource_usage else '{}',
                project.pid,
                project.cpu_usage,
                project.memory_usage,
                project.restart_count,
                project.last_restart.isoformat() if project.last_restart else None,
                project.error_log,
                project.start_count,
                project.source_hash,
                project.version,
                project.last_updated.isoformat() if project.last_updated else None,
                project.id
            ))
            conn.commit()
    
    def delete_project(self, project_id: int):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
    
    def add_admin(self, user_id: int, added_by: int) -> bool:
        with self.get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO admins (user_id, added_by)
                    VALUES (?, ?)
                """, (user_id, added_by))
                conn.execute("""
                    UPDATE users SET role = 'admin' WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return True
            except:
                return False
    
    def remove_admin(self, user_id: int) -> bool:
        with self.get_connection() as conn:
            try:
                conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
                conn.execute("""
                    UPDATE users SET role = 'user' WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                return True
            except:
                return False
    
    def is_admin(self, user_id: int) -> bool:
        with self.get_connection() as conn:
            row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
            return row is not None or user_id == OWNER_ID
    
    def get_admins(self) -> List[int]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT user_id FROM admins").fetchall()
            return [row['user_id'] for row in rows]
    
    def add_system_log(self, project_id: int, user_id: int, log_level: str, message: str):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO system_logs (project_id, user_id, log_level, message)
                VALUES (?, ?, ?, ?)
            """, (project_id, user_id, log_level, message))
            conn.commit()
    
    def get_system_logs(self, limit: int = 100) -> List[Dict]:
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
    
    def add_source_update(self, project_id: int, old_version: str, new_version: str, 
                         update_path: str, size: int, updated_by: int):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO source_updates (project_id, old_version, new_version, 
                                           update_path, size, updated_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, old_version, new_version, update_path, size, updated_by))
            conn.commit()
    
    def get_source_updates(self, project_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM source_updates WHERE project_id = ? 
                ORDER BY created_at DESC
            """, (project_id,)).fetchall()
            return [dict(row) for row in rows]

# ===== PROJECT MANAGER =====
class ProjectManager:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.running_processes: Dict[int, subprocess.Popen] = {}
        self.process_locks: Dict[int, threading.Lock] = {}
        self.logger = logging.getLogger("ProjectManager")
    
    def get_project_path(self, user_id: int, project_name: str) -> str:
        return os.path.join(UPLOAD_DIR, str(user_id), project_name)
    
    def get_user_path(self, user_id: int) -> str:
        path = os.path.join(UPLOAD_DIR, str(user_id))
        os.makedirs(path, exist_ok=True)
        return path
    
    def get_log_path(self, project_id: int) -> str:
        return os.path.join(LOG_DIR, f"project_{project_id}.log")
    
    def get_backup_path(self, project_id: int, version: str) -> str:
        return os.path.join(SOURCE_BACKUP_DIR, f"project_{project_id}_v{version}.zip")
    
    def calculate_source_hash(self, directory: str) -> str:
        """Calculate hash of all source files"""
        hash_md5 = hashlib.md5()
        for root, dirs, files in os.walk(directory):
            # Skip virtual environment and cache directories
            if any(skip in root for skip in ['__pycache__', '.venv', 'venv', 'node_modules', '.git']):
                continue
            for file in sorted(files):
                if file.endswith(('.pyc', '.pyo', '.so')):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b''):
                            hash_md5.update(chunk)
                except:
                    pass
        return hash_md5.hexdigest()
    
    def backup_project_source(self, project: Project) -> Tuple[bool, str]:
        """Backup the entire project source code"""
        try:
            project_path = self.get_project_path(project.user_id, project.name)
            if not os.path.exists(project_path):
                return False, "Project directory not found"
            
            # Create backup filename
            version = project.version or "1.0.0"
            backup_path = self.get_backup_path(project.id, version)
            
            # Create ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(project_path):
                    # Skip virtual environment and cache
                    if any(skip in root for skip in ['__pycache__', '.venv', 'venv', 'node_modules', '.git']):
                        continue
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, project_path)
                        zipf.write(file_path, arcname)
            
            return True, backup_path
            
        except Exception as e:
            self.logger.error(f"Backup error: {e}")
            return False, str(e)
    
    def update_project_source(self, project_id: int, zip_path: str, new_version: str) -> Tuple[bool, str]:
        """Update project source from ZIP"""
        project = self.db.get_project(project_id)
        if not project:
            return False, "Project not found"
        
        try:
            # Stop project if running
            was_running = project_id in self.running_processes
            if was_running:
                self.stop_project(project_id)
                time.sleep(2)
            
            # Create old version backup
            old_version = project.version
            project.status = ProjectStatus.UPDATING
            self.db.update_project(project)
            
            # Backup current source
            backup_success, backup_path = self.backup_project_source(project)
            if not backup_success:
                return False, f"Backup failed: {backup_path}"
            
            # Get project directory
            project_path = self.get_project_path(project.user_id, project.name)
            
            # Remove old source (keep requirements.txt and package.json if they exist)
            if os.path.exists(project_path):
                # Save important files
                important_files = []
                for root, dirs, files in os.walk(project_path):
                    for file in files:
                        if file in ['requirements.txt', 'package.json', 'Procfile', 'Dockerfile']:
                            important_files.append(os.path.join(root, file))
                
                # Remove old files
                shutil.rmtree(project_path)
            
            os.makedirs(project_path, exist_ok=True)
            
            # Extract new source
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(project_path)
            
            # Restore important files if not in new zip
            for file_path in important_files:
                if not os.path.exists(file_path):
                    shutil.copy(file_path, project_path)
            
            # Find main file
            main_file = self.find_main_file(project_path)
            if not main_file:
                return False, "No main file found in update"
            
            # Detect framework
            framework, project_type = self.detect_framework(project_path, main_file)
            
            # Update project
            project.main_file = main_file
            project.framework = framework
            project.project_type = project_type
            project.version = new_version
            project.source_hash = self.calculate_source_hash(project_path)
            project.last_updated = datetime.now()
            project.deps_installed = False  # Need to reinstall dependencies
            project.status = ProjectStatus.STOPPED
            self.db.update_project(project)
            
            # Install dependencies
            success, message = self.install_dependencies(project_path, framework)
            if success:
                project.deps_installed = True
                self.db.update_project(project)
            
            # Log update
            self.db.add_source_update(
                project_id, old_version, new_version, 
                backup_path, os.path.getsize(backup_path), 
                project.user_id
            )
            
            # Restart if was running
            if was_running:
                success, message = self.start_project(project_id)
            
            self.db.add_system_log(
                project_id, project.user_id, "INFO",
                f"Updated from v{old_version} to v{new_version}"
            )
            
            return True, f"Updated to version {new_version}"
            
        except Exception as e:
            self.logger.error(f"Update error: {e}")
            return False, str(e)
    
    def find_main_file(self, directory: str) -> Optional[str]:
        priority_files = [
            "main.py", "bot.py", "app.py", "server.py", "run.py", "start.py",
            "index.js", "server.js", "app.js", "bot.js", "main.js",
            "main.ts", "server.ts", "app.ts", "index.ts",
            "manage.py", "wsgi.py", "app.py"
        ]
        
        # Check root directory
        for fname in priority_files:
            if os.path.exists(os.path.join(directory, fname)):
                return fname
        
        # Check package.json
        if os.path.exists(os.path.join(directory, "package.json")):
            try:
                with open(os.path.join(directory, "package.json")) as f:
                    data = json.load(f)
                    if 'main' in data and os.path.exists(os.path.join(directory, data['main'])):
                        return data['main']
            except:
                pass
        
        # Recursive search
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file in priority_files:
                    return os.path.relpath(os.path.join(root, file), directory)
        
        # Fallback: any Python or JS file
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith((".py", ".js", ".ts")):
                    return os.path.relpath(os.path.join(root, file), directory)
        
        return None
    
    def find_requirements_txt(self, directory: str) -> Optional[str]:
        for root, dirs, files in os.walk(directory):
            if "requirements.txt" in files:
                return os.path.join(root, "requirements.txt")
        return None
    
    def detect_framework(self, directory: str, main_file: str) -> Tuple[str, str]:
        project_types = []
        framework = "Unknown"
        
        try:
            main_path = os.path.join(directory, main_file)
            if os.path.exists(main_path):
                with open(main_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    if 'telegram' in content or 'telebot' in content:
                        project_types.append('telegram')
                        framework = "Telegram Bot"
                    if 'discord' in content:
                        project_types.append('discord')
                        framework = "Discord Bot"
                    if 'flask' in content:
                        project_types.append('flask')
                        framework = "Flask Web"
                    if 'fastapi' in content:
                        project_types.append('fastapi')
                        framework = "FastAPI"
                    if 'django' in content:
                        project_types.append('django')
                        framework = "Django"
                    if 'express' in content:
                        project_types.append('express')
                        framework = "Express.js"
        
            if os.path.exists(os.path.join(directory, 'package.json')):
                project_types.append('nodejs')
                if framework == "Unknown":
                    framework = "Node.js"
            if self.find_requirements_txt(directory):
                project_types.append('python')
                if framework == "Unknown":
                    framework = "Python"
            
        except Exception as e:
            self.logger.warning(f"Framework detection error: {e}")
        
        return framework, ','.join(project_types) if project_types else 'other'
    
    def find_available_port(self, start_port: int = 8000, max_attempts: int = 100) -> Optional[int]:
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return None
    
    def install_dependencies(self, project_dir: str, framework: str) -> Tuple[bool, str]:
        try:
            # Python dependencies
            req_file = self.find_requirements_txt(project_dir)
            if req_file and ('python' in framework.lower() or 'telegram' in framework.lower()):
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_file],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    return True, "Python dependencies installed"
                else:
                    return False, f"Python install failed: {result.stderr[:500]}"
            
            # Node.js dependencies
            package_json = None
            for root, dirs, files in os.walk(project_dir):
                if 'package.json' in files:
                    package_json = os.path.join(root, 'package.json')
                    break
            
            if package_json and 'node' in framework.lower():
                result = subprocess.run(
                    ['npm', 'install'],
                    cwd=os.path.dirname(package_json),
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    return True, "Node.js dependencies installed"
                else:
                    return False, f"npm install failed: {result.stderr[:500]}"
            
            return True, "No dependencies found"
            
        except subprocess.TimeoutExpired:
            return False, "Installation timeout"
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    def get_start_command(self, project: Project, project_dir: str) -> Optional[List[str]]:
        main_file = project.main_file
        
        if main_file.endswith('.py'):
            if project.framework.lower() in ['fastapi', 'flask']:
                module = main_file.replace('.py', '').replace('/', '.').replace('\\', '.')
                return [sys.executable, "-m", "uvicorn", f"{module}:app", 
                       "--host", "0.0.0.0", "--port", str(project.port or 8000)]
            elif project.framework.lower() == 'django':
                return [sys.executable, "manage.py", "runserver", 
                       f"0.0.0.0:{project.port or 8000}"]
            else:
                return [sys.executable, "-u", main_file]
        
        elif main_file.endswith(('.js', '.mjs')):
            # Check if using npm start
            if os.path.exists(os.path.join(project_dir, 'package.json')):
                try:
                    with open(os.path.join(project_dir, 'package.json')) as f:
                        data = json.load(f)
                        if 'scripts' in data and 'start' in data['scripts']:
                            return ['npm', 'start']
                except:
                    pass
            return ['node', main_file]
        
        return None
    
    def start_project(self, project_id: int) -> Tuple[bool, str]:
        if project_id in self.running_processes:
            return False, "Project already running"
        
        project = self.db.get_project(project_id)
        if not project:
            return False, "Project not found"
        
        if project_id not in self.process_locks:
            self.process_locks[project_id] = threading.Lock()
        
        with self.process_locks[project_id]:
            try:
                project_dir = self.get_project_path(project.user_id, project.name)
                
                if not os.path.exists(project_dir):
                    return False, "Project directory not found"
                
                # Install dependencies if not installed
                if not project.deps_installed:
                    success, message = self.install_dependencies(project_dir, project.framework)
                    if not success:
                        return False, f"Dependency install failed: {message}"
                    project.deps_installed = True
                    self.db.update_project(project)
                
                # Get start command
                cmd = self.get_start_command(project, project_dir)
                if not cmd:
                    return False, "Unsupported project type"
                
                # Prepare environment
                env = os.environ.copy()
                env['PORT'] = str(project.port or 8000)
                if project.project_type == 'telegram':
                    env.pop('BOT_TOKEN', None)  # Don't inherit bot token
                
                # Start process
                log_path = self.get_log_path(project_id)
                log_dir = os.path.dirname(log_path)
                os.makedirs(log_dir, exist_ok=True)
                
                with open(log_path, 'a') as log_file:
                    log_file.write(f"\n{'='*50}\n")
                    log_file.write(f"Started: {datetime.now()}\n")
                    log_file.write(f"Command: {' '.join(cmd)}\n")
                    log_file.write(f"Directory: {project_dir}\n")
                    log_file.write(f"{'='*50}\n")
                    
                    process = subprocess.Popen(
                        cmd,
                        cwd=project_dir,
                        stdout=log_file,
                        stderr=log_file,
                        env=env,
                        preexec_fn=os.setsid if os.name != 'nt' else None
                    )
                
                self.running_processes[project_id] = process
                
                project.pid = process.pid
                project.status = ProjectStatus.RUNNING
                project.last_started = datetime.now()
                project.start_count += 1
                project.error_log = ""
                
                # Calculate source hash if not set
                if not project.source_hash:
                    project.source_hash = self.calculate_source_hash(project_dir)
                
                self.db.update_project(project)
                
                # Start monitoring
                threading.Thread(
                    target=self.monitor_project,
                    args=(project_id,),
                    daemon=True
                ).start()
                
                return True, f"Project started (PID: {process.pid})"
                
            except Exception as e:
                self.logger.error(f"Start project error: {e}")
                return False, f"Start error: {str(e)}"
    
    def stop_project(self, project_id: int) -> Tuple[bool, str]:
        if project_id not in self.running_processes:
            return False, "Project not running"
        
        with self.process_locks.get(project_id, threading.Lock()):
            try:
                process = self.running_processes[project_id]
                
                # Kill process group
                if os.name != 'nt':
                    import signal
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                process.wait(timeout=10)
                
                del self.running_processes[project_id]
                
                project = self.db.get_project(project_id)
                if project:
                    project.status = ProjectStatus.STOPPED
                    project.pid = None
                    self.db.update_project(project)
                
                return True, "Project stopped"
                
            except subprocess.TimeoutExpired:
                process.kill()
                del self.running_processes[project_id]
                return True, "Project force stopped"
            except Exception as e:
                self.logger.error(f"Stop project error: {e}")
                return False, f"Stop error: {str(e)}"
    
    def restart_project(self, project_id: int) -> Tuple[bool, str]:
        # Stop first
        if project_id in self.running_processes:
            success, message = self.stop_project(project_id)
            if not success:
                return False, f"Stop failed: {message}"
        
        # Wait a moment
        time.sleep(1)
        
        # Start
        return self.start_project(project_id)
    
    def monitor_project(self, project_id: int):
        while project_id in self.running_processes:
            try:
                process = self.running_processes[project_id]
                
                # Check if process is still running
                if process.poll() is not None:
                    # Process exited
                    project = self.db.get_project(project_id)
                    if project:
                        project.status = ProjectStatus.ERROR if project.auto_restart else ProjectStatus.STOPPED
                        project.pid = None
                        
                        # Read error log
                        log_path = self.get_log_path(project_id)
                        if os.path.exists(log_path):
                            with open(log_path, 'r') as f:
                                content = f.read()
                                if content:
                                    project.error_log = content[-2000:]  # Last 2000 chars
                        
                        self.db.update_project(project)
                    
                    del self.running_processes[project_id]
                    
                    # Auto-restart if enabled
                    if project and project.auto_restart:
                        project.restart_count += 1
                        project.last_restart = datetime.now()
                        self.db.update_project(project)
                        
                        self.logger.info(f"Auto-restarting project {project_id} (attempt {project.restart_count})")
                        
                        # Wait and restart
                        time.sleep(5)
                        success, message = self.start_project(project_id)
                        if success:
                            self.db.add_system_log(project_id, 0, "INFO", f"Auto-restart successful")
                        else:
                            self.db.add_system_log(project_id, 0, "ERROR", f"Auto-restart failed: {message}")
                    
                    break
                
                # Update resource usage
                try:
                    p = psutil.Process(process.pid)
                    cpu = p.cpu_percent(interval=0.5)
                    memory = p.memory_info().rss / 1024 / 1024
                    
                    project = self.db.get_project(project_id)
                    if project:
                        project.cpu_usage = cpu
                        project.memory_usage = memory
                        self.db.update_project(project)
                except:
                    pass
                
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Monitor error for {project_id}: {e}")
                time.sleep(10)
    
    def deploy_project_from_zip(self, user_id: int, file_path: str, project_name: str, 
                               is_free_trial: bool = False) -> Tuple[bool, str, Optional[int]]:
        try:
            # Validate ZIP
            if not zipfile.is_zipfile(file_path):
                return False, "Invalid ZIP file", None
            
            # Create project directory
            user_path = self.get_user_path(user_id)
            project_path = os.path.join(user_path, project_name)
            
            if os.path.exists(project_path):
                return False, "Project already exists", None
            
            # Extract ZIP
            os.makedirs(project_path, exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(project_path)
            
            # Find main file
            main_file = self.find_main_file(project_path)
            if not main_file:
                shutil.rmtree(project_path, ignore_errors=True)
                return False, "No main file found", None
            
            # Detect framework
            framework, project_type = self.detect_framework(project_path, main_file)
            
            # Find available port for web apps
            port = None
            if framework.lower() in ['fastapi', 'flask', 'django', 'node.js', 'express']:
                port = self.find_available_port()
            
            # Calculate source hash
            source_hash = self.calculate_source_hash(project_path)
            
            # Create project in database
            project = Project(
                id=0,
                user_id=user_id,
                name=project_name,
                main_file=main_file,
                framework=framework,
                project_type=project_type,
                port=port,
                status=ProjectStatus.DEPLOYING,
                auto_restart=True,
                deps_installed=False,
                hosting_type="zip",
                is_free_trial=is_free_trial,
                free_trial_expiry=datetime.now() + timedelta(hours=2) if is_free_trial else None,
                source_hash=source_hash,
                version="1.0.0",
                last_updated=datetime.now()
            )
            
            project_id = self.db.create_project(project)
            
            # Install dependencies
            success, message = self.install_dependencies(project_path, framework)
            if success:
                project.deps_installed = True
            
            # Start project
            project.status = ProjectStatus.RUNNING
            self.db.update_project(project)
            
            success, message = self.start_project(project_id)
            
            if success:
                return True, "Project deployed successfully", project_id
            else:
                return False, f"Deployment failed: {message}", project_id
            
        except Exception as e:
            self.logger.error(f"Deploy error: {e}")
            return False, f"Deployment error: {str(e)}", None
    
    def delete_project(self, project_id: int) -> Tuple[bool, str]:
        project = self.db.get_project(project_id)
        if not project:
            return False, "Project not found"
        
        # Stop if running
        if project_id in self.running_processes:
            self.stop_project(project_id)
        
        # Delete files
        project_path = self.get_project_path(project.user_id, project.name)
        shutil.rmtree(project_path, ignore_errors=True)
        
        # Delete logs
        log_path = self.get_log_path(project_id)
        if os.path.exists(log_path):
            os.remove(log_path)
        
        # Delete from database
        self.db.delete_project(project_id)
        
        return True, "Project deleted"

# ===== LOGGING SYSTEM =====
def setup_logging():
    logger = logging.getLogger("HostingBot")
    logger.setLevel(logging.INFO)
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(console)
    
    # File handler
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "hosting_bot.log"))
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
    ))
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

# ===== SINGLE INSTANCE =====
def cleanup_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def check_single_instance():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            old_pid = int(f.read().strip())
        if psutil.pid_exists(old_pid):
            logger.error(f"Another instance running (PID: {old_pid})")
            sys.exit(1)
    
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(cleanup_pid)

check_single_instance()

# ===== TELEGRAM BOT =====
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    from telegram.constants import ParseMode
    from telegram.error import BadRequest
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "python-telegram-bot==20.7"])
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    from telegram.constants import ParseMode
    from telegram.error import BadRequest

# ===== BOT STATE =====
db = DatabaseManager()
project_manager = ProjectManager(db)
user_states = {}
broadcast_states = {}
admin_actions = {}
update_states = {}

# ===== HELPER FUNCTIONS =====
def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or db.is_admin(user_id)

def can_host(user_id: int) -> bool:
    user = db.get_user(user_id)
    if not user:
        return False
    if user.is_banned:
        return False
    if user.role == UserRole.BANNED:
        return False
    return user.file_limit == -1 or user.total_projects < user.file_limit

def get_user_display(user) -> str:
    if isinstance(user, int):
        return f"<code>{user}</code>"
    if hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    if hasattr(user, 'first_name'):
        return user.first_name
    return str(user)

def format_time(dt: Optional[datetime]) -> str:
    if not dt:
        return "Never"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_status_emoji(status: ProjectStatus) -> str:
    emojis = {
        ProjectStatus.RUNNING: "🟢",
        ProjectStatus.STOPPED: "🔴",
        ProjectStatus.ERROR: "❌",
        ProjectStatus.STARTING: "🔄",
        ProjectStatus.STOPPING: "⏹️",
        ProjectStatus.DEPLOYING: "📦",
        ProjectStatus.DELETED: "🗑️",
        ProjectStatus.UPDATING: "🔄"
    }
    return emojis.get(status, "⚪")

def increment_version(version: str, increment_type: str = 'patch') -> str:
    parts = version.split('.')
    while len(parts) < 3:
        parts.append('0')
    major, minor, patch = parts[0], parts[1], parts[2]
    
    if increment_type == 'major':
        return f"{int(major) + 1}.0.0"
    elif increment_type == 'minor':
        return f"{major}.{int(minor) + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{int(patch) + 1}"

# ===== DASHBOARD FUNCTIONS =====
def create_dashboard_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📦 My Projects", callback_data="dashboard_projects"),
            InlineKeyboardButton("🚀 Deploy New", callback_data="dashboard_deploy")
        ],
        [
            InlineKeyboardButton("💾 Save Source", callback_data="dashboard_save_source"),
            InlineKeyboardButton("🔄 Update Source", callback_data="dashboard_update_source")
        ],
        [
            InlineKeyboardButton("📊 System Status", callback_data="dashboard_status"),
            InlineKeyboardButton("📋 Logs", callback_data="dashboard_logs")
        ]
    ]
    
    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("👥 User Management", callback_data="dashboard_users"),
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="dashboard_admin")
        ])
    
    return InlineKeyboardMarkup(keyboard)

def create_project_keyboard(project_id: int, is_running: bool) -> InlineKeyboardMarkup:
    buttons = []
    
    if is_running:
        buttons.append(InlineKeyboardButton("⏹️ Stop", callback_data=f"project_stop_{project_id}"))
        buttons.append(InlineKeyboardButton("🔄 Restart", callback_data=f"project_restart_{project_id}"))
    else:
        buttons.append(InlineKeyboardButton("▶️ Start", callback_data=f"project_start_{project_id}"))
    
    buttons.append(InlineKeyboardButton("📋 Logs", callback_data=f"project_logs_{project_id}"))
    buttons.append(InlineKeyboardButton("💾 Save Source", callback_data=f"project_save_source_{project_id}"))
    buttons.append(InlineKeyboardButton("🔄 Update Source", callback_data=f"project_update_source_{project_id}"))
    buttons.append(InlineKeyboardButton("🗑️ Delete", callback_data=f"project_delete_{project_id}"))
    
    return InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])

def create_pagination_keyboard(page: int, total_pages: int, base_callback: str) -> InlineKeyboardMarkup:
    buttons = []
    
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{base_callback}_{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"{base_callback}_{page+1}"))
    
    return InlineKeyboardMarkup([buttons]) if buttons else None

# ===== BOT COMMANDS =====
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    # Register user
    user = db.get_user(user_id)
    if not user:
        user = db.create_user(user_id, username)
    else:
        user.username = username
        db.update_user(user)
    
    # Check if user is banned
    if user.is_banned:
        await update.message.reply_text(
            "🚫 <b>You have been banned from using this bot</b>\n\n"
            "Contact @abbsydurov for assistance.",
            parse_mode=ParseMode.HTML
        )
        return
    
    welcome_text = f"""
<b>🚀 ADVANCED BOT HOSTING PLATFORM</b>

Welcome {get_user_display(update.effective_user)}! 👋

<b>📊 Your Stats:</b>
• Role: {user.role.value.title()}
• Projects: {user.total_projects}
• Limit: {user.file_limit if user.file_limit != -1 else '♾️ Unlimited'}

<b>📌 Quick Actions:</b>
• /host - Deploy a new bot
• /mybots - View your projects
• /dashboard - Full control panel
• /save - Save bot source code
• /update - Update bot source code

<b>⭐ Powered by:</b> @DEviNePORTaL
<b>👑 Owner:</b> @abbsydurov
"""
    
    keyboard = [
        ["📦 My Projects", "🚀 Deploy Bot"],
        ["💾 Save Source", "🔄 Update Source"],
        ["📊 System Status", "📋 Bot Logs"]
    ]
    
    if is_admin(user_id):
        keyboard.append(["⚙️ Admin Panel", "👥 User Management"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main dashboard"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found. Use /start to register.")
        return
    
    if user.is_banned:
        await update.message.reply_text("🚫 You are banned.")
        return
    
    projects = db.get_user_projects(user_id)
    running = sum(1 for p in projects if p.status == ProjectStatus.RUNNING)
    total = len(projects)
    
    dashboard_text = f"""
<b>📊 BOT HOSTING DASHBOARD</b>

<b>👤 User:</b> {get_user_display(update.effective_user)}
<b>📋 Role:</b> {user.role.value.title()}
<b>📦 Projects:</b> {total} ({running} running)

<b>⚡ Quick Stats:</b>
• Total Projects: {total}
• Running: {running}
• Stopped: {total - running}
• Limit: {user.file_limit if user.file_limit != -1 else '♾️'}

Select an option below:
"""
    
    keyboard = create_dashboard_keyboard(user_id)
    await update.message.reply_text(dashboard_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def host_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Host a new bot"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Register with /start first.")
        return
    
    if user.is_banned:
        await update.message.reply_text("🚫 You are banned.")
        return
    
    if not can_host(user_id):
        await update.message.reply_text(
            "❌ <b>Cannot deploy more projects</b>\n\n"
            f"Current: {user.total_projects}\n"
            f"Limit: {user.file_limit if user.file_limit != -1 else '♾️'}\n\n"
            "Contact @abbsydurov to increase your limit.",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_states[user_id] = {"state": "awaiting_zip"}
    
    await update.message.reply_text(
        f"🚀 <b>DEPLOY NEW BOT</b>\n\n"
        f"📁 Upload your bot as a <b>.zip</b> file\n"
        f"📦 Max size: {MAX_FILE_SIZE_MB}MB\n\n"
        f"<b>Requirements:</b>\n"
        f"• Include main file (main.py, bot.py, index.js, etc.)\n"
        f"• Include requirements.txt for Python bots\n"
        f"• Include package.json for Node.js bots\n\n"
        f"<b>Supported Frameworks:</b>\n"
        f"• Python (Telegram, Flask, FastAPI, Django)\n"
        f"• JavaScript/Node.js\n\n"
        f"Send your ZIP file now:",
        parse_mode=ParseMode.HTML
    )

async def mybots_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    """List user's projects"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Register with /start first.")
        return
    
    projects = db.get_user_projects(user_id)
    
    if not projects:
        await update.message.reply_text(
            "📁 <b>No Projects Found</b>\n\n"
            "Use /host to deploy your first bot!",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Pagination
    per_page = 5
    total_pages = max(1, (len(projects) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(projects))
    page_projects = projects[start_idx:end_idx]
    
    # Count running projects
    running = sum(1 for p in projects if p.status == ProjectStatus.RUNNING)
    
    text = f"""
📁 <b>YOUR PROJECTS</b>

👤 User: {get_user_display(update.effective_user)}
📦 Total: {len(projects)} ({running} running)
📄 Page {page}/{total_pages}

{'-'*30}
"""
    
    for project in page_projects:
        status_emoji = get_status_emoji(project.status)
        text += f"""
{status_emoji} <b>{project.name}</b> (v{project.version})
  📋 Type: {project.framework}
  📄 Main: {project.main_file}
  📅 Created: {format_time(project.created_at)}
  💻 PID: {project.pid or 'N/A'}
  📊 CPU: {project.cpu_usage:.1f}% | RAM: {project.memory_usage:.1f}MB
"""
    
    # Create keyboard for projects
    keyboard = []
    for project in page_projects:
        keyboard.append([
            InlineKeyboardButton(
                f"{project.name}",
                callback_data=f"project_details_{project.id}"
            )
        ])
    
    # Add pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"mybots_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="none"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"mybots_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def save_source_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save project source code"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Register with /start first.")
        return
    
    projects = db.get_user_projects(user_id)
    if not projects:
        await update.message.reply_text("📁 No projects to save.")
        return
    
    keyboard = []
    for project in projects:
        keyboard.append([
            InlineKeyboardButton(
                f"💾 {project.name} (v{project.version})",
                callback_data=f"save_source_{project.id}"
            )
        ])
    
    await update.message.reply_text(
        "💾 <b>Save Source Code</b>\n\n"
        "Select a project to download its source code:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def update_source_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update project source code"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Register with /start first.")
        return
    
    projects = db.get_user_projects(user_id)
    if not projects:
        await update.message.reply_text("📁 No projects to update.")
        return
    
    keyboard = []
    for project in projects:
        keyboard.append([
            InlineKeyboardButton(
                f"🔄 {project.name} (v{project.version})",
                callback_data=f"update_source_{project.id}"
            )
        ])
    
    await update.message.reply_text(
        "🔄 <b>Update Source Code</b>\n\n"
        "Select a project to update its source code:\n\n"
        "Send a new ZIP file with the updated source code.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command.")
        return
    
    # System stats
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Database stats
    projects = db.get_all_projects()
    running = sum(1 for p in projects if p.status == ProjectStatus.RUNNING)
    users = []
    with db.get_connection() as conn:
        users = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    
    # Count source updates
    with db.get_connection() as conn:
        updates = conn.execute("SELECT COUNT(*) as count FROM source_updates").fetchone()['count']
    
    text = f"""
🖥️ <b>SYSTEM STATUS</b>

<b>📊 System Resources:</b>
• CPU: {cpu}%
• RAM: {memory.percent}% ({memory.used // 1024//1024}MB / {memory.total // 1024//1024}MB)
• Disk: {disk.percent}% ({disk.used // 1024//1024}GB / {disk.total // 1024//1024}GB)

<b>📦 Platform Stats:</b>
• Total Users: {users}
• Total Projects: {len(projects)}
• Running: {running}
• Stopped: {len(projects) - running}
• Source Updates: {updates}

<b>⚙️ System Info:</b>
• Python: {sys.version.split()[0]}
• Platform: {sys.platform}
• PID: {os.getpid()}
"""
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View system logs"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command.")
        return
    
    logs = db.get_system_logs(50)
    
    if not logs:
        await update.message.reply_text("📋 No logs available.")
        return
    
    text = "📋 <b>Recent System Logs</b>\n\n"
    for log in logs[:20]:
        text += f"• {log['timestamp'][:19]} | {log['log_level']} | {log['message'][:100]}\n"
    
    if len(logs) > 20:
        text += f"\n... and {len(logs) - 20} more logs"
    
    await update.message.reply_text(text[:4096], parse_mode=ParseMode.HTML)

# ===== ADMIN COMMANDS =====
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
        [InlineKeyboardButton("📦 All Projects", callback_data="admin_projects")],
        [InlineKeyboardButton("💾 Source Backups", callback_data="admin_backups")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Refresh System", callback_data="admin_refresh")],
        [InlineKeyboardButton("📋 System Logs", callback_data="admin_logs")]
    ]
    
    await update.message.reply_text(
        "⚙️ <b>ADMIN PANEL</b>\n\nSelect an option:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    """Manage users"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    with db.get_connection() as conn:
        users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    
    if not users:
        await update.message.reply_text("👥 No users found.")
        return
    
    per_page = 10
    total_pages = max(1, (len(users) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(users))
    page_users = users[start_idx:end_idx]
    
    text = f"👥 <b>User Management</b> (Page {page}/{total_pages})\n\n"
    
    for user_row in page_users:
        user = User(
            user_id=user_row['user_id'],
            username=user_row['username'] or "",
            role=UserRole(user_row['role']),
            file_limit=user_row['file_limit'],
            total_projects=user_row['total_projects'],
            is_banned=bool(user_row['is_banned'])
        )
        
        status = "🚫 BANNED" if user.is_banned else "✅ Active"
        text += f"""
👤 {get_user_display(user_row)}
  🆔 {user.user_id}
  📋 Role: {user.role.value.title()}
  📦 Projects: {user.total_projects}
  📊 Limit: {user.file_limit if user.file_limit != -1 else '♾️'}
  Status: {status}
"""
    
    keyboard = []
    
    # Add user actions
    for user_row in page_users:
        keyboard.append([
            InlineKeyboardButton(
                f"Manage {user_row['username'] or user_row['user_id']}",
                callback_data=f"admin_user_{user_row['user_id']}"
            )
        ])
    
    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_users_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="none"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_users_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    """Show user detail and management options"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    user = db.get_user(target_user_id)
    if not user:
        await update.callback_query.answer("User not found")
        return
    
    projects = db.get_user_projects(target_user_id)
    running = sum(1 for p in projects if p.status == ProjectStatus.RUNNING)
    
    text = f"""
👤 <b>User Details</b>

• ID: <code>{user.user_id}</code>
• Username: {get_user_display(user)}
• Role: {user.role.value.title()}
• File Limit: {user.file_limit if user.file_limit != -1 else '♾️'}
• Projects: {len(projects)} ({running} running)
• Banned: {'✅ Yes' if user.is_banned else '❌ No'}

<b>Actions:</b>
"""
    
    keyboard = []
    
    # Action buttons
    if user.is_banned:
        keyboard.append([InlineKeyboardButton("🔓 Unban User", callback_data=f"admin_unban_{user.user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🔒 Ban User", callback_data=f"admin_ban_{user.user_id}")])
    
    if user.role != UserRole.ADMIN and user.user_id != OWNER_ID:
        keyboard.append([InlineKeyboardButton("👑 Make Admin", callback_data=f"admin_promote_{user.user_id}")])
    elif user.role == UserRole.ADMIN and user.user_id != OWNER_ID:
        keyboard.append([InlineKeyboardButton("👤 Remove Admin", callback_data=f"admin_demote_{user.user_id}")])
    
    if user.file_limit != -1:
        keyboard.append([InlineKeyboardButton("♾️ Grant Unlimited", callback_data=f"admin_unlimit_{user.user_id}")])
    
    keyboard.append([InlineKeyboardButton("📦 View Projects", callback_data=f"admin_user_projects_{user.user_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_users_1")])
    
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_backups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin view source backups"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.callback_query.answer("Admin only")
        return
    
    with db.get_connection() as conn:
        backups = conn.execute("""
            SELECT su.*, p.name as project_name 
            FROM source_updates su
            JOIN projects p ON su.project_id = p.id
            ORDER BY su.created_at DESC LIMIT 50
        """).fetchall()
    
    if not backups:
        await update.callback_query.edit_message_text("💾 No source backups found.")
        return
    
    text = "💾 <b>Source Backup History</b>\n\n"
    
    for backup in backups[:20]:
        text += f"""
📦 <b>{backup['project_name']}</b>
  Version: {backup['old_version']} → {backup['new_version']}
  Size: {backup['size'] / 1024:.1f}KB
  Date: {backup['created_at'][:19]}
"""
    
    if len(backups) > 20:
        text += f"\n... and {len(backups) - 20} more backups"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
    await update.callback_query.edit_message_text(text[:4096], parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== FILE HANDLER =====
async def file_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ZIP file upload for hosting or update"""
    user_id = update.effective_user.id
    
    # Check if user is updating a project
    if user_id in update_states and update_states[user_id].get("state") == "awaiting_update":
        await handle_update_upload(update, context)
        return
    
    # Check if user is expecting to upload
    if user_id not in user_states or user_states[user_id].get("state") != "awaiting_zip":
        await update.message.reply_text("❌ Use /host first to deploy a bot.")
        return
    
    document = update.message.document
    
    if not document or not document.file_name.endswith('.zip'):
        await update.message.reply_text("❌ Please send a valid .zip file.")
        return
    
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File too large!\n\n"
            f"Max: {MAX_FILE_SIZE_MB}MB\n"
            f"Your file: {document.file_size / 1024 / 1024:.2f}MB"
        )
        return
    
    # Get user
    user = db.get_user(user_id)
    if not user or user.is_banned:
        await update.message.reply_text("❌ You are not authorized to host bots.")
        return
    
    # Check limit
    if not can_host(user_id):
        await update.message.reply_text(
            "❌ You have reached your project limit.\n"
            f"Limit: {user.file_limit if user.file_limit != -1 else '♾️'}"
        )
        return
    
    # Download file
    processing_msg = await update.message.reply_text("📥 <b>Processing your bot...</b>", parse_mode=ParseMode.HTML)
    
    try:
        file = await context.bot.get_file(document.file_id)
        temp_path = os.path.join(TEMP_DIR, f"{user_id}_{document.file_name}")
        await file.download_to_drive(temp_path)
        
        # Generate project name
        project_name = re.sub(r'[^a-zA-Z0-9_-]', '', document.file_name.replace('.zip', ''))
        if not project_name:
            project_name = f"bot_{user_id}_{int(time.time())}"
        
        # Deploy
        success, message, project_id = project_manager.deploy_project_from_zip(
            user_id, temp_path, project_name, is_free_trial=False
        )
        
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Update user total projects
        if success:
            projects = db.get_user_projects(user_id)
            user.total_projects = len(projects)
            db.update_user(user)
        
        # Cleanup state
        if user_id in user_states:
            del user_states[user_id]
        
        if success:
            project = db.get_project(project_id)
            await processing_msg.edit_text(
                f"✅ <b>Bot Deployed Successfully!</b>\n\n"
                f"📦 <b>Project:</b> {project_name}\n"
                f"📋 <b>Framework:</b> {project.framework}\n"
                f"📄 <b>Main File:</b> {project.main_file}\n"
                f"📌 <b>Version:</b> {project.version}\n"
                f"🔒 <b>Source Hash:</b> {project.source_hash[:8]}...\n\n"
                f"Use /mybots to manage your projects.",
                parse_mode=ParseMode.HTML
            )
        else:
            await processing_msg.edit_text(
                f"❌ <b>Deployment Failed</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"File upload error: {e}")
        await processing_msg.edit_text(f"❌ <b>Error</b>\n\n{str(e)}", parse_mode=ParseMode.HTML)

async def handle_update_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ZIP upload for updating a project"""
    user_id = update.effective_user.id
    
    if user_id not in update_states:
        return
    
    project_id = update_states[user_id].get("project_id")
    if not project_id:
        return
    
    document = update.message.document
    
    if not document or not document.file_name.endswith('.zip'):
        await update.message.reply_text("❌ Please send a valid .zip file.")
        return
    
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ File too large!\n\n"
            f"Max: {MAX_FILE_SIZE_MB}MB\n"
            f"Your file: {document.file_size / 1024 / 1024:.2f}MB"
        )
        return
    
    processing_msg = await update.message.reply_text("🔄 <b>Updating bot source...</b>", parse_mode=ParseMode.HTML)
    
    try:
        # Download file
        file = await context.bot.get_file(document.file_id)
        temp_path = os.path.join(TEMP_DIR, f"update_{user_id}_{document.file_name}")
        await file.download_to_drive(temp_path)
        
        # Get version
        version = update_states[user_id].get("version", "1.0.0")
        
        # Update project
        success, message = project_manager.update_project_source(project_id, temp_path, version)
        
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Cleanup state
        if user_id in update_states:
            del update_states[user_id]
        
        if success:
            project = db.get_project(project_id)
            await processing_msg.edit_text(
                f"✅ <b>Bot Updated Successfully!</b>\n\n"
                f"📦 <b>Project:</b> {project.name}\n"
                f"📌 <b>New Version:</b> {project.version}\n"
                f"📋 <b>Framework:</b> {project.framework}\n"
                f"📄 <b>Main File:</b> {project.main_file}\n"
                f"🔒 <b>Source Hash:</b> {project.source_hash[:8]}...\n\n"
                f"{message}",
                parse_mode=ParseMode.HTML
            )
        else:
            await processing_msg.edit_text(
                f"❌ <b>Update Failed</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"Update upload error: {e}")
        await processing_msg.edit_text(f"❌ <b>Error</b>\n\n{str(e)}", parse_mode=ParseMode.HTML)

# ===== CALLBACK HANDLER =====
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # ===== PROJECT ACTIONS =====
    if data.startswith("project_"):
        parts = data.split("_")
        action = parts[1]
        project_id = int(parts[2])
        
        project = db.get_project(project_id)
        if not project:
            await query.edit_message_text("❌ Project not found.")
            return
        
        # Check ownership or admin
        if project.user_id != user_id and not is_admin(user_id):
            await query.edit_message_text("❌ You don't own this project.")
            return
        
        if action == "start":
            success, message = project_manager.start_project(project_id)
            await query.edit_message_text(
                f"{'✅' if success else '❌'} <b>Start Result</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            if success:
                await asyncio.sleep(2)
                await mybots_command(update, context)
        
        elif action == "stop":
            success, message = project_manager.stop_project(project_id)
            await query.edit_message_text(
                f"{'✅' if success else '❌'} <b>Stop Result</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            if success:
                await asyncio.sleep(2)
                await mybots_command(update, context)
        
        elif action == "restart":
            success, message = project_manager.restart_project(project_id)
            await query.edit_message_text(
                f"{'✅' if success else '❌'} <b>Restart Result</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            if success:
                await asyncio.sleep(2)
                await mybots_command(update, context)
        
        elif action == "delete":
            success, message = project_manager.delete_project(project_id)
            await query.edit_message_text(
                f"{'✅' if success else '❌'} <b>Delete Result</b>\n\n{message}",
                parse_mode=ParseMode.HTML
            )
            if success:
                await asyncio.sleep(2)
                await mybots_command(update, context)
        
        elif action == "logs":
            log_path = project_manager.get_log_path(project_id)
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    log_content = f.read()[-3000:]  # Last 3000 chars
                await query.edit_message_text(
                    f"📋 <b>Logs for {project.name}</b>\n\n<pre>{log_content}</pre>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text("📋 No logs available.")
        
        elif action == "save_source":
            # Save project source
            success, backup_path = project_manager.backup_project_source(project)
            if success:
                # Send the ZIP file
                with open(backup_path, 'rb') as f:
                    await query.edit_message_text(
                        f"✅ <b>Source saved!</b>\n\n"
                        f"📦 Project: {project.name}\n"
                        f"📌 Version: {project.version}\n"
                        f"💾 Size: {os.path.getsize(backup_path) / 1024:.1f}KB\n\n"
                        f"Sending the source file...",
                        parse_mode=ParseMode.HTML
                    )
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=f,
                        filename=f"{project.name}_v{project.version}.zip",
                        caption=f"📦 Source code for {project.name} (v{project.version})"
                    )
            else:
                await query.edit_message_text(
                    f"❌ <b>Save Failed</b>\n\n{backup_path}",
                    parse_mode=ParseMode.HTML
                )
            return
        
        elif action == "update_source":
            # Set state for update
            update_states[user_id] = {
                "state": "awaiting_update",
                "project_id": project_id,
                "version": increment_version(project.version, 'patch')
            }
            
            await query.edit_message_text(
                f"🔄 <b>Update Source for {project.name}</b>\n\n"
                f"Current Version: {project.version}\n"
                f"New Version: {increment_version(project.version, 'patch')}\n\n"
                f"Send a new ZIP file with the updated source code.\n\n"
                f"<b>Note:</b> The bot will be stopped during the update.",
                parse_mode=ParseMode.HTML
            )
            return
        
        elif action == "details":
            await show_project_details(update, context, project_id)
        
        return
    
    # ===== SAVE SOURCE =====
    if data.startswith("save_source_"):
        project_id = int(data.split("_")[2])
        project = db.get_project(project_id)
        
        if not project:
            await query.edit_message_text("❌ Project not found.")
            return
        
        if project.user_id != user_id and not is_admin(user_id):
            await query.edit_message_text("❌ You don't own this project.")
            return
        
        success, backup_path = project_manager.backup_project_source(project)
        if success:
            with open(backup_path, 'rb') as f:
                await query.edit_message_text(
                    f"✅ <b>Source saved!</b>\n\n"
                    f"📦 Project: {project.name}\n"
                    f"📌 Version: {project.version}\n"
                    f"💾 Size: {os.path.getsize(backup_path) / 1024:.1f}KB\n\n"
                    f"Sending the source file...",
                    parse_mode=ParseMode.HTML
                )
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"{project.name}_v{project.version}.zip",
                    caption=f"📦 Source code for {project.name} (v{project.version})"
                )
        else:
            await query.edit_message_text(
                f"❌ <b>Save Failed</b>\n\n{backup_path}",
                parse_mode=ParseMode.HTML
            )
        return
    
    # ===== UPDATE SOURCE =====
    if data.startswith("update_source_"):
        project_id = int(data.split("_")[2])
        project = db.get_project(project_id)
        
        if not project:
            await query.edit_message_text("❌ Project not found.")
            return
        
        if project.user_id != user_id and not is_admin(user_id):
            await query.edit_message_text("❌ You don't own this project.")
            return
        
        update_states[user_id] = {
            "state": "awaiting_update",
            "project_id": project_id,
            "version": increment_version(project.version, 'patch')
        }
        
        await query.edit_message_text(
            f"🔄 <b>Update Source for {project.name}</b>\n\n"
            f"Current Version: {project.version}\n"
            f"New Version: {increment_version(project.version, 'patch')}\n\n"
            f"Send a new ZIP file with the updated source code.\n\n"
            f"<b>Note:</b> The bot will be stopped during the update.",
            parse_mode=ParseMode.HTML
        )
        return
    
    # ===== DASHBOARD ACTIONS =====
    if data.startswith("dashboard_"):
        action = data.split("_")[1]
        
        if action == "projects":
            await mybots_command(update, context)
            return
        
        elif action == "deploy":
            await host_command(update, context)
            return
        
        elif action == "save_source":
            await save_source_command(update, context)
            return
        
        elif action == "update_source":
            await update_source_command(update, context)
            return
        
        elif action == "status":
            await status_command(update, context)
            return
        
        elif action == "logs":
            await logs_command(update, context)
            return
        
        elif action == "users":
            await admin_users_command(update, context)
            return
        
        elif action == "admin":
            await admin_panel_command(update, context)
            return
    
    # ===== MYBOTS PAGINATION =====
    if data.startswith("mybots_"):
        page = int(data.split("_")[1])
        await mybots_command(update, context, page)
        return
    
    # ===== ADMIN ACTIONS =====
    if data.startswith("admin_"):
        parts = data.split("_")
        action = parts[1]
        
        if action == "back":
            await admin_panel_command(update, context)
            return
        
        if action == "users":
            page = int(parts[2]) if len(parts) > 2 else 1
            await admin_users_command(update, context, page)
            return
        
        if action == "backups":
            await admin_backups_command(update, context)
            return
        
        if action == "user":
            target_user_id = int(parts[2])
            await admin_user_detail(update, context, target_user_id)
            return
        
        if action == "ban":
            target_user_id = int(parts[2])
            user = db.get_user(target_user_id)
            if user:
                user.is_banned = True
                db.update_user(user)
                await query.edit_message_text(f"✅ User {target_user_id} has been banned.")
                await asyncio.sleep(2)
                await admin_user_detail(update, context, target_user_id)
            return
        
        if action == "unban":
            target_user_id = int(parts[2])
            user = db.get_user(target_user_id)
            if user:
                user.is_banned = False
                db.update_user(user)
                await query.edit_message_text(f"✅ User {target_user_id} has been unbanned.")
                await asyncio.sleep(2)
                await admin_user_detail(update, context, target_user_id)
            return
        
        if action == "promote":
            target_user_id = int(parts[2])
            if db.add_admin(target_user_id, user_id):
                await query.edit_message_text(f"✅ User {target_user_id} is now an admin.")
                await asyncio.sleep(2)
                await admin_user_detail(update, context, target_user_id)
            else:
                await query.edit_message_text("❌ Failed to promote user.")
            return
        
        if action == "demote":
            target_user_id = int(parts[2])
            if db.remove_admin(target_user_id):
                await query.edit_message_text(f"✅ User {target_user_id} is no longer an admin.")
                await asyncio.sleep(2)
                await admin_user_detail(update, context, target_user_id)
            else:
                await query.edit_message_text("❌ Failed to demote user.")
            return
        
        if action == "unlimit":
            target_user_id = int(parts[2])
            user = db.get_user(target_user_id)
            if user:
                user.file_limit = -1
                db.update_user(user)
                await query.edit_message_text(f"✅ User {target_user_id} now has unlimited projects.")
                await asyncio.sleep(2)
                await admin_user_detail(update, context, target_user_id)
            return
        
        if action == "projects":
            await admin_all_projects(update, context)
            return
        
        if action == "broadcast":
            broadcast_states[user_id] = {"state": "awaiting_broadcast"}
            await query.edit_message_text(
                "📢 <b>Broadcast Mode</b>\n\n"
                "Send the message you want to broadcast to all users.\n\n"
                "You can send text, photos, videos, or documents.\n\n"
                "Type /cancel to cancel.",
                parse_mode=ParseMode.HTML
            )
            return
        
        if action == "refresh":
            await query.edit_message_text("🔄 <b>Refreshing System...</b>", parse_mode=ParseMode.HTML)
            # Clear running processes
            for pid in list(project_manager.running_processes.keys()):
                project_manager.stop_project(pid)
            await query.edit_message_text("✅ <b>System Refreshed</b>", parse_mode=ParseMode.HTML)
            return
        
        if action == "logs":
            await logs_command(update, context)
            return
        
        if action == "user_projects":
            target_user_id = int(parts[2])
            await admin_user_projects(update, context, target_user_id)
            return
        
        return
    
    # ===== DEFAULT =====
    await query.edit_message_text("❌ Unknown action.")

async def show_project_details(update: Update, context: ContextTypes.DEFAULT_TYPE, project_id: int):
    """Show detailed project information"""
    project = db.get_project(project_id)
    if not project:
        await update.callback_query.edit_message_text("❌ Project not found.")
        return
    
    user = db.get_user(project.user_id)
    
    text = f"""
📋 <b>Project Details</b>

<b>📦 Name:</b> {project.name}
<b>👤 Owner:</b> {get_user_display(user)}
<b>📋 Framework:</b> {project.framework}
<b>📄 Main File:</b> {project.main_file}
<b>📊 Status:</b> {get_status_emoji(project.status)} {project.status.value.title()}
<b>📌 Version:</b> v{project.version}

<b>⚙️ Technical:</b>
• PID: {project.pid or 'N/A'}
• Port: {project.port or 'N/A'}
• CPU: {project.cpu_usage:.1f}%
• RAM: {project.memory_usage:.1f}MB
• Restarts: {project.restart_count}
• Start Count: {project.start_count}
• Source Hash: {project.source_hash[:8] if project.source_hash else 'N/A'}...

<b>📅 Timeline:</b>
• Created: {format_time(project.created_at)}
• Last Started: {format_time(project.last_started)}
• Last Restart: {format_time(project.last_restart)}
• Last Updated: {format_time(project.last_updated)}

<b>🔧 Options:</b>
• Auto-Restart: {'✅' if project.auto_restart else '❌'}
• Dependencies: {'✅' if project.deps_installed else '❌'}
• Free Trial: {'✅' if project.is_free_trial else '❌'}
"""
    
    keyboard = create_project_keyboard(project_id, project.status == ProjectStatus.RUNNING)
    await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def admin_all_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin view all projects"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.callback_query.answer("Admin only")
        return
    
    projects = db.get_all_projects()
    
    if not projects:
        await update.callback_query.edit_message_text("📦 No projects found.")
        return
    
    text = "📦 <b>All Projects</b>\n\n"
    
    for project in projects[:20]:
        user = db.get_user(project.user_id)
        username = get_user_display(user) if user else "Unknown"
        status = get_status_emoji(project.status)
        text += f"{status} <b>{project.name}</b> (v{project.version})\n"
        text += f"  👤 {username} | {project.framework}\n"
        text += f"  💻 CPU: {project.cpu_usage:.1f}% | RAM: {project.memory_usage:.1f}MB\n\n"
    
    if len(projects) > 20:
        text += f"\n... and {len(projects) - 20} more projects"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
    await update.callback_query.edit_message_text(text[:4096], parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_user_projects(update: Update, context: ContextTypes.DEFAULT_TYPE, target_user_id: int):
    """Admin view user's projects"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.callback_query.answer("Admin only")
        return
    
    projects = db.get_user_projects(target_user_id)
    user = db.get_user(target_user_id)
    
    if not projects:
        await update.callback_query.edit_message_text(f"📦 User has no projects.")
        return
    
    text = f"📦 <b>Projects for {get_user_display(user)}</b>\n\n"
    
    for project in projects:
        status = get_status_emoji(project.status)
        text += f"{status} <b>{project.name}</b> (v{project.version}) | {project.framework}\n"
        text += f"  Status: {project.status.value.title()} | CPU: {project.cpu_usage:.1f}%\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=f"admin_user_{target_user_id}")]]
    await update.callback_query.edit_message_text(text[:4096], parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# ===== MESSAGE HANDLER =====
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check for broadcast mode
    if user_id in broadcast_states and broadcast_states[user_id].get("state") == "awaiting_broadcast":
        if text == "/cancel":
            del broadcast_states[user_id]
            await update.message.reply_text("✅ Broadcast cancelled.")
            return
        
        await broadcast_send(update, context, text)
        return
    
    # Handle button commands
    if text == "📦 My Projects":
        await mybots_command(update, context)
    elif text == "🚀 Deploy Bot":
        await host_command(update, context)
    elif text == "💾 Save Source":
        await save_source_command(update, context)
    elif text == "🔄 Update Source":
        await update_source_command(update, context)
    elif text == "📊 System Status":
        await status_command(update, context)
    elif text == "📋 Bot Logs":
        await logs_command(update, context)
    elif text == "⚙️ Admin Panel":
        await admin_panel_command(update, context)
    elif text == "👥 User Management":
        await admin_users_command(update, context)
    else:
        await update.message.reply_text(
            "🤖 Use the menu buttons or commands:\n"
            "/start - Start the bot\n"
            "/dashboard - Open dashboard\n"
            "/host - Deploy a bot\n"
            "/mybots - View your projects\n"
            "/save - Save bot source code\n"
            "/update - Update bot source code"
        )

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send broadcast message to all users"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    with db.get_connection() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    success = 0
    failed = 0
    
    for user_row in users:
        try:
            await context.bot.send_message(user_row['user_id'], message, parse_mode=ParseMode.HTML)
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    if user_id in broadcast_states:
        del broadcast_states[user_id]
    
    await update.message.reply_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"📤 Sent: {success}\n"
        f"❌ Failed: {failed}",
        parse_mode=ParseMode.HTML
    )

# ===== MEDIA BROADCAST =====
async def media_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle media for broadcast"""
    user_id = update.effective_user.id
    
    if user_id not in broadcast_states or broadcast_states[user_id].get("state") != "awaiting_broadcast":
        return
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only.")
        return
    
    with db.get_connection() as conn:
        users = conn.execute("SELECT user_id FROM users").fetchall()
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    success = 0
    failed = 0
    
    for user_row in users:
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    user_row['user_id'], 
                    update.message.photo[-1].file_id,
                    caption=update.message.caption
                )
            elif update.message.video:
                await context.bot.send_video(
                    user_row['user_id'],
                    update.message.video.file_id,
                    caption=update.message.caption
                )
            elif update.message.document:
                await context.bot.send_document(
                    user_row['user_id'],
                    update.message.document.file_id,
                    caption=update.message.caption
                )
            success += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    if user_id in broadcast_states:
        del broadcast_states[user_id]
    
    await update.message.reply_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"📤 Sent: {success}\n"
        f"❌ Failed: {failed}",
        parse_mode=ParseMode.HTML
    )

# ===== ERROR HANDLER =====
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ <b>An error occurred</b>\n\nPlease try again later.",
                parse_mode=ParseMode.HTML
            )
    except:
        pass

# ===== CANCEL COMMAND =====
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    user_id = update.effective_user.id
    
    if user_id in user_states:
        del user_states[user_id]
    
    if user_id in broadcast_states:
        del broadcast_states[user_id]
    
    if user_id in update_states:
        del update_states[user_id]
    
    await update.message.reply_text("✅ Operation cancelled.")

# ===== MAIN =====
def main():
    """Main entry point"""
    print(f"""
╔═══════════════════════════════════════╗
║   🚀 ADVANCED BOT HOSTING PLATFORM    ║
║   Version: 3.1                        ║
║   Creator: @abbsydurov                ║
║   Channel: https://t.me/DEviNePORTaL  ║
║   Features: Save & Update Source      ║
╚═══════════════════════════════════════╝
    """)
    
    logger.info("Starting Advanced Bot Hosting Platform...")
    logger.info(f"Owner: {OWNER_ID}")
    logger.info(f"Channel: {CHANNEL_ID}")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("host", host_command))
    app.add_handler(CommandHandler("mybots", mybots_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("admin", admin_panel_command))
    app.add_handler(CommandHandler("save", save_source_command))
    app.add_handler(CommandHandler("update", update_source_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    app.add_handler(MessageHandler(filters.Document.ZIP, file_upload_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, media_broadcast_handler))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    app.add_error_handler(error_handler)
    
    # Start auto-restart for projects
    def auto_restart_loop():
        while True:
            try:
                projects = db.get_all_projects()
                for project in projects:
                    if project.auto_restart and project.status == ProjectStatus.STOPPED:
                        logger.info(f"Auto-starting {project.name}")
                        project_manager.start_project(project.id)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Auto-restart loop error: {e}")
                time.sleep(300)
    
    threading.Thread(target=auto_restart_loop, daemon=True).start()
    
    # Start bot
    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        cleanup_pid()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        cleanup_pid()
        raise
