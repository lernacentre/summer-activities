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
    next_day, activity = get_next_day(student_data)
    
    if not next_day:
        st.success("🎉 Congratulations! You've completed all your activities!")
        st.balloons()
        st.stop()
    
    # Prevent infinite rerun loop
    if st.session_state.get("completed_day") == next_day:
        st.success(f"✅ Day {get_day_number(next_day)} completed! Great job!")
        del st.session_state["completed_day"]
        time.sleep(2)
        st.session_state.show_welcome = True
        st.session_state.activity_started = False
        st.rerun()
    
    day_number = get_day_number(next_day)
    st.subheader(f"📘 Day {day_number} Activity")
    st.caption(f"This activity has {len(activity['fields'])} sections to complete.")
    
    # ---------- FORM ----------
    with st.form("activity_form"):
        responses = {}
        
        for i, field in enumerate(activity["fields"]):
            fid = field.get("id", f"field_{i}")
            label = field.get("label", f"Field {i}")
            ftype = field.get("type", "text_input")
            content = field.get("content", "")
            
            # Display the field label
            st.markdown(f"**{i+1}. {label}**")
            
            if ftype == "text_input":
                # Display content as instruction if present
                if content:
                    st.info(content)
                responses[fid] = st.text_input("Your answer:", key=f"text_input_{fid}")
                
            elif ftype == "text_area":
                # Display content as instruction if present
                if content:
                    st.info(content)
                responses[fid] = st.text_area("Your answer:", key=f"text_area_{fid}", height=100)
                
            elif ftype == "static":
                # Just display the content
                st.info(content)
                
            elif ftype == "checkbox":
                # Display checkboxes for each item in content
                if isinstance(content, list):
                    st.caption("Check the words you've practiced:")
                    responses[fid] = []
                    cols = st.columns(min(len(content), 3))  # Create columns for better layout
                    for j, word in enumerate(content):
                        with cols[j % len(cols)]:
                            if st.checkbox(word, key=f"checkbox_{fid}_{j}"):
                                responses[fid].append(word)
                
            elif ftype == "radio":
                # Display content as instruction if present
                if content:
                    st.info(content)
                options = field.get("options", [])
                if options:
                    responses[fid] = st.radio("Choose one:", options=options, key=f"radio_{fid}")
                else:
                    st.warning("No options provided for radio field")
                    
            else:
                st.warning(f"⚠️ Unknown field type: {ftype}")
            
            # Add spacing between fields
            st.markdown("---")
        
        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("✅ Submit Day's Activity", use_container_width=True)
    
    # ---------- SUBMIT HANDLER ----------
    if submitted:
        # Validate that required fields are filled
        all_filled = True
        for field in activity["fields"]:
            fid = field.get("id", "")
            ftype = field.get("type", "")
            
            if ftype in ["text_input", "text_area"] and fid in responses:
                if not responses[fid].strip():
                    all_filled = False
                    break
            elif ftype == "checkbox" and fid in responses:
                if not responses[fid]:
                    all_filled = False
                    break
        
        if all_filled:
            student_data[next_day]["complete"] = True
            save_student_data(student_id, student_data)
            st.session_state["completed_day"] = next_day
            st.rerun()
        else:
            st.error("⚠️ Please complete all fields before submitting!")
