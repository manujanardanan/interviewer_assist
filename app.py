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
    # ... (code for PDF generation is unchanged)
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

# --- Session State Initialization (with new question_number) ---
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.questions_asked = []
    st.session_state.current_question = "Click 'Suggest Question 1' to begin."
    st.session_state.notes = ""
    st.session_state.transcript = ""
    st.session_state.evaluation = None
    st.session_state.audio_bytes = None
    st.session_state.question_number = 0 # NEW: Tracks the question sequence

# --- Helper Functions ---
def start_new_interview():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

def generate_question(role_level, question_number):
    """Generates a question based on the interview stage."""
    prompt = ""
    if question_number == 1:
        # Open-ended situational question
        prompt = f"Generate ONE open-ended, situational GenAI interview question for a '{role_level}' level candidate. The question should explore their experience with a challenging project. Return ONLY the question text."
    elif question_number == 2:
        # Diagnostic question
        prompt = f"Generate a problem-situation for a '{role_level}' level GenAI professional. Describe a scenario where a GenAI project is failing (e.g., high latency, poor accuracy, unexpected costs). Phrase the question to ask the candidate to identify potential causes. Example: 'A deployed model is suddenly hallucinating... what are the first things you would investigate?' Return ONLY the question text."
    elif question_number == 3:
        # Solution-oriented question
        prompt = f"Generate a problem for a '{role_level}' level GenAI professional where the problem and diagnosis are given. The candidate must explain how to solve it. Example: 'Our RAG system is slow because of inefficient embedding lookups. How would you architect a solution to fix this?' Return ONLY the question text."
    
    if prompt:
        return get_ai_response(prompt)
    return "All questions have been asked."

def get_ai_response(prompt_text, model="gpt-4-turbo", as_json=False):
    # This function remains the same
    try:
        # ... (code for get_ai_response is unchanged)
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
    # ... (form code is the same as before)
    with st.form("setup_form"):
        name = st.text_input("Candidate Name")
        lpa = st.number_input("Salary Expectation (LPA)", min_value=10, value=30)
        submitted = st.form_submit_button("Start Interview")
        if submitted and name:
            st.session_state.candidate_details = {"name": name, "lpa": lpa, "role_level": "Senior" if lpa > 35 else "Mid"}
            st.session_state.status = 'live_interview'
            st.rerun()

# --- SCREEN 2: LIVE INTERVIEW (with new question logic) ---
elif st.session_state.status == 'live_interview':
    st.header(f"Stage 2: Live Interview with {st.session_state.candidate_details['name']}")
    st.info(f"**Instructions:** Follow the 3-question sequence. Start the recorder for the entire interview.")
    
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Interview Recorder")
        st.write("Click the microphone to start/stop recording.")
        audio_bytes = st_audiorec()
        if audio_bytes:
            st.session_state.audio_bytes = audio_bytes
        
        st.subheader("Question Controls")
        
        # Logic for the 3-question sequence
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
                    # Update both the current question and the last item in the asked list
                    if rephrased_q:
                        st.session_state.current_question = rephrased_q
                        if st.session_state.questions_asked:
                            st.session_state.questions_asked[-1] = rephrased_q


    with col2:
        st.subheader("Current Question & Notes")
        st.markdown(f"> **{st.session_state.current_question}**")
        st.session_state.notes = st.text_area("Interviewer's Notes:", height=350, value=st.session_state.notes)
        
    st.markdown("---")
    
    if st.button("Finish Interview & Evaluate", type="primary", disabled=(not st.session_state.audio_bytes)):
        st.session_state.status = 'evaluating'
        st.rerun()

# --- SCREEN 3: EVALUATION & REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 3: Evaluation & Final Report")
    # ... (This entire screen's code remains the same as the previous version)
    if st.session_state.status == 'evaluating':
        with st.spinner("Processing full interview... This may take a few minutes."):
            # 1. Transcribe
            transcript_response = client.audio.transcriptions.create(model="whisper-1", file=("interview.wav", st.session_state.audio_bytes))
            st.session_state.transcript = transcript_response.text
            # 2. Evaluate
            eval_prompt = f"""
            **Persona:** You are an expert GenAI Technical Interviewer providing a holistic evaluation of a full interview.
            **Task:** Evaluate the candidate's entire performance based on the transcript, the specific questions asked, and the interviewer's notes.
            **Candidate Level:** {st.session_state.candidate_details['role_level']}
            **Questions Asked:** {st.session_state.questions_asked}
            **Interviewer Notes:** {st.session_state.notes}
            **Full Transcript:** {st.session_state.transcript}
            **Rules:** Provide a final "overall_summary". Output MUST be in a valid JSON format like: {{"overall_summary": "..."}}
            """
            evaluation = get_ai_response(eval_prompt, as_json=True)
            if evaluation:
                st.session_state.evaluation = evaluation
                st.session_state.status = 'report'
                st.rerun()
            else:
                st.error("Evaluation failed.")
                st.session_state.status = 'live_interview'
    if st.session_state.status == 'report':
        st.subheader(f"Overall Assessment for {st.session_state.candidate_details['name']}")
        if st.session_state.evaluation:
            st.info(f"**Holistic Summary:** {st.session_state.evaluation.get('overall_summary', 'No summary available.')}")
            pdf_data = create_pdf(st.session_state.candidate_details, st.session_state.questions_asked, st.session_state.transcript, st.session_state.evaluation)
            st.download_button(label="⬇️ Download Full Report as PDF", data=pdf_data, file_name=f"Interview_Report_{st.session_state.candidate_details['name']}.pdf", mime="application/pdf")
            with st.expander("View Full Transcript and Questions Asked"):
                st.write("**Questions Asked:**", st.session_state.questions_asked)
                st.write("**Full Transcript:**", st.session_state.transcript)
        else:
            st.error("Could not retrieve evaluation data.")
        st.button("Start New Interview", on_click=start_new_interview)
