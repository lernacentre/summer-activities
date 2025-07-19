import streamlit as st
import json
import base64
import boto3
from botocore.exceptions import ClientError
import time
import random

# --- Session State ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_day" not in st.session_state:
    st.session_state.current_day = None
if "completed_days" not in st.session_state:
    st.session_state.completed_days = set()
if "question_page" not in st.session_state:
    st.session_state.question_page = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "opening_audio_played" not in st.session_state:
    st.session_state.opening_audio_played = set()
if "day_started" not in st.session_state:
    st.session_state.day_started = False

# --- S3 Setup ---
@st.cache_resource(show_spinner=False)
def get_s3_client():
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    BUCKET_NAME = "summer-activities-streamli-app"
    BUCKET_REGION = "eu-north-1"

    client = boto3.client(
        's3',
        region_name=BUCKET_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    client.head_bucket(Bucket=BUCKET_NAME)
    return client, BUCKET_NAME

try:
    s3, BUCKET_NAME = get_s3_client()
except Exception as e:
    st.error(f"S3 Error: {e}")
    st.stop()

# --- Helpers ---
@st.cache_data(show_spinner=False)
def read_s3_file(s3_key):
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except ClientError:
        return None

def fix_audio_path(audio_file, student_s3_prefix, current_day):
    if not audio_file or audio_file == "[Path to audio]":
        return None
    if audio_file.startswith("day"):
        return f"{student_s3_prefix}/{audio_file}"
    else:
        return f"{student_s3_prefix}/{current_day}/{audio_file}"

def play_audio_and_trigger_js(s3_key, trigger_id):
    """Play audio and trigger a JS event on audio end"""
    audio_content = read_s3_file(s3_key)
    if audio_content:
        b64 = base64.b64encode(audio_content).decode()
        audio_html = f"""
        <audio id="{trigger_id}_audio" autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
            var audio = document.getElementById("{trigger_id}_audio");
            audio.onended = function() {{
                window.parent.postMessage({{"streamlit_trigger":"{trigger_id}"}}, "*");
            }};
        </script>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

def show_multisensory_modal(script_text):
    """Show a modal popup for multisensory practice"""
    st.markdown(f"""
    <div id="multisensoryModal" style="
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: #fff8e1; border: 3px solid #ff9800; border-radius: 20px;
        padding: 30px; z-index: 9999; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
        <h2 style="color: #ff9800;">🤹 Time to Practice!</h2>
        <p style="font-size: 1.2em; margin-top: 15px;">{script_text}</p>
        <button onclick="document.getElementById('multisensoryModal').remove()" style="
            margin-top: 20px; padding: 10px 20px; background: linear-gradient(45deg, #4ECDC4, #FF6B6B);
            color: white; border: none; border-radius: 10px; font-size: 16px; cursor: pointer;">Got It!</button>
    </div>
    """, unsafe_allow_html=True)

# --- Main App ---
def main():
    st.title("Student Activities")

    # --- Login ---
    if not st.session_state.authenticated:
        st.header("Student Login")
        selected_student = st.text_input("Student Name")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            # For simplicity, accept any non-empty credentials
            if selected_student and password:
                st.session_state.authenticated = True
                st.session_state.student = selected_student
                st.success(f"Welcome, {selected_student}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Enter both name and password")

    # --- After Login ---
    else:
        st.header(f"Welcome back, {st.session_state.student}!")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

        # Simulate S3 prefix
        student_s3_prefix = f"Summer_Activities/Group1/{st.session_state.student}"
        current_day = "day1"

        # Simulate activity content
        teaching_audio_key = fix_audio_path("teach.mp3", student_s3_prefix, current_day)
        multisensory_audio_key = fix_audio_path("multi.mp3", student_s3_prefix, current_day)
        multisensory_script = "Clap your hands and say the word aloud 3 times!"

        teach_key = f"teach_done_{current_day}"
        multi_key = f"multi_done_{current_day}"
        confirm_key = f"practice_confirmed_{current_day}"

        # --- Teach Me Button ---
        if not st.session_state.get(teach_key, False):
            if st.button("📖 Teach Me", key="teach_button"):
                # Play Teach audio and trigger multisensory when done
                play_audio_and_trigger_js(teaching_audio_key, "teach_finished")
                st.session_state[teach_key] = True

        # --- Handle JS Event for Teach Finished ---
        if "_streamlit_trigger" in st.query_params:
            if st.query_params["_streamlit_trigger"] == "teach_finished":
                show_multisensory_modal(multisensory_script)
                play_audio_and_trigger_js(multisensory_audio_key, "multi_finished")
                st.session_state[multi_key] = True
                st.experimental_rerun()

        # --- Confirmation after Multisensory ---
        if st.session_state.get(multi_key, False) and not st.session_state.get(confirm_key, False):
            if st.button("✅ Yes, I practiced!", key="confirm_practice"):
                st.session_state[confirm_key] = True
                st.success("Great job! Now let's move to the questions.")

        # --- Questions Placeholder ---
        if st.session_state.get(confirm_key, False):
            st.markdown("---")
            st.header("📝 Questions")
            st.write("Here come the activity questions...")

if __name__ == "__main__":
    main()
