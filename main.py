#!/usr/bin/env python3
"""
=============================================================================
BOLLYFLIX BOT - MAIN ENTRY POINT
=============================================================================

🎬 BollyFlix Telegram Bot v3.0
   Complete Movie & Series Download Bot

Features:
   • Movie & Web Series Search
   • Multiple Qualities (480p - 4K)
   • Season-wise Downloads
   • ENI's Ultra Bypass (Timer Nuke)
   • User & Admin Management

Usage:
   python main.py

Author: ENI
=============================================================================
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# =============================================================================
# DEPENDENCY CHECK
# =============================================================================

def check_dependencies() -> bool:
    """
    Check if all required dependencies are installed
    
    Returns:
        True if all dependencies available, False otherwise
    """
    missing = []
    
    # Required packages
    required = [
        ("telegram", "python-telegram-bot"),
        ("requests", "requests"),
        ("bs4", "beautifulsoup4"),
    ]
    
    # Optional packages
    optional = [
        ("undetected_chromedriver", "undetected-chromedriver"),
        ("pyrogram", "pyrogram"),
    ]
    
    print("🔍 Checking dependencies...\n")
    
    # Check required
    for module, package in required:
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (REQUIRED)")
            missing.append(package)
    
    # Check optional
    print()
    for module, package in optional:
        try:
            __import__(module)
            print(f"  ✅ {package} (optional)")
        except ImportError:
            print(f"  ⚠️ {package} (optional - some features disabled)")
    
    print()
    
    if missing:
        print("❌ Missing required packages!")
        print("\n📦 Install with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


# =============================================================================
# CONFIGURATION CHECK
# =============================================================================

def check_configuration() -> bool:
    """
    Check if bot is properly configured
    
    Returns:
        True if configuration valid, False otherwise
    """
    print("⚙️ Checking configuration...\n")
    
    try:
        from config import BOT_TOKEN, OWNER_IDS, API_ID, API_HASH
        
        # Check bot token
        if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
            print("  ❌ BOT_TOKEN not set!")
            print("     Edit config.py and add your bot token")
            return False
        
        if len(BOT_TOKEN) < 40:
            print("  ❌ BOT_TOKEN looks invalid!")
            return False
        
        print(f"  ✅ BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
        
        # Check owner IDs
        if not OWNER_IDS:
            print("  ❌ OWNER_IDS not set!")
            print("     Add your Telegram ID to OWNER_IDS in config.py")
            return False
        
        print(f"  ✅ OWNER_IDS: {OWNER_IDS}")
        
        # Check API credentials (optional)
        if API_ID and API_HASH:
            print(f"  ✅ Pyrogram API configured")
        else:
            print(f"  ⚠️ Pyrogram API not configured (Telegram intercept disabled)")
        
        print()
        return True
        
    except ImportError as e:
        print(f"  ❌ Failed to import config: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """
    Main entry point
    
    - Checks dependencies
    - Validates configuration
    - Starts the bot
    """
    print("\n" + "=" * 60)
    print("🎬 BOLLYFLIX BOT STARTUP")
    print("=" * 60 + "\n")
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed!")
        print("Please install missing packages and try again.")
        sys.exit(1)
    
    print("✅ Dependencies OK!\n")
    print("-" * 60 + "\n")
    
    # Step 2: Check configuration
    if not check_configuration():
        print("\n❌ Configuration check failed!")
        print("Please fix the configuration and try again.")
        sys.exit(1)
    
    print("✅ Configuration OK!\n")
    print("-" * 60 + "\n")
    
    # Step 3: Start the bot
    print("🚀 Starting bot...\n")
    
    try:
        from bot import run_bot
        run_bot()
        
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user (Ctrl+C)")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        
        # Print traceback in debug mode
        import traceback
        traceback.print_exc()
        
        sys.exit(1)


# =============================================================================
# ALTERNATIVE ENTRY POINTS
# =============================================================================

def run_dev():
    """
    Run in development mode with auto-reload
    
    Usage:
        python main.py dev
    """
    print("🔧 Development mode")
    print("⚠️ Auto-reload not implemented yet")
    main()


def run_test():
    """
    Run tests
    
    Usage:
        python main.py test
    """
    print("🧪 Running tests...\n")
    
    # Basic import test
    print("📦 Import tests:")
    
    modules = [
        "config",
        "logger",
        "database",
        "helpers",
        "detectors",
        "scraper",
        "extractors",
        "bypass",
        "handlers",
        "callbacks",
        "user",
        "admin",
        "bot",
    ]
    
    failed = []
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            failed.append(module)
    
    print()
    
    if failed:
        print(f"❌ {len(failed)} module(s) failed to import")
        sys.exit(1)
    else:
        print("✅ All modules imported successfully!")
        
    # Function tests
    print("\n🔧 Function tests:")
    
    try:
        from helpers import format_size, clean_title, generate_stars
        
        # Test format_size
        assert format_size(1024) == "1 KB"
        assert "GB" in format_size(1024 ** 3)
        print("  ✅ format_size()")
        
        # Test clean_title
        title = clean_title("Avengers 2019 1080p WEB-DL")
        assert "WEB-DL" not in title
        print("  ✅ clean_title()")
        
        # Test generate_stars
        stars = generate_stars(7.5)
        assert "⭐" in stars
        print("  ✅ generate_stars()")
        
    except AssertionError as e:
        print(f"  ❌ Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)
    
    try:
        from detectors import detect_content_type, is_series_content
        
        # Test detection
        assert detect_content_type("Money Heist S01-S05") == "series"
        assert detect_content_type("Avengers 2019") == "movie"
        print("  ✅ detect_content_type()")
        
        assert is_series_content("Breaking Bad Complete") == True
        assert is_series_content("Oppenheimer 2023") == False
        print("  ✅ is_series_content()")
        
    except AssertionError as e:
        print(f"  ❌ Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ Error: {e}")
        sys.exit(1)
    
    print("\n✅ All tests passed!")
    sys.exit(0)


def show_help():
    """Show help message"""
    help_text = """
🎬 BOLLYFLIX BOT

Usage:
    python main.py [command]

Commands:
    (none)      Start the bot normally
    dev         Start in development mode
    test        Run tests
    help        Show this help message

Examples:
    python main.py              # Start bot
    python main.py test         # Run tests
    python main.py help         # Show help

Configuration:
    Edit config.py to set:
    • BOT_TOKEN     - Your Telegram bot token
    • OWNER_IDS     - List of owner Telegram IDs
    • API_ID        - Telegram API ID (optional)
    • API_HASH      - Telegram API Hash (optional)

For more information, check the README.md file.
"""
    print(help_text)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ("help", "-h", "--help"):
            show_help()
        elif command in ("test", "-t", "--test"):
            run_test()
        elif command in ("dev", "-d", "--dev"):
            run_dev()
        else:
            print(f"❌ Unknown command: {command}")
            print("Use 'python main.py help' for usage info")
            sys.exit(1)
    else:
        # Normal startup
        main()