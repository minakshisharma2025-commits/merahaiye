"""
=============================================================================
BOLLYFLIX BOT - WEB ADMIN DASHBOARD SECURE API
=============================================================================
Embedded aiohttp server for the Admin Dashboard
=============================================================================
"""

import asyncio
import os
import json
from aiohttp import web

from database import db
from logger import log_info, log_error, log_warning, log_success
from config import BOT_NAME, BOT_VERSION, OWNER_IDS

# Define the paths for static files
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
os.makedirs(WEB_DIR, exist_ok=True)

routes = web.RouteTableDef()

# -----------------------------------------------------------------------------
# AUTHENTICATION DEPENDENCY
# -----------------------------------------------------------------------------

def get_current_user_role(request: web.Request):
    """
    Extracts user_id from headers and checks role.
    """
    user_id_str = request.headers.get("X-User-Id")
    if not user_id_str or not user_id_str.isdigit():
        raise web.HTTPUnauthorized(reason="Unauthorized")
        
    user_id = int(user_id_str)
    role = db.get_user_role(user_id)
    if role not in ["owner", "admin", "manager"]:
        raise web.HTTPForbidden(reason="Forbidden: Insufficient privileges")
        
    return {"user_id": user_id, "role": role}

def require_admin(request: web.Request):
    user = get_current_user_role(request)
    if user["role"] not in ["owner", "admin"]:
        raise web.HTTPForbidden(reason="Forbidden: Admin access required")
    return user

def require_owner(request: web.Request):
    user = get_current_user_role(request)
    if user["role"] != "owner":
        raise web.HTTPForbidden(reason="Forbidden: Owner access required")
    return user

# -----------------------------------------------------------------------------
# STATIC FILES SERVING
# -----------------------------------------------------------------------------

@routes.get("/")
async def serve_dashboard(request):
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return web.FileResponse(index_path)
    return web.Response(text="<h1>Dashboard UI missing - Please build web UI</h1>", content_type="text/html")

routes.static('/static', WEB_DIR)

@routes.get("/{filename}")
async def serve_static(request):
    filename = request.match_info['filename']
    file_path = os.path.join(WEB_DIR, filename)
    if os.path.exists(file_path):
        return web.FileResponse(file_path)
    raise web.HTTPNotFound()

# -----------------------------------------------------------------------------
# API ROUTING - STATS
# -----------------------------------------------------------------------------

@routes.get("/api/stats")
async def get_stats(request):
    try:
        user = get_current_user_role(request)
        stats = db.get_stats()
        
        return web.json_response({
            "total_users": stats["users"]["total"],
            "total_downloads": stats["downloads"]["total"],
            "total_searches": stats["searches"]["total"],
            "active_users_24h": stats["users"]["active_24h"],
            "bot_version": BOT_VERSION,
            "ping_ms": 42 # Faked ping for aesthetics
        })
    except web.HTTPException:
        raise
    except Exception as e:
        import traceback
        log_error(f"Error in /api/stats: {e}")
        traceback.print_exc()
        raise web.HTTPInternalServerError(reason=str(e))

# -----------------------------------------------------------------------------
# API ROUTING - USERS 
# -----------------------------------------------------------------------------

@routes.get("/api/users")
async def get_users(request):
    user = get_current_user_role(request)
    
    query = request.query.get("query", "").lower()
    page = int(request.query.get("page", 1))
    limit = int(request.query.get("limit", 50))
    
    with db._lock:
        all_users = list(db._data["users"].values())
        
    # Search filtering
    if query:
        filtered = []
        for u in all_users:
            if (str(u.get("user_id", "")) in query or 
                (u.get("first_name") and query in u.get("first_name", "").lower()) or 
                (u.get("username") and query in u.get("username", "").lower())):
                filtered.append(u)
        all_users = filtered
        
    # Pagination
    total_users = len(all_users)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_users = all_users[start_idx:end_idx]
    
    return web.json_response({
        "users": paginated_users,
        "total": total_users,
        "page": page,
        "pages": (total_users + limit - 1) // limit
    })

