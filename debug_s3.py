import streamlit as st
import boto3
from botocore.exceptions import ClientError

st.title("S3 Structure Debug")

# S3 Configuration
try:
    AWS_ACCESS_KEY_ID = st.secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]
    BUCKET_NAME = "summer-activities-streamli-app"
    BUCKET_REGION = "eu-north-1"
    
    s3 = boto3.client(
        's3',
        region_name=BUCKET_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    st.success("✅ Connected to S3")
    
except Exception as e:
    st.error(f"Connection error: {e}")
    st.stop()

# Debug 1: List top-level folders
st.header("1. Top-level folders in bucket:")
try:
    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Delimiter='/',
        MaxKeys=20
    )
    
    if 'CommonPrefixes' in response:
        for prefix in response['CommonPrefixes']:
            st.write(f"📁 {prefix['Prefix']}")
    else:
        st.warning("No top-level folders found")
        
except Exception as e:
    st.error(f"Error: {e}")

# Debug 2: List everything under Summer_Activities
st.header("2. Contents of Summer_Activities folder:")
try:
    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix="Summer_Activities/",
        MaxKeys=50
    )
    
    if 'Contents' in response:
        st.write(f"Found {len(response['Contents'])} objects:")
        for obj in response['Contents'][:20]:
            st.write(f"- {obj['Key']}")
        if len(response['Contents']) > 20:
            st.write(f"... and {len(response['Contents']) - 20} more")
    else:
        st.warning("No objects found in Summer_Activities/")
        
except Exception as e:
    st.error(f"Error: {e}")

# Debug 3: Show folder structure
st.header("3. Folder structure analysis:")
try:
    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix="Summer_Activities/",
        MaxKeys=100
    )
    
    if 'Contents' in response:
        # Parse structure
        groups = set()
        students = set()
        passwords_files = []
        day_folders = []
        
        for obj in response['Contents']:
            key = obj['Key']
            parts = key.split('/')
            
            if len(parts) >= 2 and parts[1]:
                groups.add(parts[1])
            
            if len(parts) >= 3 and parts[2]:
                if parts[2] == "passwords.json":
                    passwords_files.append(key)
                else:
                    students.add(f"{parts[1]}/{parts[2]}")
            
            if len(parts) >= 4 and parts[3].startswith("day"):
                day_folders.append(key)
        
        st.write(f"**Groups found:** {len(groups)}")
        for g in sorted(groups):
            st.write(f"  - {g}")
            
        st.write(f"\n**Password files found:** {len(passwords_files)}")
        for p in passwords_files[:5]:
            st.write(f"  - {p}")
            
        st.write(f"\n**Students found:** {len(students)}")
        for s in sorted(students)[:10]:
            st.write(f"  - {s}")
        if len(students) > 10:
            st.write(f"  ... and {len(students) - 10} more")
            
        st.write(f"\n**Day folders found:** {len(day_folders)}")
        
except Exception as e:
    st.error(f"Error: {e}")

# Debug 4: Test get_all_students function
st.header("4. Testing get_all_students logic:")

def test_get_all_students():
    student_to_group = {}
    base_prefix = "Summer_Activities/"
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=base_prefix)
        
        all_keys = []
        for page in pages:
            if 'Contents' in page:
                all_keys.extend([obj['Key'] for obj in page['Contents']])
        
        st.info(f"Total keys found: {len(all_keys)}")
        
        # Show sample keys
        st.write("Sample keys:")
        for key in all_keys[:10]:
            st.write(f"  - {key}")
            parts = key.split('/')
            st.write(f"    Parts: {parts}")
            st.write(f"    Length: {len(parts)}")
            if len(parts) >= 4:
                st.write(f"    Group check: {parts[1].startswith('Group')}")
                st.write(f"    Student: {parts[2]}")
        
        # Original logic
        for key in all_keys:
            parts = key.split('/')
            if len(parts) >= 4:
                if parts[1].startswith("Group") and parts[2] and parts[2] != "passwords.json":
                    group = parts[1]
                    student = parts[2]
                    
                    student_prefix = f"Summer_Activities/{group}/{student}/"
                    has_days = any(k.startswith(student_prefix + "day") for k in all_keys)
                    
                    if has_days:
                        student_to_group[student] = group
                        st.write(f"✅ Found student: {student} in {group}")
        
        return student_to_group
        
    except Exception as e:
        st.error(f"Error: {e}")
        return {}

result = test_get_all_students()
st.write(f"\n**Final result:** {len(result)} students found")
st.write(result)
