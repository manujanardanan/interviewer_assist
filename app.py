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

# --- PDF Generation Function ---
def create_pdf(details, questions, transcript, evaluation):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Sanitize candidate name before using it
    sanitized_name = details['name'].encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, f"Interview Report for: {sanitized_name}", 0, 1, 'C')
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Role Level: {details['role_level']} | Salary Expectation: {details['lpa']} LPA", 0, 1, 'C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Questions Asked During Interview:")
    pdf.set_font("Arial", '', 11)
    for i, q in enumerate(questions):
        # Sanitize each question
        sanitized_q = q.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, f"{i+1}. {sanitized_q}")
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Full Interview Transcript:")
    pdf.set_font("Arial", 'I', 11)
    # Sanitize the full transcript
    sanitized_transcript = transcript.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, sanitized_transcript)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 5, "Overall Evaluation:")
    pdf.set_font("Arial", '', 11)
    # Sanitize the evaluation summary
    summary = evaluation.get('overall_summary', 'N/A')
    sanitized_summary = summary.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, sanitized_summary)
    pdf.ln(10)
    
    # The output encoding remains the same
    return pdf.output(dest='S').encode('latin-1')

# --- Session State Initialization ---
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

def generate_question(role_level, question_number):
    prompt = ""
    if question_number == 1:
        prompt = f"Generate ONE open-ended, situational GenAI interview question for a '{role_level}' level candidate. The question should explore their experience with a challenging project. Return ONLY the question text."
    elif question_number == 2:
        prompt = f"Generate a problem-situation for a '{role_level}' level GenAI professional. Describe a scenario where a GenAI project is failing (e.g., high latency, poor accuracy, unexpected costs). Phrase the question to ask the candidate to identify potential causes. Example: 'A deployed model is suddenly hallucinating... what are the first things you would investigate?' Return ONLY the question text."
    elif question_number == 3:
        prompt = f"Generate a problem for a '{role_level}' level GenAI professional where the problem and diagnosis are given. The candidate must explain how to solve it. Example: 'Our RAG system is slow because of inefficient embedding lookups. How would you architect a solution to fix this?' Return ONLY the question text."
    
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
            st.session_state.status = 'question_prep' # Corrected status
            st.rerun()

# --- SCREEN 2: QUESTION PREPARATION ---
elif st.session_state.status == 'question_prep':
    st.header("Stage 2: Prepare Interview Questions") # Corrected header
    st.info("Generate and refine your questions before starting the recording.")

    # --- Logic to handle state changes from button clicks ---
    if st.session_state.get('rephrase_triggered', False):
        st.session_state.rephrase_triggered = False 
        last_question = st.session_state.questions_to_ask[-1]
        prompt = f"Rephrase the following interview question: '{last_question}'"
        with st.spinner("Rephrasing..."):
            rephrased_q = get_ai_response(prompt)
            if rephrased_q:
                st.session_state.questions_to_ask[-1] = rephrased_q
    
    if st.session_state.question_number > len(st.session_state.questions_to_ask):
        with st.spinner("Generating..."):
            new_question = generate_question(st.session_state.candidate_details['role_level'], st.session_state.question_number)
            if new_question and new_question != "All questions have been asked.":
                st.session_state.questions_to_ask.append(new_question)

    # --- UI Layout ---
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Question Controls")
        next_q_num = st.session_state.question_number + 1
        
        if next_q_num <= 3:
            st.button(f"Suggest Question {next_q_num}/3", on_click=lambda: st.session_state.update(question_number=st.session_state.question_number + 1))
        
        if st.session_state.questions_to_ask:
            st.button("Rephrase Last Question", on_click=lambda: st.session_state.update(rephrase_triggered=True))
    
    with col2:
        st.subheader("Prepared Questions")
        if not st.session_state.questions_to_ask:
            st.write("Click 'Suggest Question 1/3' to begin.")
        else:
            for i, q in enumerate(st.session_state.questions_to_ask):
                st.markdown(f"**{i+1}.** {q}")
    
    st.markdown("---")
    if st.button("Proceed to Live Recording", type="primary"):
        st.session_state.status = 'recording'
        st.rerun()

# --- SCREEN 3: LIVE RECORDING ---
elif st.session_state.status == 'recording':
    st.header("Stage 3: Live Recording") # Corrected header
    st.success("RECORDING IN PROGRESS...")
    st.info("Ask the prepared questions and record the candidate's responses in one continuous session. Click 'Stop' when done.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Audio Recorder")
        audio_bytes = st_audiorec()
        
        # Automatic navigation trigger
        if audio_bytes:
            st.session_state.audio_bytes = audio_bytes
            st.session_state.status = 'evaluating'
            st.rerun()

    with col2:
        st.subheader("Questions to Ask")
        if not st.session_state.questions_to_ask:
            st.warning("No questions were prepared.")
        else:
            for i, q in enumerate(st.session_state.questions_to_ask):
                st.markdown(f"**{i+1}.** {q}")
    
    st.subheader("Interviewer's Notes")
    st.session_state.notes = st.text_area("Take live notes here:", height=200, value=st.session_state.notes)

# --- SCREEN 4: EVALUATION & REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 4: Evaluation & Final Report") # Corrected header
    
    if st.session_state.status == 'evaluating':
        with st.spinner("Processing full interview... This may take a few minutes."):
            try:
                transcript_response = client.audio.transcriptions.create(model="whisper-1", file=("interview.wav", st.session_state.audio_bytes))
                st.session_state.transcript = transcript_response.text

                eval_prompt = f"""
                **Persona:** You are an expert GenAI Technical Interviewer providing a holistic evaluation of a full interview.
                **Task:** Evaluate the candidate's entire performance based on the transcript, the questions asked, and the interviewer's notes.
                **Candidate Level:** {st.session_state.candidate_details['role_level']}
                **Questions Asked:** {st.session_state.questions_to_ask}
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
                    st.error("Evaluation failed to return valid data.")
                    st.session_state.status = 'recording'
            except Exception as e:
                st.error(f"An error occurred during processing: {e}")
                st.session_state.status = 'recording'

    if st.session_state.status == 'report':
        st.subheader(f"Overall Assessment for {st.session_state.candidate_details['name']}")
        if st.session_state.evaluation:
            st.info(f"**Holistic Summary:** {st.session_state.evaluation.get('overall_summary', 'No summary available.')}")
            pdf_data = create_pdf(st.session_state.candidate_details, st.session_state.questions_to_ask, st.session_state.transcript, st.session_state.evaluation)
            st.download_button(label="⬇️ Download Full Report as PDF", data=pdf_data, file_name=f"Interview_Report_{st.session_state.candidate_details['name']}.pdf", mime="application/pdf")
            with st.expander("View Full Transcript and Questions Asked"):
                st.write("**Questions Asked:**", st.session_state.questions_to_ask)
                st.write("**Full Transcript:**", st.session_state.transcript)
        else:
            st.error("Could not retrieve evaluation data.")
        st.button("Start New Interview", on_click=start_new_interview)
