from typing import Any, Generic, TypeVar, Sequence
from sqlmodel import Session, SQLModel, select
from pydantic import BaseModel

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base Repository/Service with default CRUD operations.
    Provides standard implementation for basic database interactions to keep controllers clean.
    """
    def __init__(self, model: type[ModelType]):
        self.model = model

    def get(self, session: Session, id: Any) -> ModelType | None:
        """Fetch a single record by its primary key using a read/replica session."""
        return session.get(self.model, id)

    def get_multi(self, session: Session, *, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Fetch multiple records with pagination using a read/replica session."""
        statement = select(self.model).offset(skip).limit(limit)
        return session.exec(statement).all()

    def create(self, session: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record using a write/primary session."""
        db_obj = self.model.model_validate(obj_in)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

    def update(self, session: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]) -> ModelType:
        """Update an existing record using a write/primary session."""
        obj_data = db_obj.model_dump()
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

    def remove(self, session: Session, *, id: Any) -> ModelType | None:
        """Delete a record by its primary key using a write/primary session."""
        obj = session.get(self.model, id)
        if obj:
            session.delete(obj)
            session.commit()
        return obj
