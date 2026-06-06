from typing import Any
from sqlmodel import Session, select
from app.models.user import User, UserCreate, UserUpdate
from app.services.base import BaseService
from app.core.security import get_password_hash

class UserService(BaseService[User, UserCreate, UserUpdate]):
    """
    User specific repository/service logic.
    Inherits standard CRUD from BaseService and adds custom domain logic.
    """
    
    def get_by_id(self, session: Session, *, user_id: str) -> User | None:
        """
        Fetch a user by their user_id using a read/replica session.
        """
        statement = select(User).where(User.id == user_id)
        return session.exec(statement).first()

    def create(self, session: Session, *, obj_in: UserCreate) -> User:
        """
        Custom create logic to handle password hashing before saving to the DB.
        Should be used with a write/primary session.
        """
        db_obj = User.model_validate(
            obj_in, 
            update={"hashed_password": get_password_hash(obj_in.password)}
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

# Instantiate a global instance of the service to be used across the app
user_service = UserService(User)
