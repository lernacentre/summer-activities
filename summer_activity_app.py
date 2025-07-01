import streamlit as st
import pandas as pd
from PIL import Image

# Set page title and icon
st.set_page_config(page_title="Lerna Summer Literacy", page_icon="📘", layout="centered")

# Load student data (if needed later)
# students = pd.read_csv("students.csv")

# Display logo
st.image("images/lernacentre_logo-min.png", width=180)  # Adjust path & size as needed

# Program title
st.markdown(
    "<h1 style='text-align: center; color: #2a5d84;'>📘 Lerna Summer Literacy Program</h1>",
    unsafe_allow_html=True
)

st.markdown("---")  # Horizontal line

# Login form
st.subheader("🔐 Student Login")
name = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    # You can replace this with a real authentication check later
    if name.strip() != "" and password.strip() != "":
        st.success(f"Welcome back, {name.title()}! 🎉")
        st.info("We'll load your personalized dashboard next...")
    else:
        st.error("Please enter both username and password.")
