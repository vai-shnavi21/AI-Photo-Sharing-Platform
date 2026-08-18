import logging
import os
import secrets
import sys
import time
from urllib.parse import urlencode
from typing import Optional
import requests as http_requests
from fastapi import APIRouter, Depends, File, HTTPException, Header, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from services.auth_service import create_token, hash_password, read_token, verify_password
from services.database import connection

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

router = APIRouter(prefix="/auth", tags=["Authentication"])
CAPTCHAS = {}
GOOGLE_OAUTH_STATES = {}
class SignUp(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    captcha_id: str
    captcha_answer: int
class SignIn(BaseModel): email: EmailStr; password: str
class GoogleSignIn(BaseModel): credential: str
class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    avatar_url: Optional[str] = Field(default=None, max_length=1000)
def user_data(u): return {"id":u["id"],"email":u["email"],"full_name":u["full_name"],"avatar_url":u["avatar_url"]}

def get_google_user(info):
    """Return a Google account, linking a matching verified email on first use."""
    if not info.get("email_verified"):
        raise HTTPException(401, "Google account email is not verified")

    email = info.get("email", "").lower()
    if not email or not info.get("sub"):
        raise HTTPException(401, "Google sign-in did not provide an account identity")

    with connection() as db:
        user = db.execute("SELECT * FROM users WHERE google_id=?", (info["sub"],)).fetchone()
        if not user:
            # An email/password account can safely be linked because Google has
            # verified ownership of the same email address in this request.
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if not user:
                raise HTTPException(401, "Account not found. Please create an account first.")
            if user["google_id"] and user["google_id"] != info["sub"]:
                raise HTTPException(409, "This email is already linked to another Google account")
            db.execute("UPDATE users SET google_id=? WHERE id=?", (info["sub"], user["id"]))
            user = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    
    # Update avatar if available
    if info.get("picture"):
        with connection() as db:
            db.execute(
                "UPDATE users SET avatar_url=? WHERE id=?",
                (info.get("picture"), user["id"])
            )
    
    with connection() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    
    return user


def create_google_user(info):
    """Create new Google user - for signup flow only."""
    if not info.get("email_verified"):
        raise HTTPException(401, "Google account email is not verified")
    
    with connection() as db:
        # Check if user already exists
        existing_user = db.execute(
            "SELECT * FROM users WHERE google_id=? OR email=?",
            (info["sub"], info["email"].lower())
        ).fetchone()
        
        if existing_user:
            # Let an existing email/password account adopt Google sign-in; the
            # caller has just proved ownership of the address with Google.
            if not existing_user["google_id"]:
                db.execute("UPDATE users SET google_id=?, avatar_url=? WHERE id=?", (info["sub"], info.get("picture"), existing_user["id"]))
                return db.execute("SELECT * FROM users WHERE id=?", (existing_user["id"],)).fetchone()
            if existing_user["google_id"] == info["sub"]:
                return existing_user
            raise HTTPException(409, "Account with this email is already linked to another Google account")
        
        # Create new user with Google info
        user = db.execute(
            "INSERT INTO users(email, full_name, avatar_url, google_id) VALUES(?, ?, ?, ?) RETURNING *",
            (info["email"].lower(), info.get("name", "Google User"), info.get("picture"), info["sub"])
        ).fetchone()
    
    return user

def current_user(authorization: str = Header(default="")):
    token = authorization[7:] if authorization.startswith("Bearer ") else None
    user_id = read_token(token) if token else None
    logger.info("current_user: authorization_present=%s token_len=%s resolved_user_id=%s", bool(token), len(token) if token else 0, user_id)
    if not user_id:
        raise HTTPException(401, "Please sign in to continue")
    with connection() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user: raise HTTPException(401, "User not found")
    return user
@router.get("/captcha")
def captcha():
    a,b=secrets.randbelow(8)+1,secrets.randbelow(8)+1; key=secrets.token_urlsafe(24)
    CAPTCHAS[key]=(a+b,time.time()+300)
    return {"captcha_id":key,"question":f"What is {a} + {b}?"}
@router.post("/signup")
def signup(data: SignUp):
    answer=CAPTCHAS.pop(data.captcha_id,None)
    if not answer or answer[1]<time.time() or answer[0]!=data.captcha_answer: raise HTTPException(400,"CAPTCHA answer is invalid or expired")
    try:
        with connection() as db:
            user=db.execute("INSERT INTO users(email,password_hash,full_name) VALUES(?,?,?) RETURNING *",(data.email.lower(),hash_password(data.password),data.full_name.strip())).fetchone()
    except Exception as exc:
        # SQLite reports a UNIQUE error; PostgreSQL reports SQLSTATE 23505.
        if getattr(exc, "sqlstate", None) == "23505" or "unique" in str(exc).lower():
            raise HTTPException(409,"An account with this email already exists") from exc
        raise
    return {"token":create_token(user["id"]),"user":user_data(user)}
@router.post("/signin")
def signin(data: SignIn):
    """Sign in with email and password - requires prior signup."""
    with connection() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (data.email.lower(),)).fetchone()
    
    # Check if user exists
    if not user:
        raise HTTPException(401, "Invalid email or password")
    
    # Check if user has a password hash (prevents Google-OAuth-only accounts from signin)
    if not user["password_hash"]:
        raise HTTPException(401, "This account was not created with an email/password. Please use Google Sign-In or create a new account.")
    
    # Verify password matches
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    
    return {"token": create_token(user["id"]), "user": user_data(user)}
