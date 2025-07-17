import streamlit as st
import json
import base64
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
import time
import random

# Initialize session state
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
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME, 
            Prefix=base_prefix,
            MaxKeys=1000
        )
        if 'Contents' not in response:
            return {}
        all_keys = [obj['Key'] for obj in response['Contents']]
        for key in all_keys:
            parts = key.split('/')
            if len(parts) >= 4:
                if parts[1].startswith("Group") and parts[2] and parts[2] != "passwords.json":
                    group = parts[1]
                    student = parts[2]
                    if student.endswith("_passwords.txt"):
                        continue
                    if student not in student_to_group:
                        student_prefix = f"Summer_Activities/{group}/{student}/"
                        has_days = any(k.startswith(student_prefix + "day") for k in all_keys)
                        if has_days:
                            student_to_group[student] = group
        return student_to_group
    except ClientError as e:
        st.error(f"Error accessing S3: {e}")
        return {}

# Helper function to fix audio paths
def fix_audio_path(audio_file, student_s3_prefix, current_day):
    if not audio_file or audio_file == "[Path to audio]":
        return None
    if audio_file.startswith("day"):
        return f"{student_s3_prefix}/{audio_file}"
    else:
        return f"{student_s3_prefix}/{current_day}/{audio_file}"

# Load passwords - Fixed to handle both JSON and TXT files
@st.cache_data(show_spinner=False)
def load_passwords(group_folder):
    passwords = {}
    
    # Try to load passwords.json first
    password_json_key = f"Summer_Activities/{group_folder}/passwords.json"
    content = read_s3_file(password_json_key)
    if content:
        passwords = json.loads(content.decode('utf-8'))
    
    # Also check for individual password txt files
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=f"Summer_Activities/{group_folder}/",
            MaxKeys=1000
        )
        
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('_passwords.txt'):
                    # Extract student name from filename
                    filename = key.split('/')[-1]
                    student_name = filename.replace('_passwords.txt', '')
                    
                    # Read the password from the txt file
                    txt_content = read_s3_file(key)
                    if txt_content:
                        # The txt file should contain the simple password
                        simple_password = txt_content.decode('utf-8').strip()
                        # Override the JSON password with the simple one from txt
                        passwords[student_name] = simple_password
    
    except ClientError as e:
        st.warning(f"Could not check for individual password files: {e}")
    
    return passwords

# Play audio without showing controls - Fixed for consecutive plays
def play_audio_hidden(s3_key):
    audio_content = read_s3_file(s3_key)
    if audio_content:
        b64 = base64.b64encode(audio_content).decode()
        # Add a unique timestamp to force re-rendering
        unique_id = str(time.time()).replace('.', '')
        audio_tag = f"""
            <audio id="audio_{unique_id}" autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                // Force play in case autoplay is blocked
                document.getElementById('audio_{unique_id}').play();
            </script>
        """
        st.markdown(audio_tag, unsafe_allow_html=True)
    else:
        st.error(f"Error playing audio: File not found")

# Function to show success animation
def show_success_animation(message):
    # Create confetti effect
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

