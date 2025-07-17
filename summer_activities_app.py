import streamlit as st
import json
import base64
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
import time
import random

# Initialize Streamlit session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False

# Initialize other session state
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

# S3 Configuration
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
    # Test connection
    client.head_bucket(Bucket=BUCKET_NAME)
    return client, BUCKET_NAME

try:
    s3, BUCKET_NAME = get_s3_client()
    st.success("✅ Connected to S3")
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
    st.info("Please add AWS credentials to Streamlit secrets")
    st.stop()
except ClientError as e:
    st.error(f"❌ S3 Connection Error: {e}")
    st.info("Check your AWS credentials and bucket name")
    st.stop()
except Exception as e:
    st.error(f"❌ Unexpected error: {e}")
    st.stop()

# Add custom CSS for animations
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

# Helper function to read files from S3
@st.cache_data(show_spinner=False)
def read_s3_file(s3_key):
    """Read a file from S3 and return its content"""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except ClientError:
        return None

# Get all students from all groups
@st.cache_data(show_spinner=False)
def get_all_students():
    student_to_group = {}
    base_prefix = "Summer_Activities/"
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=BUCKET_NAME,
            Prefix=base_prefix
        )
        
        all_keys = []
        for page in pages:
            if 'Contents' in page:
                all_keys.extend([obj['Key'] for obj in page['Contents']])
        
        for key in all_keys:
            parts = key.split('/')
            if len(parts) >= 3:
                group = parts[1]
                potential_student = parts[2]
                if not group.startswith("Group"):
                    continue
                if potential_student in ["passwords.json", ""] or potential_student.endswith("_passwords.txt"):
                    continue
                if len(parts) >= 4 and parts[3].startswith("day"):
                    if potential_student not in student_to_group:
                        student_to_group[potential_student] = group
        return student_to_group
        
    except ClientError as e:
        st.error(f"Error accessing S3: {e}")
        return {}

# Fix audio paths
def fix_audio_path(audio_file, student_s3_prefix, current_day):
    if not audio_file or audio_file == "[Path to audio]":
        return None
    if audio_file.startswith("day"):
        return f"{student_s3_prefix}/{audio_file}"
    else:
        return f"{student_s3_prefix}/{current_day}/{audio_file}"

# Load passwords
@st.cache_data(show_spinner=False)
def load_passwords(group_folder):
    passwords = {}
    password_json_key = f"Summer_Activities/{group_folder}/passwords.json"
    content = read_s3_file(password_json_key)
    if content:
        try:
            passwords = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError:
            st.warning(f"Could not parse passwords.json for {group_folder}")

    group_password_key = f"Summer_Activities/{group_folder}/{group_folder}_passwords.txt"
    txt_content = read_s3_file(group_password_key)
    if txt_content:
        lines = txt_content.decode('utf-8').strip().split('\n')
        for line in lines:
            if ':' in line and not line.startswith('=') and not line.startswith('GROUP'):
                parts = line.split(':')
                if len(parts) == 2:
                    student_name = parts[0].strip()
                    password = parts[1].strip()
                    passwords[student_name] = password
                    passwords[student_name.lower()] = password
    return passwords

# Play audio hidden
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
        st.error(f"Error playing audio: File not found")

# Show animations
def show_success_animation(message):
    confetti_html = ""
    colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
    for i in range(20):
        left = random.randint(10, 90)
        delay = random.random() * 0.5
        color = random.choice(colors)
        confetti_html += f"""
        <div class="confetti" style="left: {left}%;
             animation-delay: {delay}s;
             background-color: {color};"></div>
        """
    st.markdown(f"""
    <div class="completion-animation">
        <h2 style="text-align: center; color: #4CAF50;">🎉 {message} 🎉</h2>
    </div>
    {confetti_html}
    """, unsafe_allow_html=True)

def show_welcome_animation(student_name):
    st.markdown(f"""
    <div class="welcome-animation">
        <h1 style="text-align: center; color: #2196F3;">
            Welcome, {student_name}! 👋
        </h1>
        <p style="text-align: center; font-size: 1.2em;">
            Ready for today's activities?
        </p>
    </div>
    """, unsafe_allow_html=True)

# Main app
def main():
    st.title("Student Activities")
    add_custom_css()

    student_to_group = get_all_students()
    if not student_to_group:
        st.error("No students found")
        return

    if not st.session_state.authenticated:
        st.header("Student Login")
        selected_student = st.selectbox("Select Student", sorted(student_to_group.keys()))
        password = st.text_input("Password", type="password")
        if st.button("Login", key="login_button"):
            group = student_to_group[selected_student]
            passwords = load_passwords(group)
            possible_names = [
                selected_student,
                selected_student.lower(),
                selected_student.capitalize(),
                selected_student.upper(),
            ]
            correct_password = None
            for name_variant in possible_names:
                if name_variant in passwords:
                    correct_password = passwords[name_variant]
                    break
            if correct_password and correct_password == password:
                st.session_state.authenticated = True
                st.session_state.student = selected_student
                st.session_state.group = group
                st.session_state.welcome_shown = False
                st.rerun()
            elif correct_password:
                st.error("Wrong password")
            else:
                st.error(f"No password found for {selected_student}")

    else:
        # Welcome animation block
        if not st.session_state.welcome_shown:
            st.balloons()
            show_welcome_animation(st.session_state.student)
            st.session_state.welcome_shown = True
            time.sleep(2)
            st.rerun()

        # Logout button
        if st.button("Logout", key="logout_button"):
            st.session_state.clear()
            st.rerun()

        # Main app content goes here
        st.write(f"Welcome back, {st.session_state.student}! 🎉")
        # ... (rest of your existing app code) ...

if __name__ == "__main__":
    main()
