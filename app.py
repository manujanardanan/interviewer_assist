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

# --- PDF Generation Function (Unchanged) ---
def create_pdf(details, questions, transcript, evaluation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Interview Report for: {details['name']}", 0, 1, 'C')
    # ... (rest of the PDF function is unchanged)
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

def get_ai_response(prompt_text, model="gpt-4-turbo", as_json=False):
    # ... (code for get_ai_response is unchanged)
    try:
        # ...
        return ...
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

def generate_question(role_level, question_number):
    # ... (code for generate_question is unchanged)
    prompt = ""
    # ...
    if prompt:
        return get_ai_response(prompt)
    return "All questions have been asked."

# --- SCREEN 1: SETUP ---
if st.session_state.status == 'setup':
    st.header("Stage 1: Candidate Details")
    with st.form("setup_form"):
        name = st.text_input("Candidate Name")
        lpa = st.number_input("Salary Expectation (LPA)", min_value=10, value=30)
        submitted = st.form_submit_button("Proceed to Question Prep")
        if submitted and name:
            st.session_state.candidate_details = {"name": name, "lpa": lpa, "role_level": "Senior" if lpa > 35 else "Mid"}
            st.session_state.status = 'question_prep' # New status
            st.rerun()

# --- SCREEN 2: QUESTION PREPARATION ---
elif st.session_state.status == 'question_prep':
    st.header("Stage 2: Prepare Interview Questions")
    st.info("Generate and refine your questions before starting the recording.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Question Controls")
        next_q_num = st.session_state.question_number + 1
        if next_q_num <= 3:
            if st.button(f"Suggest Question {next_q_num}/3"):
                st.session_state.question_number = next_q_num
                with st.spinner("Generating..."):
                    new_question = generate_question(st.session_state.candidate_details['role_level'], st.session_state.question_number)
                    if new_question:
                        st.session_state.questions_to_ask.append(new_question)
        
        if st.session_state.questions_to_ask:
            if st.button("Rephrase Last Question"):
                last_question = st.session_state.questions_to_ask[-1]
                prompt = f"Rephrase the following interview question to be clearer or provide a different angle: '{last_question}'"
                with st.spinner("Rephrasing..."):
                    rephrased_q = get_ai_response(prompt)
                    if rephrased_q:
                        st.session_state.questions_to_ask[-1] = rephrased_q
    
    with col2:
        st.subheader("Prepared Questions")
        if not st.session_state.questions_to_ask:
            st.write("No questions generated yet.")
        else:
            for i, q in enumerate(st.session_state.questions_to_ask):
                st.markdown(f"{i+1}. {q}")
    
    st.markdown("---")
    if st.button("Proceed to Live Recording", type="primary"):
        st.session_state.status = 'recording'
        st.rerun()

# --- SCREEN 3: LIVE RECORDING ---
elif st.session_state.status == 'recording':
    st.header("Stage 3: Live Recording")
    st.success("RECORDING IN PROGRESS...")
    st.info("Ask the prepared questions and record the candidate's responses in one continuous session. Click 'Stop' when done.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Audio Recorder")
        audio_bytes = st_audiorec()
        
        # This is the automatic navigation trigger
        if audio_bytes:
            st.session_state.audio_bytes = audio_bytes
            st.session_state.status = 'evaluating'
            st.rerun()

    with col2:
        st.subheader("Questions to Ask")
        if not st.session_state.questions_to_ask:
            st.warning("No questions were prepared. Please go back.")
        else:
            for i, q in enumerate(st.session_state.questions_to_ask):
                st.markdown(f"**{i+1}.** {q}")
    
    st.subheader("Interviewer's Notes")
    st.session_state.notes = st.text_area("Take live notes here:", height=200, value=st.session_state.notes)

# --- SCREEN 4: EVALUATION & REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 4: Evaluation & Final Report")
    
    if st.session_state.status == 'evaluating':
        with st.spinner("Processing full interview... This may take a few minutes."):
            # ... (evaluation logic is the same)
            pass

    if st.session_state.status == 'report':
        # ... (report display logic is the same)
        pass
    
    st.button("Start New Interview", on_click=start_new_interview)
