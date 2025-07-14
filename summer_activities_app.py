import streamlit as st
import boto3
from botocore.exceptions import ClientError

st.title("S3 Connection Test")

# Test 1: Check if secrets exist
st.header("1. Checking Secrets")
try:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    st.success("✅ Secrets found")
    st.write(f"Access Key (first 10 chars): {AWS_ACCESS_KEY_ID[:10]}...")
except KeyError as e:
    st.error(f"❌ Missing secret: {e}")
    st.stop()

# Test 2: Create S3 client
st.header("2. Creating S3 Client")
try:
    s3 = boto3.client(
        's3',
        region_name='eu-north-1',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    st.success("✅ S3 client created")
except Exception as e:
    st.error(f"❌ Failed to create S3 client: {e}")
    st.stop()

# Test 3: List buckets
st.header("3. Testing S3 Access")
try:
    response = s3.list_buckets()
    buckets = [b['Name'] for b in response['Buckets']]
    st.success(f"✅ Can access S3. Found {len(buckets)} buckets")
    st.write("Buckets:", buckets)
except Exception as e:
    st.error(f"❌ Cannot list buckets: {e}")
    st.stop()

# Test 4: Access specific bucket
st.header("4. Accessing Your Bucket")
BUCKET_NAME = "summer-activities-streamli-app"
try:
    s3.head_bucket(Bucket=BUCKET_NAME)
    st.success(f"✅ Can access bucket: {BUCKET_NAME}")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404':
        st.error(f"❌ Bucket not found: {BUCKET_NAME}")
    else:
        st.error(f"❌ Error accessing bucket: {error_code}")
    st.stop()

# Test 5: List some objects
st.header("5. Listing Objects")
try:
    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix="Summer_Activities/",
        MaxKeys=10
    )
    
    if 'Contents' in response:
        st.success(f"✅ Found {len(response['Contents'])} objects")
        for obj in response['Contents'][:5]:
            st.write(f"- {obj['Key']}")
    else:
        st.warning("No objects found in Summer_Activities/")
except Exception as e:
    st.error(f"❌ Error listing objects: {e}")

st.success("🎉 All tests passed! Your S3 connection is working.")
