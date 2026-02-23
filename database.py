"""
=============================================================================
BOLLYFLIX BOT - DATABASE SYSTEM
=============================================================================
Simple JSON-based database for users, searches, downloads, cache & stats
Thread-safe with auto-save functionality
=============================================================================
"""

import os
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

from logger import log_info, log_error, log_success, log_database, log_warning


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class User:
    """User data model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    joined: str = ""
    last_active: str = ""
    searches: int = 0
    downloads: int = 0
    banned: bool = False
    ban_reason: Optional[str] = None
    is_premium: bool = False
    role: str = "user"  # user, manager, admin, owner
    
    def __post_init__(self):
        if not self.joined:
            self.joined = datetime.now().isoformat()
        if not self.last_active:
            self.last_active = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SearchLog:
    """Search log entry"""
    user_id: int
    query: str
    results_count: int
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DownloadLog:
    """Download log entry"""
    user_id: int
    title: str
    quality: str
    content_type: str  # "movie" or "series"
    season: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CacheEntry:
    """Cache entry for bypassed URLs"""
    url: str
    result_url: str
    timestamp: str = ""
    hit_count: int = 0
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if cache entry is expired"""
        try:
            cached_time = datetime.fromisoformat(self.timestamp)
            return datetime.now() - cached_time > timedelta(hours=max_age_hours)
        except:
            return True


# =============================================================================
# DATABASE CLASS
# =============================================================================

