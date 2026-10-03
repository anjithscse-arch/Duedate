# DueDate 📅

A Streamlit chat app that reads deadlines from photos of syllabi,
timetables and assignment sheets using Gemini vision, then emails
you a sorted digest.

## Features
- Upload a photo or type your deadlines
- Gemini extracts every date and never invents one
- Politely handles photos with no deadlines
- One click emails you a digest, soonest first

## Run locally
1. `python -m venv venv` and activate it
2. `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
   and fill in your Gemini API key and Gmail App Password
4. `streamlit run app.py`

## Tech
Streamlit, Google Gemini (google-genai), Gmail SMTP

## Live app
(add your Streamlit link here after deploying)