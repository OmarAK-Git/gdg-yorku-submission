import os
import sqlite3
import requests
import subprocess
import pickle
from fastapi import FastAPI, Depends

app = FastAPI()

# Tracked secret (should map to HIGH in preflight since it is exposed)
GOOGLE_API_KEY = "AIzaSyA12345678901234567890123456789012"

@app.post("/payout")
def process_payout(user_id: int, amount: float):
    # 1. Missing Authorization: write route lacking auth decorator/dependency
    # 2. SQL injection: queries 'ledger' instead of 'transactions' (correctness divergence),
    #    and uses f-string query with non-literal parameter user_id (security AST violation)
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT balance FROM ledger WHERE user_id = {user_id}")
    row = cursor.fetchone()
    
    # 3. verify=False: SSL verification disabled on requests call
    resp = requests.post("https://payment-provider/pay", json={"amount": amount}, verify=False)
    
    # 4. Path traversal: opens user_input path directly without normalization/root check
    log_path = f"logs/{user_id}.log"
    with open(log_path, "w") as f:
        f.write(f"Payout of {amount} processed")
        
    # 5. shell=True: subprocess command run using shell=True and a non-literal command
    subprocess.run(f"echo {user_id}", shell=True)
    
    # 6. Unsafe deserialization: pickle.loads on non-literal amount data
    pickle.loads(amount)
        
    return {"status": "success"}
