import streamlit as st
import json
import base64
import boto3
from botocore.exceptions import ClientError
from io import BytesIO

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
try:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    BUCKET_NAME = "summer-activities-streamli-app"
    BUCKET_REGION = "eu-north-1"
    
    # Create S3 client
    s3 = boto3.client(
        's3',
        region_name=BUCKET_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Test connection
    s3.head_bucket(Bucket=BUCKET_NAME)
    st.success("✅ Connected to S3")
    
    # Debug mode
    if st.checkbox("🔍 Debug Mode - Show S3 Structure"):
        st.header("S3 Bucket Contents:")
        try:
            # Show top-level folders
            response = s3.list_objects_v2(
                Bucket=BUCKET_NAME,
                Delimiter='/',
                MaxKeys=20
            )
            
            st.subheader("Top-level folders:")
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    st.write(f"📁 {prefix['Prefix']}")
            else:
                st.warning("No top-level folders found")
            
            # Show Summer_Activities contents
            st.subheader("Summer_Activities contents:")
            response = s3.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix="Summer_Activities/",
                MaxKeys=100
            )
            
            if 'Contents' in response:
                st.write(f"Found {len(response['Contents'])} objects:")
                
                # Analyze structure
                groups = set()
                students = {}
                
                for obj in response['Contents'][:50]:
                    key = obj['Key']
                    st.write(f"- {key}")
                    
                    parts = key.split('/')
                    if len(parts) >= 3 and parts[1] and parts[1].startswith("Group"):
                        groups.add(parts[1])
                        if parts[2] and parts[2] != "passwords.json":
                            if parts[1] not in students:
                                students[parts[1]] = set()
                            students[parts[1]].add(parts[2])
                
                st.write(f"\n**Found {len(groups)} groups:**")
                for g in sorted(groups):
                    st.write(f"- {g}")
                    if g in students:
                        st.write(f"  Students: {sorted(students[g])}")
                        
            else:
                st.warning("No objects found in Summer_Activities/")
                
        except Exception as e:
            st.error(f"Debug error: {e}")
    
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

# Helper function to read files from S3
def read_s3_file(s3_key):
    """Read a file from S3 and return its content"""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        return response['Body'].read()
    except ClientError:
        return None

# Get all students from all groups
def get_all_students():
    student_to_group = {}
    base_prefix = "Summer_Activities/"
    
    try:
        # List all objects under Summer_Activities/
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME, 
            Prefix=base_prefix,
            MaxKeys=1000
        )
        
        if 'Contents' not in response:
            return {}
        
        all_keys = [obj['Key'] for obj in response['Contents']]
        
        # Parse keys to find groups and students
        for key in all_keys:
            parts = key.split('/')
            if len(parts) >= 4:  # Summer_Activities/Group/Student/...
                if parts[1].startswith("Group") and parts[2] and parts[2] != "passwords.json":
                    group = parts[1]
                    student = parts[2]
                    
                    # Skip if it's the passwords file
                    if student.endswith("_passwords.txt"):
                        continue
                    
                    # Only add each student once
                    if student not in student_to_group:
                        # Check if this student has day folders
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
    """Create S3 key for audio files"""
    if not audio_file or audio_file == "[Path to audio]":
        return None
    
    if audio_file.startswith("day"):
        return f"{student_s3_prefix}/{audio_file}"
    else:
        return f"{student_s3_prefix}/{current_day}/{audio_file}"

# Load passwords
def load_passwords(group_folder):
    password_key = f"Summer_Activities/{group_folder}/passwords.json"
    content = read_s3_file(password_key)
    
    if content:
        return json.loads(content.decode('utf-8'))
    return {}

# Play audio without showing controls (hidden bar)
def play_audio_hidden(s3_key):
    """Generate audio HTML without triggering rerun"""
    try:
        audio_content = read_s3_file(s3_key)
        if audio_content:
            b64 = base64.b64encode(audio_content).decode()
            audio_html = f"""
                <audio controls autoplay>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            """
            return audio_html
        else:
            return None
    except Exception as e:
        return None

