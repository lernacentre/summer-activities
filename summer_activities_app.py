import streamlit as st
import json
import os
import base64

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

# Get all students from all groups
def get_all_students():
    student_to_group = {}
    base_path = "Summer_Activities"

    for item in os.listdir(base_path):
        group_path = os.path.join(base_path, item)
        if os.path.isdir(group_path) and item.startswith("Group"):
            for student in os.listdir(group_path):
                student_path = os.path.join(group_path, student)
                if os.path.isdir(student_path) and student != "passwords.json":
                    # Check if this student has day folders
                    has_days = False
                    for subfolder in os.listdir(student_path):
                        if os.path.isdir(os.path.join(student_path, subfolder)) and subfolder.startswith("day"):
                            has_days = True
                            break
                    if has_days:
                        student_to_group[student] = item

    return student_to_group

# Helper function to fix audio paths
def fix_audio_path(audio_file, student_path, current_day):
    """Handle audio file paths with mixed formats"""
    if not audio_file or audio_file == "[Path to audio]":
        return None
    
    # Handle different path formats in the JSON
    if audio_file.startswith("day"):
        # Path like "day1/audio/file.mp3" - use as is
        return os.path.join(student_path, audio_file)
    else:
        # Path like "audio/file.mp3" - add current day
        return os.path.join(student_path, current_day, audio_file)

# Load passwords
def load_passwords(group_folder):
    password_file = os.path.join("Summer_Activities", group_folder, "passwords.json")
    if os.path.exists(password_file):
        with open(password_file, 'r') as f:
            return json.load(f)
    return {}

