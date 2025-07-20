import streamlit as st
import json
import base64
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
import time
import random
from difflib import SequenceMatcher
import math

# Page config must be first
st.set_page_config(layout="wide", page_title="Student Activities", page_icon="📚")

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
if "audio_playing" not in st.session_state:
    st.session_state.audio_playing = {}
if "day_scores" not in st.session_state:
    st.session_state.day_scores = {}
if "all_time_scores" not in st.session_state:
    st.session_state.all_time_scores = {}
if "transition_audio_played" not in st.session_state:
    st.session_state.transition_audio_played = set()
if "audio_containers" not in st.session_state:
    st.session_state.audio_containers = {}
if "scroll_to_top" not in st.session_state:
    st.session_state.scroll_to_top = False

# S3 Configuration
BUCKET_NAME = "summer-activities-streamli-app"
BUCKET_REGION = "eu-north-1"

@st.cache_resource
def get_s3_client():
    try:
        AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
        AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
        
        client = boto3.client(
            's3',
            region_name=BUCKET_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        return client
    except Exception as e:
        st.error(f"Failed to create S3 client: {e}")
        return None

s3 = get_s3_client()
if not s3:
    st.stop()

# Add custom CSS
def add_custom_css():
    st.markdown("""
    <style>
    /* Smooth transitions and prevent flashing */
    iframe {
        visibility: hidden;
    }
    
    iframe.finished-loading {
        visibility: visible;
    }
    
    /* Hide Streamlit's default processing message */
    .stSpinner > div {
        display: none;
    }
    
    /* Custom animations */
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
    
    /* Custom chart styles */
    .progress-bar-container {
        margin: 20px 0;
        padding: 15px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .progress-bar {
        background-color: #f0f0f0;
        border-radius: 15px;
        height: 30px;
        overflow: hidden;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .progress-fill {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
        transition: width 0.5s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        border-radius: 15px;
    }
    
    /* Navigation buttons */
    .nav-button {
        background: linear-gradient(45deg, #4ECDC4, #44A3AA);
        color: white;
        font-size: 18px;
        padding: 12px 24px;
        border-radius: 25px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        margin: 10px 5px;
    }
    
    /* Hide duplicate audio buttons */
    div[data-testid="stButton"] > button {
        transition: none !important;
    }
    
    /* Scroll to top on page change */
    .scroll-top {
        scroll-behavior: auto;
        position: fixed;
        top: 0;
    }
    </style>
    
    <script>
    // Prevent iframe flashing
    window.addEventListener('load', function() {
        setTimeout(function() {
            document.querySelectorAll('iframe').forEach(function(iframe) {
                iframe.classList.add('finished-loading');
            });
        }, 100);
    });
    </script>
    """, unsafe_allow_html=True)

# Helper function to scroll to top
def scroll_to_top():
    st.markdown("""
    <script>
    window.scrollTo({top: 0, behavior: 'instant'});
    </script>
    """, unsafe_allow_html=True)

# Helper function to read files from S3
@st.cache_data
def read_s3_file(s3_key):
    """Read a file from S3 and return its content"""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except ClientError:
        return None

# Get all students - hidden from UI
@st.cache_data
def _get_all_students():
    student_to_group = {}
    base_prefix = "Summer_Activities/"
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        all_objects = []
        page_iterator = paginator.paginate(
            Bucket=BUCKET_NAME,
            Prefix=base_prefix
        )
        
        for page in page_iterator:
            if 'Contents' in page:
                all_objects.extend(page['Contents'])
        
        for obj in all_objects:
            key = obj['Key']
            relative_key = key[len(base_prefix):] if key.startswith(base_prefix) else key
            parts = relative_key.split('/')
            
            if len(parts) >= 2:
                group = parts[0]
                student = parts[1]
                
                if not group or not student:
                    continue
                
                if len(parts) == 2 and '.' in student:
                    continue
                
                if (student.endswith('_passwords.txt') or 
                    student.endswith('.json') or
                    student == "passwords.json" or
                    '.txt' in student or
                    '.json' in student):
                    continue
                
                if len(parts) >= 3:
                    if student not in student_to_group:
                        student_to_group[student] = group
        
        return student_to_group
        
    except Exception as e:
        st.error(f"Error loading students: {e}")
        return {}

# Fix audio paths
def fix_audio_path(audio_file, student_s3_prefix, current_day):
    if not audio_file or audio_file == "[Path to audio]":
        return None
    if audio_file.startswith("day"):
        return f"{student_s3_prefix}/{audio_file}"
    else:
        return f"{student_s3_prefix}/{current_day}/{audio_file}"

# Load passwords - hidden function
@st.cache_data
def _load_passwords(group_folder):
    passwords = {}
    
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
                    filename = key.split('/')[-1]
                    student_name = filename.replace('_passwords.txt', '')
                    
                    txt_content = read_s3_file(key)
                    if txt_content:
                        simple_password = txt_content.decode('utf-8').strip()
                        passwords[student_name] = simple_password
                        passwords[student_name.lower()] = simple_password
    
    except ClientError:
        pass
    
    if not passwords:
        password_json_key = f"Summer_Activities/{group_folder}/passwords.json"
        content = read_s3_file(password_json_key)
        if content:
            try:
                passwords = json.loads(content.decode('utf-8'))
            except json.JSONDecodeError:
                pass
    
    return passwords

# Play audio with autoplay
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
            window.addEventListener('load', function() {{
                var audio = document.getElementById('{element_id}');
                if (audio) {{
                    audio.volume = 0.8;
                    var playPromise = audio.play();
                    
                    if (playPromise !== undefined) {{
                        playPromise.then(_ => {{
                            console.log("Audio playing automatically");
                        }}).catch(error => {{
                            console.log("Autoplay prevented:", error);
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

# Play audio hidden with container management
def play_audio_hidden(s3_key, audio_key=None):
    """Play audio with proper handling"""
    if audio_key not in st.session_state.audio_containers:
        st.session_state.audio_containers[audio_key] = st.empty()
    
    audio_content = read_s3_file(s3_key)
    if audio_content:
        b64 = base64.b64encode(audio_content).decode()
        unique_id = f"{audio_key}_{str(time.time()).replace('.', '')}"
        
        with st.session_state.audio_containers[audio_key]:
            st.markdown(f"""
            <audio id="audio_{unique_id}" autoplay>
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            <script>
                document.getElementById('audio_{unique_id}').play();
            </script>
            """, unsafe_allow_html=True)

# Play story with highlight
def play_story_with_highlight(story_text, audio_s3_key):
    """Play story audio with synchronized text highlighting"""
    audio_content = read_s3_file(audio_s3_key)
    if audio_content:
        b64 = base64.b64encode(audio_content).decode()
        words = story_text.split()
        word_duration = 0.3
        
        highlighted_html = f"""
        <div id="story-container" style="background-color: #f9f9f9; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #4CAF50;">
            <p style="font-size: 18px; line-height: 2; color: #333;">
                {' '.join([f'<span id="word-{i}" style="transition: background-color 0.3s ease;">{word}</span>' for i, word in enumerate(words)])}
            </p>
        </div>
        <audio id="story-audio" autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        <script>
            var audio = document.getElementById('story-audio');
            var words = {len(words)};
            var currentWord = 0;
            
            function highlightWord(index) {{
                if (index > 0) {{
                    document.getElementById('word-' + (index - 1)).style.backgroundColor = 'transparent';
                }}
                if (index < words) {{
                    document.getElementById('word-' + index).style.backgroundColor = 'yellow';
                }}
            }}
            
            audio.addEventListener('play', function() {{
                var interval = setInterval(function() {{
                    if (currentWord < words) {{
                        highlightWord(currentWord);
                        currentWord++;
                    }} else {{
                        clearInterval(interval);
                        if (currentWord > 0) {{
                            document.getElementById('word-' + (currentWord - 1)).style.backgroundColor = 'transparent';
                        }}
                    }}
                }}, {word_duration * 1000});
            }});
            
            audio.play();
        </script>
        """
        st.markdown(highlighted_html, unsafe_allow_html=True)

# Calculate similarity
def calculate_similarity(user_answer, correct_answer):
    """Calculate similarity percentage between two strings"""
    if not user_answer or not correct_answer:
        return 0
    
    user_lower = user_answer.lower().strip()
    correct_lower = correct_answer.lower().strip()
    
    similarity = SequenceMatcher(None, user_lower, correct_lower).ratio()
    return similarity * 100

def is_valid_dictation_answer(user_answer, correct_answer):
    """Check if user answer is valid for dictation"""
    if not user_answer:
        return False, "Please write your answer"
    
    word_count = len(user_answer.strip().split())
    if word_count < 2:
        return False, "Please write at least 2 words"
    
    similarity = calculate_similarity(user_answer, correct_answer)
    if similarity < 20:
        return False, "Please try again or type 'I don't know'"
    
    return True, f"Good effort! ({similarity:.0f}% accurate)"

# Create a beautiful combined progress chart
def create_combined_progress_chart(activities_data):
    """Create a visually appealing combined progress visualization"""
    if not activities_data:
        return
    
    # Calculate total progress
    total_correct = sum(data['correct'] for data in activities_data.values())
    total_questions = sum(data['total'] for data in activities_data.values())
    overall_percentage = (total_correct / total_questions * 100) if total_questions > 0 else 0
    
    # Create circular progress indicator
    radius = 60
    circumference = 2 * math.pi * radius
    offset = circumference - (overall_percentage / 100 * circumference)
    
    # Color based on performance
    if overall_percentage >= 80:
        color = "#4CAF50"
        emoji = "🌟"
    elif overall_percentage >= 60:
        color = "#FFA500"
        emoji = "👍"
    else:
        color = "#FF6B6B"
        emoji = "💪"
    
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <svg width="150" height="150" style="transform: rotate(-90deg);">
            <circle cx="75" cy="75" r="{radius}" stroke="#e0e0e0" stroke-width="15" fill="none" />
            <circle cx="75" cy="75" r="{radius}" stroke="{color}" stroke-width="15" fill="none"
                    stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
                    style="transition: stroke-dashoffset 0.5s ease;" />
        </svg>
        <div style="margin-top: -90px; font-size: 36px; font-weight: bold; color: {color};">
            {overall_percentage:.0f}% {emoji}
        </div>
        <h4 style="margin-top: 20px;">Today's Activity Completion</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Show individual activities with beautiful bar charts
    st.markdown("### 📚 Activities")
    
    for activity_name, data in activities_data.items():
        percentage = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
        component = data.get('component', '')
        
        # Determine color scheme
        if percentage >= 80:
            bar_gradient = 'linear-gradient(90deg, #4CAF50 0%, #45a049 100%)'
            text_color = '#4CAF50'
        elif percentage >= 60:
            bar_gradient = 'linear-gradient(90deg, #FFA500 0%, #ff8c00 100%)'
            text_color = '#FFA500'
        else:
            bar_gradient = 'linear-gradient(90deg, #FF6B6B 0%, #ff5252 100%)'
            text_color = '#FF6B6B'
        
        # Create beautiful bar chart for each activity
        st.markdown(f"""
        <div style="margin: 15px 0;">
            <h5 style="margin-bottom: 8px; color: #1a1a1a; font-weight: 600; font-size: 14px;">{component}</h5>
            <div style="background-color: #f0f0f0; border-radius: 10px; height: 20px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                <div style="
                    width: {percentage}%;
                    height: 100%;
                    background: {bar_gradient};
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    transition: width 0.5s ease;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                ">
                    {f'{percentage:.0f}%' if percentage > 15 else ''}
                </div>
            </div>
            <p style="text-align: right; margin-top: 3px; color: {text_color}; font-size: 11px; font-weight: 500;">
                {data['correct']}/{data['total']} correct {f'({percentage:.0f}%)' if percentage <= 15 else ''}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Add overall progress bar at the bottom
    st.markdown("---")
    st.markdown("### 📊 Overall Progress")
    
    # Determine overall color
    if overall_percentage >= 80:
        overall_gradient = 'linear-gradient(90deg, #4CAF50 0%, #45a049 100%)'
        overall_color = '#4CAF50'
    elif overall_percentage >= 60:
        overall_gradient = 'linear-gradient(90deg, #FFA500 0%, #ff8c00 100%)'
        overall_color = '#FFA500'
    else:
        overall_gradient = 'linear-gradient(90deg, #FF6B6B 0%, #ff5252 100%)'
        overall_color = '#FF6B6B'
    
    st.markdown(f"""
    <div style="margin: 15px 0;">
        <div style="background-color: #f0f0f0; border-radius: 12px; height: 25px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
            <div style="
                width: {overall_percentage}%;
                height: 100%;
                background: {overall_gradient};
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 14px;
                transition: width 0.5s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            ">
                {overall_percentage:.0f}%
            </div>
        </div>
        <p style="text-align: center; margin-top: 5px; color: {overall_color}; font-size: 13px; font-weight: 600;">
            {total_correct}/{total_questions} Total Questions Correct
        </p>
    </div>
    """, unsafe_allow_html=True)

# Progress sidebar
def create_progress_sidebar(all_days, day_to_content, current_day, student_s3_prefix):
    """Create a sidebar with progress tracking"""
    with st.sidebar:
        if "student" in st.session_state:
            st.markdown(f"## 👤 {st.session_state.student}")
        st.markdown("---")
        
        # Overall progress
        st.markdown("### 📊 Overall Progress")
        completed_count = len(st.session_state.completed_days)
        total_days = len(all_days)
        progress_percentage = (completed_count / total_days * 100) if total_days > 0 else 0
        
        st.progress(progress_percentage / 100)
        st.markdown(f"<p style='text-align: center;'>{completed_count}/{total_days} Days ({progress_percentage:.0f}%)</p>", unsafe_allow_html=True)
        
        # Current day progress
        if current_day and current_day in day_to_content:
            st.markdown("---")
            
            day_data = day_to_content[current_day]
            activities_data = {}
            
            for field in day_data['fields']:
                if field.get('type') == 'enhanced_structured_literacy_session':
                    content = field.get('content', {})
                    
                    for activity in content.get('activities', []):
                        activity_num = activity.get('activity_number', '')
                        component = activity.get('component', '')
                        
                        correct = 0
                        total = 0
                        
                        for q in activity.get('questions', []):
                            total += 1
                            for global_idx, (act, _, question) in enumerate([(a, i, qu) for a in content.get('activities', []) for i, qu in enumerate(a.get('questions', []))]):
                                if act == activity and question == q:
                                    answer_key = f"answer_{current_day}_{global_idx}"
                                    user_answer = st.session_state.answers.get(answer_key)
                                    
                                    if q.get('answer_type') == 'single_select':
                                        if user_answer == q.get('correct_answer'):
                                            correct += 1
                                    elif q.get('answer_type') == 'text_input':
                                        if user_answer and (is_valid_dictation_answer(user_answer, q.get('correct_answer', ''))[0] or user_answer.lower() == "i don't know"):
                                            correct += 1
                        
                        activities_data[f"activity_{activity_num}"] = {
                            'correct': correct,
                            'total': total,
                            'component': component
                        }
            
            # Create beautiful combined chart
            create_combined_progress_chart(activities_data)
        
        # Day status
        st.markdown("---")
        st.markdown("### 📅 Daily Status")
        for day in all_days:
            is_current = day == current_day
            is_completed = day in st.session_state.completed_days
            
            if is_current:
                st.markdown(f"**➡️ {day.replace('day', 'Day ')} (Current)**")
            elif is_completed:
                st.markdown(f"✅ {day.replace('day', 'Day ')}")
            else:
                st.markdown(f"⭕ {day.replace('day', 'Day ')}")

# Welcome animation
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

# Success animation
def show_success_animation(message):
    completion_sound_html = """
    <script>
    var audioContext = new (window.AudioContext || window.webkitAudioContext)();
    function playCompletionSound() {
        var notes = [
            {freq: 523.25, time: 0},
            {freq: 659.25, time: 0.3},
            {freq: 783.99, time: 0.5},
            {freq: 1046.50, time: 0.7}
        ];
        notes.forEach(function(note) {
            var oscillator = audioContext.createOscillator();
            var gainNode = audioContext.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            oscillator.frequency.value = note.freq;
            oscillator.type = 'square';
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
    
    confetti_html = ""
    colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
    for i in range(20):
        left = random.randint(10, 90)
        delay = random.random() * 0.5
        color = random.choice(colors)
        confetti_html += f'<div class="confetti" style="left: {left}%; animation-delay: {delay}s; background-color: {color};"></div>'
   
    st.markdown(f"""
    <div class="completion-animation">
        <h2 style="text-align: center; color: #4CAF50;">🎉 {message} 🎉</h2>
    </div>
    {confetti_html}
    """, unsafe_allow_html=True)

# Main app
def main():
    st.title("Student Activities")
    add_custom_css()

    # Check if we need to scroll to top
    if st.session_state.get('scroll_to_top', False):
        scroll_to_top()
        st.session_state.scroll_to_top = False

    student_to_group = _get_all_students()

    if not student_to_group:
        st.error("No students found in the system")
        return

    # Login section
    if not st.session_state.authenticated:
        st.header("Student Login")
        
        student_names = sorted([name.capitalize() for name in student_to_group.keys()])
        selected_student = st.selectbox("Select Student", student_names)
        password = st.text_input("Password", type="password")
        
        if st.button("Login", key="login_button"):
            original_student = None
            for orig_name in student_to_group.keys():
                if orig_name.lower() == selected_student.lower():
                    original_student = orig_name
                    break
            
            if original_student:
                group = student_to_group[original_student]
                passwords = _load_passwords(group)
                
                possible_names = [
                    original_student,
                    original_student.lower(),
                    original_student.capitalize(),
                    original_student.upper(),
                    selected_student,
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
        st.write(f"Welcome back, {st.session_state.student}!")
        
        if st.button("Logout", key="logout_button"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        student_s3_prefix = f"Summer_Activities/{st.session_state.group}/{st.session_state.original_student}"

        # Load day packs
        @st.cache_data
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

        # Set current day
        if st.session_state.current_day is None and all_days:
            for day in all_days:
                if day not in st.session_state.completed_days:
                    st.session_state.current_day = day
                    break
            else:
                st.session_state.current_day = all_days[-1]

        current_day = st.session_state.current_day

        # Create sidebar
        create_progress_sidebar(all_days, day_to_content, current_day, student_s3_prefix)

        if current_day and current_day in day_to_content:
            day_data = day_to_content[current_day]
            
            for field in day_data['fields']:
                if field.get('type') == 'enhanced_structured_literacy_session':
                    content = field.get('content', {})
                    
                    # Start day screen
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
                                st.session_state.audio_containers = {}
                                st.rerun()
                        return
                    
                    # Play opening audio once
                    if current_day not in st.session_state.opening_audio_played:
                        opening_audio = content.get('opening_audio_file', '')
                        audio_s3_key = fix_audio_path(opening_audio, student_s3_prefix, current_day)
                        if audio_s3_key:
                            play_audio_with_autoplay(audio_s3_key)
                            st.session_state.opening_audio_played.add(current_day)
                   
                    st.header(f"Day: {current_day.replace('day', 'Day ')}")
                    st.subheader(content.get('theme', current_day))
                    
                    # Prepare questions
                    all_questions = []
                    for activity in content.get('activities', []):
                        for idx, q in enumerate(activity.get('questions', [])):
                            all_questions.append((activity, idx, q))
                   
                    questions_per_page = 2
                    total_pages = (len(all_questions) + questions_per_page - 1) // questions_per_page
                    page = st.session_state.question_page

                    # Navigation at top
                    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                    with nav_col1:
                        if page > 0:
                            if st.button("⬅️ Previous", key="prev_top", use_container_width=True):
                                st.session_state.question_page -= 1
                                st.session_state.scroll_to_top = True
                                st.session_state.audio_containers = {}
                                st.rerun()
                    
                    start_idx = page * questions_per_page
                    end_idx = start_idx + questions_per_page
                    current_questions = all_questions[start_idx:end_idx]

                    # Check for transition audio
                    if page > 0:
                        transition_key = f"transition_{current_day}_{page}"
                        if transition_key not in st.session_state.transition_audio_played:
                            for activity, local_idx, _ in current_questions:
                                if local_idx == 0:
                                    transition_audio = activity.get('tutor_intro_audio_file', '')
                                    if transition_audio:
                                        audio_key = fix_audio_path(transition_audio, student_s3_prefix, current_day)
                                        if audio_key:
                                            play_audio_hidden(audio_key, f"transition_{page}")
                                            st.session_state.transition_audio_played.add(transition_key)
                                    break

                    # Display questions
                    for i, (activity, local_idx, q) in enumerate(current_questions):
                        global_idx = start_idx + i
                        
                        if local_idx == 0:
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0;">
                                <h4 style="color: #2c3e50; margin-bottom: 10px;">
                                    📚 {activity.get('component', '')}
                                </h4>
                                <p style="color: #7f8c8d; margin-bottom: 5px;">
                                    <strong>Skill:</strong> {activity.get('skill_target', '')}
                                </p>
                                <p style="color: #7f8c8d;">
                                    <strong>Time:</strong> {activity.get('time_allocation', '')}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Activity intro button
                            tutor_audio = activity.get('tutor_intro_audio_file', '')
                            if tutor_audio:
                                tutor_audio_key = fix_audio_path(tutor_audio, student_s3_prefix, current_day)
                                if tutor_audio_key:
                                    if st.button("🎯 Activity Introduction", key=f"intro_{activity.get('activity_number')}_{page}", use_container_width=True):
                                        play_audio_hidden(tutor_audio_key, f"intro_{activity.get('activity_number')}_{page}")
                            
                            # Teaching and practice buttons
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                teaching_audio = activity.get('teaching_audio', '')
                                if teaching_audio:
                                    teaching_audio_key = fix_audio_path(teaching_audio, student_s3_prefix, current_day)
                                    if teaching_audio_key and st.button("📖 Teach Me", key=f"teach_{activity.get('activity_number')}_{page}", use_container_width=True, type="primary"):
                                        play_audio_hidden(teaching_audio_key, f"teach_{activity.get('activity_number')}_{page}")
                            
                            with col2:
                                multisensory_audio = activity.get('multisensory_audio', '')
                                if multisensory_audio:
                                    multisensory_audio_key = fix_audio_path(multisensory_audio, student_s3_prefix, current_day)
                                    practice_key = f"practice_{current_day}_{activity.get('activity_number')}"
                                    
                                    if multisensory_audio_key and st.button("🤹 Practice", key=f"multi_{activity.get('activity_number')}_{page}", use_container_width=True, type="secondary"):
                                        play_audio_hidden(multisensory_audio_key, f"multi_{activity.get('activity_number')}_{page}")
                                        if not st.session_state.get(practice_key):
                                            st.session_state[practice_key] = True
                                            st.success("✅ Practice completed!")
                        
                        # Reading comprehension story
                        if activity.get('component') == 'Reading Comprehension' and local_idx == 0 and activity.get('story_display'):
                            story_text = activity.get('story_text', '')
                            if story_text:
                                st.markdown("📖 **Read the story:**")
                                story_audio = activity.get('story_audio_file', '')
                                
                                if story_audio:
                                    story_key = fix_audio_path(story_audio, student_s3_prefix, current_day)
                                    if story_key and st.button("🎧 Listen & Read", key=f"story_{activity.get('activity_number')}_{page}", use_container_width=True):
                                        play_story_with_highlight(story_text, story_key)
                                
                                st.markdown(f"""
                                <div style="background-color: #f9f9f9; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #4CAF50;">
                                    <p style="font-size: 18px; line-height: 2; color: #333;">
                                        {story_text}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Question display
                        st.markdown(f"**Q{global_idx + 1}: {q.get('prompt', '')}**")
                        
                        # Question audio
                        q_audio = q.get('prompt_audio_file', '')
                        if q_audio:
                            audio_s3_key = fix_audio_path(q_audio, student_s3_prefix, current_day)
                            if audio_s3_key and st.button(f"🔊 Play Question", key=f"q_{global_idx}_{page}"):
                                play_audio_hidden(audio_s3_key, f"q_{global_idx}_{page}")

                        answer_key = f"answer_{current_day}_{global_idx}"
                        
                        # Handle answer types
                        if q.get('answer_type') == 'single_select':
                            options = q.get('options', [])
                            current_answer = st.session_state.answers.get(answer_key)
                            
                            # Show feedback
                            feedback_key = f"feedback_{current_day}_{global_idx}"
                            if feedback_key in st.session_state and time.time() - st.session_state[feedback_key]['show_time'] < 5:
                                feedback_data = st.session_state[feedback_key]
                                is_correct = feedback_data['selected'] == feedback_data['correct']
                                
                                if is_correct:
                                    st.success("✅ Correct! Well done!")
                                    if feedback_data.get('feedback_audio'):
                                        feedback_audio_key = fix_audio_path(feedback_data['feedback_audio'], student_s3_prefix, current_day)
                                        if feedback_audio_key:
                                            play_audio_hidden(feedback_audio_key, f"fb_{global_idx}")
                                else:
                                    st.warning("❌ Try again!")
                            
                            # Option buttons
                            for opt_idx, option in enumerate(options):
                                label = option.get('text', f"Option {opt_idx+1}")
                                col1, col2 = st.columns([5, 1])
                                
                                with col1:
                                    button_label = f"{'✓ ' if current_answer == label else ''}{label}"
                                    if st.button(button_label, key=f"opt_{global_idx}_{opt_idx}_{page}"):
                                        st.session_state.answers[answer_key] = label
                                        st.session_state[feedback_key] = {
                                            'selected': label,
                                            'correct': q.get('correct_answer', ''),
                                            'feedback_audio': q.get('feedback_audio_file', ''),
                                            'show_time': time.time()
                                        }
                                        st.rerun()
                                
                                with col2:
                                    opt_audio = option.get('audio_file', '')
                                    if opt_audio and opt_audio != "[Path to audio]":
                                        audio_s3_key = fix_audio_path(opt_audio, student_s3_prefix, current_day)
                                        if audio_s3_key and st.button("🔊", key=f"opt_audio_{global_idx}_{opt_idx}_{page}"):
                                            play_audio_hidden(audio_s3_key, f"opt_audio_{global_idx}_{opt_idx}_{page}")

                        elif q.get('answer_type') == 'text_input':
                            if q.get('question_type') == 'text_input_dictation':
                                dictation_audio = q.get('dictation_audio_file', '')
                                if dictation_audio:
                                    dictation_key = fix_audio_path(dictation_audio, student_s3_prefix, current_day)
                                    if dictation_key:
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            st.info("📝 Click play to hear the sentence")
                                        with col2:
                                            if st.button("▶️ Play", key=f"dict_{global_idx}_{page}", type="primary"):
                                                play_audio_hidden(dictation_key, f"dict_{global_idx}_{page}")
                            
                            current_answer = st.text_input("Your Answer:", key=answer_key, value=st.session_state.answers.get(answer_key, ""))
                            
                            if current_answer:
                                is_valid, message = is_valid_dictation_answer(current_answer, q.get('correct_answer', ''))
                                if is_valid or current_answer.lower() == "i don't know":
                                    st.session_state.answers[answer_key] = current_answer
                                    st.success(message if current_answer.lower() != "i don't know" else "That's okay!")
                                else:
                                    st.warning(message)
                        
                        if i < len(current_questions) - 1:
                            st.divider()

                    # Clean old feedback
                    current_time = time.time()
                    keys_to_remove = [key for key in st.session_state if key.startswith(f"feedback_{current_day}_") and isinstance(st.session_state[key], dict) and current_time - st.session_state[key].get('show_time', 0) > 5]
                    for key in keys_to_remove:
                        del st.session_state[key]

                    # Check if all answered
                    all_answered = all(
                        st.session_state.answers.get(f"answer_{current_day}_{start_idx + i}")
                        for i in range(len(current_questions))
                    )

                    # Bottom navigation
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                    
                    with nav_col1:
                        if page > 0 and st.button("⬅️ Previous", key="prev_bottom", type="secondary", use_container_width=True):
                            st.session_state.question_page -= 1
                            st.session_state.scroll_to_top = True
                            st.session_state.audio_containers = {}
                            st.rerun()
                    
                    with nav_col3:
                        if all_answered:
                            if page + 1 < total_pages:
                                if st.button("Next ➡️", key="next_page", type="primary", use_container_width=True):
                                    st.session_state.question_page += 1
                                    st.session_state.scroll_to_top = True
                                    st.session_state.audio_containers = {}
                                    st.rerun()
                            else:
                                if st.button("✅ Complete Day", key="complete_day", type="primary", use_container_width=True):
                                    st.session_state.completed_days.add(current_day)
                                    current_index = all_days.index(current_day)
                                    
                                    if current_index + 1 < len(all_days):
                                        st.session_state.current_day = all_days[current_index + 1]
                                        st.session_state.question_page = 0
                                        st.session_state.answers = {}
                                        st.session_state.day_started = False
                                        st.session_state.audio_containers = {}
                                        st.session_state.transition_audio_played = set()
                                        st.success(f"Great job! Moving to next day...")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        show_success_animation("All activities completed! 🎉")
                                        st.balloons()
                    
                    with nav_col2:
                        if not all_answered:
                            st.warning("Answer all questions to continue")

if __name__ == "__main__":
    main()