# Function to show welcome animation
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
    
    # Add custom CSS
    add_custom_css()

    # Get all students
    student_to_group = get_all_students()

    if not student_to_group:
        st.error("No students found")
        return

    # Login
    if not st.session_state.authenticated:
        selected_student = st.selectbox("Select Student", sorted(student_to_group.keys()))
        password = st.text_input("Password", type="password")
        if st.button("Login", key="login_button"):
            group = student_to_group[selected_student]
            passwords = load_passwords(group)
            if passwords.get(selected_student) == password:
                st.session_state.authenticated = True
                st.session_state.student = selected_student
                st.session_state.group = group
                st.balloons()  # Streamlit's built-in celebration
                show_welcome_animation(selected_student)
                time.sleep(2)  # Give time to see the animation
                st.experimental_rerun()
            else:
                st.error("Wrong password")

    # After login
    else:
        if st.button("Logout", key="logout_button"):
            st.session_state.clear()
            st.experimental_rerun()

        student_s3_prefix = f"Summer_Activities/{st.session_state.group}/{st.session_state.student}"

        # Load day activity packs (cache them)
        @st.cache_data(show_spinner=False)
        def load_day_packs(student_s3_prefix):
            all_days = []
            day_to_content = {}
            try:
                response = s3.list_objects_v2(
                    Bucket=BUCKET_NAME,
                    Prefix=student_s3_prefix + "/",
                    Delimiter='/'
                )
                day_folders = []
                if 'CommonPrefixes' in response:
                    for prefix in response['CommonPrefixes']:
                        folder_name = prefix['Prefix'].rstrip('/').split('/')[-1]
                        if folder_name.startswith("day"):
                            day_folders.append(folder_name)
                day_folders.sort(key=lambda x: int(x.replace("day", "")))
                for day_folder in day_folders:
                    activity_pack_key = f"{student_s3_prefix}/{day_folder}/activity_pack.json"
                    content = read_s3_file(activity_pack_key)
                    if content:
                        data = json.loads(content.decode('utf-8'))
                        all_days.append(day_folder)
                        day_to_content[day_folder] = data
                return all_days, day_to_content
            except ClientError as e:
                st.error(f"Error loading activities: {e}")
                return [], {}
        
        all_days, day_to_content = load_day_packs(student_s3_prefix)

        if st.session_state.current_day is None and all_days:
            st.session_state.current_day = all_days[0]

        current_day = st.session_state.current_day

        if current_day and current_day in day_to_content:
            day_data = day_to_content[current_day]
            st.header(f"Day: {current_day.replace('day', 'Day ')}")

            for field in day_data['fields']:
                if field.get('type') == 'enhanced_structured_literacy_session':
                    content = field.get('content', {})
                    if current_day not in st.session_state.opening_audio_played:
                        opening_audio = content.get('opening_audio_file', '')
                        audio_s3_key = fix_audio_path(opening_audio, student_s3_prefix, current_day)
                        if audio_s3_key:
                            play_audio_hidden(audio_s3_key)
                            st.session_state.opening_audio_played.add(current_day)
                    
                    st.subheader(content.get('theme', current_day))
                    all_questions = []
                    for activity in content.get('activities', []):
                        for idx, q in enumerate(activity.get('questions', [])):
                            all_questions.append((activity, idx, q))
                    
                    questions_per_page = 2
                    total_pages = (len(all_questions) + questions_per_page - 1) // questions_per_page
                    page = st.session_state.question_page

                    start_idx = page * questions_per_page
                    end_idx = start_idx + questions_per_page
                    current_questions = all_questions[start_idx:end_idx]

                    for i, (activity, local_idx, q) in enumerate(current_questions):
                        global_idx = start_idx + i
                        st.markdown(f"**Q{global_idx + 1}: {q.get('prompt', '')}**")
                        q_audio = q.get('prompt_audio_file', '')
                        audio_s3_key = fix_audio_path(q_audio, student_s3_prefix, current_day)
                        if audio_s3_key:
                            if st.button(f"🔊 Play Question Audio", key=f"q_audio_{current_day}_{global_idx}"):
                                play_audio_hidden(audio_s3_key)

                        answer_key = f"answer_{current_day}_{global_idx}"
                        if q.get('answer_type') == 'single_select':
                            options = q.get('options', [])
                            current_answer = st.session_state.answers.get(answer_key)
                            for opt_idx, option in enumerate(options):
                                label = option.get('text', f"Option {opt_idx+1}")
                                col1, col2 = st.columns([5, 1])
                                with col1:
                                    button_label = f"{'✓ ' if current_answer == label else ''}{label}"
                                    if st.button(button_label, key=f"answer_{current_day}_{global_idx}_{opt_idx}"):
                                        st.session_state.answers[answer_key] = label
                                        st.experimental_rerun()
                                with col2:
                                    opt_audio = option.get('audio_file', '')
                                    audio_s3_key = fix_audio_path(opt_audio, student_s3_prefix, current_day)
                                    if opt_audio and opt_audio != "[Path to audio]" and audio_s3_key:
                                        if st.button("🔊", key=f"opt_audio_{current_day}_{global_idx}_{opt_idx}"):
                                            play_audio_hidden(audio_s3_key)

                        elif q.get('answer_type') == 'text_input':
                            st.session_state.answers[answer_key] = st.text_input("Your Answer:", key=answer_key)
                        
                        # Add divider after each question except the last one
                        if i < len(current_questions) - 1:
                            st.divider()

                    all_answered = all(
                        st.session_state.answers.get(f"answer_{current_day}_{start_idx + i}")
                        for i in range(len(current_questions))
                    )

                    if all_answered:
                        if page + 1 < total_pages:
                            if st.button("Next Questions", key="next_questions"):
                                st.session_state.question_page += 1
                                st.experimental_rerun()
                        else:
                            current_index = all_days.index(current_day)
                            if current_index + 1 < len(all_days):
                                next_day = all_days[current_index + 1]
                                if st.button("✅ Continue to Next Day", key="next_day"):
                                    st.success(f"Great job completing {current_day}! 🌟")
                                    st.session_state.completed_days.add(current_day)
                                    st.session_state.current_day = next_day
                                    st.session_state.question_page = 0
                                    st.session_state.answers = {}
                                    time.sleep(1)
                                    st.experimental_rerun()
                            else:
                                show_success_animation("Congratulations! You've completed all activities!")
                                st.balloons()
                    else:
                        st.warning("Please answer all questions to continue.")
        else:
            st.error("No activities found for the current day.")

if __name__ == "__main__":
    main()