# Play audio without showing controls (hidden bar)
def play_audio_hidden(audio_file):
    try:
        with open(audio_file, 'rb') as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        audio_tag = f"""
            <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        """
        st.markdown(audio_tag, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error playing audio: {e}")

# Main app
def main():
    st.title("Student Activities")

    # Get all students
    student_to_group = get_all_students()

    if not student_to_group:
        st.error("No students found")
        return

    # Login
    if not st.session_state.authenticated:
        selected_student = st.selectbox("Select Student", sorted(student_to_group.keys()))
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            group = student_to_group[selected_student]
            passwords = load_passwords(group)
            if passwords.get(selected_student) == password:
                st.session_state.authenticated = True
                st.session_state.student = selected_student
                st.session_state.group = group
                st.rerun()
            else:
                st.error("Wrong password")

    # After login
    else:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.current_day = None
            st.session_state.completed_days = set()
            st.session_state.question_page = 0
            st.session_state.answers = {}
            st.session_state.opening_audio_played = set()
            st.rerun()

        # Student path
        student_path = os.path.join("Summer_Activities", st.session_state.group, st.session_state.student)

        # Load activity_pack.json from each day folder
        all_days = []
        day_to_content = {}

        # Look for day folders
        day_folders = [f for f in os.listdir(student_path) if os.path.isdir(os.path.join(student_path, f)) and f.startswith("day")]
        day_folders.sort(key=lambda x: int(x.replace("day", "")))  # Sort by day number

        for day_folder in day_folders:
            activity_pack_path = os.path.join(student_path, day_folder, "activity_pack.json")
            if os.path.exists(activity_pack_path):
                with open(activity_pack_path, 'r') as f:
                    data = json.load(f)
                    day_name = day_folder  # Use folder name as day identifier
                    all_days.append(day_name)
                    day_to_content[day_name] = data

        # Set the first day if not already set
        if st.session_state.current_day is None and all_days:
            st.session_state.current_day = all_days[0]

        # Get current day content
        current_day = st.session_state.current_day
        
        if current_day and current_day in day_to_content:
            day_data = day_to_content[current_day]

            st.header(f"Day: {current_day.replace('day', 'Day ')}")

            # Debug info to see what audio files are available
            if st.checkbox("Show debug info"):
                st.write("Current day data structure:")
                st.json(day_data)

            # Opening audio - autoplay hidden (play only once per day)
            for field in day_data['fields']:
                if field.get('type') == 'enhanced_structured_literacy_session':
                    content = field.get('content', {})

                    # Play opening audio only if not already played for this day
                    if current_day not in st.session_state.opening_audio_played:
                        opening_audio = content.get('opening_audio_file', '')
                        audio_path = fix_audio_path(opening_audio, student_path, current_day)
                        
                        if audio_path and os.path.exists(audio_path):
                            play_audio_hidden(audio_path)
                            st.session_state.opening_audio_played.add(current_day)
                        elif audio_path:
                            st.warning(f"Opening audio file not found: {audio_path}")

                    # Display activities
                    st.subheader(content.get('theme', current_day))

                    all_questions = []
                    for activity in content.get('activities', []):
                        # Collect all questions with their parent activity
                        for idx, q in enumerate(activity.get('questions', [])):
                            all_questions.append((activity, idx, q))

                    # Pagination: show 2 questions per page
                    questions_per_page = 2
                    total_pages = (len(all_questions) + questions_per_page - 1) // questions_per_page
                    page = st.session_state.question_page

                    start_idx = page * questions_per_page
                    end_idx = start_idx + questions_per_page
                    current_questions = all_questions[start_idx:end_idx]

                    # Track question number across all activities
                    for i, (activity, local_idx, q) in enumerate(current_questions):
                        global_idx = start_idx + i
                        st.markdown(f"**Q{global_idx + 1}: {q.get('prompt', '')}**")

                        # Question audio - hidden player
                        q_audio = q.get('prompt_audio_file', '')
                        audio_path = fix_audio_path(q_audio, student_path, current_day)
                        
                        if audio_path and os.path.exists(audio_path):
                            if st.button(f"🔊 Play Question Audio", key=f"q_audio_{current_day}_{global_idx}"):
                                play_audio_hidden(audio_path)
                        elif audio_path:
                            st.warning(f"Question audio file not found: {audio_path}")
                        
                        # Handle dictation audio if present
                        if q.get('question_type') == 'text_input_dictation':
                            dictation_audio = q.get('dictation_audio_file', '')
                            dictation_path = fix_audio_path(dictation_audio, student_path, current_day)
                            
                            if dictation_path and os.path.exists(dictation_path):
                                if st.button(f"🔊 Play Dictation", key=f"dictation_{current_day}_{global_idx}"):
                                    play_audio_hidden(dictation_path)
                            elif dictation_path:
                                st.warning(f"Dictation audio file not found: {dictation_path}")

                        # Render answer input with option buttons and audio buttons
                        answer_key = f"answer_{current_day}_{global_idx}"
                        if q.get('answer_type') == 'single_select':
                            options = q.get('options', [])
                            
                            # Display current selection if any
                            current_answer = st.session_state.answers.get(answer_key, None)
                            if current_answer:
                                st.info(f"Selected: {current_answer}")
                            
                            # Create buttons for each option
                            for opt_idx, option in enumerate(options):
                                label = option.get('text', f"Option {opt_idx+1}")
                                opt_audio = option.get('audio_file', '')
                                
                                # Create columns for answer button and audio button
                                col1, col2 = st.columns([5, 1])
                                
                                with col1:
                                    # Answer selection button
                                    button_label = f"{'✓ ' if current_answer == label else ''}{label}"
                                    if st.button(button_label, key=f"answer_{current_day}_{global_idx}_{opt_idx}", use_container_width=True):
                                        st.session_state.answers[answer_key] = label
                                        st.rerun()
                                
                                with col2:
                                    # Audio button (if audio exists)
                                    if opt_audio and opt_audio != "[Path to audio]":
                                        audio_path = fix_audio_path(opt_audio, student_path, current_day)
                                        
                                        if audio_path and os.path.exists(audio_path):
                                            if st.button("🔊", key=f"opt_audio_{current_day}_{global_idx}_{opt_idx}"):
                                                play_audio_hidden(audio_path)
                                        elif audio_path:
                                            st.warning(f"Option audio file not found: {audio_path}")
                        
                        elif q.get('answer_type') == 'text_input':
                            st.session_state.answers[answer_key] = st.text_input("Your Answer:", key=answer_key)

                    # Check if all questions on current page are answered
                    all_answered = all(
                        st.session_state.answers.get(f"answer_{current_day}_{start_idx + i}")
                        for i in range(len(current_questions))
                    )

                    if all_answered:
                        if page + 1 < total_pages:
                            if st.button("Next Questions"):
                                st.session_state.question_page += 1
                                st.rerun()
                        else:
                            # Mark day complete and allow continue to next day
                            current_index = all_days.index(current_day)
                            if current_index + 1 < len(all_days):
                                next_day = all_days[current_index + 1]
                                if st.button("✅ Continue to Next Day"):
                                    st.session_state.completed_days.add(current_day)
                                    st.session_state.current_day = next_day
                                    st.session_state.question_page = 0
                                    # Clear answers for new day but keep opening_audio_played
                                    st.session_state.answers = {}
                                    st.rerun()
                            else:
                                st.success("🎉 You have completed all available days!")
                    else:
                        st.warning("Please answer all questions to continue.")
        else:
            st.error("No activities found for the current day.")

if __name__ == "__main__":
    main()
