import os
from datetime import datetime
from auth import get_supabase

# ── Supabase Schema Required ────────────────────────────
# Table: user_profiles
#   id (uuid, primary key, default gen_random_uuid())
#   username (text, unique, not null)
#   full_name (text)
#   email (text)
#   company (text)
#   role (text)
#   created_at (timestamptz, default now())
#   last_login (timestamptz)
#
# Table: analysis_history
#   id (uuid, primary key, default gen_random_uuid())
#   username (text, not null)
#   filename (text)
#   risk_score (int)
#   risk_label (text)
#   high_count (int)
#   medium_count (int)
#   low_count (int)
#   total_clauses (int)
#   analyzed_at (timestamptz, default now())
# ───────────────────────────────────────────────────────


def get_or_create_profile(username):
    """Fetch user profile, create one if it doesn't exist."""
    try:
        supabase = get_supabase()
        result = supabase.table("user_profiles").select("*").eq("username", username).execute()

        if result.data:
            return result.data[0]

        # Create blank profile
        new_profile = {
            "username": username,
            "full_name": "",
            "email": "",
            "company": "",
            "role": "",
            "created_at": datetime.utcnow().isoformat(),
            "last_login": datetime.utcnow().isoformat(),
        }
        supabase.table("user_profiles").insert(new_profile).execute()
        return new_profile

    except Exception as e:
        return {
            "username": username,
            "full_name": "",
            "email": "",
            "company": "",
            "role": "",
            "created_at": datetime.utcnow().isoformat(),
            "last_login": datetime.utcnow().isoformat(),
        }


def update_profile(username, full_name, email, company, role):
    """Update user profile fields."""
    try:
        supabase = get_supabase()
        supabase.table("user_profiles").upsert({
            "username": username,
            "full_name": full_name,
            "email": email,
            "company": company,
            "role": role,
        }).execute()
        return True, "Profile updated successfully."
    except Exception as e:
        return False, f"Update failed: {str(e)}"


def update_last_login(username):
    """Update last login timestamp."""
    try:
        supabase = get_supabase()
        supabase.table("user_profiles").update({
            "last_login": datetime.utcnow().isoformat()
        }).eq("username", username).execute()
    except Exception:
        pass


def save_analysis(username, filename, risk_data, results):
    """Save a contract analysis result to history."""
    try:
        supabase = get_supabase()
        breakdown = risk_data.get("breakdown", {})
        record = {
            "username": username,
            "filename": filename,
            "risk_score": risk_data.get("score", 0),
            "risk_label": risk_data.get("label", ""),
            "high_count": breakdown.get("HIGH", 0),
            "medium_count": breakdown.get("MEDIUM", 0),
            "low_count": breakdown.get("LOW", 0),
            "total_clauses": len(results) if results else 0,
            "analyzed_at": datetime.utcnow().isoformat(),
        }
        supabase.table("analysis_history").insert(record).execute()
        return True
    except Exception:
        return False


def get_analysis_history(username, limit=20):
    """Fetch past analyses for a user."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("analysis_history")
            .select("*")
            .eq("username", username)
            .order("analyzed_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception:
        return []


def get_user_stats(username):
    """Compute aggregate stats from analysis history."""
    history = get_analysis_history(username, limit=100)

    if not history:
        return {
            "total_analyses": 0,
            "avg_risk_score": 0,
            "high_risk_contracts": 0,
            "low_risk_contracts": 0,
            "total_clauses_found": 0,
            "most_recent": None,
        }

    scores = [h["risk_score"] for h in history]
    return {
        "total_analyses": len(history),
        "avg_risk_score": round(sum(scores) / len(scores)),
        "high_risk_contracts": sum(1 for h in history if h["risk_score"] >= 60),
        "low_risk_contracts": sum(1 for h in history if h["risk_score"] < 30),
        "total_clauses_found": sum(h.get("total_clauses", 0) for h in history),
        "most_recent": history[0]["analyzed_at"] if history else None,
    }


def delete_analysis(record_id):
    """Delete a single analysis record."""
    try:
        supabase = get_supabase()
        supabase.table("analysis_history").delete().eq("id", record_id).execute()
        return True
    except Exception:
        return False


def change_password(username, old_password, new_password):
    """Change password after verifying the old one."""
    from auth import hash_password
    try:
        supabase = get_supabase()
        result = supabase.table("users").select("password_hash").eq("username", username).execute()
        if not result.data:
            return False, "User not found."
        if result.data[0]["password_hash"] != hash_password(old_password):
            return False, "Current password is incorrect."
        supabase.table("users").update({
            "password_hash": hash_password(new_password)
        }).eq("username", username).execute()
        return True, "Password changed successfully."
    except Exception as e:
        return False, f"Failed: {str(e)}"
