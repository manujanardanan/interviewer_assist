import streamlit as st
from openai import OpenAI
import json
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="GenAI Interview Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 GenAI Interview Agent")

# --- OpenAI Client Initialization ---
try:
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
except Exception as e:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- Session State Initialization ---
# This now includes states for the new interview flow.
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.suggested_question = "Click 'Suggest Next Question' to begin."
    st.session_state.interview_notes = ""
    st.session_state.transcript = ""
    st.session_state.evaluation = None

# --- Helper Functions ---
def start_new_interview():
    """Resets the entire session state to the beginning."""
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.suggested_question = "Click 'Suggest Next Question' to begin."
    st.session_state.interview_notes = ""
    st.session_state.transcript = ""
    st.session_state.evaluation = None

def generate_question(role_level):
    """Calls OpenAI to generate a single interview question."""
    try:
        question_prompt = f"""
        **Persona:**
        You are an expert GenAI technical interviewer.

        **Task:**
        Based on the provided role level ('{role_level}'), generate ONE unique, situational interview question.

        **Rules:**
        - The question must be about a practical challenge in GenAI.
        - For "Senior" roles, focus on architecture or strategy.
        - For "Mid" roles, focus on development or problem-solving.
        - Return ONLY the question text, without any preamble.
        """
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates interview questions."},
                {"role": "user", "content": question_prompt}
            ],
            temperature=0.8,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating question: {e}"

# --- SCREEN 1: SETUP ---
if st.session_state.status == 'setup':
    st.header("Stage 1: Candidate Details")
    with st.form("setup_form"):
        name = st.text_input("Candidate Name")
        lpa = st.number_input("Salary Expectation (LPA)", min_value=10, value=30)
        submitted = st.form_submit_button("Start Interview")

        if submitted and name:
            st.session_state.candidate_details = {
                "name": name,
                "lpa": lpa,
                "role_level": "Senior" if lpa > 35 else "Mid"
            }
            st.session_state.status = 'live_interview'
            st.rerun()

# --- SCREEN 2: LIVE INTERVIEW ---
elif st.session_state.status == 'live_interview':
    st.header(f"Stage 2: Live Interview with {st.session_state.candidate_details['name']}")
    st.info(f"**Role Level:** {st.session_state.candidate_details['role_level']} | **Simulated Timer:** 30 minutes")
    
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Question Suggester")
        if st.button("Suggest Next Question"):
            with st.spinner("Generating question..."):
                st.session_state.suggested_question = generate_question(st.session_state.candidate_details['role_level'])
        
        st.markdown(f"> {st.session_state.suggested_question}")
        st.markdown("---")
        if st.button("Finish Interview & Stop Recording", type="primary"):
            st.session_state.status = 'awaiting_upload'
            st.rerun()

    with col2:
        st.subheader("Interviewer's Notes")
        st.session_state.interview_notes = st.text_area(
            "Take notes on the candidate's answers here. They will be used for the final evaluation.",
            height=400,
            value=st.session_state.interview_notes
        )

# --- SCREEN 3: UPLOAD & EVALUATE ---
elif st.session_state.status == 'awaiting_upload':
    st.header("Stage 3: Generate & Evaluate Transcript")
    
    st.subheader("A. Upload Interview Audio")
    audio_file = st.file_uploader("Upload the final interview recording (.mp3, .wav):", type=["mp3", "m4a", "wav", "mpeg"])

    if audio_file:
        if st.button("Generate Transcript"):
            with st.spinner("Transcription in progress... Please wait."):
                try:
                    transcript_response = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
                    st.session_state.transcript = transcript_response.text
                    st.success("Transcription complete!", icon="✅")
                except Exception as e:
                    st.error(f"Transcription failed: {e}", icon="🚨")

    if st.session_state.transcript:
        st.subheader("B. Confirm & Evaluate")
        st.session_state.transcript = st.text_area(
            "Review or edit the transcript for accuracy:",
            value=st.session_state.transcript,
            height=200
        )

        if st.button("Evaluate Now", type="primary"):
            with st.spinner("AI evaluation in progress..."):
                try:
                    evaluation_prompt = f"""
                    **Persona:**
                    You are a fair and objective GenAI Technical Interviewer. Your task is to evaluate a candidate's interview performance based on their role level, the full audio transcript, and the interviewer's notes.

                    **Rubric & Scoring (Score each category from 1-10):**
                    1. Clarity: How clear and well-communicated were the answers?
                    2. Correctness: Was the technical information accurate?
                    3. Depth: How deep was the candidate's knowledge? Did they cover trade-offs and edge cases?

                    **Task:**
                    Evaluate the candidate based on the provided materials. The candidate is a '{st.session_state.candidate_details['role_level']}' level professional.

                    **Rules:**
                    - Provide a score and a brief justification for each category.
                    - Provide an "overall_summary".
                    - The entire output MUST be in a valid JSON format.
                    
                    ---
                    **INTERVIEWER'S NOTES (for context):**
                    {st.session_state.interview_notes}

                    ---
                    **FULL TRANSCRIPT TO EVALUATE:**
                    {st.session_state.transcript}
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4-turbo",
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                            {"role": "user", "content": evaluation_prompt}
                        ]
                    )
                    st.session_state.evaluation = json.loads(response.choices[0].message.content)
                    st.session_state.status = 'report'
                    st.rerun()

                except Exception as e:
                    st.error(f"AI evaluation failed: {e}", icon="🚨")

# --- SCREEN 4: FINAL REPORT ---
elif st.session_state.status == 'report':
    st.header(f"Stage 4: Final Report for {st.session_state.candidate_details['name']}")
    
    evaluation = st.session_state.evaluation.get("evaluation")
    summary = st.session_state.evaluation.get("overall_summary")

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
        st.info(summary)
    else:
        st.error("Could not parse evaluation data.", icon="🚨")
    
    st.button("Start New Interview", on_click=start_new_interview)
