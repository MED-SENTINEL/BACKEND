"""
Auth endpoints for SENTINEL.
Register → Verify Email → Login (JWT) → Get Current User.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import (
    User, RegisterRequest, LoginRequest, VerifyRequest,
    ResendCodeRequest, UserResponse, AuthResponse, MeResponse,
)
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from app.core.config import settings
from app.services.email_service import generate_verification_code, send_verification_email
from app.models.profile import PatientProfile

from fastapi_sso.sso.google import GoogleSSO
from starlette.requests import Request
from fastapi.responses import RedirectResponse

router = APIRouter()

sso = GoogleSSO(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=f"http://localhost:8000/api/auth/google/callback",
    allow_insecure_http=True # For local development
)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    POST /api/auth/register
    Create a new user account and send a verification code.
    """
    # Check existing email
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate password strength
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Generate verification code
    code = generate_verification_code()
    expires = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES)

    # Create user
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        is_verified=not settings.REQUIRE_VERIFICATION,
        verification_code=code,
        verification_expires_at=expires,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    if settings.REQUIRE_VERIFICATION:
        send_verification_email(req.email, code)

    return user


@router.post("/verify", response_model=AuthResponse)
def verify_email(req: VerifyRequest, db: Session = Depends(get_db)):
    """
    POST /api/auth/verify
    Verify email with the 6-digit code. Returns JWT on success.
    """
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")

    # Check code
    if user.verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    # Check expiry
    if user.verification_expires_at and datetime.utcnow() > user.verification_expires_at:
        raise HTTPException(status_code=400, detail="Verification code has expired. Request a new one.")

    # Mark as verified
    user.is_verified = True
    user.verification_code = None
    user.verification_expires_at = None
    db.commit()
    db.refresh(user)

    # Issue token
    token = create_access_token(user.id, user.email)

    return AuthResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/resend-code", status_code=200)
def resend_code(req: ResendCodeRequest, db: Session = Depends(get_db)):
    """
    POST /api/auth/resend-code
    Resend a new verification code to the user's email.
    """
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")

    # Generate new code
    code = generate_verification_code()
    expires = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES)

    user.verification_code = code
    user.verification_expires_at = expires
    db.commit()

    # Send new code
    send_verification_email(req.email, code)

    return {"message": "Verification code sent"}


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    POST /api/auth/login
    Validate credentials and return JWT token.
    """
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check verification
    if settings.REQUIRE_VERIFICATION and not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your email for the verification code.",
        )

    # Issue token
    token = create_access_token(user.id, user.email)

    return AuthResponse(user=UserResponse.model_validate(user), token=token)


@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    GET /api/auth/me
    Returns the current user's auth data merged with their patient profile.
    This gives the frontend blood_type, emergency contacts, etc. in one call.
    """
    # Build base response from user auth fields
    data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_verified": current_user.is_verified,
        "is_onboarded": current_user.is_onboarded,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }

    # Merge profile data if it exists
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == current_user.id).first()
    if profile:
        data.update({
            "gender": profile.gender,
            "date_of_birth": profile.date_of_birth,
            "blood_type": profile.blood_type,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "phone": profile.phone,
            "address": profile.address,
            "emergency_contact_name": profile.emergency_contact_name,
            "emergency_contact_phone": profile.emergency_contact_phone,
            "emergency_contact_relation": profile.emergency_contact_relation,
            "allergies": profile.allergies,
            "past_surgeries": profile.past_surgeries,
        })

    return data


@router.get("/google/login", tags=["Google SSO"])
async def google_login(request: Request):
    """Redirects the user to Google's SSO login page."""
    # Build dynamic redirect URI based on how the user reached the server
    callback_url = str(request.url_for("google_callback"))
    
    # If using reverse-proxy like Render, we must force https
    if "localhost" not in callback_url:
        callback_url = callback_url.replace("http://", "https://")
    
    sso.redirect_uri = callback_url
    
    with sso:
        return await sso.get_login_redirect(params={"prompt": "consent", "access_type": "offline"})


@router.get("/google/callback", tags=["Google SSO"])
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handles the callback from Google SSO."""
    with sso:
        google_user = await sso.verify_and_process(request)
        
    if not google_user or not google_user.email:
        raise HTTPException(status_code=400, detail="Failed to authenticate with Google")

    # Check if user already exists
    user = db.query(User).filter(User.email == google_user.email).first()

    if not user:
        # Create a new user account if they don't exist
        # We generate a random password hash since they use Google
        import secrets
        random_password = secrets.token_urlsafe(32)
        
        user = User(
            email=google_user.email,
            password_hash=hash_password(random_password),
            full_name=google_user.display_name or google_user.email.split('@')[0],
            is_verified=True,  # Google accounts are already verified
            google_id=google_user.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.google_id:
        # Link existing account to Google
        user.google_id = google_user.id
        user.is_verified = True # Auto-verify if they linked Google
        db.commit()
        db.refresh(user)

    # Issue our JWT token
    token = create_access_token(user.id, user.email)
    
    # Redirect back to the frontend with the token
    # We pass the token in the hash fragment or query param so the frontend can grab it
    redirect_url = f"{settings.FRONTEND_URL}/auth/google/callback#token={token}"
    return RedirectResponse(url=redirect_url)
