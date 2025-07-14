import streamlit as st
from openai import OpenAI
import json
from st_audiorec import st_audiorec
from fpdf import FPDF

# --- Page Configuration ---
st.set_page_config(page_title="GenAI Interview Agent", page_icon="🤖", layout="wide")
st.title("🤖 GenAI Interview Agent")

# --- OpenAI Client Initialization ---
try:
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
except Exception:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- PDF Generation Function (with robust sanitization) ---
def create_pdf(details, questions, transcript, evaluation):
    # This function now has a more robust way to handle special characters
    def sanitize_text(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Interview Report for: {sanitize_text(details['name'])}", 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Role Level: {details['role_level']} | Salary Expectation: {details['lpa']} LPA", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Questions Asked During Interview:")
    pdf.set_font("Arial", '', 11)
    for i, q in enumerate(questions):
        pdf.multi_cell(0, 5, f"{i+1}. {sanitize_text(q)}")
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Full Interview Transcript:")
    pdf.set_font("Arial", 'I', 11)
    pdf.multi_cell(0, 5, sanitize_text(transcript))
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Overall Evaluation:")
    pdf.set_font("Arial", '', 11)
    summary = evaluation.get('overall_summary', 'N/A')
    pdf.multi_cell(0, 5, sanitize_text(summary))
    pdf.ln(10)
    return pdf.output(dest='S').encode('latin1')

# --- Session State Initialization (with new statuses) ---
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.questions_to_ask = []
    st.session_state.notes = ""
    st.session_state.transcript = ""
    st.session_state.evaluation = None
    st.session_state.audio_bytes = None
    st.session_state.question_number = 0

# --- Helper Functions ---
def start_new_interview():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# ... (get_ai_response and generate_question functions remain the same)
def get_ai_response(prompt_text, model="gpt-4-turbo", as_json=False):
    # ...
    return ...

def generate_question(role_level, question_number):
    # ...
    return ...
    
# --- SCREEN 1: SETUP ---
if st.session_state.status == 'setup':
    st.header("Stage 1: Candidate Details")
    with st.form("setup_form"):
        name = st.text_input("Candidate Name")
        lpa = st.number_input("Salary Expectation (LPA)", min_value=10, value=30)
        submitted = st.form_submit_button("Proceed to Question Prep")
        if submitted and name:
            st.session_state.candidate_details = {"name": name, "lpa": lpa, "role_level": "Senior" if lpa > 35 else "Mid"}
            st.session_state.status = 'question_prep'
            st.rerun()

# --- SCREEN 2: QUESTION PREPARATION ---
elif st.session_state.status == 'question_prep':
    st.header("Stage 2: Prepare Interview Questions")
    # ... (This screen's code from the previous version is correct and unchanged)
    # ... It ends with a button that sets status to 'recording'
    if st.button("Proceed to Live Recording", type="primary"):
        st.session_state.status = 'recording'
        st.rerun()

# --- SCREEN 3: LIVE RECORDING ---
elif st.session_state.status == 'recording':
    st.header("Stage 3: Live Recording")
    st.success("RECORDING IN PROGRESS...")
    # ... (This screen's code is also correct)
    audio_bytes = st_audiorec()
    if audio_bytes:
        st.session_state.audio_bytes = audio_bytes
        st.session_state.status = 'transcribing' # NEW status to start processing
        st.rerun()

# --- SCREEN 4: TRANSCRIPT CONFIRMATION (NEW SCREEN) ---
elif st.session_state.status in ['transcribing', 'transcript_confirmation']:
    st.header("Stage 4: Review & Confirm Transcript")
    
    # This block runs only once to perform the transcription
    if st.session_state.status == 'transcribing':
        with st.spinner("Transcription in progress... Please wait."):
            try:
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=("interview.wav", st.session_state.audio_bytes)
                )
                st.session_state.transcript = transcript_response.text
                st.session_state.status = 'transcript_confirmation' # Move to confirmation
                st.rerun()
            except Exception as e:
                st.error(f"Transcription failed: {e}")
                st.session_state.status = 'recording' # Go back if fails

    # This block displays the transcript for user confirmation
    if st.session_state.status == 'transcript_confirmation':
        st.info("Please review and edit the transcript for accuracy before evaluation.")
        st.session_state.transcript = st.text_area(
            "Full Interview Transcript:",
            value=st.session_state.transcript,
            height=300
        )
        if st.button("Confirm Transcript & Evaluate", type="primary"):
            st.session_state.status = 'evaluating'
            st.rerun()

# --- SCREEN 5: FINAL REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 5: Evaluation & Final Report")
    
    if st.session_state.status == 'evaluating':
        with st.spinner("AI evaluation in progress..."):
            try:
                eval_prompt = f"""
                **Persona:** You are an expert GenAI Technical Interviewer providing a holistic evaluation of a full interview.
                **Task:** Evaluate the candidate's entire performance based on the confirmed transcript, the questions asked, and the interviewer's notes.
                **Candidate Level:** {st.session_state.candidate_details['role_level']}
                **Questions Asked:** {st.session_state.questions_to_ask}
                **Interviewer Notes:** {st.session_state.notes}
                **Confirmed Full Transcript:** {st.session_state.transcript}
                **Rules:** Provide a final "overall_summary". Output MUST be in a valid JSON format like: {{"overall_summary": "..."}}
                """
                evaluation = get_ai_response(eval_prompt, as_json=True)
                if evaluation:
                    st.session_state.evaluation = evaluation
                    st.session_state.status = 'report'
                    st.rerun()
                else:
                    st.error("Evaluation failed to return valid data.")
                    st.session_state.status = 'transcript_confirmation'
            except Exception as e:
                st.error(f"An error occurred during evaluation: {e}")
                st.session_state.status = 'transcript_confirmation'

    if st.session_state.status == 'report':
        st.subheader(f"Overall Assessment for {st.session_state.candidate_details['name']}")
        if st.session_state.evaluation:
            st.info(f"**Holistic Summary:** {st.session_state.evaluation.get('overall_summary', 'No summary available.')}")
            pdf_data = create_pdf(st.session_state.candidate_details, st.session_state.questions_to_ask, st.session_state.transcript, st.session_state.evaluation)
            st.download_button(
                label="⬇️ Download Full Report as PDF",
                data=pdf_data,
                file_name=f"Interview_Report_{st.session_state.candidate_details['name']}.pdf",
                mime="application/pdf"
            )
            with st.expander("View Full Transcript and Questions Asked"):
                st.write("**Questions Asked:**", st.session_state.questions_to_ask)
                st.write("**Full Transcript:**", st.session_state.transcript)
        else:
            st.error("Could not retrieve evaluation data.")
        st.button("Start New Interview", on_click=start_new_interview)