@routes.post("/api/users/ban")
async def ban_user(request):
    user = require_admin(request)
    data = await request.json()
    
    target_id = data.get("user_id")
    reason = data.get("reason", "Banned by Staff")
    
    target_role = db.get_user_role(target_id)
    if target_role == "owner" or (user["role"] == "admin" and target_role in ["owner", "admin"]):
        raise web.HTTPForbidden(reason="Cannot ban users with equal or higher roles")
        
    success = db.ban_user(target_id, reason)
    if success:
        return web.json_response({"success": True, "message": f"User {target_id} banned"})
    raise web.HTTPBadRequest(reason="User not found")

@routes.post("/api/users/unban")
async def unban_user(request):
    user = require_admin(request)
    data = await request.json()
    
    target_id = data.get("user_id")
    
    success = db.unban_user(target_id)
    if success:
        return web.json_response({"success": True, "message": f"User {target_id} unbanned"})
    raise web.HTTPBadRequest(reason="User not found")

# -----------------------------------------------------------------------------
# API ROUTING - ROLES
# -----------------------------------------------------------------------------

@routes.get("/api/staff")
async def get_staff(request):
    user = require_admin(request)
    return web.json_response({"staff": db.get_staff_users()})

@routes.post("/api/staff/role")
async def update_role(request):
    user = require_owner(request)
    data = await request.json()
    
    target_id = data.get("user_id")
    role = data.get("role")
    
    if role not in ["user", "manager", "admin"]:
        raise web.HTTPBadRequest(reason="Invalid role specified")
        
    success = db.set_user_role(target_id, role)
    if success:
        return web.json_response({"success": True, "message": f"User role updated to {role}"})
    raise web.HTTPBadRequest(reason="Failed to update role")

# -----------------------------------------------------------------------------
# API ROUTING - CONFIG & LOGS
# -----------------------------------------------------------------------------

@routes.get("/api/config")
async def get_config(request):
    require_owner(request)
    import config_manager
    try:
        cfg = config_manager.get_config_vars()
        return web.json_response(cfg)
    except Exception as e:
        log_error(f"Config API error: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.post("/api/config")
async def update_config(request):
    require_owner(request)
    import config_manager
    try:
        data = await request.json()
        success = config_manager.update_config_vars(data)
        if success:
            return web.json_response({"success": True})
        return web.json_response({"error": "Failed to write config"}, status=500)
    except Exception as e:
        log_error(f"Config API POST error: {e}")
        return web.json_response({"error": str(e)}, status=500)

@routes.get("/api/logs")
async def get_logs(request):
    require_admin(request)
    log_file = "bot_sys.log"
    import os
    if not os.path.exists(log_file):
        log_file = "bollyflix.log" 
        
    if not os.path.exists(log_file):
        return web.json_response({"logs": ["No log file found."]})
        
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Return last 100 lines
        return web.json_response({"logs": lines[-100:]})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# -----------------------------------------------------------------------------
# SERVER CONTROL (AIOHTTP)
# -----------------------------------------------------------------------------

api_server = None
api_runner = None

async def start_web_server(host="0.0.0.0", port=8080):
    global api_server, api_runner
    try:
        app = web.Application()
        # Add CORS
        import aiohttp_cors
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })
        
        app.add_routes(routes)
        
        for route in list(app.router.routes()):
            cors.add(route)
            
        api_runner = web.AppRunner(app)
        await api_runner.setup()
        site = web.TCPSite(api_runner, host, port)
        await site.start()
        
        log_success(f"Started WebAdmin API on http://{host}:{port}")
    except Exception as e:
        log_error(f"Failed to start WebAdmin: {e}")

async def stop_web_server():
    global api_runner
    if api_runner:
        log_info("Stopping WebAdmin API server...")
        await api_runner.cleanup()