# Main app
def main():
    st.title("Student Activities")
    
    # Get all students
    student_to_group = get_all_students()

    if not student_to_group:
        st.error("No students found")
        st.info("Check if the S3 bucket contains the Summer_Activities folder with the correct structure")
        
        # Show what's in the bucket for debugging
        if st.checkbox("Show S3 bucket contents"):
            response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="Summer_Activities/", MaxKeys=20)
            if 'Contents' in response:
                st.write("Files found:")
                for obj in response['Contents']:
                    st.write(f"- {obj['Key']}")
        return

    if not student_to_group:
        st.error("No students found")
        st.info("Check if the S3 bucket contains the Summer_Activities folder with the correct structure")
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

        # Student S3 prefix
        student_s3_prefix = f"Summer_Activities/{st.session_state.group}/{st.session_state.student}"

        # Load activity_pack.json from each day folder
        all_days = []
        day_to_content = {}

        try:
            # List all objects for this student
            response = s3.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=student_s3_prefix + "/",
                Delimiter='/'
            )
            
            # Get day folders
            day_folders = []
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    folder_name = prefix['Prefix'].rstrip('/').split('/')[-1]
                    if folder_name.startswith("day"):
                        day_folders.append(folder_name)
            
            day_folders.sort(key=lambda x: int(x.replace("day", "")))  # Sort by day number

            for day_folder in day_folders:
                activity_pack_key = f"{student_s3_prefix}/{day_folder}/activity_pack.json"
                content = read_s3_file(activity_pack_key)
                
                if content:
                    data = json.loads(content.decode('utf-8'))
                    day_name = day_folder  # Use folder name as day identifier
                    all_days.append(day_name)
                    day_to_content[day_name] = data

        except ClientError as e:
            st.error(f"Error loading activities: {e}")
            return

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
                        audio_s3_key = fix_audio_path(opening_audio, student_s3_prefix, current_day)
                        
                        if audio_s3_key and read_s3_file(audio_s3_key):
                            st.session_state.opening_audio_played.add(current_day)
                            audio_html = play_audio_hidden(audio_s3_key)
                            if audio_html:
                                # Place audio in a container at the top
                                audio_container = st.container()
                                with audio_container:
                                    st.markdown(audio_html, unsafe_allow_html=True)
                                    st.caption("Opening audio playing...")

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

                        # Question audio - using container to avoid rerun
                        q_audio = q.get('prompt_audio_file', '')
                        audio_s3_key = fix_audio_path(q_audio, student_s3_prefix, current_day)
                        
                        if audio_s3_key and read_s3_file(audio_s3_key):
                            audio_html = play_audio_hidden(audio_s3_key)
                            if audio_html:
                                with st.expander(f"🔊 Play Question Audio"):
                                    st.markdown(audio_html, unsafe_allow_html=True)
                        
                        # Handle dictation audio if present
                        if q.get('question_type') == 'text_input_dictation':
                            dictation_audio = q.get('dictation_audio_file', '')
                            dictation_s3_key = fix_audio_path(dictation_audio, student_s3_prefix, current_day)
                            
                            if dictation_s3_key and read_s3_file(dictation_s3_key):
                                audio_html = play_audio_hidden(dictation_s3_key)
                                if audio_html:
                                    with st.expander(f"🔊 Play Dictation"):
                                        st.markdown(audio_html, unsafe_allow_html=True)

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
                                    # Audio in expander (no rerun)
                                    if opt_audio and opt_audio != "[Path to audio]":
                                        audio_s3_key = fix_audio_path(opt_audio, student_s3_prefix, current_day)
                                        
                                        if audio_s3_key and read_s3_file(audio_s3_key):
                                            audio_html = play_audio_hidden(audio_s3_key)
                                            if audio_html:
                                                st.markdown(audio_html, unsafe_allow_html=True)
                        
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
