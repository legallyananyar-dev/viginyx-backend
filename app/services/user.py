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

    def get_by_email(self, session: Session, *, email: str) -> User | None:
        """
        Fetch a user by their email using a read/replica session.
        """
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()

    def get_by_phone_number(self, session: Session, *, phone_number: str) -> User | None:
        """
        Fetch a user by their phone number using a read/replica session.
        """
        statement = select(User).where(User.phone_number == phone_number)
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

    def update(self, session: Session, *, db_obj: User, obj_in: UserUpdate | dict[str, Any]) -> User:
        """
        Custom update logic to handle password hashing.
        Should be used with a write/primary session.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            update_data["hashed_password"] = hashed_password
            del update_data["password"]
            
        return super().update(session, db_obj=db_obj, obj_in=update_data)

# Instantiate a global instance of the service to be used across the app
user_service = UserService(User)
