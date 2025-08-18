import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from supabase import create_client, Client
import random
from bs4 import BeautifulSoup # Nayi library import karo

# --- IMPORTANT ---
# Keys ab Render ke Environment Variables se aayengi
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ... (Aapka CAREER_MAP, app, aur CORS middleware ka code yahan aayega) ...
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


# --- NAYA: Web Scraper Function ---
def scrape_internshala_jobs():
    url = "https://internshala.com/internships/work-from-home-software-development-internships/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException:
        return [] # Agar website fetch na ho to khaali list bhejo

    soup = BeautifulSoup(response.content, 'html.parser')
    job_listings = []
    
    job_cards = soup.find_all('div', class_='internship_meta')

    for card in job_cards:
        title_element = card.find('h3', class_='heading_4_5')
        company_element = card.find('a', class_='link_display_like_text')
        
        if title_element and company_element:
            title = title_element.text.strip()
            company = company_element.text.strip()
            # Link ke liye hum 'a' tag dhoondhenge jisme job ka title ho
            link_element = title_element.find('a')
            apply_link = "https://internshala.com" + link_element['href'] if link_element else None

            if title and company and apply_link:
                job_listings.append({
                    "title": title,
                    "company_name": company,
                    "location": "Remote",
                    "apply_link": apply_link,
                    "tags": ["Internship", "Software Development"] # Default tags
                })
    return job_listings


# --- NAYA: API Endpoint jo Scraper ko Chalayega ---
@app.post("/scrape-jobs")
def scrape_and_save_jobs():
    # Pehle, database se saare purane links nikal lo taaki duplicate na ho
    try:
        existing_jobs_response = supabase.table('job_postings').select('apply_link').execute()
        existing_links = {job['apply_link'] for job in existing_jobs_response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database se purane jobs fetch nahi ho paaye: {str(e)}")

    # Ab nayi jobs scrape karo
    new_jobs = scrape_internshala_jobs()
    if not new_jobs:
        raise HTTPException(status_code=500, detail="Internshala se jobs scrape nahi ho paaye.")

    # Sirf un jobs ko select karo jo database me pehle se nahi hain
    jobs_to_add = [job for job in new_jobs if job['apply_link'] not in existing_links]

    if not jobs_to_add:
        return {"message": "Koi nayi job nahi mili."}

    # Nayi jobs ko database me daal do
    try:
        response = supabase.table('job_postings').insert(jobs_to_add).execute()
        return {"message": f"{len(response.data)} nayi jobs सफलतापूर्वक (successfully) add ho gayi hain."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database me nayi jobs save nahi ho paayi: {str(e)}")


# ... (Aapke purane endpoints jaise /analyze, /generate-plan, /profile/update, /jobs yahan aayenge) ...
@app.get("/analyze")
def analyze_profile(github_username: str):
    api_url = f"https://api.github.com/users/{github_username}/repos"
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        response = requests.get(api_url, headers=headers)
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
                recommendations.append({
                    "career": career,
                    "score": final_score,
                    "matched_skills": matched_skills,
                    "all_required_skills": skills["required"]
                })
        sorted_recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)
        return sorted_recommendations
    except Exception as e:
        return {"error": str(e)}

@app.post("/generate-plan")
def generate_plan(data: dict):
    user_skills = data.get("user_skills", [])
    target_career = data.get("target_career", {})
    if not user_skills or not target_career:
        return {"error": "User skills and target career are required."}
    required_skills = target_career.get("all_required_skills", [])
    skill_gaps = [skill for skill in required_skills if skill not in user_skills]
    if not skill_gaps:
        return {"plan": [{"title": "You have all the required skills! Great job!", "url": ""}]}
    skill_to_learn = random.choice(skill_gaps)
    try:
        response = supabase.table('learning_resources').select("*").eq('skill_name', skill_to_learn).eq('difficulty', 'Beginner').execute()
        if not response.data:
            return {"plan": [{"title": f"No beginner resources found for {skill_to_learn}. Try searching online!", "url": ""}]}
        learning_plan = []
        for resource in response.data:
            learning_plan.append({
                "title": f"Learn {skill_to_learn}: {resource['title']}",
                "url": resource['url']
            })
        return {"plan": learning_plan}
    except Exception as e:
        return {"error": str(e)}

@app.post("/profile/update")
def update_profile(data: dict):
    user_id = data.get("user_id")
    github_username = data.get("github_username")
    if not user_id or not github_username:
        return {"error": "User ID and GitHub username are required."}
    try:
        response = supabase.table('profiles').update({'github_username': github_username}).eq('id', user_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"error": str(e)}

@app.get("/jobs")
def get_jobs():
    try:
        response = supabase.table('job_postings').select("*").order('id', desc=True).execute() # Naya: Jobs ko naye se purane order me dikhao
        return response.data
    except Exception as e:
        return {"error": str(e)}
