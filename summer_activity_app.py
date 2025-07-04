import streamlit as st
import os
import json
import time
import hashlib

# ---------- SETTINGS ----------
DATA_DIR = "summer_activities/Group 7"
PASSWORD_FILE = os.path.join(DATA_DIR, "passwords.json")
st.set_page_config("📘 Literacy App", layout="centered")

# ---------- HELPERS ----------
def load_student_data(student_id):
    path = os.path.join(DATA_DIR, f"{student_id}.json")
    with open(path, "r") as f:
        return json.load(f)

def save_student_data(student_id, data):
    path = os.path.join(DATA_DIR, f"{student_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_next_day(data):
    for day_key, day_data in data.items():
        if not day_data.get("complete"):
            return day_key, day_data
    return None, None

def calculate_progress(data):
    total = len(data)
    completed = sum(1 for d in data.values() if d.get("complete"))
    return int((completed / total) * 100)

def get_day_number(day_key):
    # Extract day number from day_key (e.g., "day_1" -> 1)
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
if "responses" not in st.session_state:
    st.session_state.responses = {}

# ---------- LOGIN PAGE ----------
if not st.session_state.authenticated:
    st.title("🎓 Summer Literacy Activities")
    st.subheader("Please log in to continue")
    
    # Get list of students
    student_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and f != "passwords.json"]
    student_names = [f.replace(".json", "").replace("_", " ").title() for f in student_files]
    
    # Check if we're in password reset mode
    if st.session_state.show_reset_password:
        st.info("🔐 Reset Your Password")
        
        with st.form("reset_password_form"):
            selected_name = st.selectbox("Select your name:", ["-- Select --"] + student_names)
            new_password = st.text_input("Enter new password:", type="password")
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
            
            # Check if this is first time login
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
    # Load student data to get current day
    try:
        student_data = load_student_data(st.session_state.student_id)
        next_day, _ = get_next_day(student_data)
        
        if next_day:
            day_number = get_day_number(next_day)
            
            # Welcome message
            st.balloons()
            st.title(f"🌟 Hello {st.session_state.student_name}!")
            st.header(f"You are on Day {day_number}")
            st.subheader("Enjoy today's activity! 📚")
            
            # Add some spacing
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # Start button
            if st.button("🚀 Start Today's Activity", use_container_width=True):
                st.session_state.activity_started = True
                st.session_state.show_welcome = False
                st.session_state.responses = {}  # Clear previous responses
                st.rerun()
        else:
            st.success("🎉 You've completed all your activities!")
            st.balloons()
            
    except FileNotFoundError:
        st.error("Student file not found.")
        if st.button("🔙 Back to Login"):
            st.session_state.authenticated = False
            st.session_state.show_welcome = False
            st.rerun()

