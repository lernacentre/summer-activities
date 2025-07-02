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
        st.success("🎉 You’ve completed all your activities!")
        st.balloons()
        st.stop()

    st.subheader(f"📘 Activity: {next_day.replace('_', ' ').title()}")

    # ---------- FORM ----------
    with st.form("activity_form"):
        responses = {}

        for i, field in enumerate(activity["fields"]):
            fid = field["id"]
            label = field["label"]
            ftype = field["type"]
            content = field.get("content", "")

            st.markdown(f"**{label}**")

            if ftype == "text_input":
                responses[fid] = st.text_input("", key=f"{fid}_{i}")
            elif ftype == "text_area":
                responses[fid] = st.text_area("", key=f"{fid}_{i}")
            elif ftype == "static":
                st.info(content)
            elif ftype == "checkbox":
                for j, word in enumerate(content):
                    st.checkbox(word, key=f"{fid}_{j}")
            elif ftype == "radio":
                responses[fid] = st.radio("Choose one:", options=field["options"], key=f"{fid}_{i}")

        submitted = st.form_submit_button("✅ Submit")

    if submitted:
        student_data[next_day]["complete"] = True
        save_student_data(student_id, student_data)
        st.success(f"✅ {next_day.replace('_', ' ').title()} marked as complete!")
        st.rerun()
