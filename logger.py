"""
=============================================================================
BOLLYFLIX BOT - LOGGING SYSTEM
=============================================================================
Beautiful console logging with emojis, colors, and file support
=============================================================================
"""

import os
import sys
from datetime import datetime
from typing import Optional, TextIO
from enum import Enum


# =============================================================================
# LOG LEVELS
# =============================================================================

class LogLevel(Enum):
    """Log level enumeration with priority values"""
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    
    def __str__(self):
        return self.name


# =============================================================================
# COLORS FOR TERMINAL
# =============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    
    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Text colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    
    @staticmethod
    def disable():
        """Disable colors (for non-terminal output)"""
        for attr in dir(Colors):
            if not attr.startswith('_') and attr.isupper():
                setattr(Colors, attr, "")
    
    @staticmethod
    def is_terminal() -> bool:
        """Check if running in a terminal"""
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


# =============================================================================
# LOG CONFIGURATION
# =============================================================================

class LogConfig:
    """Logger configuration settings"""
    
    # Emojis for each log level
    EMOJIS = {
        LogLevel.DEBUG: "🔍",
        LogLevel.INFO: "ℹ️",
        LogLevel.SUCCESS: "✅",
        LogLevel.WARNING: "⚠️",
        LogLevel.ERROR: "❌",
        LogLevel.CRITICAL: "🔥",
    }
    
    # Colors for each log level
    LEVEL_COLORS = {
        LogLevel.DEBUG: Colors.DIM + Colors.WHITE,
        LogLevel.INFO: Colors.BRIGHT_BLUE,
        LogLevel.SUCCESS: Colors.BRIGHT_GREEN,
        LogLevel.WARNING: Colors.BRIGHT_YELLOW,
        LogLevel.ERROR: Colors.BRIGHT_RED,
        LogLevel.CRITICAL: Colors.BOLD + Colors.BRIGHT_RED,
    }
    
    # Additional emojis for special log types
    SPECIAL_EMOJIS = {
        "working": "⚡",
        "waiting": "⏳",
        "download": "📥",
        "upload": "📤",
        "search": "🔎",
        "bypass": "🚀",
        "telegram": "📱",
        "database": "🗄️",
        "cache": "💾",
        "user": "👤",
        "admin": "👑",
        "bot": "🤖",
        "movie": "🎬",
        "series": "📺",
        "start": "🚀",
        "stop": "🛑",
        "config": "⚙️",
    }


# =============================================================================
# MAIN LOGGER CLASS
# =============================================================================