# ---------- ACTIVITY PAGE ----------
else:
    st.title("🎓 Summer Literacy Activities")
    
    # Add logout button in the sidebar
    with st.sidebar:
        st.write(f"👤 Logged in as: {st.session_state.student_name}")
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.student_name = None
            st.session_state.student_id = None
            st.session_state.show_welcome = False
            st.session_state.activity_started = False
            st.session_state.responses = {}
            st.rerun()
    
    try:
        student_data = load_student_data(st.session_state.student_id)
    except FileNotFoundError:
        st.error("Student file not found.")
        st.stop()
    
    # ---------- PROGRESS ----------
    progress = calculate_progress(student_data)
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric("Overall Progress", f"{progress}% Complete")
    with col2:
        completed_days = sum(1 for d in student_data.values() if d.get("complete"))
        st.metric("Days Completed", f"{completed_days}/{len(student_data)}")
    
    # ---------- NEXT ACTIVITY ----------
    next_day, day_data = get_next_day(student_data)
    
    if not next_day:
        st.success("🎉 Congratulations! You've completed all your activities!")
        st.balloons()
        st.stop()
    
    day_number = get_day_number(next_day)
    st.subheader(f"📘 Day {day_number} Activity")
    
    # Get the activity pack content
    activity_pack = None
    for field in day_data.get("fields", []):
        if field.get("id") == "activity_pack":
            activity_pack = field.get("content", {})
            break
    
    if not activity_pack:
        st.error("Activity pack not found!")
        st.stop()
    
    # Display duration
    st.caption(f"Duration: {activity_pack.get('duration', '15 minutes')}")
    
    # Display activities
    activities = activity_pack.get("activities", [])
    total_questions = sum(len(activity.get("questions", [])) for activity in activities)
    
    # Initialize responses in session state if not present
    if "current_responses" not in st.session_state:
        st.session_state.current_responses = {}
    
    # Display each activity
    for activity_idx, activity in enumerate(activities):
        st.markdown("---")
        st.markdown(f"### Activity {activity.get('activity_number', activity_idx + 1)}: {activity.get('component', 'Activity')}")
        st.caption(f"Source: {activity.get('source', 'Unknown')} | Time: {activity.get('time_allocation', '5 minutes')}")
        
        instructions = activity.get("instructions", "")
        if instructions:
            st.info(f"📋 **Instructions:** {instructions}")
        
        # Display questions
        questions = activity.get("questions", [])
        for q_idx, question in enumerate(questions):
            question_key = f"activity_{activity_idx}_question_{q_idx}"
            st.markdown(f"**Question {q_idx + 1}:**")
            st.write(question.get("prompt", ""))
            
            options = question.get("options", [])
            if options:
                # Store the selected answer
                selected = st.radio(
                    "Choose your answer:",
                    options=options,
                    key=question_key,
                    index=None
                )
                
                if selected:
                    st.session_state.current_responses[question_key] = {
                        "selected": options.index(selected),
                        "correct": question.get("correct", [])[0] if question.get("correct") else None
                    }
    
    # Feedback question
    st.markdown("---")
    feedback = activity_pack.get("feedback", {})
    if feedback:
        st.markdown("### Feedback")
        st.write(feedback.get("prompt", "How did you feel about today's activity?"))
        feedback_options = feedback.get("options", ["👍 Great!", "😊 Good", "😐 Okay", "👎 Hard"])
        feedback_response = st.radio(
            "Select one:",
            options=feedback_options,
            key="feedback_response",
            index=None
        )
        
        if feedback_response:
            st.session_state.current_responses["feedback"] = feedback_response
    
    # Submit button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Check if all questions are answered
        expected_responses = sum(len(activity.get("questions", [])) for activity in activities) + 1  # +1 for feedback
        actual_responses = len(st.session_state.current_responses)
        
        if st.button("✅ Submit Day's Activity", use_container_width=True):
            if actual_responses >= expected_responses:
                # Calculate score
                correct_answers = 0
                total_answers = 0
                
                for key, response in st.session_state.current_responses.items():
                    if key != "feedback" and isinstance(response, dict):
                        total_answers += 1
                        if response.get("selected") == response.get("correct"):
                            correct_answers += 1
                
                # Save responses and mark day as complete
                student_data[next_day]["responses"] = st.session_state.current_responses
                student_data[next_day]["score"] = {
                    "correct": correct_answers,
                    "total": total_answers,
                    "percentage": round((correct_answers / total_answers * 100) if total_answers > 0 else 0, 1)
                }
                student_data[next_day]["complete"] = True
                save_student_data(st.session_state.student_id, student_data)
                
                # Show completion message
                st.success(f"✅ Day {day_number} completed! You got {correct_answers}/{total_answers} questions correct!")
                st.balloons()
                
                # Clear responses and go back to welcome screen
                st.session_state.current_responses = {}
                st.session_state.show_welcome = True
                st.session_state.activity_started = False
                time.sleep(3)
                st.rerun()
            else:
                st.error(f"⚠️ Please answer all questions before submitting! ({actual_responses}/{expected_responses} answered)")
    
    # Progress indicator at the bottom
    st.caption(f"Questions answered: {len(st.session_state.current_responses)}/{expected_responses}")
