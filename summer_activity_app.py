import os
import re
import json
import pandas as pd
import pdfplumber
from docx import Document
import openai
from elevenlabs import client as elevenlabs_client
from elevenlabs import save
import hashlib

# --- SETTINGS ---
BASE_DIR = '../../SLG_Mar25/OG_Lesson Plans/LRC_Final_OG_Lesson Plans/'
OUTPUT_DIR = os.path.join(BASE_DIR, "Summer_Activities")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio_files")
my_api_key = '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'
ELEVENLABS_API_KEY = 'your_elevenlabs_api_key_here'  # Add your ElevenLabs API key

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Initialize clients
openai_client = openai.OpenAI(api_key=my_api_key)
elevenlabs = elevenlabs_client.ElevenLabs(api_key=ELEVENLABS_API_KEY)

# --- AUDIO GENERATION ---
def generate_audio_elevenlabs(text, student_name, activity_type="dictation"):
    """
    Generate audio using ElevenLabs API
    Uses British voices for UK curriculum
    """
    try:
        # Generate unique filename
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        filename = f"{student_name.lower().replace(' ', '_')}_{activity_type}_{text_hash}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        
        # Skip if already exists
        if os.path.exists(filepath):
            print(f"   🔊 Audio already exists: {filename}")
            return filepath
        
        # Generate audio with British voice
        # Available British voices: "Charlotte", "Daniel", "Lily", "George"
        audio = elevenlabs.generate(
            text=text,
            voice="Charlotte",  # British female voice
            model="eleven_monolingual_v1"
        )
        
        # Save audio file
        save(audio, filepath)
        print(f"   🔊 Generated audio: {filename}")
        return filepath
        
    except Exception as e:
        print(f"   ⚠️ Audio generation failed: {e}")
        return None

def list_available_voices():
    """List all available ElevenLabs voices"""
    try:
        voices = elevenlabs.voices.get_all()
        british_voices = []
        for voice in voices:
            if voice.labels and any('british' in label.lower() or 'uk' in label.lower() for label in voice.labels.values()):
                british_voices.append(voice.name)
                print(f"British voice available: {voice.name}")
        return british_voices
    except Exception as e:
        print(f"Error listing voices: {e}")
        return []

# --- HELPERS ---

def extract_group_info(folder_name):
    print(f"🔍 Attempting to extract group info from: {folder_name}")
    group_match = re.search(r'Group(\d+)', folder_name)
    year_match = re.search(r'Year(\d+)', folder_name)
    skill_level_match = re.search(r'Skill Level\s*Year\d+', folder_name)

    group_number = group_match.group(1) if group_match else None
    year_level = year_match.group(1) if year_match else None
    skill_level = skill_level_match.group(0) if skill_level_match else None

    print(f"    ➤ group_number: {group_number}, year_level: {year_level}, skill_level: {skill_level}")
    return group_number, year_level, skill_level

def extract_text_from_docx(path):
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        print(f"⚠️ Error reading DOCX {path}: {e}")
        return ""

def extract_tables_from_pdf(pdf_path):
    tables_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        clean_row = [cell.strip() if cell else "" for cell in row]
                        tables_text.append(" | ".join(clean_row))
        return "\n".join(tables_text)
    except Exception as e:
        print(f"⚠️ Error reading PDF {pdf_path}: {e}")
        return ""

def normalize_student_profile(row):
    return {
        "name": row.get("Your Name"),
        "interests": row.get("What are your hobbies or interests outside of school? \n📝 (Write or tell us what you like doing — games, music, sport, reading, etc.)"),
        "enjoys": row.get("What helps you enjoy learning? (Tick any that apply)"),
        "difficulties": row.get("What do you find difficult or want to improve?\n🛠️ (This could be something in school, at home, or in your learning.)"),
        "preferred_work": row.get("What kind of work do you enjoy the most here?"),
        "sentiment": row.get("How do you feel about your time at Lexicon Centre this half term?")
    }