@router.post("/google")
def google(data: GoogleSignIn):
    """Sign in with existing Google account - requires prior signup."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(503, "Google sign-in is not configured on the server")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests
        info = id_token.verify_oauth2_token(data.credential, requests.Request(), client_id)
    except Exception:
        raise HTTPException(401, "Google sign-in could not be verified")
    
    user = get_google_user(info)  # Only gets existing users
    return {"token": create_token(user["id"]), "user": user_data(user)}


@router.post("/google/signup")
def google_signup(data: GoogleSignIn):
    """Sign up with new Google account - creates new account."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(503, "Google sign-up is not configured on the server")
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests
        info = id_token.verify_oauth2_token(data.credential, requests.Request(), client_id)
    except Exception:
        raise HTTPException(401, "Google sign-up could not be verified")
    
    user = create_google_user(info)  # Creates new user
    return {"token": create_token(user["id"]), "user": user_data(user)}

@router.get("/google/login")
def google_login():
    """Redirect to Google for signin - requires existing account."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(503, "Google OAuth is not configured on the server")
    
    state = secrets.token_urlsafe(32)
    GOOGLE_OAUTH_STATES[state] = (time.time() + 600, "signin")  # Store flow type
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@router.get("/google/signup-login")
def google_signup_login():
    """Redirect to Google for signup - creates new account."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(503, "Google OAuth is not configured on the server")
    
    state = secrets.token_urlsafe(32)
    GOOGLE_OAUTH_STATES[state] = (time.time() + 600, "signup")  # Store flow type
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

@router.get("/google/callback")
def google_callback(code: str = Query(...), state: str = Query(...)):
    """Handle Google OAuth callback - supports both signup and signin flows."""
    state_data = GOOGLE_OAUTH_STATES.pop(state, None)
    
    if not state_data:
        raise HTTPException(400, "Google sign-in session is invalid or expired")
    
    expires_at, flow_type = state_data
    
    if expires_at < time.time():
        raise HTTPException(400, "Google sign-in session is invalid or expired")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(503, "Google OAuth is not configured on the server")
    
    logger.info("Processing Google OAuth callback for %s flow", flow_type)
    
    try:
        response = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        
        if response.status_code != 200:
            logger.error(
                "Google token exchange failed with status %s",
                response.status_code,
            )
            raise HTTPException(401, "Google sign-in could not be verified")
        
        token_data = response.json()
        id_token_value = token_data.get("id_token")
        
        if not id_token_value:
            logger.error("Google token response is missing an ID token")
            raise HTTPException(401, "Google sign-in could not be verified")
        
        from google.oauth2 import id_token
        from google.auth.transport import requests
        
        # Verify the ID token with clock skew tolerance
        info = id_token.verify_oauth2_token(
            id_token_value,
            requests.Request(),
            client_id,
            clock_skew_in_seconds=10,
        )
        
    except http_requests.exceptions.RequestException as exc:
        logger.exception("Google token endpoint request failed")
        raise HTTPException(401, "Google sign-in could not be verified")
    except ValueError as exc:
        logger.exception("Google ID token verification failed")
        raise HTTPException(401, "Google sign-in could not be verified")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected Google sign-in callback failure")
        raise HTTPException(401, "Google sign-in could not be verified")
    
    # Handle signup vs signin flows
    if flow_type == "signup":
        user = create_google_user(info)  # Creates new account
    else:  # signin flow
        user = get_google_user(info)  # Gets existing account only
    
    token = create_token(user["id"])
    frontend_url = os.getenv("GOOGLE_OAUTH_SUCCESS_URL")
    
    if frontend_url:
        frontend_url = frontend_url.rstrip("/")
        if not frontend_url.endswith("/signin"):
            frontend_url = f"{frontend_url}/signin"
        return RedirectResponse(f"{frontend_url}#token={token}")
    
    return {"token": token, "user": user_data(user)}

@router.get("/me")
def me(user=Depends(current_user)): return user_data(user)
@router.put("/me")
def update(data:ProfileUpdate,user=Depends(current_user)):
    with connection() as db:
        db.execute("UPDATE users SET full_name=?,avatar_url=? WHERE id=?",(data.full_name.strip(),data.avatar_url or None,user["id"])); updated=db.execute("SELECT * FROM users WHERE id=?",(user["id"],)).fetchone()
    return user_data(updated)

@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(current_user)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Use a JPG, PNG, or WebP image for your profile photo")
    if not all(os.getenv(k) for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")):
        raise HTTPException(503, "Cloudinary is not configured. Add backend/.env credentials.")
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"], api_key=os.environ["CLOUDINARY_API_KEY"], api_secret=os.environ["CLOUDINARY_API_SECRET"], secure=True)
    result = cloudinary.uploader.upload(file.file, folder=f"ai-event-gallery/avatars/user-{user['id']}")
    with connection() as db:
        db.execute("UPDATE users SET avatar_url=? WHERE id=?", (result["secure_url"], user["id"]))
        updated = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    return user_data(updated)
