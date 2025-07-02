import streamlit as st
import os
import json

# ---------- SETTINGS ----------
DATA_DIR = "summer_activities/Group 7"
st.set_page_config("📘 Literacy App", layout="centered")
st.title("🎓 Summer Literacy Activities")

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

# ---------- LOGIN ----------
student_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
student_names = [f.replace(".json", "").replace("_", " ").title() for f in student_files]
selected_name = st.selectbox("Select your name:", ["-- Select --"] + student_names)

if selected_name != "-- Select --":
    student_id = selected_name.lower().replace(" ", "_")
    
    try:
        student_data = load_student_data(student_id)
    except FileNotFoundError:
        st.error("Student file not found.")
        st.stop()
    
    st.success(f"✅ Welcome, {selected_name}!")
    
    # ---------- PROGRESS ----------
    progress = calculate_progress(student_data)
    st.metric("Progress", f"{progress}% Complete")
    
    # ---------- NEXT ACTIVITY ----------
    next_day, activity = get_next_day(student_data)
    
    if not next_day:
        st.success("🎉 You've completed all your activities!")
        st.balloons()
        st.stop()
    
    # Prevent infinite rerun loop
    if st.session_state.get("completed_day") == next_day:
        st.success(f"✅ {next_day.replace('_', ' ').title()} marked as complete!")
        del st.session_state["completed_day"]
        st.rerun()
    
    st.subheader(f"📘 Activity: {next_day.replace('_', ' ').title()}")
    st.caption(f"🔍 This activity has {len(activity['fields'])} fields.")
    
    # ---------- FORM ----------
    with st.form("activity_form"):
        responses = {}
        
        for i, field in enumerate(activity["fields"]):
            fid = field.get("id", f"field_{i}")
            label = field.get("label", f"Field {i}")
            ftype = field.get("type", "text_input")
            content = field.get("content", "")
            
            # Display the field label
            st.markdown(f"**{label}**")
            
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
        submitted = st.form_submit_button("✅ Submit Activity", use_container_width=True)
    
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
