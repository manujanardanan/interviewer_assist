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

# --- PDF Generation Function (remains the same) ---
def create_pdf(details, questions, transcript, evaluation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Interview Report for: {details['name']}", 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Role Level: {details['role_level']} | Salary Expectation: {details['lpa']} LPA", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Questions Asked During Interview:")
    pdf.set_font("Arial", '', 11)
    for i, q in enumerate(questions):
        pdf.multi_cell(0, 5, f"{i+1}. {q}")
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Full Interview Transcript:")
    pdf.set_font("Arial", 'I', 11)
    pdf.multi_cell(0, 5, transcript)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Overall Evaluation:")
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 5, evaluation.get('overall_summary', 'N/A'))
    pdf.ln(10)
    return pdf.output(dest='S').encode('latin1')

# --- Session State Initialization ---
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.questions_asked = []
    st.session_state.current_question = "Click 'Suggest Question 1' to begin."
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
        messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt_text}]
        if as_json:
            response = client.chat.completions.create(model=model, response_format={"type": "json_object"}, messages=messages)
            return json.loads(response.choices[0].message.content)
        else:
            response = client.chat.completions.create(model=model, messages=messages, temperature=0.7, max_tokens=250)
            return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- SCREEN 1: SETUP ---
if st.session_state.status == 'setup':
    st.header("Stage 1: Candidate Details")
    with st.form("setup_form"):
        name = st.text_input("Candidate Name")
        lpa = st.number_input("Salary Expectation (LPA)", min_value=10, value=30)
        submitted = st.form_submit_button("Start Interview")
        if submitted and name:
            st.session_state.candidate_details = {"name": name, "lpa": lpa, "role_level": "Senior" if lpa > 35 else "Mid"}
            st.session_state.status = 'live_interview'
            st.rerun()

# --- SCREEN 2: LIVE INTERVIEW ---
elif st.session_state.status == 'live_interview':
    st.header(f"Stage 2: Live Interview with {st.session_state.candidate_details['name']}")
    st.info(f"**Instructions:** Start the recorder, use the question controls, and stop the recorder when done.")
    
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Interview Recorder")
        st.write("Click the microphone to start/stop recording.")
        audio_bytes = st_audiorec()
        
        # This logic correctly saves the audio and forces a rerun
        if audio_bytes and not st.session_state.audio_bytes:
            st.session_state.audio_bytes = audio_bytes
            st.rerun()

        st.subheader("Question Controls")
        
        # --- THIS IS THE RESTORED LOGIC ---
        next_q_num = st.session_state.question_number + 1
        if next_q_num <= 3:
            if st.button(f"Suggest Question {next_q_num}/3"):
                st.session_state.question_number = next_q_num
                with st.spinner("Generating..."):
                    new_question = generate_question(st.session_state.candidate_details['role_level'], st.session_state.question_number)
                    if new_question:
                        st.session_state.current_question = new_question
                        st.session_state.questions_asked.append(new_question)
        
        if st.session_state.question_number > 0:
            if st.button("Rephrase Current Question"):
                prompt = f"Rephrase the following interview question to be clearer or provide a different angle: '{st.session_state.current_question}'"
                with st.spinner("Rephrasing..."):
                    rephrased_q = get_ai_response(prompt)
                    if rephrased_q:
                        st.session_state.current_question = rephrased_q
                        if st.session_state.questions_asked:
                            st.session_state.questions_asked[-1] = rephrased_q
        # --- END OF RESTORED LOGIC ---

    with col2:
        st.subheader("Current Question & Notes")
        st.markdown(f"> **{st.session_state.current_question}**")
        st.session_state.notes = st.text_area("Interviewer's Notes:", height=350, value=st.session_state.notes)
        
    st.markdown("---")
    
    # This button logic is correct and relies on the state update above
    if st.button("Finish Interview & Evaluate", type="primary", disabled=(not st.session_state.audio_bytes)):
        st.session_state.status = 'evaluating'
        st.rerun()

# --- SCREEN 3: EVALUATION & REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 3: Evaluation & Final Report")
    # ... (This entire screen's code remains the same as the previous version)
    if st.session_state.status == 'evaluating':
        with st.spinner("Processing full interview... This may take a few minutes."):
            # ... (transcription and evaluation logic is unchanged)
            pass
    if st.session_state.status == 'report':
        st.subheader(f"Overall Assessment for {st.session_state.candidate_details['name']}")
        # ... (report display logic is unchanged)
        pass
