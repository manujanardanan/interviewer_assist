import streamlit as st
from openai import OpenAI
import json
import traceback
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

# --- NEW, MORE ROBUST PDF GENERATION FUNCTION ---
def create_pdf(details, report_data):
    # This function now has a more robust way to handle special characters
    def sanitize_text(text):
        # Replace common problematic Unicode characters with ASCII equivalents
        text = str(text)
        replacements = {
            '’': "'", '“': '"', '”': '"', '—': '-', '…': '...'
        }
        for uni_char, ascii_char in replacements.items():
            text = text.replace(uni_char, ascii_char)
        # Encode to latin-1, replacing any other unknown characters
        return text.encode('latin-1', 'replace').decode('latin-1')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Interview Report for: {sanitize_text(details['name'])}", 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Role Level: {details['role_level']} | Salary Expectation: {details['lpa']} LPA", 0, 1, 'C')
    pdf.ln(10)

    for i, item in enumerate(report_data):
        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 5, f"Question {i+1}: {sanitize_text(item['question'])}")
        pdf.ln(2)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.multi_cell(0, 5, "Candidate's Answer:")
        pdf.set_font("Arial", 'I', 11)
        pdf.multi_cell(0, 5, f"{sanitize_text(item.get('answer', 'N/A'))}")
        pdf.ln(2)

        pdf.set_font("Arial", 'B', 11)
        pdf.multi_cell(0, 5, "Evaluation:")
        pdf.set_font("Arial", '', 11)
        
        # Format the evaluation JSON nicely instead of dumping it raw
        eval_data = item.get('evaluation', {}).get('evaluation', {})
        if eval_data:
            clarity = eval_data.get('clarity', {})
            correctness = eval_data.get('correctness', {})
            depth = eval_data.get('depth', {})
            pdf.multi_cell(0, 5, f"  Clarity: {clarity.get('score', 0)}/10 - {sanitize_text(clarity.get('justification', ''))}")
            pdf.multi_cell(0, 5, f"  Correctness: {correctness.get('score', 0)}/10 - {sanitize_text(correctness.get('justification', ''))}")
            pdf.multi_cell(0, 5, f"  Depth: {depth.get('score', 0)}/10 - {sanitize_text(depth.get('justification', ''))}")
        
        summary = item.get('evaluation', {}).get('overall_summary', 'N/A')
        pdf.multi_cell(0, 5, f"Summary: {sanitize_text(summary)}")
        pdf.ln(8)
    
    return pdf.output(dest='S').encode('latin1')

# --- Session State Initialization ---
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.questions_to_ask = []
    st.session_state.notes = ""
    st.session_state.labeled_transcript = ""
    st.session_state.detailed_report = []
    st.session_state.audio_bytes = None
    st.session_state.question_number = 0

# --- Helper Functions ---
def start_new_interview():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def get_ai_response(prompt_text, model="gpt-4-turbo", as_json=False):
    try:
        messages = [{"role": "system", "content": "You are a helpful assistant designed to output JSON if requested."}, {"role": "user", "content": prompt_text}]
        if as_json:
            response = client.chat.completions.create(model=model, response_format={"type": "json_object"}, messages=messages)
            return json.loads(response.choices[0].message.content)
        else:
            response = client.chat.completions.create(model=model, messages=messages, temperature=0.7, max_tokens=1000)
            return response.choices[0].message.content
    except Exception as e:
        st.error(f"AI Error: {e}")
        st.error(traceback.format_exc())
        return None

def generate_question(role_level, question_number):
    prompt = ""
    if question_number == 1:
        prompt = f"Generate ONE open-ended, situational GenAI interview question for a '{role_level}' level candidate..."
    elif question_number == 2:
        prompt = f"Generate a problem-situation for a '{role_level}' level GenAI professional..."
    elif question_number == 3:
        prompt = f"Generate a problem for a '{role_level}' level GenAI professional where the problem and diagnosis are given..."
    elif question_number == 4:
        prompt = f"Generate a moderately tough diagnostic GenAI interview question for a '{role_level}' level candidate..."
    if prompt:
        return get_ai_response(prompt)
    return "All questions have been asked."

