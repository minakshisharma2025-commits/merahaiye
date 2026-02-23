import os
import re

CONFIG_FILE = "config.py"

# Strictly define which keys are safe to parse and edit from the UI.
# This prevents the regex from corrupting os.environ calls, multiline strings, lists, or dicts.
EDITABLE_KEYS = {
    "BOT_TOKEN": str,
    "BOT_NAME": str,
    "BOT_VERSION": str,
    "MAX_LOGIN_ATTEMPTS": int,
    "MAX_CACHE_AGE_HOURS": int,
    "MAX_SEARCH_LOG": int,
    "MAX_DOWNLOAD_LOG": int,
    "FREE_DAILY_LIMIT": int,
    "PREMIUM_DAILY_LIMIT": int,
    "BOLLYFLIX_BASE_URL": str,
    "MAX_SEARCH_RESULTS": int,
    "REQUEST_TIMEOUT": int,
    "BYPASS_TIMEOUT": int,
    "BOT_RESPONSE_TIMEOUT": int,
    "MAX_RETRIES": int,
    "RETRY_DELAY": int,
    "WELCOME_IMAGE_ENABLED": bool
}

def get_config_vars():
    """Reads only the whitelisted safe configuration variables by parsing config.py"""
    if not os.path.exists(CONFIG_FILE):
        return {}
        
    config_dict = {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        match = re.match(r'^([A-Z0-9_]+)\s*=\s*(.+)$', line)
        if match:
            key = match.group(1)
            if key not in EDITABLE_KEYS:
                continue
                
            val_str = match.group(2).strip()
            
            # Remove inline comments if not inside string
            if ' #' in val_str:
                val_str = val_str.split(' #')[0].strip()
                
            # Strip quotes for strings
            if val_str.startswith('"') and val_str.endswith('"'):
                val_str = val_str[1:-1]
            elif val_str.startswith("'") and val_str.endswith("'"):
                val_str = val_str[1:-1]
                
            config_dict[key] = val_str
            
    return config_dict

def update_config_vars(updates: dict):
    """Updates config.py with only whitelisted keys, preserving formatting safely"""
    if not os.path.exists(CONFIG_FILE):
        return False
        
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            match = re.match(r'^([A-Z0-9_]+)\s*=\s*(.+)$', stripped)
            if match:
                key = match.group(1)
                
                if key in updates and key in EDITABLE_KEYS:
                    new_val = updates[key]
                    expected_type = EDITABLE_KEYS[key]
                    
                    # Format correctly for Python syntax
                    if expected_type == str:
                        formatted_val = f'"{new_val}"'
                    elif expected_type == bool:
                        formatted_val = "True" if str(new_val).lower() == "true" else "False"
                    else: # int
                        try:
                            formatted_val = str(int(new_val))
                        except ValueError:
                            formatted_val = match.group(2) # fallback to original
                            
                    # Maintain existing indentation
                    indent = line[:len(line) - len(line.lstrip())]
                    line = f"{indent}{key} = {formatted_val}\n"
        
        new_lines.append(line)
        
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    return True
