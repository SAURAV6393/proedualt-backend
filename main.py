import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from supabase import create_client, Client

# --- IMPORTANT ---
# Make sure your Supabase URL and Key are here
SUPABASE_URL = "https://kutzcpkonzplozbgucng.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzII1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt1dHpjcGtvbnpwbG96Ymd1Y25nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTUzMjM0NTIsImV4cCI6MjA3MDg5OTQ1Mn0.1qCpi-u4StISx3dyPHF-f8tDOnw4Lu0JJgq9kJuTCgQ"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# DEFINE JOB ROLES AND THEIR SKILLS
CAREER_MAP = {
    "Frontend Developer": {
        "required": ["JavaScript", "HTML", "CSS", "TypeScript", "Vue", "Svelte", "Stylus"],
        "weight": 1.0
    },
    "Backend Developer": {
        "required": ["Python", "Java", "Go", "Ruby", "PHP", "C++", "C#", "Kotlin", "Rust"],
        "weight": 1.0
    },
    "Data Scientist / ML Engineer": {
        "required": ["Python", "Jupyter Notebook", "R"],
        "weight": 1.5
    },
    "Mobile App Developer": {
        "required": ["Dart", "Kotlin", "Java", "Swift", "Objective-C"],
        "weight": 1.0
    },
    "DevOps Engineer": {
        "required": ["Shell", "Go", "Python", "Dockerfile", "PowerShell"],
        "weight": 1.0
    }
}

app = FastAPI()

# CORS Middleware
origins = [ "http://localhost:3000", ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/analyze")
def analyze_profile(github_username: str):
    api_url = f"https://api.github.com/users/{github_username}/repos"
    try:
        response = requests.get(api_url)
        repos = response.json()
        if response.status_code != 200:
            return {"error": "Could not fetch data from GitHub. User might not exist."}
        
        language_counts = {}
        for repo in repos:
            language = repo.get("language")
            if language:
                language_counts[language] = language_counts.get(language, 0) + 1
        
        if not language_counts:
            return {"error": f"No repositories with languages found for user '{github_username}'."}

    except Exception as e:
        return {"error": str(e)}

    user_languages = language_counts.keys()
    recommendations = []
    for career, skills in CAREER_MAP.items():
        score = 0
        matched_skills = []
        for lang in user_languages:
            if lang in skills["required"]:
                score += language_counts[lang]
                matched_skills.append(lang)
        
        final_score = score * skills["weight"]
        
        if final_score > 0:
            recommendations.append({
                "career": career,
                "score": final_score,
                "matched_skills": matched_skills
            })

    sorted_recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)
    return sorted_recommendations

# NEW ENDPOINT TO UPDATE A USER'S PROFILE
@app.post("/profile/update")
def update_profile(data: dict):
    user_id = data.get("user_id")
    github_username = data.get("github_username")

    if not user_id or not github_username:
        return {"error": "User ID and GitHub username are required."}

    try:
        # Update the row in the profiles table where the id matches the user's id
        response = supabase.table('profiles').update({'github_username': github_username}).eq('id', user_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"error": str(e)}

@app.get("/jobs")
def get_jobs():
    try:
        response = supabase.table('job_postings').select("*").execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}
