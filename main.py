import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from supabase import create_client, Client
import random

# --- Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CAREER_MAP = {
    "Frontend Developer": {"required": ["JavaScript", "HTML", "CSS", "React"],"weight": 1.0},
    "Backend Developer": {"required": ["Python", "Java", "Go", "SQL"],"weight": 1.0},
    "Data Scientist / ML Engineer": {"required": ["Python", "Jupyter Notebook", "SQL"],"weight": 1.5},
}
app = FastAPI()
origins = [ "http://localhost:3000", "https://proedualt-frontend.vercel.app" ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Existing Endpoints (No changes needed) ---
@app.get("/analyze")
def analyze_profile(github_username: str):
    # ... (code is the same)
    api_url = f"https://api.github.com/users/{github_username}/repos"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        response = requests.get(api_url, headers=headers)
        repos = response.json()
        if response.status_code != 200: return {"error": "Could not fetch data from GitHub. User might not exist."}
        language_counts = {}
        for repo in repos:
            language = repo.get("language")
            if language: language_counts[language] = language_counts.get(language, 0) + 1
        if not language_counts: return {"error": f"No repositories with languages found for user '{github_username}'."}
        user_languages = list(language_counts.keys())
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
                recommendations.append({"career": career, "score": final_score, "matched_skills": matched_skills, "all_required_skills": skills["required"]})
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate-plan")
def generate_plan(data: dict):
    # ... (code is the same, but we will add resource IDs to the response)
    user_skills = data.get("user_skills", [])
    target_career = data.get("target_career", {})
    if not user_skills or not target_career: return {"error": "User skills and target career are required."}
    required_skills = target_career.get("all_required_skills", [])
    skill_gaps = [skill for skill in required_skills if skill not in user_skills]
    if not skill_gaps: return {"plan": [{"id": 0, "title": "You have all the required skills! Great job!", "url": ""}]}
    skill_to_learn = random.choice(skill_gaps)
    try:
        response = supabase.table('learning_resources').select("id, title, url").eq('skill_name', skill_to_learn).eq('difficulty', 'Beginner').execute()
        if not response.data: return {"plan": [{"id": 0, "title": f"No beginner resources found for {skill_to_learn}. Try searching online!", "url": ""}]}
        learning_plan = [{"id": resource['id'], "title": f"Learn {skill_to_learn}: {resource['title']}", "url": resource['url']} for resource in response.data]
        return {"plan": learning_plan}
    except Exception as e:
        return {"error": str(e)}

@app.post("/profile/update")
def update_profile(data: dict):
    # ... (code is the same)
    user_id = data.get("user_id")
    github_username = data.get("github_username")
    if not user_id or not github_username: return {"error": "User ID and GitHub username are required."}
    try:
        response = supabase.table('profiles').update({'github_username': github_username}).eq('id', user_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"error": str(e)}

@app.get("/jobs")
def get_jobs():
    # ... (code is the same)
    try:
        response = supabase.table('job_postings').select("*").order('id', desc=True).execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}

# --- NEW ENDPOINTS FOR LEARNING PROGRESS ---

# 1. Endpoint to get a user's completed tasks
@app.get("/learning-progress/{user_id}")
def get_learning_progress(user_id: str):
    try:
        response = supabase.table('user_learning_progress').select('resource_id').eq('user_id', user_id).execute()
        # Return a simple list of completed resource IDs
        completed_ids = [item['resource_id'] for item in response.data]
        return {"completed_ids": completed_ids}
    except Exception as e:
        return {"error": str(e)}

# 2. Endpoint to mark a task as complete
@app.post("/learning-progress")
def mark_as_complete(data: dict):
    user_id = data.get("user_id")
    resource_id = data.get("resource_id")
    is_complete = data.get("is_complete") # True if checking, False if unchecking

    if not user_id or not resource_id:
        return {"error": "User ID and Resource ID are required."}

    try:
        if is_complete:
            # Add a new entry to the progress table
            response = supabase.table('user_learning_progress').insert({
                'user_id': user_id,
                'resource_id': resource_id
            }).execute()
            return {"success": True, "message": "Progress saved."}
        else:
            # Remove the entry from the progress table
            response = supabase.table('user_learning_progress').delete().eq('user_id', user_id).eq('resource_id', resource_id).execute()
            return {"success": True, "message": "Progress removed."}
    except Exception as e:
        # Handle the case where the user tries to complete the same task twice
        if "duplicate key value violates unique constraint" in str(e):
            return {"success": True, "message": "Already marked as complete."}
        return {"error": str(e)}