def build_prompt(student, og_text, skills_text, year_level, skill_level, previous_content):
    print('name: ', student['name'])
    print('interests: ', student['interests'])
    print('enjoys: ', student['enjoys'])
    print('prefered work: ', student['preferred_work'])
    print('difficulties', student['difficulties'])
    
    # Extract first name for more natural usage
    student_first_name = student['name'].split()[0]
    
    # Format previous content for the prompt
    previous_content_str = ""
    if previous_content:
        previous_content_str = "\n\nPREVIOUS CONTENT TO AVOID REPEATING:\n"
        for day, content in previous_content.items():
            previous_content_str += f"\n{day}:\n"
            if 'dictation' in content:
                previous_content_str += f"- Dictation: {content['dictation']}\n"
            if 'passage' in content:
                previous_content_str += f"- Passage Theme: {content['passage_theme']}\n"
                previous_content_str += f"- Passage Extract: {content['passage'][:100]}...\n"
    
    return f"""
You are a British literacy tutor. Create a 15-minute phonics and comprehension activity pack for the following student:

- Name: {student['name']} (use {student_first_name} in passages)
- Interests: {student['interests']}
- Struggles: {student['difficulties']}
- Enjoys: {student['enjoys']}
- Preferred work: {student['preferred_work']}
- Target Year Level: Year {year_level}
- Current Skill Level: {skill_level}

LESSON CONTENT TO USE:
OG Lesson Content:
{og_text}

SkillsApp Content:
{skills_text}

{previous_content_str}

AUDIO REQUIREMENTS:
For EVERY activity that involves listening (dictation, spelling, "teacher says"), include:
- "audio_text": The EXACT text to be spoken (no quotation marks)
- "audio_instructions": Brief instruction like "Listen carefully and choose the correct spelling"

CRITICAL REQUIREMENTS:
1. EXTRACT and USE the ACTUAL concepts from BOTH lessons
2. Grammar must match SkillsApp lesson complexity (not basic nouns/verbs)
3. Include vocabulary building strategies from SkillsApp
4. Add multiple fill-in-the-blank writing exercises
5. Test advanced concepts, not simplified versions
6. Include audio_text for ALL listening activities

EXPANDED ACTIVITY STRUCTURE (15 minutes total):

1. DICTATION (1.5 minutes)
   - Complex sentence about {student_first_name} using OG patterns
   - MUST include "audio_text" field

2. MORPHOLOGY - Greek/Latin Analysis (1 minute)
   - Test actual roots/combining forms from OG lesson

3. VOCABULARY BUILDING STRATEGY from SkillsApp (1.5 minutes)
   - Apply specific strategy taught in lesson

4. ADVANCED GRAMMAR from SkillsApp (1.5 minutes)
   - Test complex concepts from lesson

5. SENTENCE STRUCTURE - Fill in the Blank (1.5 minutes)
   - Practice patterns from SkillsApp

6. PARAGRAPH STRUCTURE - Fill in the Blank (1.5 minutes)
   - Transition and cohesion practice

7. PREFIX/SUFFIX APPLICATION (1 minute)
   - Using morphemes from OG lesson

8. INTEGRATED READING PASSAGE (4 minutes)
   - Comprehensive passage with 6 varied questions

9-11. Additional writing practice activities

Return valid JSON with audio fields included:

```json
{{
  "activity_pack": {{
    "duration": "15 minutes",
    "activities": [
      {{
        "activity_number": 1,
        "source": "OG-Dictation",
        "component": "Complex Sentence Dictation",
        "time_allocation": "1.5 minutes",
        "instructions": "Choose the correctly spelled sentence",
        "questions": [
          {{
            "prompt": "The teacher says: '[Complex sentence]'",
            "audio_text": "[Exact sentence without quotes]",
            "audio_instructions": "Listen carefully and choose the correct spelling",
            "options": [
              "[Correct sentence]",
              "[Error in Greek/Latin root spelling]",
              "[Error in suffix attachment]",
              "[Multiple morphological errors]"
            ],
            "correct": [0]
          }}
        ]
      }},
      // ... rest of activities with audio_text where needed
    ]
  }}
}}

Return valid JSON only — no extra explanation or text output."""

def extract_content_for_tracking(activity_data):
    """Extract dictation sentence and passage content for tracking"""
    content = {}
    
    if "activity_pack" in activity_data:
        activities = activity_data["activity_pack"].get("activities", [])
        
        # Extract dictation sentence
        for activity in activities:
            if activity.get("source") == "OG-Dictation":
                questions = activity.get("questions", [])
                if questions:
                    # Get audio_text if available, otherwise extract from prompt
                    audio_text = questions[0].get("audio_text", "")
                    if audio_text:
                        content["dictation"] = audio_text
                    else:
                        prompt = questions[0].get("prompt", "")
                        if "The teacher says:" in prompt:
                            dictation = prompt.split("The teacher says:")[1].strip().strip("'\"")
                            content["dictation"] = dictation
            
            # Extract reading passage
            if "Reading Passage" in activity.get("component", "") or "passage" in activity:
                passage = activity.get("passage", "")
                if passage:
                    content["passage"] = passage
                    content["passage_theme"] = passage[:100] + "..."
    
    return content

def process_activity_audio(activity_data, student_name):
    """Generate audio files for all listening activities"""
    if "activity_pack" in activity_data:
        activities = activity_data["activity_pack"].get("activities", [])
        
        for activity in activities:
            activity_type = activity.get("component", "").lower()
            questions = activity.get("questions", [])
            
            for q_idx, question in enumerate(questions):
                # Check if this question needs audio
                if "audio_text" in question:
                    audio_text = question["audio_text"]
                    
                    # Generate audio file
                    audio_file = generate_audio_elevenlabs(
                        audio_text, 
                        student_name,
                        activity_type
                    )
                    
                    if audio_file:
                        # Add relative path for web access
                        question["audio_file"] = os.path.relpath(audio_file, OUTPUT_DIR)
                    else:
                        print(f"   ⚠️ Failed to generate audio for: {audio_text[:50]}...")

