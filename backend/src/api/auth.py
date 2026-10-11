from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.core.security import (
    check_password,
    create_token,
    hash_password,
    hash_token,
)
from src.db.database import get_db
from src.repositories.session_repository import SessionRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    SessionListResponse,
    SessionResponse,
)
from src.schemas.user_schema import UserResponse
from datetime import datetime, timedelta, timezone


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user_repository = UserRepository(db)

    existing_user = await user_repository.get_by_username(data.username)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists",
        )

    password_hash = hash_password(data.password)

    user = await user_repository.create(
        username=data.username,
        password_hash=password_hash,
    )

    user = await user_repository.get_by_id(user.id)

    return user


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_repository = UserRepository(db)

    user = await user_repository.get_by_username(
        data.username
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    password_correct = check_password(
        data.password,
        user.password_hash,
    )

    if not password_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_token()

    token_hash = hash_token(token)

    session_repository = SessionRepository(db)

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    await session_repository.create(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    return LoginResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user=Depends(get_current_user),
):
    return current_user


async def get_current_session(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession,
):
    token_hash = hash_token(credentials.credentials)
    session_repository = SessionRepository(db)
    session = await session_repository.get_by_token_hash(token_hash)

    if session is None or session.expires_at <= datetime.now(timezone.utc):
        if session is not None:
            await session_repository.delete_by_token_hash(token_hash)

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return session


@router.get(
    "/sessions",
    response_model=SessionListResponse,
)
async def get_sessions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_session = await get_current_session(credentials, db)
    session_repository = SessionRepository(db)
    sessions = await session_repository.get_active_by_user_id(current_user.id)

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=session.id,
                created_at=session.created_at,
                expires_at=session.expires_at,
                is_current=session.id == current_session.id,
            )
            for session in sessions
        ]
    )


@router.delete("/sessions/others")
async def logout_other_sessions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_session = await get_current_session(credentials, db)
    session_repository = SessionRepository(db)
    deleted_count = await session_repository.delete_other_for_user(
        user_id=current_user.id,
        current_session_id=current_session.id,
    )

    return {"message": "Other sessions logged out", "deleted_count": deleted_count}


@router.delete("/sessions/{session_id}")
async def logout_session(
    session_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_session = await get_current_session(credentials, db)
    session_repository = SessionRepository(db)

    if session_id != current_session.id:
        deleted = await session_repository.delete_by_id_for_user(
            session_id=session_id,
            user_id=current_user.id,
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")

        return {"message": "Session logged out"}

    deleted = await session_repository.delete_by_id_for_user(
        session_id=session_id,
        user_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Current session logged out", "current": True}


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials

    token_hash = hash_token(token)

    session_repository = SessionRepository(db)

    deleted = await session_repository.delete_by_token_hash(
        token_hash
    )

    if not deleted:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return {
        "message": "Logout successful"
    }


@router.delete("/account")
async def delete_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.delete(current_user)
    await db.commit()

    return {
        "message": "Account deleted successfully"
    }