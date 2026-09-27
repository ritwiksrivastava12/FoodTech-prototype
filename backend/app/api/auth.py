from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import profile_dict
from app.core.database import get_db
from app.core.security import create_token, get_current_user_id, hash_password, verify_password
from app.models.entities import InventoryItem, Profile, User
from app.schemas.schemas import LoginIn, ProfileUpdate, RegisterIn
from app.data.seed_data import DEMO_INVENTORY
from datetime import date, timedelta

router = APIRouter(prefix="/api/auth", tags=["auth"])


def seed_inventory(db: Session, user_id: int):
    for d in DEMO_INVENTORY:
        db.add(InventoryItem(user_id=user_id, name=d["name"], display=d["display"],
                             qty=d["qty"], unit=d["unit"],
                             expiry=date.today() + timedelta(days=d["days"])))


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(400, "An account with this email already exists.")
    u = User(name=body.name.strip(), email=body.email.lower().strip(),
             phone=body.phone, password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    db.add(Profile(user_id=u.id))
    seed_inventory(db, u.id)
    db.commit()
    return {"token": create_token(u.id), "user": {"id": u.id, "name": u.name, "email": u.email}}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email.lower()).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password.")
    return {"token": create_token(u.id), "user": {"id": u.id, "name": u.name, "email": u.email}}


@router.get("/me")
def me(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(404, "User not found")
    return {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone,
            "profile": profile_dict(db, uid)}


router2 = APIRouter(prefix="/api/profile", tags=["profile"])


@router2.get("")
def get_profile(uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return profile_dict(db, uid)


@router2.put("")
def update_profile(body: ProfileUpdate, uid: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == uid).first()
    if not p:
        p = Profile(user_id=uid)
        db.add(p)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            if k in ("allergies", "disliked", "favorites_food", "cuisines", "equipment") and isinstance(v, list):
                v = [str(x).strip().lower() for x in v if str(x).strip()]
            setattr(p, k, v)
    db.commit()
    return profile_dict(db, uid)
