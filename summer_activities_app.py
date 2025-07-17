import streamlit as st
import json
import hashlib
import os
import time
import random

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
# Helper function: Hash password
# ------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ------------------------------
# Load student names from TXT in GitHub repo
# ------------------------------
def get_all_students():
    st.write("📄 Loading student names from Summer_Activities folder...")
    base_path = "Summer_Activities"
    student_to_group = {}

    try:
        if not os.path.exists(base_path):
            st.error(f"❌ Summer_Activities folder not found at path: {base_path}")
            return {}

        for group_folder in os.listdir(base_path):
            group_path = os.path.join(base_path, group_folder)
            st.write(f"📁 Checking folder: {group_folder}")
            if os.path.isdir(group_path) and group_folder.lower().startswith("group"):
                txt_file = os.path.join(group_path, f"{group_folder}_passwords.txt")
                if os.path.exists(txt_file):
                    st.write(f"🔍 Found password file: {txt_file}")
                    with open(txt_file, "r") as f:
                        for line in f:
                            if ":" in line:
                                name, _ = line.strip().split(":", 1)
                                name = name.strip().lower()
                                student_to_group[name] = group_folder
    except Exception as e:
        st.error(f"⚠️ Error loading students: {e}")
    
    if not student_to_group:
        st.warning("⚠️ No students found.")
    else:
        st.write(f"✅ Loaded {len(student_to_group)} students.")
    
    return student_to_group

# ------------------------------
# Load hashed passwords from JSON in GitHub repo
# ------------------------------
def load_passwords(group_folder):
    password_file = os.path.join("Summer_Activities", group_folder, "passwords.json")
    st.write(f"🔐 Loading hashed passwords from {password_file}...")
    try:
        if not os.path.exists(password_file):
            st.error(f"❌ Password file missing for {group_folder}")
            return {}
        with open(password_file, "r") as f:
            passwords = json.load(f)
        st.write(f"✅ Loaded {len(passwords)} passwords.")
        return passwords
    except Exception as e:
        st.error(f"❌ Error loading passwords for {group_folder}: {e}")
        return {}

# ------------------------------
# Connect to S3 lazily (after login)
# ------------------------------
def get_s3_client():
    st.write("🔄 Attempting S3 connection...")
    try:
        import boto3
        from botocore.exceptions import ClientError

        AWS_ACCESS_KEY_ID = st.secrets.get("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = st.secrets.get("AWS_SECRET_ACCESS_KEY")
        BUCKET_NAME = "summer-activities-streamli-app"
        BUCKET_REGION = "eu-north-1"

        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            st.error("❌ Missing AWS credentials in Streamlit secrets.")
            st.stop()

        client = boto3.client(
            's3',
            region_name=BUCKET_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        client.head_bucket(Bucket=BUCKET_NAME)
        st.write("✅ S3 connection successful.")
        return client, BUCKET_NAME
    except ClientError as e:
        st.error(f"❌ S3 ClientError: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected error during S3 connection: {e}")
        st.stop()

# ------------------------------
# Main App
# ------------------------------
def main():
    st.title("Student Activities")
    add_custom_css()

    st.write("🚀 App has started!")
    student_to_group = get_all_students()

    if not student_to_group:
        st.error("No students found in Summer_Activities folder.")
        return

    st.write("📄 Student list loaded.")

    if not st.session_state.authenticated:
        selected_student = st.selectbox("Select Your Name", sorted(student_to_group.keys()))
        entered_password = st.text_input("Password", type="password")

        if st.button("Login"):
            normalized_student = selected_student.strip().lower()
            group = student_to_group.get(normalized_student)
            passwords = load_passwords(group)
            entered_password_hash = hash_password(entered_password)

            st.write("🔑 Verifying password...")
            if passwords.get(normalized_student) == entered_password_hash:
                st.session_state.authenticated = True
                st.session_state.student = normalized_student
                st.session_state.group = group
                st.success(f"🎉 Welcome {selected_student.title()}! Loading your activities...")
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.error("❌ Incorrect password. Try again.")

    else:
        if st.button("Logout"):
            st.session_state.clear()
            st.experimental_rerun()

        st.write("🔗 Connecting to S3...")
        s3, BUCKET_NAME = get_s3_client()

        student_s3_prefix = f"Summer_Activities/{st.session_state.group}/{st.session_state.student}"
        st.write(f"📂 Connected to S3 folder: `{student_s3_prefix}`")
        
        # Placeholder: Add your activity loading logic here
        st.write("🎯 Activities will load here...")

if __name__ == "__main__":
    main()
