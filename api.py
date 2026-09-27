from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import hmac
import hashlib
import json
from urllib.parse import parse_qs
from database import (
    get_treasury_balance, get_user_contribution, get_user_stats,
    get_total_business_income, add_transaction, get_user_debts,
    get_all_users_balance, create_user
)
from config import BOT_TOKEN

app = FastAPI()

# CORS для Telegram
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web.telegram.org", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы для веб-приложения
app.mount("/static", StaticFiles(directory="webapp"), name="static")

def validate_telegram_init_data(init_data: str) -> Optional[dict]:
    """Проверяет подпись initData от Telegram"""
    try:
        parsed = parse_qs(init_data)
        hash_value = parsed.get("hash", [None])[0]
        if not hash_value:
            return None

        # Удаляем hash из данных
        data_check_arr = []
        for key, value in parsed.items():
            if key != "hash":
                data_check_arr.append(f"{key}={value[0]}")
        data_check_arr.sort()
        data_check_string = "\n".join(data_check_arr)

        # Создаём секретный ключ
        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Проверяем подпись
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if calculated_hash == hash_value:
            user_data = json.loads(parsed.get("user", [None])[0])
            return user_data
        return None
    except Exception:
        return None

class TransactionRequest(BaseModel):
    user_id: int
    type: str  # deposit или withdraw
    amount: int
    comment: Optional[str] = ""

@app.get("/")
async def root():
    return FileResponse("webapp/index.html")

@app.get("/api/user/{user_id}")
async def get_user_data(user_id: int):
    """Получить данные пользователя"""
    balance = get_treasury_balance()
    contribution = get_user_contribution(user_id)
    stats = get_user_stats(user_id)
    business_income = get_total_business_income()

    share_percent = (contribution / balance * 100) if balance > 0 else 0

    return {
        "totalBalance": balance,
        "myShare": contribution,
        "myPercent": round(share_percent, 1),
        "businessIncome": business_income,
        "totalDeposits": stats["deposits"],
        "totalWithdraws": stats["withdraws"],
        "turnover": stats["turnover"],
        "operations": stats["operations"]
    }

@app.get("/api/treasury")
async def get_treasury_data():
    """Получить данные казны"""
    balance = get_treasury_balance()
    business_income = get_total_business_income()
    users = get_all_users_balance()

    return {
        "totalBalance": balance,
        "businessIncome": business_income,
        "users": [{"userId": u["user_id"], "username": u["username"], "balance": max(0, u["balance"])} for u in users]
    }

@app.post("/api/transaction")
async def create_transaction_endpoint(request: TransactionRequest):
    """Создать транзакцию"""
    if request.type not in ["deposit", "withdraw"]:
        raise HTTPException(status_code=400, detail="Invalid transaction type")

    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    if request.type == "withdraw":
        balance = get_treasury_balance()
        if request.amount > balance:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        user_contribution = get_user_contribution(request.user_id)
        if request.amount > user_contribution:
            raise HTTPException(status_code=400, detail="Insufficient user balance")

    add_transaction(request.user_id, request.type, request.amount, request.comment)

    return {"success": True, "message": "Transaction created"}

@app.get("/api/debts/{user_id}")
async def get_user_debts_endpoint(user_id: int):
    """Получить долги пользователя"""
    debts = get_user_debts(user_id)

    return {
        "owedToMe": [
            {
                "id": d["id"],
                "debtorName": d["debtor_name"],
                "amount": d["amount"],
                "percent": d["percent"],
                "dueDate": d["due_date"],
                "comment": d["comment"]
            }
            for d in debts["owed_to_me"]
        ]
    }

@app.get("/api/validate")
async def validate_init_data(request: Request):
    """Проверить initData от Telegram"""
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data:
        raise HTTPException(status_code=401, detail="No init data")

    user_data = validate_telegram_init_data(init_data)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid init data")

    # Создаём пользователя если его нет
    create_user(user_data["id"], user_data.get("username", "User"))

    return {"userId": user_data["id"], "username": user_data.get("username")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
