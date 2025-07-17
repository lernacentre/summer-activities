import streamlit as st
import json
import base64
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
import time
import random
import hashlib
import os

# ------------------------------
# Session state initialization
# ------------------------------
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

# ------------------------------
# S3 Configuration (connect after login)
# ------------------------------
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

# ------------------------------
# Load student names from TXT in GitHub repo
# ------------------------------
@st.cache_data(show_spinner=False)
def get_all_students():
    """
    Scan all groups in Summer_Activities folder (in GitHub repo)
    and build a student-to-group mapping from TXT files.
    """
    base_path = "summer_activities"
    student_to_group = {}

    for group_folder in os.listdir(base_path):
        group_path = os.path.join(base_path, group_folder)
        if os.path.isdir(group_path) and group_folder.lower().startswith("group"):
            txt_file = os.path.join(group_path, f"{group_folder}_passwords.txt")
            if os.path.exists(txt_file):
                with open(txt_file, "r") as f:
                    for line in f:
                        if ":" in line:
                            name, _ = line.strip().split(":", 1)
                            name = name.strip().lower()
                            student_to_group[name] = group_folder
    return student_to_group

# ------------------------------
# Load hashed passwords from JSON in GitHub repo
# ------------------------------
@st.cache_data(show_spinner=False)
def load_passwords(group_folder):
    password_file = os.path.join("Summer_Activities", group_folder, "passwords.json")
    with open(password_file, "r") as f:
        passwords = json.load(f)
    return passwords

# ------------------------------
# Helper function: Hash password
# ------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------------------
# Add custom CSS for animations
# ------------------------------
def add_custom_css():
    st.markdown("""
    <style>
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes confetti {
        0% { transform: translateY(0) rotate(0deg); opacity: 1; }
        100% { transform: translateY(300px) rotate(720deg); opacity: 0; }
    }
    .welcome-animation {
        animation: fadeIn 1s ease-out;
    }
    .completion-animation {
        animation: fadeIn 0.8s ease-out;
    }
    .confetti {
        position: fixed;
        width: 10px;
        height: 10px;
        background-color: #f0f;
        animation: confetti 3s ease-out;
        animation-fill-mode: forwards;
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------
# Helper function to read files from S3
# ------------------------------
@st.cache_data(show_spinner=False)
def read_s3_file(s3_key):
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except ClientError:
        return None

# ------------------------------
# Play audio without showing controls
# ------------------------------
def play_audio_hidden(s3_key):
    audio_content = read_s3_file(s3_key)
    if audio_content:
        b64 = base64.b64encode(audio_content).decode()
        unique_id = str(time.time()).replace('.', '')
        audio_tag = f"""
            <audio id="audio_{unique_id}" autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                document.getElementById('audio_{unique_id}').play();
            </script>
        """
        st.markdown(audio_tag, unsafe_allow_html=True)
    else:
        st.error("Error playing audio: File not found")

# ------------------------------
# Function to show success animation
# ------------------------------
def show_success_animation(message):
    confetti_html = ""
    colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
    for i in range(20):
        left = random.randint(10, 90)
        delay = random.random() * 0.5
        color = random.choice(colors)
        confetti_html += f"""
        <div class="confetti" style="left: {left}%; animation-delay: {delay}s; background-color: {color};"></div>
        """
    st.markdown(f"""
    <div class="completion-animation">
        <h2 style="text-align: center; color: #4CAF50;">🎉 {message} 🎉</h2>
    </div>
    {confetti_html}
    """, unsafe_allow_html=True)

# ------------------------------
# Function to show welcome animation
# ------------------------------
def show_welcome_animation(student_name):
    st.markdown(f"""
    <div class="welcome-animation">
        <h1 style="text-align: center; color: #2196F3;">
            Welcome, {student_name.title()}! 👋
        </h1>
        <p style="text-align: center; font-size: 1.2em;">
            Ready for today's activities?
        </p>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------
# Main App
# ------------------------------
def main():
    st.title("Student Activities")
    add_custom_css()

    # Load students from GitHub-cloned Summer_Activities folder
    student_to_group = get_all_students()

    if not student_to_group:
        st.error("No students found in Summer_Activities folder in the repo")
        return

    # --------------------
    # Login Screen
    # --------------------
    if not st.session_state.authenticated:
        selected_student = st.selectbox("Select Your Name", sorted(student_to_group.keys()))
        entered_password = st.text_input("Password", type="password")

        if st.button("Login", key="login_button"):
            normalized_student = selected_student.strip().lower()
            group = student_to_group.get(normalized_student)
            if not group:
                st.error("Student not found in any group")
                return

            passwords = load_passwords(group)
            entered_password_hash = hash_password(entered_password)

            if passwords.get(normalized_student) == entered_password_hash:
                st.session_state.authenticated = True
                st.session_state.student = normalized_student
                st.session_state.group = group
                show_welcome_animation(selected_student)
                time.sleep(2)
                st.experimental_rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")

    # --------------------
    # After Login
    # --------------------
    else:
        if st.button("Logout", key="logout_button"):
            st.session_state.clear()
            st.experimental_rerun()

        # Connect to S3 after login
        try:
            global s3, BUCKET_NAME
            s3, BUCKET_NAME = get_s3_client()
            st.success("✅ Connected to S3")
        except Exception as e:
            st.error(f"❌ S3 Connection Error: {e}")
            st.stop()

        student_s3_prefix = f"Summer_Activities/{st.session_state.group}/{st.session_state.student}"

        # Load and display activity packs as before (code unchanged)
        # ...

if __name__ == "__main__":
    main()
