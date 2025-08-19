import os
import requests
from supabase import create_client, Client
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env file se keys load karne ke liye
load_dotenv()

# --- IMPORTANT ---
# Apni Supabase keys .env file se uthao
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase URL aur Key .env file me nahi mili.")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Supabase se successfully connect ho gaye.")

def scrape_internshala_jobs():
    url = "https://internshala.com/internships/work-from-home-software-development-internships/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print("Internshala se data fetch kar rahe hain...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if "captcha" in response.text.lower():
            print("Error: Internshala ne block kar diya (Captcha mila).")
            return []
    except requests.RequestException as e:
        print(f"Error: Website fetch nahi ho paayi: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    job_listings = []
    
    container = soup.find('div', id='internship_list_container')
    if not container:
        print("Error: Internship container nahi mila. Website ka structure badal gaya hai.")
        return []
        
    job_cards = container.find_all('div', class_='internship_meta')

    for card in job_cards:
        title_element = card.find('h3', class_='heading_4_5')
        company_element = card.find('a', class_='link_display_like_text')
        
        if title_element and company_element:
            title = title_element.text.strip()
            company = company_element.text.strip()
            link_element = title_element.find('a')
            apply_link = "https://internshala.com" + link_element['href'] if link_element else None

            if title and company and apply_link:
                job_listings.append({
                    "title": title,
                    "company_name": company,
                    "location": "Remote",
                    "apply_link": apply_link,
                    "tags": ["Internship", "Software Development"]
                })
    
    print(f"{len(job_listings)} jobs mili.")
    return job_listings

def save_jobs_to_db():
    print("Database se purane jobs check kar rahe hain...")
    try:
        existing_jobs_response = supabase.table('job_postings').select('apply_link').execute()
        existing_links = {job['apply_link'] for job in existing_jobs_response.data}
    except Exception as e:
        print(f"Error: Database se purane jobs fetch nahi ho paaye: {e}")
        return

    new_jobs = scrape_internshala_jobs()
    if not new_jobs:
        return

    jobs_to_add = [job for job in new_jobs if job['apply_link'] not in existing_links]
    if not jobs_to_add:
        print("Koi nayi job nahi mili. Sab kuch up-to-date hai.")
        return

    print(f"{len(jobs_to_add)} nayi jobs database me daal rahe hain...")
    try:
        response = supabase.table('job_postings').insert(jobs_to_add).execute()
        print(f"Success! {len(response.data)} nayi jobs सफलतापूर्वक (successfully) add ho gayi hain.")
    except Exception as e:
        print(f"Error: Database me nayi jobs save nahi ho paayi: {e}")

# --- Script ko yahan se chalao ---
if __name__ == "__main__":
    save_jobs_to_db()
