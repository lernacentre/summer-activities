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
if "day_started" not in st.session_state:
    st.session_state.day_started = False
if "play_first_activity" not in st.session_state:
    st.session_state.play_first_activity = False
if "first_activity_time" not in st.session_state:
    st.session_state.first_activity_time = 0
if "audio_playing" not in st.session_state:
    st.session_state.audio_playing = {}

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

# Add custom CSS for animations and styling
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
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
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
    
    .start-day-button {
        animation: pulse 2s infinite;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        color: white;
        font-size: 24px;
        padding: 20px 40px;
        border-radius: 50px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    .start-day-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
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
        # Use paginator to handle large buckets
        paginator = s3.get_paginator('list_objects_v2')
        
        # Get all objects under Summer_Activities/
        all_objects = []
        page_iterator = paginator.paginate(
            Bucket=BUCKET_NAME,
            Prefix=base_prefix
        )
        
        for page in page_iterator:
            if 'Contents' in page:
                all_objects.extend(page['Contents'])
        
        # Process all objects to extract group and student information
        groups_found = set()
        
        for obj in all_objects:
            key = obj['Key']
            # Remove the base prefix to make parsing easier
            relative_key = key[len(base_prefix):] if key.startswith(base_prefix) else key
            parts = relative_key.split('/')
            
            # Expected structure: GroupName/StudentName/...
            if len(parts) >= 2:
                group = parts[0]
                student = parts[1]
                
                # Skip if group or student is empty
                if not group or not student:
                    continue
                
                # Track all groups found
                groups_found.add(group)
                
                # Skip files at the group level (like passwords.json)
                if len(parts) == 2 and '.' in student:
                    continue
                
                # Skip password files and system files
                if (student.endswith('_passwords.txt') or 
                    student.endswith('.json') or
                    student == "passwords.json" or
                    '.txt' in student or
                    '.json' in student):
                    continue
                
                # If we have at least 3 parts, this is likely a student with content
                if len(parts) >= 3:
                    # Add the student if not already added
                    if student not in student_to_group:
                        student_to_group[student] = group
        
        return student_to_group
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            st.error(f"❌ Bucket '{BUCKET_NAME}' does not exist")
        elif error_code == 'AccessDenied':
            st.error(f"❌ Access denied to bucket '{BUCKET_NAME}'")
        else:
            st.error(f"❌ AWS Error ({error_code}): {e}")
        return {}
    except Exception as e:
        st.error(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return {}

# Helper function to fix audio paths
def fix_audio_path(audio_file, student_s3_prefix, current_day):
    if not audio_file or audio_file == "[Path to audio]":
        return None
    if audio_file.startswith("day"):
        return f"{student_s3_prefix}/{audio_file}"
    else:
        return f"{student_s3_prefix}/{current_day}/{audio_file}"

# Load passwords - prioritize txt files over json
@st.cache_data(show_spinner=False)
def load_passwords(group_folder):
    passwords = {}
    
    # First priority: Look for group password file (e.g., Group7_passwords.txt)
    group_password_key = f"Summer_Activities/{group_folder}/{group_folder}_passwords.txt"
    txt_content = read_s3_file(group_password_key)
    
    if txt_content:
        # Parse the group password file
        lines = txt_content.decode('utf-8').strip().split('\n')
        
        for line in lines:
            # Skip header lines and empty lines
            if ':' in line and not line.startswith('=') and not line.startswith('GROUP'):
                # Parse lines like "Ahmed: W8CGBL"
                parts = line.split(':')
                if len(parts) == 2:
                    student_name = parts[0].strip()
                    password = parts[1].strip()
                    
                    # Store with exact case from file
                    passwords[student_name] = password
                    
                    # Also store lowercase version for case-insensitive matching
                    passwords[student_name.lower()] = password
    
    # Second priority: Check for individual password files
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=f"Summer_Activities/{group_folder}/",
            MaxKeys=100
        )
        
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('_passwords.txt') and not key.endswith(f'{group_folder}_passwords.txt'):
                    # Individual student password file
                    filename = key.split('/')[-1]
                    student_name = filename.replace('_passwords.txt', '')
                    
                    txt_content = read_s3_file(key)
                    if txt_content:
                        simple_password = txt_content.decode('utf-8').strip()
                        passwords[student_name] = simple_password
                        passwords[student_name.lower()] = simple_password
    
    except ClientError as e:
        st.warning(f"Could not check for individual password files: {e}")
    
    # Last priority: Only if no txt files found, try passwords.json
    if not passwords:
        password_json_key = f"Summer_Activities/{group_folder}/passwords.json"
        content = read_s3_file(password_json_key)
        if content:
            try:
                passwords = json.loads(content.decode('utf-8'))
            except json.JSONDecodeError:
                st.warning(f"Could not parse passwords.json for {group_folder}")
    
    return passwords

# Enhanced play audio function with autoplay attempt
def play_audio_with_autoplay(s3_key, element_id="opening-audio"):
    """Play audio with autoplay attempt and fallback button"""
    audio_content = read_s3_file(s3_key)
    if audio_content:
        b64 = base64.b64encode(audio_content).decode()
        audio_html = f"""
        <audio id="{element_id}" autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
            // Attempt to play audio with user interaction fallback
            window.addEventListener('load', function() {{
                var audio = document.getElementById('{element_id}');
                if (audio) {{
                    audio.volume = 0.8;
                    
                    // Try to play
                    var playPromise = audio.play();
                    
                    if (playPromise !== undefined) {{
                        playPromise.then(_ => {{
                            console.log("Audio playing automatically");
                        }}).catch(error => {{
                            console.log("Autoplay prevented:", error);
                            // Create a play button if autoplay fails
                            var playBtn = document.createElement('button');
                            playBtn.innerHTML = '🔊 Click to hear Ms. Sarah';
                            playBtn.style.cssText = 'position: fixed; top: 100px; right: 20px; z-index: 1000; padding: 15px 25px; background: linear-gradient(45deg, #FF6B6B, #4ECDC4); color: white; border: none; border-radius: 50px; cursor: pointer; font-size: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); animation: pulse 2s infinite;';
                            playBtn.onclick = function() {{
                                document.getElementById('{element_id}').play();
                                this.remove();
                            }};
                            document.body.appendChild(playBtn);
                        }});
                    }}
                }}
            }});
        </script>
        """
        st.markdown(audio_html, unsafe_allow_html=True)
    else:
        st.error(f"Error playing audio: File not found")

# Fixed play audio function
def play_audio_hidden(s3_key, audio_key=None):
    """Play audio with proper handling"""
    if audio_key and st.session_state.audio_playing.get(audio_key, False):
        return  # Don't play if already playing
    
    audio_content = read_s3_file(s3_key)
    if audio_content:
        if audio_key:
            st.session_state.audio_playing[audio_key] = True
        
        b64 = base64.b64encode(audio_content).decode()
        unique_id = str(time.time()).replace('.', '')
        
        # Create audio element in a container
        container = st.container()
        with container:
            st.markdown(f"""
            <audio id="audio_{unique_id}" autoplay>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                var audio = document.getElementById('audio_{unique_id}');
                if (audio) {{
                    audio.play().catch(function(e) {{
                        console.error('Audio play error:', e);
                    }});
                }}
            </script>
            """, unsafe_allow_html=True)

# Function to play completion sound effect
def play_completion_sound():
    """Play a completion fanfare sound effect"""
    completion_sound_html = """
    <script>
    var audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    function playCompletionSound() {
        // Create a fanfare-like sound
        var notes = [
            {freq: 523.25, time: 0},      // C
            {freq: 523.25, time: 0.1},    // C
            {freq: 523.25, time: 0.2},    // C
            {freq: 659.25, time: 0.3},    // E
            {freq: 783.99, time: 0.5},    // G
            {freq: 1046.50, time: 0.7}    // High C
        ];
        
        notes.forEach(function(note) {
            var oscillator = audioContext.createOscillator();
            var gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = note.freq;
            oscillator.type = 'square';
            
            // Create envelope
            gainNode.gain.setValueAtTime(0, audioContext.currentTime + note.time);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + note.time + 0.02);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + note.time + 0.2);
            
            oscillator.start(audioContext.currentTime + note.time);
            oscillator.stop(audioContext.currentTime + note.time + 0.2);
        });
    }
    
    playCompletionSound();
    </script>
    """
    st.markdown(completion_sound_html, unsafe_allow_html=True)

# Function to show success animation
def show_success_animation(message):
    # Play completion sound
    play_completion_sound()
    
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
            Welcome, {student_name.capitalize()}! 👋
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
        st.error("No students found in the system")
        return

    # Login with case-insensitive password checking
    if not st.session_state.authenticated:
        st.header("Student Login")
        
        # Capitalize student names in dropdown
        student_names = sorted([name.capitalize() for name in student_to_group.keys()])
        selected_student = st.selectbox("Select Student", student_names)
        password = st.text_input("Password", type="password")
        
        if st.button("Login", key="login_button"):
            # Find original case for the student
            original_student = None
            for orig_name in student_to_group.keys():
                if orig_name.lower() == selected_student.lower():
                    original_student = orig_name
                    break
            
            if original_student:
                group = student_to_group[original_student]
                passwords = load_passwords(group)
                
                # Try multiple case variations for the student name
                possible_names = [
                    original_student,  # As stored
                    original_student.lower(),  # lowercase
                    original_student.capitalize(),  # Capitalized
                    original_student.upper(),  # UPPERCASE
                    selected_student,  # As selected
                ]
                
                password_found = False
                correct_password = None
                
                for name_variant in possible_names:
                    if name_variant in passwords:
                        correct_password = passwords[name_variant]
                        password_found = True
                        break
                
                if password_found:
                    if correct_password == password:
                        st.session_state.authenticated = True
                        st.session_state.student = selected_student.capitalize()
                        st.session_state.group = group
                        st.session_state.original_student = original_student
                        st.balloons()
                        show_welcome_animation(selected_student)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Wrong password")
                else:
                    st.error(f"No password found for {selected_student}")

    # After login
    else:
        # Display capitalized student name
        st.write(f"Welcome back, {st.session_state.student}!")
        
        if st.button("Logout", key="logout_button"):
            st.session_state.clear()
            st.rerun()

        student_s3_prefix = f"Summer_Activities/{st.session_state.group}/{st.session_state.original_student}"

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

        # Set current day based on completed days
        if st.session_state.current_day is None and all_days:
            # Find the first uncompleted day
            for day in all_days:
                if day not in st.session_state.completed_days:
                    st.session_state.current_day = day
                    break
            else:
                # All days completed, show the last day
                st.session_state.current_day = all_days[-1]

        current_day = st.session_state.current_day

        if current_day and current_day in day_to_content:
            day_data = day_to_content[current_day]
            
            # Extract the activity content
            for field in day_data['fields']:
                if field.get('type') == 'enhanced_structured_literacy_session':
                    content = field.get('content', {})
                    
                    # Show start day screen if not started
                    if not st.session_state.day_started:
                        st.markdown(f"""
                        <div style="text-align: center; padding: 50px;">
                            <h1 style="color: #4ECDC4; margin-bottom: 30px;">
                                {content.get('theme', current_day.replace('day', 'Day '))}
                            </h1>
                            <p style="font-size: 20px; margin-bottom: 40px;">
                                Click the button below to start today's activities!
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button("🚀 Start Today's Activities!", key="start_day", use_container_width=True):
                                st.session_state.day_started = True
                                st.session_state.audio_playing = {}  # Reset audio state
                                st.rerun()
                        return
                    
                    # Play opening audio when day starts
                    if current_day not in st.session_state.opening_audio_played:
                        opening_audio = content.get('opening_audio_file', '')
                        audio_s3_key = fix_audio_path(opening_audio, student_s3_prefix, current_day)
                        if audio_s3_key:
                            play_audio_with_autoplay(audio_s3_key)
                            st.session_state.opening_audio_played.add(current_day)
                            
                            # Set a flag to play first activity intro after delay
                            st.session_state.play_first_activity = True
                            st.session_state.first_activity_time = time.time()
                    
                    # Check if we should play first activity intro (after 3 second delay)
                    if (st.session_state.get('play_first_activity', False) and 
                        time.time() - st.session_state.get('first_activity_time', 0) > 3):
                        
                        # Play first activity introduction
                        if content.get('activities'):
                            first_activity = content['activities'][0]
                            first_tutor_audio = first_activity.get('tutor_intro_audio_file', '')
                            first_tutor_key = fix_audio_path(first_tutor_audio, student_s3_prefix, current_day)
                            if first_tutor_key:
                                play_audio_hidden(first_tutor_key)
                        
                        # Clear the flag
                        st.session_state.play_first_activity = False
                        st.rerun()  # Rerun to update the UI
                   
                    st.header(f"Day: {current_day.replace('day', 'Day ')}")
                    st.subheader(content.get('theme', current_day))
                    
                    all_questions = []
                    activity_lookup = {}  # Store activity data for each question
                    for activity in content.get('activities', []):
                        for idx, q in enumerate(activity.get('questions', [])):
                            question_index = len(all_questions)
                            all_questions.append((activity, idx, q))
                            activity_lookup[question_index] = activity
                   
                    questions_per_page = 2
                    total_pages = (len(all_questions) + questions_per_page - 1) // questions_per_page
                    page = st.session_state.question_page

                    start_idx = page * questions_per_page
                    end_idx = start_idx + questions_per_page
                    current_questions = all_questions[start_idx:end_idx]

                    for i, (activity, local_idx, q) in enumerate(current_questions):
                        global_idx = start_idx + i
                        
                        # Display activity header if this is the first question of a new activity
                        if local_idx == 0:
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0;">
                                <h4 style="color: #2c3e50; margin-bottom: 10px;">
                                    📚 Activity {activity.get('activity_number', '')}: {activity.get('component', '')}
                                </h4>
                                <p style="color: #7f8c8d; margin-bottom: 5px;">
                                    <strong>Skill:</strong> {activity.get('skill_target', '')}
                                </p>
                                <p style="color: #7f8c8d;">
                                    <strong>Time:</strong> {activity.get('time_allocation', '')}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Add tutor introduction audio if available
                            tutor_audio = activity.get('tutor_intro_audio_file', '')
                            if tutor_audio:
                                tutor_audio_key = fix_audio_path(tutor_audio, student_s3_prefix, current_day)
                                if tutor_audio_key:
                                    col1, col2, col3 = st.columns([1, 2, 1])
                                    with col2:
                                        audio_key = f"tutor_{current_day}_{activity.get('activity_number')}"
                                        if st.button("🎯 Activity Introduction", key=audio_key, use_container_width=True):
                                            play_audio_hidden(tutor_audio_key, audio_key)
                            
                            # Session state keys for practice tracking
                            practice_key = f"practice_done_{current_day}_{activity.get('activity_number')}"
                            multi_clicked_key = f"multi_clicked_{current_day}_{activity.get('activity_number')}"
                            
                            # Add teaching and multisensory buttons
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                teaching_audio = activity.get('teaching_audio', '')
                                teaching_audio_key = fix_audio_path(teaching_audio, student_s3_prefix, current_day)
                                if teaching_audio_key:
                                    audio_key = f"teach_{current_day}_{activity.get('activity_number')}"
                                    if st.button("📖 Teach Me", key=audio_key, use_container_width=True, type="primary"):
                                        play_audio_hidden(teaching_audio_key, audio_key)
                            
                            with col2:
                                multisensory_audio = activity.get('multisensory_audio', '')
                                multisensory_audio_key = fix_audio_path(multisensory_audio, student_s3_prefix, current_day)
                                if multisensory_audio_key:
                                    audio_key = f"multi_{current_day}_{activity.get('activity_number')}"
                                    if st.button("🤹 Multisensory Practice", key=audio_key, use_container_width=True, type="secondary"):
                                        play_audio_hidden(multisensory_audio_key, audio_key)
                                        # Mark that multisensory was clicked but don't rerun yet
                                        if not st.session_state.get(practice_key, False):
                                            st.session_state[multi_clicked_key] = True
                            
                            # Show practice confirmation bar if multisensory was clicked and not yet confirmed
                            if st.session_state.get(multi_clicked_key, False) and not st.session_state.get(practice_key, False):
                                # Add some spacing
                                st.markdown("")
                                
                                # Simple confirmation prompt
                                col1, col2, col3 = st.columns([2, 1, 2])
                                with col2:
                                    if st.button("✅ I Practiced!", key=f"confirm_practice_{current_day}_{activity.get('activity_number')}", type="primary", use_container_width=True):
                                        st.session_state[practice_key] = True
                                        st.session_state[multi_clicked_key] = False
                                        st.balloons()
                                        time.sleep(1)
                                        st.rerun()
                            
                            # Show practice status if completed
                            if st.session_state.get(practice_key, False):
                                st.success("✅ Multisensory practice completed!")
                            
                            st.markdown("")  # Add spacing
                        
                        # Display the question
                        st.markdown(f"**Q{global_idx + 1}: {q.get('prompt', '')}**")
                        q_audio = q.get('prompt_audio_file', '')
                        audio_s3_key = fix_audio_path(q_audio, student_s3_prefix, current_day)
                        if audio_s3_key:
                            audio_key = f"q_audio_{current_day}_{global_idx}"
                            if st.button(f"🔊 Play Question Audio", key=audio_key):
                                play_audio_hidden(audio_s3_key, audio_key)

                        answer_key = f"answer_{current_day}_{global_idx}"
                        
                        # Handle different question types
                        if q.get('answer_type') == 'single_select':
                            options = q.get('options', [])
                            current_answer = st.session_state.answers.get(answer_key)
                            
                            # Show feedback if exists
                            feedback_key = f"feedback_{current_day}_{global_idx}"
                            if feedback_key in st.session_state and time.time() - st.session_state[feedback_key]['show_time'] < 5:
                                feedback_data = st.session_state[feedback_key]
                                is_correct = feedback_data['selected'] == feedback_data['correct']
                                
                                if is_correct:
                                    st.success("✅ " + (feedback_data['feedback_text'] if feedback_data['feedback_text'] else "Correct! Well done!"))
                                    
                                    # Play feedback audio once
                                    if feedback_data['feedback_audio'] and not st.session_state.get(f"fb_played_{feedback_key}", False):
                                        feedback_audio_key = fix_audio_path(feedback_data['feedback_audio'], student_s3_prefix, current_day)
                                        if feedback_audio_key:
                                            play_audio_hidden(feedback_audio_key)
                                            st.session_state[f"fb_played_{feedback_key}"] = True
                                    
                                    # Play completion audio if needed
                                    if 'completion_audio' in feedback_data and feedback_data['completion_audio'] and not st.session_state.get(f"comp_played_{feedback_key}", False):
                                        completion_key = fix_audio_path(feedback_data['completion_audio'], student_s3_prefix, current_day)
                                        if completion_key:
                                            # Schedule completion audio
                                            completion_b64 = base64.b64encode(read_s3_file(completion_key)).decode()
                                            st.markdown(f"""
                                            <script>
                                            setTimeout(function() {{
                                                var audio = new Audio('data:audio/mp3;base64,{completion_b64}');
                                                audio.play();
                                            }}, 3000);  // Play after 3 seconds
                                            </script>
                                            """, unsafe_allow_html=True)
                                            st.session_state[f"comp_played_{feedback_key}"] = True
                                else:
                                    st.warning("❌ Try again! Listen to the question carefully.")
                            
                            for opt_idx, option in enumerate(options):
                                label = option.get('text', f"Option {opt_idx+1}")
                                col1, col2 = st.columns([5, 1])
                                with col1:
                                    button_label = f"{'✓ ' if current_answer == label else ''}{label}"
                                    if st.button(button_label, key=f"answer_{current_day}_{global_idx}_{opt_idx}"):
                                        # Store the answer
                                        st.session_state.answers[answer_key] = label
                                        
                                        # Store feedback state to show after rerun
                                        st.session_state[feedback_key] = {
                                            'selected': label,
                                            'correct': q.get('correct_answer', ''),
                                            'feedback_text': q.get('feedback', ''),
                                            'feedback_audio': q.get('feedback_audio_file', ''),
                                            'show_time': time.time()
                                        }
                                        
                                        # Check if this completes the activity
                                        activity_questions = [qt for act, idx, qt in all_questions if act == activity]
                                        current_q_index = activity_questions.index(q)
                                        if label == q.get('correct_answer', '') and current_q_index == len(activity_questions) - 1:
                                            st.session_state[feedback_key]['completion_audio'] = activity.get('activity_completion_audio_file', '')
                                        
                                        st.rerun()
                                
                                with col2:
                                    opt_audio = option.get('audio_file', '')
                                    audio_s3_key = fix_audio_path(opt_audio, student_s3_prefix, current_day)
                                    if opt_audio and opt_audio != "[Path to audio]" and audio_s3_key:
                                        audio_key = f"opt_audio_{current_day}_{global_idx}_{opt_idx}"
                                        if st.button("🔊", key=audio_key):
                                            play_audio_hidden(audio_s3_key, audio_key)

                        elif q.get('answer_type') == 'text_input':
                            # Special handling for dictation questions
                            if q.get('question_type') == 'text_input_dictation':
                                dictation_audio = q.get('dictation_audio_file', '')
                                if dictation_audio:
                                    dictation_key = fix_audio_path(dictation_audio, student_s3_prefix, current_day)
                                    if dictation_key:
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            st.info("📝 " + q.get('dictation_instruction', 'Click play to hear the sentence'))
                                        with col2:
                                            audio_key = f"dict_{current_day}_{global_idx}"
                                            if st.button("▶️ Play Dictation", key=audio_key, type="primary"):
                                                play_audio_hidden(dictation_key, audio_key)
                            
                            st.session_state.answers[answer_key] = st.text_input("Your Answer:", key=answer_key)
                        
                        # Special handling for reading comprehension stories
                        if activity.get('component') == 'Reading Comprehension' and local_idx == 0:
                            if activity.get('story_display', False):
                                # Display the story text
                                story_text = activity.get('story_text', '')
                                if story_text:
                                    st.markdown("📖 **Read the story below:**")
                                    st.markdown(f"""
                                    <div style="background-color: #f9f9f9; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #4CAF50;">
                                        <p style="font-size: 16px; line-height: 1.8; color: #333;">
                                            {story_text}
                                        </p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Add story audio button
                                    story_audio = activity.get('story_audio_file', '')
                                    if story_audio:
                                        story_key = fix_audio_path(story_audio, student_s3_prefix, current_day)
                                        if story_key:
                                            audio_key = f"story_{current_day}_{activity.get('activity_number')}"
                                            if st.button("🎧 Listen to Story", key=audio_key, use_container_width=True):
                                                play_audio_hidden(story_key, audio_key)
                        
                        # Special handling for paragraph writing final display
                        if activity.get('component') == 'Paragraph Writing':
                            # Check if all questions for this activity are answered
                            activity_questions = [q for q in activity.get('questions', [])]
                            all_activity_answered = all(
                                st.session_state.answers.get(f"answer_{current_day}_{all_questions.index((activity, j, q))}")
                                for j, q in enumerate(activity_questions)
                            )
                            
                            if all_activity_answered and local_idx == len(activity_questions) - 1:
                                # Display the assembled paragraph
                                final_display = activity.get('final_display', {})
                                if final_display.get('complete_paragraph'):
                                    st.markdown("### 📝 Your Complete Paragraph:")
                                    st.success(final_display['complete_paragraph'])
                                    
                                    # Play the assembled paragraph audio
                                    paragraph_audio = final_display.get('audio_file', '')
                                    if paragraph_audio:
                                        para_key = fix_audio_path(paragraph_audio, student_s3_prefix, current_day)
                                        if para_key:
                                            audio_key = f"para_{current_day}_{activity.get('activity_number')}"
                                            if st.button("🎧 Listen to Complete Paragraph", key=audio_key, use_container_width=True):
                                                play_audio_hidden(para_key, audio_key)
                       
                        # Add divider after each question except the last one
                        if i < len(current_questions) - 1:
                            st.divider()

                    # Clean old feedback states
                    current_time = time.time()
                    keys_to_remove = []
                    for key in st.session_state:
                        if key.startswith(f"feedback_{current_day}_") and isinstance(st.session_state[key], dict):
                            if current_time - st.session_state[key].get('show_time', 0) > 5:
                                keys_to_remove.append(key)
                                keys_to_remove.append(f"fb_played_{key}")
                                keys_to_remove.append(f"comp_played_{key}")
                    
                    for key in keys_to_remove:
                        if key in st.session_state:
                            del st.session_state[key]

                    all_answered = all(
                        st.session_state.answers.get(f"answer_{current_day}_{start_idx + i}")
                        for i in range(len(current_questions))
                    )

                    if all_answered:
                        if page + 1 < total_pages:
                            if st.button("Next Questions", key="next_questions"):
                                st.session_state.question_page += 1
                                st.session_state.audio_playing = {}  # Reset audio state
                                st.rerun()
                        else:
                            current_index = all_days.index(current_day)
                            if current_index + 1 < len(all_days):
                                next_day = all_days[current_index + 1]
                                if st.button("✅ Continue to Next Day", key="next_day"):
                                    st.success(f"Great job completing {current_day}! 🌟")
                                    st.session_state.completed_days.add(current_day)
                                    
                                    # Clear activity-specific states
                                    keys_to_remove = []
                                    for key in st.session_state:
                                        if (key.startswith(f"practice_done_{current_day}_") or
                                            key.startswith(f"multi_clicked_{current_day}_") or
                                            key.startswith(f"feedback_{current_day}_") or
                                            key.startswith(f"fb_played_") or
                                            key.startswith(f"comp_played_")):
                                            keys_to_remove.append(key)
                                    
                                    for key in keys_to_remove:
                                        del st.session_state[key]
                                    
                                    st.session_state.current_day = next_day
                                    st.session_state.question_page = 0
                                    st.session_state.answers = {}
                                    st.session_state.day_started = False  # Reset for next day
                                    st.session_state.audio_playing = {}  # Reset audio state
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                show_success_animation("Congratulations! You've completed all activities!")
                                st.balloons()
                                
                                # Play closing audio
                                closing_audio = content.get('closing_audio_file', '')
                                if closing_audio:
                                    closing_key = fix_audio_path(closing_audio, student_s3_prefix, current_day)
                                    if closing_key:
                                        play_audio_hidden(closing_key)
                    else:
                        st.warning("Please answer all questions to continue.")
        else:
            st.error("No activities found for the current day.")

if __name__ == "__main__":
    main()
