from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.db.models import Session


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime
    ):
        session = Session(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self.db.add(session)

        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def get_by_token_hash(
        self,
        token_hash: str,
    ):
        result = await self.db.execute(
            select(Session).where(
                Session.token_hash == token_hash
            )
        )

        return result.scalar_one_or_none()

    async def delete_by_token_hash(
        self,
        token_hash: str,
    ):
        result = await self.db.execute(
            select(Session).where(
                Session.token_hash == token_hash
            )
        )

        session = result.scalar_one_or_none()

        if session is None:
            return False

        await self.db.delete(session)
        await self.db.commit()

        return True

    async def get_active_by_user_id(
        self,
        user_id: int,
    ):
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.expires_at > now,
            )
            .order_by(Session.created_at.desc())
        )

        return result.scalars().all()

    async def delete_by_id_for_user(
        self,
        session_id: int,
        user_id: int,
    ):
        result = await self.db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
        )

        session = result.scalar_one_or_none()

        if session is None:
            return False

        await self.db.delete(session)
        await self.db.commit()

        return True

    async def delete_other_for_user(
        self,
        user_id: int,
        current_session_id: int,
    ):
        result = await self.db.execute(
            select(Session).where(
                Session.user_id == user_id,
                Session.id != current_session_id,
            )
        )

        sessions = result.scalars().all()

        for session in sessions:
            await self.db.delete(session)

        await self.db.commit()

        return len(sessions)