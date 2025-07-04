import streamlit as st
import os
import json
import time
import hashlib

# ---------- SETTINGS ----------
DATA_DIR = "summer_activities/Group 7"
AUDIO_DIR = "summer_activities/audio_files/Group 7"
PASSWORD_FILE = os.path.join(DATA_DIR, "passwords.json")

# Page configuration
st.set_page_config(
    page_title="📘 Summer Literacy Activities",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stRadio > div > label {
        font-size: 16px;
        padding: 10px;
    }
    .question-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
def load_student_data(student_id):
    """Load student progress data"""
    path = os.path.join(DATA_DIR, f"{student_id}.json")
    with open(path, "r") as f:
        return json.load(f)

def save_student_data(student_id, data):
    """Save student progress data"""
    path = os.path.join(DATA_DIR, f"{student_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_next_day(data):
    """Get the next incomplete day"""
    for day_key, day_data in data.items():
        if not day_data.get("complete"):
            return day_key, day_data
    return None, None

def calculate_progress(data):
    """Calculate overall progress percentage"""
    total = len(data)
    completed = sum(1 for d in data.values() if d.get("complete"))
    return int((completed / total) * 100)

def get_day_number(day_key):
    """Extract day number from day_key"""
    return int(day_key.split("_")[1])

# ---------- PASSWORD MANAGEMENT ----------
def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_passwords():
    """Load passwords from file"""
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_passwords(passwords):
    """Save passwords to file"""
    with open(PASSWORD_FILE, 'w') as f:
        json.dump(passwords, f, indent=2)

def check_password(student_id, password):
    """Check if password is correct"""
    passwords = load_passwords()
    if student_id in passwords:
        return passwords[student_id] == hash_password(password)
    return False

def set_password(student_id, password):
    """Set or update password for student"""
    passwords = load_passwords()
    passwords[student_id] = hash_password(password)
    save_passwords(passwords)

def student_has_password(student_id):
    """Check if student has already set a password"""
    passwords = load_passwords()
    return student_id in passwords

# ---------- SESSION STATE INITIALIZATION ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "student_name" not in st.session_state:
    st.session_state.student_name = None
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = False
if "activity_started" not in st.session_state:
    st.session_state.activity_started = False
if "show_reset_password" not in st.session_state:
    st.session_state.show_reset_password = False
if "current_responses" not in st.session_state:
    st.session_state.current_responses = {}

# ---------- LOGIN PAGE ----------
if not st.session_state.authenticated:
    st.title("🎓 Summer Literacy Activities")
    st.subheader("Welcome to your personalised learning journey!")
    
    # Get list of students
    try:
        student_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and f != "passwords.json"]
        student_names = [f.replace(".json", "").replace("_", " ").title() for f in student_files]
    except FileNotFoundError:
        st.error("Student data directory not found. Please check the file structure.")
        st.stop()
    
    if not student_names:
        st.error("No student files found. Please check the data directory.")
        st.stop()
    
    # Password reset mode
    if st.session_state.show_reset_password:
        st.info("🔐 Reset Your Password")
        
        with st.form("reset_password_form"):
            selected_name = st.selectbox("Select your name:", ["-- Select --"] + student_names)
            new_password = st.text_input("Enter new password:", type="password", 
                                       help="Minimum 4 characters")
            confirm_password = st.text_input("Confirm new password:", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                reset_button = st.form_submit_button("✅ Reset Password", use_container_width=True)
            with col2:
                cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if reset_button:
                if selected_name != "-- Select --":
                    if new_password and confirm_password:
                        if new_password == confirm_password:
                            if len(new_password) >= 4:
                                student_id = selected_name.lower().replace(" ", "_")
                                set_password(student_id, new_password)
                                st.success("✅ Password reset successfully! You can now log in.")
                                st.session_state.show_reset_password = False
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ Password must be at least 4 characters long.")
                        else:
                            st.error("❌ Passwords don't match. Please try again.")
                    else:
                        st.error("❌ Please enter and confirm your password.")
                else:
                    st.warning("⚠️ Please select your name.")
            
            if cancel_button:
                st.session_state.show_reset_password = False
                st.rerun()
    
    else:
        # Normal login form
        with st.form("login_form"):
            selected_name = st.selectbox("Select your name:", ["-- Select --"] + student_names)
            
            # Dynamic password field based on selection
            if selected_name != "-- Select --":
                student_id = selected_name.lower().replace(" ", "_")
                if not student_has_password(student_id):
                    st.info("👋 Welcome! Please create a password for your first login.")
                    password = st.text_input("Create a password (at least 4 characters):", type="password")
                    confirm_password = st.text_input("Confirm password:", type="password")
                else:
                    password = st.text_input("Enter your password:", type="password")
                    confirm_password = None
            else:
                password = st.text_input("Enter your password:", type="password", disabled=True)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                login_button = st.form_submit_button("🔐 Login", use_container_width=True)
            with col2:
                forgot_button = st.form_submit_button("Forgot?")
            
            if login_button:
                if selected_name != "-- Select --":
                    student_id = selected_name.lower().replace(" ", "_")
                    
                    # First time login - create password
                    if not student_has_password(student_id):
                        if password and confirm_password:
                            if password == confirm_password:
                                if len(password) >= 4:
                                    set_password(student_id, password)
                                    st.session_state.authenticated = True
                                    st.session_state.student_name = selected_name
                                    st.session_state.student_id = student_id
                                    st.session_state.show_welcome = True
                                    st.success("✅ Password created successfully!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("❌ Password must be at least 4 characters long.")
                            else:
                                st.error("❌ Passwords don't match. Please try again.")
                        else:
                            st.error("❌ Please enter and confirm your password.")
                    
                    # Regular login
                    else:
                        if check_password(student_id, password):
                            st.session_state.authenticated = True
                            st.session_state.student_name = selected_name
                            st.session_state.student_id = student_id
                            st.session_state.show_welcome = True
                            st.rerun()
                        else:
                            st.error("❌ Incorrect password. Please try again.")
                else:
                    st.warning("⚠️ Please select your name.")
            
            if forgot_button:
                st.session_state.show_reset_password = True
                st.rerun()

# ---------- WELCOME SCREEN ----------
elif st.session_state.show_welcome and not st.session_state.activity_started:
    try:
        student_data = load_student_data(st.session_state.student_id)
        next_day, _ = get_next_day(student_data)
        
        if next_day:
            day_number = get_day_number(next_day)
            
            # Welcome message with animation
            st.balloons()
            st.title(f"🌟 Hello {st.session_state.student_name}!")
            st.header(f"Welcome to Day {day_number}")
            
            # Progress overview
            progress = calculate_progress(student_data)
            st.progress(progress / 100)
            st.caption(f"{progress}% of activities completed")
            
            st.subheader("Ready for today's adventure? 📚")
            
            # Motivational message
            if day_number == 1:
                st.info("🎯 Your first day! Let's make it amazing!")
            elif progress > 50:
                st.info("🌟 You're doing fantastic! Keep going!")
            else:
                st.info("💪 Every day is a step forward!")
            
            # Start button
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Start Today's Activity", use_container_width=True, type="primary"):
                st.session_state.activity_started = True
                st.session_state.show_welcome = False
                st.session_state.current_responses = {}
                st.rerun()
                
        else:
            # All activities completed
            st.success("🎉 Congratulations! You've completed all your activities!")
            st.balloons()
            
            # Show final stats
            st.subheader("Your Achievement Summary")
            total_days = len(student_data)
            st.metric("Days Completed", f"{total_days} / {total_days}")
            
            # Calculate average score
            total_score = 0
            total_questions = 0
            for day_data in student_data.values():
                if "score" in day_data:
                    total_score += day_data["score"]["correct"]
                    total_questions += day_data["score"]["total"]
            
            if total_questions > 0:
                avg_score = (total_score / total_questions) * 100
                st.metric("Average Score", f"{avg_score:.1f}%")
            
            st.markdown("### 🏆 You're a literacy champion!")
            
    except FileNotFoundError:
        st.error("Student file not found.")
        if st.button("🔙 Back to Login"):
            st.session_state.authenticated = False
            st.session_state.show_welcome = False
            st.rerun()

# ---------- ACTIVITY PAGE ----------
else:
    # Sidebar with logout
    with st.sidebar:
        st.write(f"👤 {st.session_state.student_name}")
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    st.title("🎓 Summer Literacy Activities")
    
    try:
        student_data = load_student_data(st.session_state.student_id)
    except FileNotFoundError:
        st.error("Student file not found.")
        st.stop()
    
    # Progress metrics
    progress = calculate_progress(student_data)
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.metric("Overall Progress", f"{progress}%")
        st.progress(progress / 100)
    with col2:
        completed_days = sum(1 for d in student_data.values() if d.get("complete"))
        st.metric("Days Completed", f"{completed_days}/{len(student_data)}")
    with col3:
        if st.button("📊 View Scores"):
            with st.expander("Your Scores"):
                for day_key, day_data in student_data.items():
                    if day_data.get("complete") and "score" in day_data:
                        day_num = get_day_number(day_key)
                        score = day_data["score"]
                        st.write(f"Day {day_num}: {score['correct']}/{score['total']} ({score['percentage']}%)")
    
    # Get next activity
    next_day, day_data = get_next_day(student_data)
    
    if not next_day:
        st.success("🎉 All activities completed!")
        st.balloons()
        st.stop()
    
    day_number = get_day_number(next_day)
    st.subheader(f"📘 Day {day_number} Activity")
    
    # Get activity pack
    activity_pack = None
    for field in day_data.get("fields", []):
        if field.get("id") == "activity_pack":
            activity_pack = field.get("content", {})
            break
    
    if not activity_pack:
        st.error("Activity pack not found!")
        st.stop()
    
    # Display duration
    st.caption(f"⏱️ Duration: {activity_pack.get('duration', '15 minutes')}")
    
    # Progress bar for activities
    activities = activity_pack.get("activities", [])
    total_activities = len(activities)
    
    # Activity tabs
    tabs = st.tabs([f"Activity {i+1}" for i in range(total_activities)])
    
    # Track total questions for progress
    total_questions = sum(len(activity.get("questions", [])) for activity in activities) + 1  # +1 for feedback
    
    # Display each activity in tabs
    for tab_idx, (tab, activity) in enumerate(zip(tabs, activities)):
        with tab:
            # Activity header
            st.markdown(f"### {activity.get('component', 'Activity')}")
            st.caption(f"Source: {activity.get('source', '')} | Time: {activity.get('time_allocation', '')}")
            
            # Instructions
            if activity.get("instructions"):
                st.info(f"📋 {activity.get('instructions')}")
            
            # Display passage if exists
            passage = activity.get("passage", "")
            if passage:
                st.markdown("### 📖 Reading Passage")
                
                # Check for passage audio
                if "passage_audio_file" in activity:
                    audio_path = os.path.join(AUDIO_DIR, os.path.basename(activity["passage_audio_file"]))
                    if os.path.exists(audio_path):
                        st.audio(audio_path, format='audio/mp3')
                        st.caption("🔊 Click to listen to the passage")
                
                # Display passage in a nice box
                st.markdown(f"""
                <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin: 10px 0;'>
                {passage}
                </div>
                """, unsafe_allow_html=True)
                st.markdown("")
            
            # Display questions
            questions = activity.get("questions", [])
            for q_idx, question in enumerate(questions):
                question_key = f"activity_{tab_idx}_question_{q_idx}"
                
                # Question container
                with st.container():
                    st.markdown(f"**Question {q_idx + 1}**")
                    
                    # Audio player if available
                    if "audio_file" in question:
                        audio_filename = os.path.basename(question["audio_file"])
                        audio_path = os.path.join(AUDIO_DIR, audio_filename)
                        
                        if os.path.exists(audio_path):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.audio(audio_path, format='audio/mp3')
                            with col2:
                                st.caption("🔊 Listen")
                    
                    # Question prompt
                    prompt = question.get("prompt", "")
                    if prompt:
                        st.write(prompt)
                    
                    # Answer options
                    options = question.get("options", [])
                    if options:
                        selected = st.radio(
                            "Choose your answer:",
                            options=options,
                            key=question_key,
                            index=None,
                            label_visibility="collapsed"
                        )
                        
                        if selected:
                            st.session_state.current_responses[question_key] = {
                                "selected": options.index(selected),
                                "correct": question.get("correct", [])[0] if question.get("correct") else None
                            }
                    
                    st.markdown("---")
    
    # Feedback section
    st.markdown("### How did you feel about today's activities?")
    feedback = activity_pack.get("feedback", {})
    if feedback:
        feedback_options = feedback.get("options", ["👍 Great!", "😊 Good", "😐 Okay", "👎 Hard"])
        feedback_response = st.radio(
            feedback.get("prompt", "Select one:"),
            options=feedback_options,
            key="feedback_response",
            index=None,
            horizontal=True
        )
        
        if feedback_response:
            st.session_state.current_responses["feedback"] = feedback_response
    
    # Submit section
    st.markdown("---")
    
    # Check completion
    actual_responses = len(st.session_state.current_responses)
    response_progress = actual_responses / total_questions if total_questions > 0 else 0
    
    # Progress indicator
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(response_progress)
        st.caption(f"Questions answered: {actual_responses}/{total_questions}")
    
    with col2:
        # Submit button - only enabled when all questions answered
        if st.button(
            "✅ Submit Activity", 
            use_container_width=True,
            disabled=(actual_responses < total_questions),
            type="primary"
        ):
            # Calculate score
            correct_answers = 0
            total_answers = 0
            
            for key, response in st.session_state.current_responses.items():
                if key != "feedback" and isinstance(response, dict):
                    total_answers += 1
                    if response.get("selected") == response.get("correct"):
                        correct_answers += 1
            
            # Save responses
            student_data[next_day]["responses"] = dict(st.session_state.current_responses)
            student_data[next_day]["score"] = {
                "correct": correct_answers,
                "total": total_answers,
                "percentage": round((correct_answers / total_answers * 100) if total_answers > 0 else 0, 1)
            }
            student_data[next_day]["complete"] = True
            save_student_data(st.session_state.student_id, student_data)
            
            # Show results
            st.success(f"✅ Day {day_number} completed!")
            st.metric("Your Score", f"{correct_answers}/{total_answers}")
            
            if correct_answers == total_answers:
                st.balloons()
                st.markdown("### 🌟 Perfect score! Amazing work!")
            elif correct_answers >= total_answers * 0.8:
                st.markdown("### 🎯 Great job! Keep it up!")
            else:
                st.markdown("### 💪 Good effort! Every day you're improving!")
            
            # Reset for next day
            st.session_state.current_responses = {}
            st.session_state.show_welcome = True
            st.session_state.activity_started = False
            
            time.sleep(3)
            st.rerun()
    
    # Help text if not all answered
    if actual_responses < total_questions:
        st.info("💡 Please answer all questions before submitting.")
