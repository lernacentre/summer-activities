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
    base_prefix = "Summer_Activities"  # No trailing slash
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=base_prefix)
        
        all_keys = []
        for page in pages:
            if 'Contents' in page:
                all_keys.extend([obj['Key'] for obj in page['Contents']])
        
        st.info(f"Total keys found: {len(all_keys)}")
        
        # Debug: Show the actual structure
        st.write("First 20 keys to understand structure:")
        for i, key in enumerate(all_keys[:20]):
            st.write(f"{i}: {key}")
            parts = key.split('/')
            st.write(f"   Parts: {parts}")
            st.write(f"   Part[0]: '{parts[0] if len(parts) > 0 else 'N/A'}'")
            st.write(f"   Part[1]: '{parts[1] if len(parts) > 1 else 'N/A'}'")
            st.write(f"   Part[2]: '{parts[2] if len(parts) > 2 else 'N/A'}'")
            st.write(f"   Part[3]: '{parts[3] if len(parts) > 3 else 'N/A'}'")
            st.write("---")
        
        # Fixed logic - adjust based on actual structure
        for key in all_keys:
            # Skip the key if it's just a folder
            if key.endswith('/'):
                continue
                
            parts = key.split('/')
            
            # Debug specific patterns
            if "Group" in key and "day" in key:
                st.success(f"Found group+day pattern: {key}")
            
            # Assuming structure: Summer_Activities/Group1/student_name/day1/...
            if len(parts) >= 4:
                # parts[0] = "Summer_Activities"
                # parts[1] = "Group1" 
                # parts[2] = "student_name"
                # parts[3] = "day1" or similar
                
                group = parts[1]
                potential_student = parts[2]
                
                # Check if this is actually a student (not passwords.json)
                if (group.startswith("Group") and 
                    potential_student and 
                    potential_student != "passwords.json" and
                    not potential_student.endswith('/')):
                    
                    # Check if this student has day folders
                    student_path = f"{base_prefix}/{group}/{potential_student}/"
                    has_day_content = any(
                        k.startswith(student_path) and '/day' in k 
                        for k in all_keys
                    )
                    
                    if has_day_content:
                        if potential_student not in student_to_group:
                            student_to_group[potential_student] = group
                            st.write(f"✅ Added student: {potential_student} from {group}")
        
        return student_to_group
        
    except Exception as e:
        st.error(f"Error in test_get_all_students: {e}")
        import traceback
        st.error(traceback.format_exc())
        return {}

result = test_get_all_students()
st.write(f"\n**Final result:** {len(result)} students found")
st.write(result)

# Debug 5: Test specific student lookup
st.header("5. Test specific student lookup:")
test_student = st.text_input("Enter a student name to test:", "emma_jones")
test_group = st.text_input("Enter group number:", "Group1")

if st.button("Test Student"):
    test_prefix = f"Summer_Activities/{test_group}/{test_student}/"
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=test_prefix,
            MaxKeys=20
        )
        
        if 'Contents' in response:
            st.success(f"Found {len(response['Contents'])} objects for {test_student}")
            for obj in response['Contents']:
                st.write(f"  - {obj['Key']}")
        else:
            st.warning(f"No objects found for prefix: {test_prefix}")
            
    except Exception as e:
        st.error(f"Error: {e}")

# Debug 6: Check case sensitivity
st.header("6. Case sensitivity check:")
response = s3.list_objects_v2(
    Bucket=BUCKET_NAME,
    Prefix="Summer_Activities/",
    MaxKeys=10
)

if 'Contents' in response:
    st.write("Checking case patterns:")
    for obj in response['Contents']:
        key = obj['Key']
        if 'group' in key.lower():
            st.write(f"Found 'group' (lowercase): {key}")
        if 'Group' in key:
            st.write(f"Found 'Group' (capitalized): {key}")
