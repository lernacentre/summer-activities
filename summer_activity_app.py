# app.py
import streamlit as st

# Set the page layout and title
st.set_page_config(page_title="Student Literacy Login", layout="centered")
st.title("📘 Student Literacy Login Portal")

# Session state to track login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.student_id = None

# Login logic
def login():
    st.subheader("🔐 Login")
    with st.form("login_form"):
        name = st.text_input("Enter your name or ID")
        submit = st.form_submit_button("Login")
        if submit:
            if name.strip() == "":
                st.warning("Please enter a valid name or ID.")
            else:
                st.session_state.student_id = name.lower().replace(" ", "_")
                st.session_state.logged_in = True
                st.success(f"Welcome, {name.title()}!")

# Show login or dashboard
if not st.session_state.logged_in:
    login()
else:
    st.success(f"🎉 Logged in as: {st.session_state.student_id.title()}")
    st.write("You are now logged in. (Daily activities will go here.)")

    # Logout
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.student_id = None
        st.experimental_rerun()
