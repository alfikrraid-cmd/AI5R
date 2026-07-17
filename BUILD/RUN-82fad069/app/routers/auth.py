from fastapi import APIRouter
from app.schemas import LoginRequest, LoginResponse

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    return LoginResponse(access_token="demo-token", token_type="bearer")
