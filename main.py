import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from supabase import create_client, Client
import random
import google.generativeai as genai # Nayi library import karo

# --- Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") # Nayi key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Gemini AI ko configure karo
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# CAREER_MAP, app, aur CORS middleware
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

# --- NAYA: AI Mentor Chatbot Endpoint ---
@app.post("/ask-mentor")
def ask_mentor(data: dict):
    question = data.get("question")
    user_skills = data.get("user_skills", [])

    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured on the server.")

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Ek behtar prompt banate hain jisme user ki skills bhi shamil hon
        prompt = f"""
        You are "ProEduAlt Mentor," an expert career counselor for software engineering students.
        A student with the following skills: {', '.join(user_skills) if user_skills else 'no specific skills listed'} has asked a question.
        
        Question: "{question}"
        
        Your answer should be helpful, encouraging, and directly related to the student's question and their skill level.
        Provide actionable advice. Keep the response concise and easy to understand.
        """
        
        response = model.generate_content(prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with Gemini API: {str(e)}")


# --- Purane Endpoints ---
@app.get("/analyze/{user_id}")
def analyze_profile(user_id: str):
    try:
        profile_response = supabase.table('profiles').select('github_username, resume_skills').eq('id', user_id).single().execute()
        profile_data = profile_response.data
        if not profile_data or not profile_data.get('github_username'):
            return {"error": "GitHub username not found for this user."}
        github_username = profile_data['github_username']
        resume_skills = set(profile_data.get('resume_skills') or [])
        api_url = f"https://api.github.com/users/{github_username}/repos"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        response = requests.get(api_url, headers=headers)
        repos = response.json()
        if response.status_code != 200: return {"error": "Could not fetch data from GitHub."}
        github_skills = set()
        for repo in repos:
            language = repo.get("language")
            if language: github_skills.add(language)
        combined_skills = list(resume_skills.union(github_skills))
        if not combined_skills: return {"error": "No skills found from GitHub or resume."}
        recommendations = []
        for career, skills in CAREER_MAP.items():
            matched_skills = [skill for skill in combined_skills if skill in skills["required"]]
            if matched_skills:
                score = len(matched_skills) * skills["weight"]
                recommendations.append({"career": career, "score": score, "matched_skills": matched_skills, "all_required_skills": skills["required"]})
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate-plan")
def generate_plan(data: dict):
    user_skills = data.get("user_skills", [])
    target_career = data.get("target_career", {})
    if not user_skills or not target_career: return {"error": "User skills and target career are required."}
    required_skills = target_career.get("all_required_skills", [])
    skill_gaps = [skill for skill in required_skills if skill not in user_skills]
    if not skill_gaps: return {"plan": [{"id": 0, "title": "You have all the required skills! Great job!", "url": "", "xp_points": 0}]}
    skill_to_learn = random.choice(skill_gaps)
    try:
        response = supabase.table('learning_resources').select("id, title, url, xp_points").eq('skill_name', skill_to_learn).eq('difficulty', 'Beginner').execute()
        if not response.data: return {"plan": [{"id": 0, "title": f"No beginner resources found for {skill_to_learn}. Try searching online!", "url": "", "xp_points": 0}]}
        learning_plan = [{"id": r['id'], "title": f"Learn {skill_to_learn}: {r['title']}", "url": r['url'], "xp_points": r['xp_points']} for r in response.data]
        return {"plan": learning_plan}
    except Exception as e:
        return {"error": str(e)}

@app.post("/profile/update")
def update_profile(data: dict):
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
    try:
        response = supabase.table('job_postings').select("*").order('id', desc=True).execute()
        return response.data
    except Exception as e:
        return {"error": str(e)}

@app.get("/learning-progress/{user_id}")
def get_learning_progress(user_id: str):
    try:
        response = supabase.table('user_learning_progress').select('resource_id').eq('user_id', user_id).execute()
        completed_ids = [item['resource_id'] for item in response.data]
        return {"completed_ids": completed_ids}
    except Exception as e:
        return {"error": str(e)}

@app.post("/learning-progress")
def mark_as_complete(data: dict):
    user_id = data.get("user_id")
    resource_id = data.get("resource_id")
    is_complete = data.get("is_complete")
    if not user_id or not resource_id: return {"error": "User ID and Resource ID are required."}
    try:
        resource_response = supabase.table('learning_resources').select('xp_points').eq('id', resource_id).single().execute()
        xp_to_change = resource_response.data.get('xp_points', 0)
        if is_complete:
            supabase.table('user_learning_progress').insert({'user_id': user_id, 'resource_id': resource_id}).execute()
            supabase.rpc('increment_xp', {'user_id_param': user_id, 'xp_param': xp_to_change}).execute()
            return {"success": True, "message": "Progress saved."}
        else:
            supabase.table('user_learning_progress').delete().eq('user_id', user_id).eq('resource_id', resource_id).execute()
            supabase.rpc('increment_xp', {'user_id_param': user_id, 'xp_param': -xp_to_change}).execute()
            return {"success": True, "message": "Progress removed."}
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e): return {"success": True, "message": "Already marked as complete."}
        return {"error": str(e)}