class Database:
    """
    Simple JSON-based database with thread-safe operations
    
    Features:
    - User management (add, update, ban/unban)
    - Search logging
    - Download logging
    - URL caching with expiry
    - User settings persistence
    - Statistics
    - Auto-save with debouncing
    
    Usage:
        from database import db
        
        # Add user
        db.add_user(123456, "john", "John Doe")
        
        # Log search
        db.log_search(123456, "avengers", 5)
        
        # Log download
        db.log_download(123456, "Avengers", "1080p", "movie")
        
        # User settings
        db.save_user_settings(123456, {"default_quality": "1080p"})
        settings = db.get_user_settings(123456)
        
        # Get stats
        stats = db.get_stats()
    """
    
    def __init__(
        self,
        filename: str = "bollyflix_data.json",
        auto_save: bool = True,
        max_logs: int = 1000,
        cache_max_age: int = 24
    ):
        """
        Initialize database
        
        Args:
            filename: JSON file path
            auto_save: Auto-save after changes
            max_logs: Maximum log entries to keep
            cache_max_age: Cache expiry in hours
        """
        self.filename = filename
        self.auto_save = auto_save
        self.max_logs = max_logs
        self.cache_max_age = cache_max_age
        
        # Thread lock for safe operations
        self._lock = threading.RLock()
        
        # Data structure
        self._data: Dict[str, Any] = {
            "users": {},
            "searches": [],
            "downloads": [],
            "cache": {},
            "user_settings": {},
            "stats": {
                "total_searches": 0,
                "total_downloads": 0,
                "bot_started": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        }
        
        # Load existing data
        self._load()
        
        log_database(f"Database initialized: {filename}")
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    def _load(self):
        """Load data from JSON file"""
        with self._lock:
            try:
                if os.path.exists(self.filename):
                    with open(self.filename, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                        
                        # Merge with default structure
                        for key in self._data:
                            if key in loaded_data:
                                self._data[key] = loaded_data[key]
                        
                        # Ensure user_settings exists in loaded data
                        if "user_settings" not in self._data:
                            self._data["user_settings"] = {}
                        
                        log_success(f"Loaded {len(self._data['users'])} users from database")
            except json.JSONDecodeError as e:
                log_error(f"Database file corrupted: {e}")
                self._backup_and_reset()
            except Exception as e:
                log_error(f"Database load error: {e}")
    
    def _save(self):
        """Save data to JSON file"""
        with self._lock:
            try:
                # Update timestamp
                self._data["stats"]["last_updated"] = datetime.now().isoformat()
                
                # Write to temp file first
                temp_file = self.filename + ".tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)
                
                # Rename to actual file (atomic operation)
                os.replace(temp_file, self.filename)
                
            except Exception as e:
                log_error(f"Database save error: {e}")
    
    def _backup_and_reset(self):
        """Backup corrupted file and reset"""
        try:
            if os.path.exists(self.filename):
                backup = f"{self.filename}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.filename, backup)
                log_warning(f"Corrupted database backed up to: {backup}")
        except:
            pass
    
    def save(self):
        """Force save database"""
        self._save()
        log_database("Database saved")
    
    def _auto_save(self):
        """Auto-save if enabled"""
        if self.auto_save:
            self._save()
    
    # =========================================================================
    # USER OPERATIONS
    # =========================================================================
    
    def add_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Add or update user"""
        with self._lock:
            user_id_str = str(user_id)
            
            if user_id_str in self._data["users"]:
                # Update existing user
                user_data = self._data["users"][user_id_str]
                user_data["username"] = username
                user_data["first_name"] = first_name
                user_data["last_name"] = last_name
                user_data["last_active"] = datetime.now().isoformat()
            else:
                # Create new user
                user = User(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                self._data["users"][user_id_str] = user.to_dict()
                log_info(f"New user added: {user_id}")
            
            self._auto_save()
            return self.get_user(user_id)
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self._lock:
            user_data = self._data["users"].get(str(user_id))
            if user_data:
                return User.from_dict(user_data)
            return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user fields"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                for key, value in kwargs.items():
                    if key in User.__dataclass_fields__:
                        self._data["users"][user_id_str][key] = value
                self._auto_save()
                return True
            return False
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        with self._lock:
            users = []
            for user_data in self._data["users"].values():
                users.append(User.from_dict(user_data))
            return users
    
    def get_user_count(self) -> int:
        """Get total user count"""
        with self._lock:
            return len(self._data["users"])
    
    def get_active_users(self, hours: int = 24) -> List[User]:
        """Get users active within specified hours"""
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            active = []
            
            for user_data in self._data["users"].values():
                try:
                    last_active = datetime.fromisoformat(user_data.get("last_active", ""))
                    if last_active > cutoff:
                        active.append(User.from_dict(user_data))
                except:
                    pass
            
            return active
    
    # =========================================================================
    # BAN OPERATIONS
    # =========================================================================
    
    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        with self._lock:
            user_data = self._data["users"].get(str(user_id))
            if user_data:
                return user_data.get("banned", False)
            return False
    
    def ban_user(self, user_id: int, reason: Optional[str] = None) -> bool:
        """Ban a user"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                self._data["users"][user_id_str]["banned"] = True
                self._data["users"][user_id_str]["ban_reason"] = reason
                self._auto_save()
                log_warning(f"User {user_id} banned. Reason: {reason}")
                return True
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                self._data["users"][user_id_str]["banned"] = False
                self._data["users"][user_id_str]["ban_reason"] = None
                self._auto_save()
                log_info(f"User {user_id} unbanned")
                return True
            return False
    
    def get_banned_users(self) -> List[User]:
        """Get all banned users"""
        with self._lock:
            banned = []
            for user_data in self._data["users"].values():
                if user_data.get("banned", False):
                    banned.append(User.from_dict(user_data))
            return banned
    
    # =========================================================================
    # SEARCH LOGGING
    # =========================================================================
    
    def log_search(self, user_id: int, query: str, results_count: int):
        """Log a search"""
        with self._lock:
            # Create log entry
            log_entry = SearchLog(
                user_id=user_id,
                query=query,
                results_count=results_count
            )
            
            # Add to logs
            self._data["searches"].append(log_entry.to_dict())
            
            # Trim if too many
            if len(self._data["searches"]) > self.max_logs:
                self._data["searches"] = self._data["searches"][-self.max_logs:]
            
            # Update user stats
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                current = self._data["users"][user_id_str].get("searches", 0)
                self._data["users"][user_id_str]["searches"] = current + 1
            
            # Update global stats
            self._data["stats"]["total_searches"] += 1
            
            self._auto_save()
    
    def increment_searches(self, user_id: int):
        """Increment user search count (simple version)"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                current = self._data["users"][user_id_str].get("searches", 0)
                self._data["users"][user_id_str]["searches"] = current + 1
            self._data["stats"]["total_searches"] += 1
            self._auto_save()
    
    def get_recent_searches(self, limit: int = 50) -> List[SearchLog]:
        """Get recent searches"""
        with self._lock:
            searches = []
            for log_data in self._data["searches"][-limit:]:
                searches.append(SearchLog(**log_data))
            return searches[::-1]  # Newest first
    
    def get_user_searches(self, user_id: int, limit: int = 20) -> List[SearchLog]:
        """Get searches by specific user"""
        with self._lock:
            searches = []
            for log_data in reversed(self._data["searches"]):
                if log_data.get("user_id") == user_id:
                    searches.append(SearchLog(**log_data))
                    if len(searches) >= limit:
                        break
            return searches
    
    # =========================================================================
    # DOWNLOAD LOGGING
    # =========================================================================
    
    def log_download(
        self,
        user_id: int,
        title: str,
        quality: str,
        content_type: str = "movie",
        season: Optional[str] = None
    ):
        """Log a download"""
        with self._lock:
            # Create log entry
            log_entry = DownloadLog(
                user_id=user_id,
                title=title,
                quality=quality,
                content_type=content_type,
                season=season
            )
            
            # Add to logs
            self._data["downloads"].append(log_entry.to_dict())
            
            # Trim if too many
            if len(self._data["downloads"]) > self.max_logs:
                self._data["downloads"] = self._data["downloads"][-self.max_logs:]
            
            # Update user stats
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                current = self._data["users"][user_id_str].get("downloads", 0)
                self._data["users"][user_id_str]["downloads"] = current + 1
            
            # Update global stats
            self._data["stats"]["total_downloads"] += 1
            
            self._auto_save()
            log_database(f"Download logged: {title} ({quality})")
    
    def increment_downloads(self, user_id: int):
        """Increment user download count (simple version)"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                current = self._data["users"][user_id_str].get("downloads", 0)
                self._data["users"][user_id_str]["downloads"] = current + 1
            self._data["stats"]["total_downloads"] += 1
            self._auto_save()
    
    def get_recent_downloads(self, limit: int = 50) -> List[DownloadLog]:
        """Get recent downloads"""
        with self._lock:
            downloads = []
            for log_data in self._data["downloads"][-limit:]:
                downloads.append(DownloadLog(**log_data))
            return downloads[::-1]  # Newest first
    
    def get_user_downloads(self, user_id: int, limit: int = 20) -> List[DownloadLog]:
        """Get downloads by specific user"""
        with self._lock:
            downloads = []
            for log_data in reversed(self._data["downloads"]):
                if log_data.get("user_id") == user_id:
                    downloads.append(DownloadLog(**log_data))
                    if len(downloads) >= limit:
                        break
            return downloads
    
    def get_today_download_count(self, user_id: int) -> int:
        """Get user's download count for today"""
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            count = 0
            for log_data in reversed(self._data["downloads"]):
                if log_data.get("user_id") == user_id:
                    ts = log_data.get("timestamp", "")
                    if ts.startswith(today):
                        count += 1
                    elif ts < today:
                        break  # Older entries, stop counting
            return count
    
    def is_premium_user(self, user_id: int) -> bool:
        """Check if user has premium status"""
        with self._lock:
            user_data = self._data["users"].get(str(user_id))
            if user_data:
                return user_data.get("is_premium", False)
            return False

    # =========================================================================
    # ROLE MANAGEMENT (Dashboard RBAC)
    # =========================================================================
    
    def get_user_role(self, user_id: int) -> str:
        """Get role of a user"""
        from config import OWNER_IDS
        if user_id in OWNER_IDS:
            return "owner"
            
        with self._lock:
            user_data = self._data["users"].get(str(user_id))
            if user_data:
                return user_data.get("role", "user")
            return "user"
            
    def set_user_role(self, user_id: int, role: str) -> bool:
        """Set role of a user. Returns True if successful"""
        from config import OWNER_IDS
        if user_id in OWNER_IDS and role != "owner":
            return False  # Cannot demote root owners
            
        valid_roles = ["user", "manager", "admin", "owner"]
        if role not in valid_roles:
            return False
            
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                self._data["users"][user_id_str]["role"] = role
                self._auto_save()
                log_info(f"User {user_id} role updated to: {role}")
                return True
            return False
            
    def get_staff_users(self) -> List[Dict]:
        """Get all managers, admins, and owners"""
        staff = []
        with self._lock:
            for uid, data in self._data["users"].items():
                role = data.get("role", "user")
                if role in ["manager", "admin", "owner"]:
                    # Safely inject the user id
                    user_info = data.copy()
                    user_info["user_id"] = int(uid)
                    staff.append(user_info)
        return staff
    
    # =========================================================================
    # USER SETTINGS OPERATIONS
    # =========================================================================
    
    def get_user_settings(self, user_id: int) -> Optional[Dict]:
        """
        Get user settings from database
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Settings dict or None if no settings saved
        """
        with self._lock:
            try:
                user_id_str = str(user_id)
                
                # Ensure user_settings key exists
                if "user_settings" not in self._data:
                    self._data["user_settings"] = {}
                
                settings = self._data["user_settings"].get(user_id_str, None)
                
                if settings:
                    log_database(f"Settings loaded for user {user_id}")
                
                return settings
                
            except Exception as e:
                log_error(f"Get settings error for user {user_id}: {e}")
                return None
    
    def save_user_settings(self, user_id: int, settings: Dict) -> bool:
        """
        Save user settings to database
        
        Args:
            user_id: Telegram user ID
            settings: Settings dict to save
        
        Returns:
            True if saved successfully
        """
        with self._lock:
            try:
                user_id_str = str(user_id)
                
                # Ensure user_settings key exists
                if "user_settings" not in self._data:
                    self._data["user_settings"] = {}
                
                # Save settings
                self._data["user_settings"][user_id_str] = settings.copy()
                
                # Persist to file
                self._auto_save()
                
                log_database(f"Settings saved for user {user_id}")
                return True
                
            except Exception as e:
                log_error(f"Save settings error for user {user_id}: {e}")
                return False
    
    def delete_user_settings(self, user_id: int) -> bool:
        """
        Delete user settings from database
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True if deleted successfully
        """
        with self._lock:
            try:
                user_id_str = str(user_id)
                
                if "user_settings" not in self._data:
                    return False
                
                if user_id_str in self._data["user_settings"]:
                    del self._data["user_settings"][user_id_str]
                    self._auto_save()
                    log_database(f"Settings deleted for user {user_id}")
                    return True
                
                return False
                
            except Exception as e:
                log_error(f"Delete settings error for user {user_id}: {e}")
                return False
    
    def get_user_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Get single setting value for user
        
        Args:
            user_id: Telegram user ID
            key: Setting key
            default: Default value if not found
        
        Returns:
            Setting value or default
        """
        with self._lock:
            try:
                user_id_str = str(user_id)
                
                if "user_settings" not in self._data:
                    return default
                
                settings = self._data["user_settings"].get(user_id_str, {})
                return settings.get(key, default)
                
            except Exception as e:
                log_error(f"Get single setting error: {e}")
                return default
    
    def update_user_setting(self, user_id: int, key: str, value: Any) -> bool:
        """
        Update single setting value for user
        
        Args:
            user_id: Telegram user ID
            key: Setting key
            value: New value
        
        Returns:
            True if updated successfully
        """
        with self._lock:
            try:
                user_id_str = str(user_id)
                
                if "user_settings" not in self._data:
                    self._data["user_settings"] = {}
                
                if user_id_str not in self._data["user_settings"]:
                    self._data["user_settings"][user_id_str] = {}
                
                self._data["user_settings"][user_id_str][key] = value
                self._auto_save()
                
                log_database(f"Setting updated for user {user_id}: {key} = {value}")
                return True
                
            except Exception as e:
                log_error(f"Update single setting error: {e}")
                return False
    
    def get_all_user_settings(self) -> Dict[str, Dict]:
        """
        Get all users settings (for admin/export)
        
        Returns:
            Dict of user_id -> settings
        """
        with self._lock:
            if "user_settings" not in self._data:
                return {}
            return self._data["user_settings"].copy()
    
    def get_settings_stats(self) -> Dict:
        """
        Get settings usage statistics
        
        Returns:
            Dict with settings stats
        """
        with self._lock:
            if "user_settings" not in self._data:
                return {"total_users_with_settings": 0, "preferences": {}}
            
            all_settings = self._data["user_settings"]
            total = len(all_settings)
            
            # Count preference distribution
            quality_counts = {}
            language_counts = {}
            content_counts = {}
            bypass_counts = {"on": 0, "off": 0}
            
            for user_settings in all_settings.values():
                # Quality
                q = user_settings.get("default_quality", "auto")
                quality_counts[q] = quality_counts.get(q, 0) + 1
                
                # Language
                l = user_settings.get("language", "all")
                language_counts[l] = language_counts.get(l, 0) + 1
                
                # Content type
                c = user_settings.get("content_type", "all")
                content_counts[c] = content_counts.get(c, 0) + 1
                
                # Auto bypass
                b = user_settings.get("auto_bypass", "on")
                if b in bypass_counts:
                    bypass_counts[b] += 1
            
            return {
                "total_users_with_settings": total,
                "preferences": {
                    "quality": quality_counts,
                    "language": language_counts,
                    "content_type": content_counts,
                    "auto_bypass": bypass_counts
                }
            }
    
    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================
    
    def get_cache(self, key: str) -> Optional[str]:
        """Get cached URL by key"""
        with self._lock:
            cached = self._data["cache"].get(key)
            if cached:
                entry = CacheEntry(**cached)
                
                # Check expiry
                if not entry.is_expired(self.cache_max_age):
                    # Increment hit count
                    self._data["cache"][key]["hit_count"] = entry.hit_count + 1
                    return entry.result_url
                else:
                    # Remove expired
                    del self._data["cache"][key]
                    self._auto_save()
            
            return None
    
    def set_cache(self, key: str, result_url: str):
        """Cache a URL"""
        with self._lock:
            entry = CacheEntry(url=key, result_url=result_url)
            self._data["cache"][key] = entry.to_dict()
            self._auto_save()
            log_database(f"Cached URL: {key[:30]}...")
    
    def clear_cache(self):
        """Clear all cache"""
        with self._lock:
            count = len(self._data["cache"])
            self._data["cache"] = {}
            self._auto_save()
            log_database(f"Cleared {count} cache entries")
    
    def clean_expired_cache(self) -> int:
        """Remove expired cache entries"""
        with self._lock:
            expired_keys = []
            
            for key, cached in self._data["cache"].items():
                entry = CacheEntry(**cached)
                if entry.is_expired(self.cache_max_age):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._data["cache"][key]
            
            if expired_keys:
                self._auto_save()
                log_database(f"Cleaned {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            total_hits = sum(
                c.get("hit_count", 0) 
                for c in self._data["cache"].values()
            )
            return {
                "total_entries": len(self._data["cache"]),
                "total_hits": total_hits
            }
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get complete statistics"""
        with self._lock:
            active_24h = len(self.get_active_users(24))
            cache_stats = self.get_cache_stats()
            settings_stats = self.get_settings_stats()
            
            return {
                "users": {
                    "total": len(self._data["users"]),
                    "active_24h": active_24h,
                    "banned": len(self.get_banned_users()),
                    "with_settings": settings_stats["total_users_with_settings"]
                },
                "searches": {
                    "total": self._data["stats"]["total_searches"],
                    "logged": len(self._data["searches"])
                },
                "downloads": {
                    "total": self._data["stats"]["total_downloads"],
                    "logged": len(self._data["downloads"])
                },
                "cache": cache_stats,
                "settings": settings_stats,
                "bot": {
                    "started": self._data["stats"].get("bot_started", "N/A"),
                    "last_updated": self._data["stats"].get("last_updated", "N/A")
                }
            }
    
    def get_top_users(self, limit: int = 10, by: str = "downloads") -> List[User]:
        """Get top users by downloads or searches"""
        with self._lock:
            users = self.get_all_users()
            
            if by == "downloads":
                users.sort(key=lambda u: u.downloads, reverse=True)
            else:
                users.sort(key=lambda u: u.searches, reverse=True)
            
            return users[:limit]
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def reset_user_stats(self, user_id: int) -> bool:
        """Reset user's search and download counts"""
        with self._lock:
            user_id_str = str(user_id)
            if user_id_str in self._data["users"]:
                self._data["users"][user_id_str]["searches"] = 0
                self._data["users"][user_id_str]["downloads"] = 0
                self._auto_save()
                return True
            return False
    
    def export_data(self, filepath: str) -> bool:
        """Export database to file"""
        with self._lock:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)
                log_success(f"Database exported to: {filepath}")
                return True
            except Exception as e:
                log_error(f"Export failed: {e}")
                return False
    
    def get_user_ids(self) -> List[int]:
        """Get all user IDs"""
        with self._lock:
            return [int(uid) for uid in self._data["users"].keys()]
    
    def user_exists(self, user_id: int) -> bool:
        """Check if user exists"""
        with self._lock:
            return str(user_id) in self._data["users"]
    
    # =========================================================================
    # SESSION STORAGE (Pyrogram Login)
    # =========================================================================
    
    def set_session(self, user_id: int, session_string: str):
        """Save Pyrogram session string"""
        with self._lock:
            if "sessions" not in self._data:
                self._data["sessions"] = {}
            self._data["sessions"][str(user_id)] = session_string
            self._auto_save()
            log_info(f"Session saved for {user_id}")
    
    def get_session(self, user_id: int) -> str:
        """Get Pyrogram session string"""
        with self._lock:
            if "sessions" not in self._data:
                return None
            return self._data["sessions"].get(str(user_id))
    
    def remove_session(self, user_id: int) -> bool:
        """Remove Pyrogram session"""
        with self._lock:
            if "sessions" not in self._data:
                return False
            if str(user_id) in self._data["sessions"]:
                del self._data["sessions"][str(user_id)]
                self._auto_save()
                log_info(f"Session removed for {user_id}")
                return True
            return False


# =============================================================================
# GLOBAL DATABASE INSTANCE
# =============================================================================

# Create default database
db = Database()


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

def get_db() -> Database:
    """Get the global database instance"""
    return db


def add_user(user_id: int, username: str = None, first_name: str = None) -> User:
    """Add or update user"""
    return db.add_user(user_id, username, first_name)


def is_banned(user_id: int) -> bool:
    """Check if user is banned"""
    return db.is_banned(user_id)


def ban_user(user_id: int, reason: str = None) -> bool:
    """Ban a user"""
    return db.ban_user(user_id, reason)


def unban_user(user_id: int) -> bool:
    """Unban a user"""
    return db.unban_user(user_id)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Demo
    print("=" * 50)
    print("DATABASE DEMO")
    print("=" * 50)
    
    # Add users
    db.add_user(123456, "john_doe", "John")
    db.add_user(789012, "jane_doe", "Jane")
    
    # Log searches
    db.log_search(123456, "avengers", 5)
    db.log_search(123456, "spiderman", 3)
    
    # Log downloads
    db.log_download(123456, "Avengers Endgame", "1080p", "movie")
    db.log_download(789012, "Money Heist", "720p", "series", "S01")
    
    # Cache
    db.set_cache("test_key", "https://example.com/file")
    print(f"Cache hit: {db.get_cache('test_key')}")
    
    # Settings
    db.save_user_settings(123456, {
        "default_quality": "1080p",
        "language": "hindi",
        "content_type": "all",
        "results_count": "10",
        "auto_bypass": "on"
    })
    
    settings = db.get_user_settings(123456)
    print(f"\nUser settings: {settings}")
    
    # Update single setting
    db.update_user_setting(123456, "default_quality", "720p")
    print(f"Updated quality: {db.get_user_setting(123456, 'default_quality')}")
    
    # Settings stats
    settings_stats = db.get_settings_stats()
    print(f"\nSettings stats: {json.dumps(settings_stats, indent=2)}")
    
    # Stats
    stats = db.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")
    
    # User history
    user = db.get_user(123456)
    if user:
        print(f"\nUser: {user.first_name}")
        print(f"Searches: {user.searches}")
        print(f"Downloads: {user.downloads}")
    
    print("\n✅ Database demo complete!")