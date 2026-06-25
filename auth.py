import hashlib
import os
from supabase import create_client

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    try:
        supabase = get_supabase()
        # Check if username exists
        existing = supabase.table("users").select("username").eq("username", username).execute()
        if existing.data:
            return False, "Username already exists."
        
        # Insert new user
        supabase.table("users").insert({
            "username": username,
            "password_hash": hash_password(password)
        }).execute()
        return True, "Account created successfully!"
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def login_user(username, password):
    try:
        supabase = get_supabase()
        result = supabase.table("users").select("*").eq("username", username).execute()
        
        if not result.data:
            return False, "Username not found."
        
        user = result.data[0]
        if user["password_hash"] != hash_password(password):
            return False, "Incorrect password."
        
        return True, "Login successful!"
    except Exception as e:
        return False, f"Login failed: {str(e)}"
