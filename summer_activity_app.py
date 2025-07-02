import streamlit as st
import os
import json

# --- CONFIG ---
DATA_DIR = "data/Group7"
st.set_page_config("📘 Literacy App", layout="centered")

# --- HELPERS ---
def load_student_data(student_id):
    with open(os.path.join(DATA_DIR, f"{student_id}.json"), "r") as f:
        return json.load(f)

def save_student_data(student_id, data):
    with open(os.path.join(DATA_DIR, f"{student_id}.json"), "w") as f:
        json.dump(data, f, indent=2)

def get_next_incomplete_day(data):
    for day_key, content in data.items():
        if not content.get("complete", False):
            return day_key, content
    return None, None

def calculate_progress(data):
    total = len(data)
    done = sum(1 for d in data.values() if d.get("complete"))
    return int((done / total) * 100)

# --- UI ---
st.title("🎓 Literacy Activities")
st.subheader("Log in to begin your learning")

# Step 1: Student Login Dropdown
student_files = [f.replace(".json", "") for f in os.listdir(DATA_DIR) if f.endswith(".json")]
student_names = [f.replace("_", " ").title() for f in student_files]
selected_name = st.selectbox("Select your name", ["-- Select --"] + student_names)

if selected_name != "-- Select --":
    student_id = selected_name.lower().replace(" ", "_")
    data = load_student_data(student_id)

    st.success(f"✅ Welcome, {selected_name}!")

    # Step 2: Progress Tracker
    progress = calculate_progress(data)
    st.metric("Progress", f"{progress}% Complete")

    # Step 3: Get next day in sequence
    next_day, activity = get_next_incomplete_day(data)

    if not next_day:
        st.success("🎉 You have completed all your activities!")
        st.balloons()
        st.stop()

    st.header(f"📘 Activity: {next_day.replace('_', ' ').title()}")

    # Step 4: Display Activity Form
    with st.form("activity_form"):
        responses = {}

        for field in activity["fields"]:
            label = f"**{field['label']}**"
            ftype = field["type"]
            fid = field["id"]
            content = field.get("content", "")

            st.markdown(label)

            if ftype == "text_input":
                responses[fid] = st.text_input("", value="")
            elif ftype == "text_area":
                responses[fid] = st.text_area("", value="")
            elif ftype == "static":
                st.info(content)
            elif ftype == "checkbox":
                for word in content:
                    st.checkbox(word, key=f"{fid}_{word}")
            elif ftype == "radio":
                responses[fid] = st.radio("Choose one:", options=field["options"])

        submitted = st.form_submit_button("✅ Submit")

    # Step 5: Mark complete and save
    if submitted:
        data[next_day]["complete"] = True
        save_student_data(student_id, data)
        st.success(f"✅ {next_day.replace('_', ' ').title()} marked as complete!")
        st.rerun()
