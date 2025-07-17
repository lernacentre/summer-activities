import streamlit as st
import boto3
from botocore.exceptions import ClientError

st.title("S3 Structure Debug - Fixed")

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

# Debug 1-3: [Keep your existing code for sections 1-3]

# Debug 4: FIXED get_all_students function with limits
st.header("4. Testing get_all_students logic (LIMITED):")

def test_get_all_students_limited():
    student_to_group = {}
    base_prefix = "Summer_Activities"
    
    try:
        # Add progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        paginator = s3.get_paginator('list_objects_v2')
        
        # Configure pagination with limits
        page_config = {
            'PageSize': 100,  # Items per page
            'MaxItems': 1000  # Total limit
        }
        
        pages = paginator.paginate(
            Bucket=BUCKET_NAME, 
            Prefix=base_prefix,
            PaginationConfig=page_config
        )
        
        all_keys = []
        page_count = 0
        
        # Process with limits
        for page in pages:
            page_count += 1
            status_text.text(f"Processing page {page_count}...")
            progress_bar.progress(min(page_count * 10, 100))
            
            if 'Contents' in page:
                all_keys.extend([obj['Key'] for obj in page['Contents']])
            
            # Stop if too many
            if len(all_keys) > 1000:
                st.warning("Limiting to 1000 objects for performance")
                break
        
        st.info(f"Total keys found: {len(all_keys)}")
        
        # Show sample structure
        st.write("First 10 keys:")
        for i, key in enumerate(all_keys[:10]):
            st.write(f"{i}: {key}")
        
        # Process students
        status_text.text("Processing students...")
        
        for i, key in enumerate(all_keys):
            if i % 100 == 0:
                progress_bar.progress(min(50 + (i / len(all_keys) * 50), 100))
            
            if key.endswith('/'):
                continue
                
            parts = key.split('/')
            
            if len(parts) >= 4:
                group = parts[1]
                potential_student = parts[2]
                
                if (group.startswith("Group") and 
                    potential_student and 
                    potential_student != "passwords.json"):
                    
                    # Quick check for day content
                    if 'day' in key:
                        if potential_student not in student_to_group:
                            student_to_group[potential_student] = group
        
        progress_bar.progress(100)
        status_text.text("Complete!")
        
        return student_to_group
        
    except Exception as e:
        st.error(f"Error: {e}")
        return {}

# Use button to control execution
if st.button("Run Limited Test"):
    with st.spinner("Processing..."):
        result = test_get_all_students_limited()
        st.write(f"\n**Final result:** {len(result)} students found")
        if result:
            st.write("Students found:")
            for student, group in list(result.items())[:20]:
                st.write(f"  - {student} in {group}")
            if len(result) > 20:
                st.write(f"  ... and {len(result) - 20} more")

# Alternative: Quick scan approach
st.header("4b. Alternative: Quick Group Scan")

@st.cache_data(ttl=300)
def quick_scan_groups():
    students = {}
    
    try:
        # Just check first 5 groups
        for group_num in range(1, 6):
            group_name = f"Group{group_num}"
            prefix = f"Summer_Activities/{group_name}/"
            
            response = s3.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=prefix,
                Delimiter='/',
                MaxKeys=50
            )
            
            if 'CommonPrefixes' in response:
                for prefix_info in response['CommonPrefixes']:
                    student_folder = prefix_info['Prefix']
                    parts = student_folder.rstrip('/').split('/')
                    if len(parts) >= 3:
                        student_name = parts[-1]
                        if student_name != "passwords.json":
                            students[student_name] = group_name
        
        return students
        
    except Exception as e:
        st.error(f"Error in quick scan: {e}")
        return {}

if st.button("Run Quick Scan"):
    result = quick_scan_groups()
    st.success(f"Quick scan found {len(result)} students")
    st.write(result)

# Keep your Debug 5 and 6 sections as they are