class Logger:
    """
    Beautiful logging system with emoji and color support
    
    Usage:
        from logger import Logger, log
        
        log = Logger("BollyFlix")
        log.info("Bot started")
        log.success("Download complete")
        log.error("Something failed")
        
        # Or use module-level functions
        from logger import log_info, log_error
        log_info("Hello!")
    """
    
    def __init__(
        self,
        name: str = "Bot",
        min_level: LogLevel = LogLevel.DEBUG,
        use_colors: bool = True,
        use_emojis: bool = True,
        log_file: Optional[str] = None,
        timestamp_format: str = "%H:%M:%S",
        full_timestamp: bool = False
    ):
        """
        Initialize logger
        
        Args:
            name: Logger name (shown in output)
            min_level: Minimum log level to display
            use_colors: Enable terminal colors
            use_emojis: Enable emoji prefixes
            log_file: Optional file path for logging
            timestamp_format: Time format string
            full_timestamp: Include date in timestamp
        """
        self.name = name
        self.min_level = min_level
        self.use_colors = use_colors and Colors.is_terminal()
        self.use_emojis = use_emojis
        self.log_file = log_file
        self.timestamp_format = timestamp_format
        self.full_timestamp = full_timestamp
        
        # File handle
        self._file_handle: Optional[TextIO] = None
        
        # Open log file if specified
        if self.log_file:
            self._open_file()
        
        # Disable colors if not terminal
        if not self.use_colors:
            Colors.disable()
    
    def _open_file(self):
        """Open log file for writing"""
        try:
            # Create directory if needed
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            self._file_handle = open(self.log_file, 'a', encoding='utf-8')
        except Exception as e:
            print(f"Failed to open log file: {e}")
    
    def _close_file(self):
        """Close log file"""
        if self._file_handle:
            try:
                self._file_handle.close()
            except:
                pass
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        now = datetime.now()
        if self.full_timestamp:
            return now.strftime("%Y-%m-%d " + self.timestamp_format)
        return now.strftime(self.timestamp_format)
    
    def _format_message(
        self,
        level: LogLevel,
        message: str,
        emoji_override: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Format log message for console and file
        
        Returns:
            Tuple of (console_message, file_message)
        """
        timestamp = self._get_timestamp()
        
        # Get emoji
        if emoji_override:
            emoji = emoji_override
        elif self.use_emojis:
            emoji = LogConfig.EMOJIS.get(level, "•")
        else:
            emoji = ""
        
        # Console message (with colors)
        if self.use_colors:
            color = LogConfig.LEVEL_COLORS.get(level, "")
            console_msg = (
                f"{Colors.DIM}[{timestamp}]{Colors.RESET} "
                f"{emoji} "
                f"{color}{message}{Colors.RESET}"
            )
        else:
            console_msg = f"[{timestamp}] {emoji} {message}"
        
        # File message (plain text)
        level_name = level.name.ljust(8)
        file_msg = f"[{timestamp}] [{level_name}] {message}"
        
        return console_msg, file_msg
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        emoji_override: Optional[str] = None
    ):
        """Internal log method"""
        # Check minimum level
        if level.value < self.min_level.value:
            return
        
        console_msg, file_msg = self._format_message(level, message, emoji_override)
        
        # Print to console
        print(console_msg)
        
        # Write to file
        if self._file_handle:
            try:
                self._file_handle.write(file_msg + "\n")
                self._file_handle.flush()
            except:
                pass
    
    # =========================================================================
    # STANDARD LOG METHODS
    # =========================================================================
    
    def debug(self, message: str):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message)
    
    def info(self, message: str):
        """Log info message"""
        self._log(LogLevel.INFO, message)
    
    def success(self, message: str):
        """Log success message"""
        self._log(LogLevel.SUCCESS, message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._log(LogLevel.WARNING, message)
    
    def error(self, message: str):
        """Log error message"""
        self._log(LogLevel.ERROR, message)
    
    def critical(self, message: str):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message)
    
    # =========================================================================
    # SPECIAL LOG METHODS (With custom emojis)
    # =========================================================================
    
    def working(self, message: str):
        """Log working/processing message"""
        self._log(LogLevel.INFO, message, "⚡")
    
    def waiting(self, message: str):
        """Log waiting message"""
        self._log(LogLevel.INFO, message, "⏳")
    
    def download(self, message: str):
        """Log download message"""
        self._log(LogLevel.INFO, message, "📥")
    
    def upload(self, message: str):
        """Log upload message"""
        self._log(LogLevel.INFO, message, "📤")
    
    def search(self, message: str):
        """Log search message"""
        self._log(LogLevel.INFO, message, "🔎")
    
    def bypass(self, message: str):
        """Log bypass message"""
        self._log(LogLevel.INFO, message, "🚀")
    
    def telegram(self, message: str):
        """Log telegram message"""
        self._log(LogLevel.INFO, message, "📱")
    
    def database(self, message: str):
        """Log database message"""
        self._log(LogLevel.INFO, message, "🗄️")
    
    def cache(self, message: str):
        """Log cache message"""
        self._log(LogLevel.INFO, message, "💾")
    
    def user(self, message: str):
        """Log user message"""
        self._log(LogLevel.INFO, message, "👤")
    
    def admin(self, message: str):
        """Log admin message"""
        self._log(LogLevel.INFO, message, "👑")
    
    def bot(self, message: str):
        """Log bot message"""
        self._log(LogLevel.INFO, message, "🤖")
    
    def movie(self, message: str):
        """Log movie message"""
        self._log(LogLevel.INFO, message, "🎬")
    
    def series(self, message: str):
        """Log series message"""
        self._log(LogLevel.INFO, message, "📺")
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def separator(self, char: str = "=", length: int = 60):
        """Print a separator line"""
        print(char * length)
    
    def blank(self):
        """Print a blank line"""
        print()
    
    def header(self, title: str, char: str = "=", length: int = 60):
        """Print a header with title"""
        self.separator(char, length)
        padding = (length - len(title) - 2) // 2
        print(f"{char}{' ' * padding}{title}{' ' * padding}{char}")
        self.separator(char, length)
    
    def box(self, message: str, char: str = "─", corner: str = "┌┐└┘"):
        """Print message in a box"""
        lines = message.split('\n')
        max_len = max(len(line) for line in lines)
        
        print(f"{corner[0]}{char * (max_len + 2)}{corner[1]}")
        for line in lines:
            print(f"│ {line.ljust(max_len)} │")
        print(f"{corner[2]}{char * (max_len + 2)}{corner[3]}")
    
    def set_level(self, level: LogLevel):
        """Change minimum log level"""
        self.min_level = level
    
    def close(self):
        """Close logger and file handle"""
        self._close_file()
    
    def __del__(self):
        """Destructor - close file handle"""
        self._close_file()


# =============================================================================
# GLOBAL LOGGER INSTANCE
# =============================================================================

# Create default logger
_default_logger = Logger(
    name="BollyFlix",
    min_level=LogLevel.DEBUG,
    use_colors=True,
    use_emojis=True,
    log_file="bollyflix.log"
)


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

def log_admin(message: str):
    """Log admin message"""
    _default_logger.admin(message)


def log_debug(message: str):
    """Log debug message"""
    _default_logger.debug(message)

def log_info(message: str):
    """Log info message"""
    _default_logger.info(message)

def log_success(message: str):
    """Log success message"""
    _default_logger.success(message)

def log_warning(message: str):
    """Log warning message"""
    _default_logger.warning(message)

def log_error(message: str):
    """Log error message"""
    _default_logger.error(message)

def log_critical(message: str):
    """Log critical message"""
    _default_logger.critical(message)

def log_working(message: str):
    """Log working message"""
    _default_logger.working(message)

def log_waiting(message: str):
    """Log waiting message"""
    _default_logger.waiting(message)

def log_download(message: str):
    """Log download message"""
    _default_logger.download(message)

def log_search(message: str):
    """Log search message"""
    _default_logger.search(message)

def log_bypass(message: str):
    """Log bypass message"""
    _default_logger.bypass(message)

def log_telegram(message: str):
    """Log telegram message"""
    _default_logger.telegram(message)

def log_database(message: str):
    """Log database message"""
    _default_logger.database(message)

def log_user(message: str):
    """Log user message"""
    _default_logger.user(message)

def log_bot(message: str):
    """Log bot message"""
    _default_logger.bot(message)

def log_movie(message: str):
    """Log movie message"""
    _default_logger.movie(message)

def log_series(message: str):
    """Log series message"""
    _default_logger.series(message)

# Aliases for backward compatibility
log_failed = log_error


# =============================================================================
# GET/SET DEFAULT LOGGER
# =============================================================================

def get_logger() -> Logger:
    """Get the default logger instance"""
    return _default_logger

def set_logger(logger: Logger):
    """Set a custom default logger"""
    global _default_logger
    _default_logger = logger

def create_logger(
    name: str = "Bot",
    log_file: Optional[str] = None,
    min_level: LogLevel = LogLevel.DEBUG
) -> Logger:
    """Create a new logger instance"""
    return Logger(
        name=name,
        log_file=log_file,
        min_level=min_level
    )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Demo the logger
    log = Logger("Demo")
    
    log.header("BOLLYFLIX BOT LOGGER DEMO")
    log.blank()
    
    # Standard levels
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.success("This is a success message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.critical("This is a critical message")
    
    log.blank()
    log.separator("-")
    log.blank()
    
    # Special types
    log.working("Processing bypass...")
    log.waiting("Waiting for response...")
    log.download("Downloading file...")
    log.search("Searching for movie...")
    log.bypass("Bypassing OzoLinks...")
    log.telegram("Sending to Telegram...")
    log.database("Saving to database...")
    log.movie("Found: Avengers Endgame")
    log.series("Found: Money Heist S01")
    log.user("User 123456 started bot")
    log.admin("Admin logged in")
    
    log.blank()
    log.separator()
    
    # Test module-level functions
    log_info("Using module-level function")
    log_success("All tests passed!")