def call_gpt(prompt):
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

# --- MAIN LOOP ---

# First, check available voices
print("\n🎤 Checking available ElevenLabs voices...")
# list_available_voices()  # Uncomment to see all available voices

for group_folder in os.listdir(BASE_DIR):
    if group_folder == "Summer_Activities":
        continue

    group_path = os.path.join(BASE_DIR, group_folder)
    if not os.path.isdir(group_path):
        continue

    print(f"\n🗂️ Scanning folder: {group_folder}")

    group_number, year_level, skill_level = extract_group_info(group_folder)
    if not (group_number and year_level and skill_level) or group_number != '7':
        print(f"❌ Skipping folder: {group_folder} — group info missing or not Group 7")
        continue

    print(f"✅ Group {group_number} | Year {year_level} | Level {skill_level}")

    group_output_dir = os.path.join(OUTPUT_DIR, f"Group{group_number}")
    group_audio_dir = os.path.join(AUDIO_DIR, f"Group{group_number}")
    os.makedirs(group_output_dir, exist_ok=True)
    os.makedirs(group_audio_dir, exist_ok=True)

    # --- Load OG Lessons ---
    og_lessons = {}
    for f in os.listdir(group_path):
        if f.endswith(".docx") and "OG" in f:
            og_lessons[f] = extract_text_from_docx(os.path.join(group_path, f))
    print(f"📄 Found {len(og_lessons)} OG Lessons")

    # --- Load SkillsApp Tables ---
    skills_lessons = {}
    skills_path = os.path.join(group_path, "skillsapp_lessons")
    if os.path.exists(skills_path):
        for f in os.listdir(skills_path):
            if f.endswith(".pdf"):
                skills_lessons[f] = extract_tables_from_pdf(os.path.join(skills_path, f))
    print(f"📘 Found {len(skills_lessons)} SkillsApp PDFs")

    # --- Load Reflection Form ---
    reflection_data = []
    for f in os.listdir(group_path):
        if f.endswith(".xlsx") and "Reflection" in f:
            print(f"📥 Reading: {f}")
            df = pd.read_excel(os.path.join(group_path, f))
            reflection_data = [normalize_student_profile(row) for _, row in df.iterrows()]
            print(f"👧 Found {len(reflection_data)} students")
            break

    if not reflection_data:
        print("⚠️ No reflection form data — skipping")
        continue

    # --- Generate Activities Per Student ---
    for student in reflection_data:
        if not student["name"]:
            print("⚠️ Skipping unnamed student")
            continue

        student_id = student["name"].strip().lower().replace(" ", "_")
        student_activities = {}
        print(f"🧠 Generating for: {student['name']}")
        
        # Track previous content for this student
        previous_content = {}

        for day in range(1, 6):
            og_text = list(og_lessons.values())[day % len(og_lessons)] if og_lessons else ""
            skills_text = list(skills_lessons.values())[day % len(skills_lessons)] if skills_lessons else ""

            prompt = build_prompt(student, og_text, skills_text, year_level, skill_level, previous_content)
            try:
                ai_response = call_gpt(prompt)
                activity_data = json.loads(ai_response)
                
                # Extract the activity_pack directly
                if "activity_pack" in activity_data:
                    activity_content = activity_data["activity_pack"]
                else:
                    activity_content = activity_data
                
                # Generate audio files for this day's activities
                print(f"   🎵 Generating audio for Day {day}...")
                process_activity_audio(activity_data, student["name"])
                
                # Extract content for tracking
                day_content = extract_content_for_tracking(activity_data)
                if day_content:
                    previous_content[f"Day {day}"] = day_content
                    print(f"   📝 Tracked content for Day {day}")
                    
            except Exception as e:
                print(f"[⚠️ Error] GPT failed for {student_id} Day {day}: {e}")
                continue

            # Create a single field with the activity pack content
            student_activities[f"day_{day}"] = {
                "complete": False,
                "fields": [
                    {
                        "id": "activity_pack",
                        "label": "Activity Pack",
                        "content": activity_content,
                        "type": "text_area"
                    }
                ]
            }

        output_path = os.path.join(group_output_dir, f"{student_id}.json")
        with open(output_path, "w") as f:
            json.dump(student_activities, f, indent=2)
        print(f"✅ Saved: {output_path}")

print("\n🎉 All activity generation complete!")
print(f"📂 Audio files saved in: {AUDIO_DIR}")
