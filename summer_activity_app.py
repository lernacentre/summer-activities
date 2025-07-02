import streamlit as st
import os
import json

DATA_DIR = "data/Group7"

# Get all student files
student_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]

# Extract names from filenames
student_names = [f.replace(".json", "").replace("_", " ").title() for f in student_files]

# Dropdown login
selected_name = st.selectbox("Select your name", ["-- Select --"] + student_names)

if selected_name and selected_name != "-- Select --":
    student_id = selected_name.lower().replace(" ", "_")
    json_path = os.path.join(DATA_DIR, f"{student_id}.json")

    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            student_data = json.load(f)
        st.success(f"✅ Welcome, {selected_name}!")
        # ... continue with activity display ...
    else:
        st.error("Could not load student file.")
