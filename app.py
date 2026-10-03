import re
import smtplib
from datetime import date
from email.mime.text import MIMEText

import streamlit as st
from google import genai
from google.genai import types

from prompts import DIGEST_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

MODEL_NAME = "gemini-2.5-flash"
st.set_page_config(page_title="DueDate", page_icon="📅")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GMAIL_ADDRESS = st.secrets["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)


gemini_client = get_gemini_client()

def get_system_prompt():
    return SYSTEM_PROMPT.replace("{today}", date.today().strftime("%d %B %Y"))


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])


def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"


def make_digest():
    """One-off call: reads the chat history but does not add itself to it."""
    try:
        history = st.session_state.chat.get_history()
        request = types.Content(
            role="user", parts=[types.Part(text=DIGEST_REQUEST_PROMPT)]
        )
        response = gemini_client.models.generate_content(
            model=MODEL_NAME,
            contents=history + [request],
            config=types.GenerateContentConfig(system_instruction=get_system_prompt()),
        )
        return response.text
    except Exception:
        return None


def send_email(to_address, user_name, digest):
    try:
        message = MIMEText(f"Hi {user_name},\n\n{digest}\n\n- DueDate 📅", "plain", "utf-8")
        message["Subject"] = "Your DueDate deadline digest"
        message["From"] = GMAIL_ADDRESS
        message["To"] = to_address
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(message)
        return True, "sent"
    except Exception as error:
        return False, str(error)

# ---------- Onboarding ----------
if "onboarded" not in st.session_state:
    st.title("📅 DueDate")
    st.caption("Snap it. Spot it. Never miss it.")
    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        email = st.text_input("Your email", placeholder="you@example.com")
        submitted = st.form_submit_button("Let's go 🚀")
    if submitted:
        valid_email = re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip())
        if not name.strip() or not valid_email:
            st.warning("Please enter your name and a valid email address.")
        else:
            st.session_state.name = name.strip()
            st.session_state.email = email.strip()
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=get_system_prompt()),
            )
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()


header_col, button_col = st.columns([5, 2], vertical_alignment="center")

with header_col:
    st.title("📅 DueDate")

with button_col:
    send_disabled = len(st.session_state.messages) <= 2
    if st.button("📧 Email my deadlines", disabled=send_disabled, use_container_width=True):
        with st.spinner("Building your digest..."):
            digest = make_digest()
        if not digest:
            st.error("Couldn't build the digest. Please try again.")
        else:
            success, info = send_email(st.session_state.email, st.session_state.name, digest)
            if success:
                st.success("Sent! Check your inbox (and spam folder) 📬")
            else:
                st.error(f"Couldn't send that: {info}")


st.caption(f"Logged in as {st.session_state.name} - digest goes to {st.session_state.email}")

if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

user_input = st.chat_input(
    "Type your deadlines, or attach a photo of a syllabus or timetable",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("List every deadline you can find in this image.")

    with st.spinner("Scanning for deadlines..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)
    st.rerun()