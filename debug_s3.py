import streamlit as st
import time

st.title("S3 Structure Debug - Optimized")

# Lazy load boto3 to improve startup time
@st.cache_resource
def get_s3_client():
    """Create and cache S3 client - only imported when needed"""
    import boto3
    from botocore.config import Config
    
    # Add connection config for better performance
    config = Config(
        region_name='eu-north-1',
        retries={'max_attempts': 2, 'mode': 'adaptive'},
        max_pool_connections=10
    )
    
    try:
        client = boto3.client(
            's3',
            config=config,
            aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
        )
        return client, None
    except Exception as e:
        return None, str(e)

# Show immediate feedback
st.info("🚀 App loaded! Click buttons below to connect to S3.")

# S3 Configuration
BUCKET_NAME = "summer-activities-streamli-app"
BUCKET_REGION = "eu-north-1"

# Debug 1: Test Connection (only when button clicked)
st.header("1. Test S3 Connection")
if st.button("Connect to S3"):
    with st.spinner("Connecting..."):
        start = time.time()
        s3, error = get_s3_client()
        elapsed = time.time() - start
        
        if error:
            st.error(f"❌ Connection failed: {error}")
        else:
            st.success(f"✅ Connected to S3 in {elapsed:.2f}s")
            
            # Test bucket access
            try:
                response = s3.head_bucket(Bucket=BUCKET_NAME)
                st.success(f"✅ Bucket '{BUCKET_NAME}' is accessible")
            except Exception as e:
                st.error(f"❌ Bucket access error: {e}")

# Debug 4: Optimized get_all_students
st.header("4. Get Students (Optimized)")

@st.cache_data(ttl=300, show_spinner=False)
def get_students_cached(max_groups=5):
    """Cached version of student retrieval"""
    s3, error = get_s3_client()
    if error:
        return {}, error
    
    students = {}
    
    try:
        # Quick scan approach - check specific groups
        for group_num in range(1, max_groups + 1):
            group_name = f"Group{group_num}"
            prefix = f"Summer_Activities/{group_name}/"
            
            # Use paginator for efficiency
            paginator = s3.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=BUCKET_NAME,
                Prefix=prefix,
                Delimiter='/'
            )
            
            for page in page_iterator:
                if 'CommonPrefixes' in page:
                    for prefix_info in page['CommonPrefixes']:
                        student_folder = prefix_info['Prefix']
                        parts = student_folder.rstrip('/').split('/')
                        if len(parts) >= 3:
                            student_name = parts[-1]
                            if student_name != "passwords.json":
                                students[student_name] = group_name
                                
                # Limit check
                if len(students) > 100:  # Safety limit
                    break
                    
        return students, None
        
    except Exception as e:
        return {}, str(e)

# Only run when button clicked
col1, col2 = st.columns(2)
with col1:
    if st.button("Quick Scan (Groups 1-5)"):
        with st.spinner("Scanning..."):
            students, error = get_students_cached(max_groups=5)
            if error:
                st.error(f"Error: {error}")
            else:
                st.success(f"Found {len(students)} students")
                if students:
                    st.write("Sample students:")
                    for i, (student, group) in enumerate(list(students.items())[:10]):
                        st.write(f"- {student} → {group}")

with col2:
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared!")

# Alternative: Direct prefix check
st.header("5. Direct Student Check")

student_name = st.text_input("Enter student name to check:")
if student_name and st.button("Check Student"):
    s3, error = get_s3_client()
    if error:
        st.error(f"Connection error: {error}")
    else:
        found = False
        for group_num in range(1, 11):  # Check first 10 groups
            prefix = f"Summer_Activities/Group{group_num}/{student_name}/"
            try:
                response = s3.list_objects_v2(
                    Bucket=BUCKET_NAME,
                    Prefix=prefix,
                    MaxKeys=1
                )
                if 'Contents' in response:
                    st.success(f"✅ Found {student_name} in Group{group_num}")
                    found = True
                    break
            except Exception as e:
                st.error(f"Error checking Group{group_num}: {e}")
                break
        
        if not found:
            st.warning(f"Student '{student_name}' not found in Groups 1-10")

# Performance monitoring
with st.expander("Performance Tips"):
    st.markdown("""
    ### Optimization Strategies Applied:
    
    1. **Lazy Loading**: boto3 only imported when needed
    2. **Connection Caching**: S3 client cached with @st.cache_resource
    3. **Data Caching**: Results cached with @st.cache_data
    4. **Connection Pooling**: Better connection management
    5. **Immediate UI**: Page loads instantly, S3 only on demand
    
    ### If still experiencing issues:
    - Check Streamlit Cloud logs
    - Consider using environment variables instead of secrets
    - Try deploying with minimal requirements.txt
    - Monitor AWS region latency
    """)

# Footer with diagnostics
st.markdown("---")
if st.checkbox("Show diagnostics"):
    st.write("Session state size:", len(str(st.session_state)))
    import sys
    st.write("Modules loaded:", len(sys.modules))
