# ProEduAlt - Backend 🚀

<!-- Note: You need to upload your logo to a site like Imgur and paste the direct link here -->

This is the backend server for **ProEduAlt**, an AI-powered career guidance platform. This server is responsible for analyzing user data, providing career recommendations, and serving job notifications.

The live frontend for this project can be viewed at: **https://proedualt-frontend.vercel.app/**

---

## ✨ Features

- **GitHub Profile Analysis:** Fetches a user's public repositories and analyzes the programming languages used.
- **Career Recommendation Engine:** Calculates a match score for various tech careers based on the user's skills.
- **Job Listings:** Serves relevant job and internship opportunities from the database.
- **User Profile Management:** Allows users to save and update their personal information, such as their GitHub username.

---

## 🛠️ Tech Stack

- **Framework:** **FastAPI** - A modern, fast (high-performance) web framework for building APIs with Python.
- **Database:** **Supabase (PostgreSQL)** - Used for storing user profiles and job postings.
- **Libraries:**
  - `requests`: For making HTTP requests to the GitHub API.
  - `uvicorn`: For running the ASGI server.
  - `supabase-py`: The official Python client for Supabase.

---

## ⚙️ API Endpoints

Here are the main endpoints provided by this server:

### 1. Analyze GitHub Profile

- **Endpoint:** `GET /analyze`
- **Query Parameter:** `github_username` (string)
- **Description:** Takes a GitHub username and returns a list of career recommendations sorted by match score.
- **Example Request:**
  ```
  [https://proedualt-backend63.onrender.com/analyze?github_username=SAURAV6393](https://proedualt-backend63.onrender.com/analyze?github_username=SAURAV6393)
  ```

### 2. Get Job Listings

- **Endpoint:** `GET /jobs`
- **Description:** Fetches all job postings from the database.
- **Example Request:**
  ```
  [https://proedualt-backend63.onrender.com/jobs](https://proedualt-backend63.onrender.com/jobs)
  ```

### 3. Update User Profile

- **Endpoint:** `POST /profile/update`
- **Description:** Saves or updates a user's GitHub username in the database.
- **Request Body:**
  ```json
  {
    "user_id": "your-supabase-user-id",
    "github_username": "new-github-username"
  }
  ```

---

## 🚀 Local Setup and Installation

To run this project on your local machine, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/SAURAV6393/proedualt-backend.git](https://github.com/SAURAV6393/proedualt-backend.git)
    cd proedualt-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate  # On Windows
    # source .venv/bin/activate    # On macOS/Linux
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables:**
    You need to provide your Supabase keys. Make sure to replace the placeholder values in `main.py`:
    ```python
    SUPABASE_URL = "YOUR_SUPABASE_URL"
    SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"
    ```

5.  **Run the server:**
    ```bash
    python -m uvicorn main:app --reload
    ```
    The server will be running at `http://localhost:8000`.

---

## ☁️ Deployment

This backend is deployed on **Render**. Any changes pushed to the `main` branch will trigger an automatic redeployment.
