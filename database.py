import sqlite3
from datetime import datetime

DB_PATH = "treasury.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        notifications_enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount INTEGER,
        comment TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creditor_id INTEGER,
        debtor_name TEXT,
        amount INTEGER,
        percent INTEGER DEFAULT 0,
        due_date TEXT,
        status TEXT DEFAULT 'active',
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS business_income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        business_amount INTEGER,
        treasury_amount INTEGER,
        comment TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def get_treasury_balance():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(CASE WHEN type='deposit' THEN amount ELSE -amount END) FROM transactions")
    balance = c.fetchone()[0] or 0
    conn.close()
    return balance

def get_user_contribution(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(CASE WHEN type='deposit' THEN amount WHEN type='withdraw' THEN -amount ELSE 0 END) FROM transactions WHERE user_id = ?", (user_id,))
    contribution = c.fetchone()[0] or 0
    conn.close()
    return contribution

def add_transaction(user_id, type, amount, comment=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (user_id, type, amount, comment) VALUES (?, ?, ?, ?)",
              (user_id, type, amount, comment))
    conn.commit()
    conn.close()

def get_transactions(limit=10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT t.*, u.username 
        FROM transactions t 
        LEFT JOIN users u ON t.user_id = u.user_id 
        ORDER BY date DESC LIMIT ?
    """, (limit,))
    transactions = c.fetchall()
    conn.close()
    return transactions

def get_user_stats(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='deposit'", (user_id,))
    total_deposits = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type='withdraw'", (user_id,))
    total_withdraws = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,))
    total_operations = c.fetchone()[0] or 0
    
    conn.close()
    return {
        "deposits": total_deposits,
        "withdraws": total_withdraws,
        "turnover": total_deposits + total_withdraws,
        "operations": total_operations
    }

def get_all_users_balance():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT 
            u.user_id,
            u.username,
            SUM(CASE WHEN t.type='deposit' THEN t.amount WHEN t.type='withdraw' THEN -t.amount ELSE 0 END) as balance
        FROM users u
        LEFT JOIN transactions t ON u.user_id = t.user_id
        GROUP BY u.user_id
        ORDER BY balance DESC
    """)
    stats = c.fetchall()
    conn.close()
    return stats

def toggle_notifications(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET notifications_enabled = 1 - notifications_enabled WHERE user_id = ?", (user_id,))
    conn.commit()
    c.execute("SELECT notifications_enabled FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_users_with_notifications():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE notifications_enabled = 1")
    users = c.fetchall()
    conn.close()
    return [u["user_id"] for u in users]

def add_debt(creditor_id, debtor_name, amount, percent, due_date, comment=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO debts (creditor_id, debtor_name, amount, percent, due_date, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (creditor_id, debtor_name, amount, percent, due_date, comment))
    conn.commit()
    conn.close()

def get_user_debts(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT * FROM debts
        WHERE creditor_id = ? AND status = 'active'
        ORDER BY created_at DESC
    """, (user_id,))
    owed_to_me = c.fetchall()
    
    conn.close()
    return {"owed_to_me": owed_to_me}

def close_debt(debt_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE debts SET status = 'closed' WHERE id = ? AND creditor_id = ?",
              (debt_id, user_id))
    conn.commit()
    conn.close()

def add_business_income(user_id, business_amount, treasury_amount, comment=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO business_income (user_id, business_amount, treasury_amount, comment) VALUES (?, ?, ?, ?)",
              (user_id, business_amount, treasury_amount, comment))
    conn.commit()
    conn.close()

def get_total_business_income():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(treasury_amount) FROM business_income")
    total = c.fetchone()[0] or 0
    conn.close()
    return total

# Админ-функции
def admin_set_balance(admin_id, new_balance):
    current_balance = get_treasury_balance()
    diff = new_balance - current_balance
    
    if diff != 0:
        add_transaction(admin_id, "deposit" if diff > 0 else "withdraw", abs(diff), "Админ-корректировка")
    
    return new_balance

def admin_set_user_share(user_id, new_share):
    current_share = get_user_contribution(user_id)
    diff = new_share - current_share
    
    if diff != 0:
        add_transaction(user_id, "deposit" if diff > 0 else "withdraw", abs(diff), "Админ-корректировка доли")
    
    return new_share

def admin_add_to_balance(admin_id, amount):
    add_transaction(admin_id, "deposit", amount, "Админ-пополнение")
    return get_treasury_balance()

def admin_reset_all():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM transactions")
    c.execute("DELETE FROM debts")
    c.execute("DELETE FROM business_income")
    conn.commit()
    conn.close()
