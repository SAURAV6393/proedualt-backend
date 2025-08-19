import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import requests
from supabase import create_client, Client
import random
import fitz # PyMuPDF

# --- Environment Variables ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MASTER SKILL LIST ---
# This is the list of skills our app will look for in a resume.
SKILL_LIST = [
    "python", "java", "c++", "c#", "javascript", "typescript", "html", "css", 
    "react", "angular", "vue", "next.js", "node.js", "express", "django", "flask",
    "fastapi", "sql", "mysql", "postgresql", "mongodb", "firebase", "aws", "azure",
    "google cloud", "docker", "kubernetes", "git", "github", "linux", "rest api",
    "graphql", "machine learning", "data science", "pandas", "numpy", "tensorflow",
    "pytorch", "scikit-learn", "swift", "kotlin", "dart", "flutter", "react native"
]

CAREER_MAP = {
    "Frontend Developer": {"required": ["JavaScript", "HTML", "CSS", "React", "TypeScript", "Next.js"],"weight": 1.0},
    "Backend Developer": {"required": ["Python", "Java", "Go", "SQL", "Node.js", "REST API"],"weight": 1.0},
    "Data Scientist / ML Engineer": {"required": ["Python", "SQL", "Machine Learning", "Pandas", "TensorFlow"],"weight": 1.5},
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

# --- Helper function to extract skills from text ---
def extract_skills_from_text(text):
    found_skills = set()
    text_lower = text.lower()
    for skill in SKILL_LIST:
        if skill.lower() in text_lower:
            # Find the original casing if possible (e.g., "Next.js" instead of "next.js")
            original_casing_skill = next((s for s in CAREER_MAP.get("Frontend Developer", {}).get("required", []) + CAREER_MAP.get("Backend Developer", {}).get("required", []) + CAREER_MAP.get("Data Scientist / ML Engineer", {}).get("required", []) if s.lower() == skill.lower()), skill)
            found_skills.add(original_casing_skill)
    return list(found_skills)

# --- UPDATED Resume Upload Endpoint ---
@app.post("/upload-resume/{user_id}")
async def upload_resume(user_id: str, file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    try:
        pdf_document = fitz.open(stream=await file.read(), filetype="pdf")
        text = "".join(page.get_text() for page in pdf_document)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not read text from the PDF.")
        
        # Extract skills from the text
        resume_skills = extract_skills_from_text(text)
        
        # Save the extracted skills to the user's profile in the database
        response = supabase.table('profiles').update({'resume_skills': resume_skills}).eq('id', user_id).execute()
        
        return {"message": "Resume processed successfully!", "skills_found": resume_skills}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


# --- UPDATED Analyze Endpoint ---
@app.get("/analyze/{user_id}")
def analyze_profile(user_id: str):
    try:
        # Fetch user's profile, including GitHub username and resume skills
        profile_response = supabase.table('profiles').select('github_username, resume_skills').eq('id', user_id).single().execute()
        profile_data = profile_response.data
        
        if not profile_data or not profile_data.get('github_username'):
            return {"error": "GitHub username not found for this user."}
            
        github_username = profile_data['github_username']
        resume_skills = set(profile_data.get('resume_skills') or [])

        # Fetch skills from GitHub
        api_url = f"https://api.github.com/users/{github_username}/repos"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        response = requests.get(api_url, headers=headers)
        repos = response.json()
        if response.status_code != 200: return {"error": "Could not fetch data from GitHub."}
        
        github_skills = set()
        for repo in repos:
            language = repo.get("language")
            if language:
                github_skills.add(language)
        
        # Combine skills from resume and GitHub
        combined_skills = list(resume_skills.union(github_skills))
        
        if not combined_skills:
            return {"error": "No skills found from GitHub or resume."}

        # Generate recommendations based on the combined skill set
        recommendations = []
        for career, skills in CAREER_MAP.items():
            matched_skills = [skill for skill in combined_skills if skill in skills["required"]]
            if matched_skills:
                # Simple score: number of matched skills
                score = len(matched_skills) * skills["weight"]
                recommendations.append({
                    "career": career,
                    "score": score,
                    "matched_skills": matched_skills,
                    "all_required_skills": skills["required"]
                })
        
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)

    except Exception as e:
        return {"error": str(e)}

# ... (All other endpoints like /generate-plan, /profile/update, etc. remain the same)
@app.post("/generate-plan")
def generate_plan(data: dict):
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
        if is_complete:
            response = supabase.table('user_learning_progress').insert({'user_id': user_id, 'resource_id': resource_id}).execute()
            return {"success": True, "message": "Progress saved."}
        else:
            response = supabase.table('user_learning_progress').delete().eq('user_id', user_id).eq('resource_id', resource_id).execute()
            return {"success": True, "message": "Progress removed."}
    except Exception as e:
        if "duplicate key value violates unique constraint" in str(e): return {"success": True, "message": "Already marked as complete."}
        return {"error": str(e)}
