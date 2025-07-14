import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import requests
import json
import random
import time

# --- Firebase Initialization ---
# This function initializes the Firebase app, using credentials from Streamlit secrets.
# It checks if the app is already initialized to avoid errors.

def initialize_firebase():
    if not firebase_admin._apps:
        # Load credentials from st.secrets
        # Ensure your secrets.toml file is configured correctly
        creds_json = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        }
        creds = credentials.Certificate(creds_json)
        firebase_admin.initialize_app(creds, {
            'storageBucket': f"{st.secrets['firebase']['project_id']}.appspot.com"
        })
    return firestore.client()

# --- Main App Logic ---

st.set_page_config(layout="wide")
st.title("🤖 GenAI Interview Agent")

# Initialize Firebase and Firestore client
db = initialize_firebase()

# Initialize session state to manage the interview flow
if 'status' not in st.session_state:
    st.session_state.status = 'not_started'
if 'interview_id' not in st.session_state:
    st.session_state.interview_id = None
if 'suggested_question' not in st.session_state:
    st.session_state.suggested_question = "Click 'Suggest Question' to begin."

# --- SCREEN 1: Pre-Interview Setup ---
if st.session_state.status == 'not_started':
    st.header("1. Pre-Interview Setup")
    
    candidate_name = st.text_input("Candidate Name")
    salary_lpa = st.number_input("Candidate Salary Expectation (LPA)", min_value=10, max_value=100, value=30)

    if st.button("Start Interview", disabled=(not candidate_name)):
        # Determine role level based on salary
        role_level = "Senior" if salary_lpa > 35 else "Mid"
        
        # Create a new interview document in Firestore
        doc_ref = db.collection("interviews").document()
        doc_ref.set({
            "candidateName": candidate_name,
            "salaryLPA": salary_lpa,
            "roleLevel": role_level,
            "status": "in_progress",
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        # Update session state to move to the next screen
        st.session_state.interview_id = doc_ref.id
        st.session_state.status = 'in_progress'
        st.rerun()

# --- SCREEN 2: Live Interview Assistance ---
elif st.session_state.status == 'in_progress':
    st.header(f"2. Live Interview Assistance")
    st.info(f"**Interview in Progress for:** `{st.session_state.interview_id}`")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Question Suggester")
        if st.button("Suggest Question"):
            # Fetch a random question from the 'questions' collection
            questions_ref = db.collection("questions").stream()
            questions = [doc.to_dict().get("text") for doc in questions_ref]
            st.session_state.suggested_question = random.choice(questions) if questions else "No questions found in database."
        
        st.markdown(f"> {st.session_state.suggested_question}")
    
    with col2:
        st.subheader("Upload Interview Audio")
        audio_file = st.file_uploader(
            "Upload the interview recording (.mp3) when complete:", 
            type=["mp3"]
        )

        if audio_file is not None:
            with st.spinner("Uploading and processing audio... This may take a few minutes."):
                # Upload to Firebase Storage
                bucket = storage.bucket()
                blob = bucket.blob(f"interviews/{st.session_state.interview_id}/audio.mp3")
                blob.upload_from_file(audio_file)
                
                # Update status and wait for transcription
                db.collection("interviews").document(st.session_state.interview_id).update({"status": "processing_audio"})
                st.session_state.status = 'awaiting_confirmation'
                st.success("Audio uploaded! Awaiting transcription.")
                st.info("The page will auto-refresh to check for the transcript.")
                time.sleep(5) # Give a moment for the user to see the message
                st.rerun()


# --- SCREEN 3: Transcript Confirmation ---
elif st.session_state.status == 'awaiting_confirmation':
    st.header("3. Transcript Confirmation")
    
    # Check Firestore for the transcript
    doc_ref = db.collection("interviews").document(st.session_state.interview_id)
    interview_doc = doc_ref.get()
    transcript = interview_doc.get("raw_transcript")

    if transcript:
        st.info("Please review and edit the transcript below for accuracy before evaluation.")
        confirmed_transcript = st.text_area("Confirmed Transcript", value=transcript, height=400)
        
        if st.button("Confirm & Evaluate Transcript"):
            with st.spinner("Submitting for evaluation..."):
                # Call the evaluation Cloud Function
                # IMPORTANT: Replace with your actual Cloud Function URL
                EVALUATION_FUNCTION_URL = st.secrets["firebase"]["evaluation_function_url"]
                
                response = requests.post(
                    EVALUATION_FUNCTION_URL,
                    json={
                        "interviewId": st.session_state.interview_id,
                        "confirmedTranscript": confirmed_transcript,
                        "questionAsked": "Please evaluate the candidate's overall performance based on the transcript." # Generic question for now
                    }
                )
                
                if response.status_code == 200:
                    st.success("Evaluation complete!")
                    st.session_state.status = 'complete'
                    st.rerun()
                else:
                    st.error(f"Evaluation failed: {response.text}")

    else:
        st.info("Transcription is in progress. The page will automatically refresh every 20 seconds.")
        time.sleep(20)
        st.rerun()


# --- SCREEN 4: Final Report ---
elif st.session_state.status == 'complete':
    st.header("4. Final Report")
    
    doc_ref = db.collection("interviews").document(st.session_state.interview_id)
    interview_doc = doc_ref.get().to_dict()

    st.subheader(f"Evaluation for: {interview_doc.get('candidateName')}")
    st.write(f"**Role Level:** {interview_doc.get('roleLevel')} | **Salary Expectation:** {interview_doc.get('salaryLPA')} LPA")
    
    evaluation = interview_doc.get("evaluation", {}).get("evaluation", {})
    if evaluation:
        col1, col2, col3 = st.columns(3)
        col1.metric("Clarity", f"{evaluation['clarity']['score']}/10")
        col2.metric("Correctness", f"{evaluation['correctness']['score']}/10")
        col3.metric("Depth", f"{evaluation['depth']['score']}/10")

        st.subheader("Justification")
        st.markdown(f"**Clarity:** {evaluation['clarity']['justification']}")
        st.markdown(f"**Correctness:** {evaluation['correctness']['justification']}")
        st.markdown(f"**Depth:** {evaluation['depth']['justification']}")

        st.subheader("Overall Summary")
        st.write(interview_doc.get("evaluation", {}).get("overall_summary", "No summary provided."))
    else:
        st.error("Evaluation data not found.")

    if st.button("Start New Interview"):
        st.session_state.status = 'not_started'
        st.session_state.interview_id = None
        st.rerun()
