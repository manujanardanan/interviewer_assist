import streamlit as st
from openai import OpenAI
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="GenAI Interview Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 GenAI Interview Agent (All-in-One)")

# --- OpenAI Client Initialization ---
# The API key is securely stored in Streamlit's secrets management.
try:
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
except Exception as e:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- Session State Initialization ---
# This dictionary holds the application's state and persists across reruns.
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.transcript = ""
    st.session_state.evaluation = None

# --- Helper Function to Reset ---
def start_new_interview():
    """Resets the session state to the beginning."""
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.transcript = ""
    st.session_state.evaluation = None


# --- SCREEN 1: SETUP ---
if st.session_state.status == 'setup':
    st.header("1. Candidate Details")
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
            st.session_state.status = 'interview'
            st.rerun()
        elif submitted and not name:
            st.warning("Please enter the candidate's name.", icon="⚠️")

# --- SCREEN 2: INTERVIEW & EVALUATION ---
elif st.session_state.status == 'interview':
    st.header(f"2. Interview with {st.session_state.candidate_details['name']}")
    st.info(f"**Role Level:** {st.session_state.candidate_details['role_level']} | **LPA:** {st.session_state.candidate_details['lpa']}")

    st.subheader("A. Transcribe Audio")
    audio_file = st.file_uploader("Upload interview audio recording (.mp3, .wav):", type=["mp3", "m4a", "wav", "mpeg"])

    if audio_file:
        if st.button("Transcribe Audio"):
            with st.spinner("Transcription in progress... Please wait."):
                try:
                    transcript_response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    st.session_state.transcript = transcript_response.text
                    st.success("Transcription complete!", icon="✅")
                except Exception as e:
                    st.error(f"Transcription failed: {e}", icon="🚨")

    if st.session_state.transcript:
        st.subheader("B. Review and Evaluate")
        st.session_state.transcript = st.text_area(
            "Review or edit the transcript for accuracy:",
            value=st.session_state.transcript,
            height=300
        )

        if st.button("Evaluate Transcript", type="primary"):
            with st.spinner("AI evaluation in progress..."):
                try:
                    # This is the prompt we designed earlier, now inside the code.
                    evaluation_prompt = f"""
                    **Persona:**
                    You are a fair and objective GenAI Technical Interviewer. Your task is to evaluate a candidate's response based on their role level and the provided transcript.

                    **Rubric & Scoring (Score each category from 1-10):**
                    1. Clarity: How clear and well-communicated were the answers?
                    2. Correctness: Was the technical information accurate?
                    3. Depth: How deep was the candidate's knowledge? Did they cover trade-offs and edge cases?

                    **Task:**
                    Evaluate the candidate's transcript using the rubric. The candidate is a '{st.session_state.candidate_details['role_level']}' level professional.

                    **Rules:**
                    - Provide a score and a brief justification for each category.
                    - Provide an "overall_summary".
                    - The entire output MUST be in a valid JSON format like the example below.

                    **JSON Output Example:**
                    {{
                      "evaluation": {{
                        "clarity": {{"score": 8, "justification": "Clear and concise."}},
                        "correctness": {{"score": 9, "justification": "Technically accurate."}},
                        "depth": {{"score": 6, "justification": "Lacked depth on topic X."}}
                      }},
                      "overall_summary": "Solid candidate with good fundamentals."
                    }}
                    
                    ---
                    **Transcript to Evaluate:**
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

# --- SCREEN 3: FINAL REPORT ---
elif st.session_state.status == 'report':
    st.header(f"3. Final Report for {st.session_state.candidate_details['name']}")
    
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