# --- STAGE 1: SETUP ---
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

# --- STAGE 2: QUESTION PREPARATION ---
elif st.session_state.status == 'question_prep':
    st.header("Stage 2: Prepare Interview Questions")
    if 'rephrase_triggered' in st.session_state and st.session_state.rephrase_triggered:
        # Handle rephrasing action
        pass # Logic remains the same
    if 'question_number' in st.session_state and st.session_state.question_number > len(st.session_state.questions_to_ask):
        # Handle new question generation
        pass # Logic remains the same
    # ... UI for question prep also remains the same
    if st.button("Proceed to Live Recording", type="primary"):
        st.session_state.status = 'recording'
        st.rerun()

# --- STAGE 3: LIVE RECORDING ---
elif st.session_state.status == 'recording':
    st.header("Stage 3: Live Recording")
    # ... UI for recording remains the same
    audio_bytes = st_audiorec()
    if audio_bytes:
        st.session_state.audio_bytes = audio_bytes
        st.session_state.status = 'processing'
        st.rerun()

# --- STAGE 4: PROCESSING & CONFIRMATION ---
elif st.session_state.status in ['processing', 'transcript_confirmation']:
    if st.session_state.status == 'processing':
        with st.spinner("Step 1/2: Transcribing audio..."):
            raw_transcript = ""
            try:
                transcript_response = client.audio.transcriptions.create(model="whisper-1", file=("interview.wav", st.session_state.audio_bytes))
                raw_transcript = transcript_response.text
            except Exception as e:
                st.error(f"Transcription Failed: {e}")
                st.session_state.status = 'recording'
                st.stop()
        
        with st.spinner("Step 2/2: AI is labeling speakers in the transcript..."):
            # --- NEW, MORE ROBUST PROMPT TO PREVENT HALLUCINATION ---
            labeling_prompt = f"""You are an assistant that processes interview transcripts. Reformat the transcript below by adding 'Interviewer:' and 'Candidate:' labels.

            **CRITICAL RULES:**
            1. The candidate's speech directly follows each question.
            2. If the speech after a question is not a real answer (e.g., they just repeat the question or say "I don't know"), label it as 'Candidate:' but keep the content as is.
            3. **Do NOT invent or create any text for the candidate's answer.** If you cannot find a distinct response for a question, label the answer as 'Candidate: [No clear answer was recorded for this question]'.
            
            QUESTIONS ASKED:
            {st.session_state.questions_to_ask}

            FULL TRANSCRIPT:
            {raw_transcript}
            """
            labeled_transcript = get_ai_response(labeling_prompt)
            if labeled_transcript:
                st.session_state.labeled_transcript = labeled_transcript
                st.session_state.status = 'transcript_confirmation'
                st.rerun()
            else:
                st.error("AI Speaker Labeling Failed.")
                st.session_state.status = 'recording'
    
    if st.session_state.status == 'transcript_confirmation':
        st.header("Stage 4: Confirm Speaker Labels")
        # --- NEW, CLEARER UI TEXT ---
        st.info("✅ **CRITICAL STEP:** Review the AI-labeled transcript below. **You can and should edit the text in this box** to correct any errors before running the final evaluation.")
        
        st.session_state.labeled_transcript = st.text_area(
            "**Editable Labeled Transcript:**",
            value=st.session_state.labeled_transcript,
            height=400
        )
        
        if st.button("Confirm Transcript & Run Final Evaluation", type="primary"):
            st.session_state.status = 'evaluating'
            st.rerun()

# --- STAGE 5: FINAL REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 5: Evaluation & Final Report")
    # ... Evaluation and Report logic remains the same
    if st.session_state.status == 'evaluating':
        # ... 
        pass
    if st.session_state.status == 'report':
        # ...
        pass
    st.button("Start New Interview", on_click=start_new_interview)
