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
def create_pdf(interview_data, candidate_details):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Interview Report for: {candidate_details['name']}", 0, 1, 'C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Role Level: {candidate_details['role_level']} | Salary Expectation: {candidate_details['lpa']} LPA", 0, 1, 'C')
    pdf.ln(10)

    for i, item in enumerate(interview_data):
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 5, f"Question {i+1}: {item['question']}")
        pdf.ln(5)

        pdf.set_font("Arial", 'I', 11)
        pdf.multi_cell(0, 5, f"Candidate's Answer: {item['transcript']}")
        pdf.ln(5)

        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 5, f"Evaluation: {item['evaluation'].get('overall_summary', 'N/A')}")
        pdf.ln(10)
    
    return pdf.output(dest='S').encode('latin1')

# --- Session State Initialization ---
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.interview_flow = [] # Will store a list of Q&A + evaluation dicts
    st.session_state.current_question = "Click 'Suggest Question' to begin."

# --- Helper Functions ---
def start_new_interview():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

def generate_question(role_level):
    # This function remains the same
    try:
        # ... (code for generating question, same as before)
        response = client.chat.completions.create(...)
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def process_answer(audio_bytes, question, role_level):
    """Transcribes and evaluates a single answer."""
    try:
        # 1. Transcribe Audio
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1", file=("interview_answer.wav", audio_bytes)
        )
        transcript = transcript_response.text

        # 2. Evaluate Transcript
        evaluation_prompt = f"""
        **Persona:** You are a fair GenAI Technical Interviewer.
        **Task:** Evaluate the candidate's single response to the specific question asked.
        **Rubric (Score 1-10):** Clarity, Correctness, Depth.
        **Rules:** Provide a score and justification for each category, an "overall_summary", and output in a valid JSON format.
        ---
        **CANDIDATE LEVEL:** {role_level}
        **QUESTION ASKED:** {question}
        **CANDIDATE'S ANSWER TO EVALUATE:** {transcript}
        """
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an assistant that evaluates interview answers and outputs JSON."},
                {"role": "user", "content": evaluation_prompt}
            ]
        )
        evaluation = json.loads(response.choices[0].message.content)
        return transcript, evaluation
    except Exception as e:
        st.error(f"Could not process answer: {e}")
        return None, None

# --- SCREEN 1: SETUP ---
if st.session_state.status == 'setup':
    st.header("Stage 1: Candidate Details")
    # ... (form code is the same as before)
    with st.form("setup_form"):
        name = st.text_input("Candidate Name")
        lpa = st.number_input("Salary Expectation (LPA)", min_value=10, value=30)
        submitted = st.form_submit_button("Start Interview")

        if submitted and name:
            st.session_state.candidate_details = {
                "name": name, "lpa": lpa, "role_level": "Senior" if lpa > 35 else "Mid"
            }
            st.session_state.status = 'live_interview'
            st.rerun()


# --- SCREEN 2: LIVE INTERVIEW (Q&A Loop) ---
elif st.session_state.status == 'live_interview':
    st.header(f"Stage 2: Live Interview with {st.session_state.candidate_details['name']}")
    st.info(f"**Instructions:** Suggest a question, let the candidate answer, record their response, and process it. Repeat as needed.")

    st.subheader("1. Get a Question")
    st.markdown(f"> **Suggested Question:** {st.session_state.current_question}")
    if st.button("Suggest Next Question"):
        st.session_state.current_question = generate_question(st.session_state.candidate_details['role_level'])
        st.rerun()

    st.subheader("2. Record Candidate's Answer")
    audio_bytes = st_audiorec()

    if audio_bytes:
        if st.button("Process This Answer"):
            with st.spinner("Transcribing and evaluating answer..."):
                transcript, evaluation = process_answer(
                    audio_bytes,
                    st.session_state.current_question,
                    st.session_state.candidate_details['role_level']
                )
                if transcript and evaluation:
                    st.session_state.interview_flow.append({
                        "question": st.session_state.current_question,
                        "transcript": transcript,
                        "evaluation": evaluation
                    })
                    st.success("Answer processed!")
                    st.session_state.current_question = "Suggest another question or finish the interview."

    st.markdown("---")
    st.subheader("3. Interview Progress")
    if st.session_state.interview_flow:
        for i, item in enumerate(st.session_state.interview_flow):
            with st.expander(f"View Processed Answer for Question {i+1}"):
                st.write(f"**Question:** {item['question']}")
                st.write(f"**Transcript:** {item['transcript']}")
                st.write(f"**Summary:** {item['evaluation'].get('overall_summary', 'N/A')}")
    else:
        st.write("No answers processed yet.")

    st.markdown("---")
    if st.button("Finish Interview & View Final Report", type="primary"):
        st.session_state.status = 'report'
        st.rerun()


# --- SCREEN 3: FINAL REPORT (The new "Fourth Screen") ---
elif st.session_state.status == 'report':
    st.header(f"Stage 3: Final Report for {st.session_state.candidate_details['name']}")

    if not st.session_state.interview_flow:
        st.warning("No interview data was recorded.")
    else:
        # Generate PDF data in memory
        pdf_data = create_pdf(st.session_state.interview_flow, st.session_state.candidate_details)
        st.download_button(
            label="⬇️ Download Report as PDF",
            data=pdf_data,
            file_name=f"Interview_Report_{st.session_state.candidate_details['name']}.pdf",
            mime="application/pdf"
        )
        
        st.markdown("---")
        st.subheader("Detailed Question-by-Question Breakdown")
        
        for i, item in enumerate(st.session_state.interview_flow):
            with st.container(border=True):
                st.markdown(f"**Question {i+1}:** {item['question']}")
                st.info(f"**Candidate's Answer:** {item['transcript']}")
                
                eval_data = item['evaluation'].get('evaluation', {})
                if eval_data:
                    st.write("**Evaluation:**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Clarity", f"{eval_data.get('clarity', {}).get('score', 0)}/10")
                    col2.metric("Correctness", f"{eval_data.get('correctness', {}).get('score', 0)}/10")
                    col3.metric("Depth", f"{eval_data.get('depth', {}).get('score', 0)}/10")
                st.success(f"**Summary:** {item['evaluation'].get('overall_summary', 'N/A')}")

    st.button("Start New Interview", on_click=start_new_interview)
