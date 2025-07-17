import os
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

import streamlit as st

st.title("🔍 Debug Test")
st.success("✅ Streamlit is working!")

# Test 1: Basic functionality
if st.button("Click me"):
    st.balloons()
    st.write("✅ Buttons work!")

# Test 2: Secrets
try:
    if "AWS_ACCESS_KEY_ID" in st.secrets:
        st.success("✅ Secrets are accessible")
    else:
        st.error("❌ No AWS secrets found")
except Exception as e:
    st.error(f"❌ Secrets error: {e}")

# Test 3: Boto3 import
if st.button("Test Boto3 Import"):
    try:
        import boto3
        st.success("✅ Boto3 imported successfully")
    except Exception as e:
        st.error(f"❌ Boto3 import failed: {e}")

# Test 4: S3 Connection
if st.button("Test S3 Connection"):
    try:
        import boto3
        s3 = boto3.client(
            's3',
            region_name='eu-north-1',
            aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
        )
        # Just test if we can access the bucket
        s3.head_bucket(Bucket='summer-activities-streamli-app')
        st.success("✅ S3 connection works!")
    except Exception as e:
        st.error(f"❌ S3 error: {e}")
