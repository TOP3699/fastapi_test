from typing import List

from fastapi import Depends, FastAPI, HTTPException, Header, status
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_session = Depends(get_db)


def get_current_user(
  db: Session = db_session,
  x_api_token: str = Header(None)
):
    if not x_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-TOKEN header")
    user = crud.get_user_by_token(db, x_api_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
    return user


@app.get("/health-check")
def health_check(db: Session = db_session):
    return {"status": "ok"}


@app.post("/users/", response_model=schemas.User)
def create_user(
  user: schemas.UserCreate,
  db: Session = db_session
):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=List[schemas.User])
def read_users(
  skip: int = 0,
  limit: int = 100,
  db: Session = db_session,
  current_user: models.User = Depends(get_current_user)
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(
  user_id: int,
  db: Session = db_session,
  current_user: models.User = Depends(get_current_user)
):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.delete("/users/{user_id}", response_model=schemas.User)
def delete_user(
    user_id: int,
    db: Session = db_session,
    current_user: models.User = Depends(get_current_user)
):
    user = crud.deactivate_user_and_transfer_items(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/users/{user_id}/items/", response_model=schemas.Item)
def create_item_for_user(
    user_id: int,
    item: schemas.ItemCreate,
    db: Session = db_session,
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_user_item(db=db, item=item, user_id=user_id)


@app.get("/items/", response_model=List[schemas.Item])
def read_items(
  skip: int = 0,
  limit: int = 100,
  db: Session = db_session,
  current_user: models.User = Depends(get_current_user)
):
    items = crud.get_items(db, skip=skip, limit=limit)
    return items


@app.get("/me/items", response_model=List[schemas.Item])
def read_my_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = db_session,
    current_user: models.User = Depends(get_current_user)
):
    items = crud.get_items_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return items
