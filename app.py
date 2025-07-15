import streamlit as st
from openai import OpenAI
import json
import traceback
import unicodedata
from st_audiorec import st_audiorec
from fpdf import FPDF
import io
import csv

# --- Page Configuration ---
st.set_page_config(page_title="GenAI Interview Agent", page_icon="🤖", layout="wide")
st.title("🤖 GenAI Interview Agent")

# --- OpenAI Client Initialization ---
try:
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
except Exception:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- PDF & CSV Generation Functions ---
def create_pdf(details, report_data, holistic_summary):
    def sanitize_text(text):
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Interview Report for: {sanitize_text(details['name'])}", 0, 1, 'C')
        pdf.ln(10)

        pdf.set_font("Arial", 'B', 12)
        pdf.multi_cell(0, 5, "Holistic Assessment:")
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 5, sanitize_text(holistic_summary))
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
            # ... (rest of the PDF generation logic for per-question details) ...
        
        return pdf.output(dest='S').encode('latin1')
    except Exception as e:
        st.error(f"Failed to generate PDF. Error: {e}")
        return None

def create_csv_string(details, report_data, holistic_summary):
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Candidate Name', details['name']])
    writer.writerow(['Role Level', details['role_level']])
    writer.writerow(['Holistic Summary', holistic_summary])
    writer.writerow([]) # Spacer
    writer.writerow(['Question', 'Candidate Answer', 'Evaluation Summary', 'Clarity', 'Correctness', 'Depth'])

    for item in report_data:
        eval_data = item.get('evaluation', {})
        summary = eval_data.get('overall_summary', 'N/A')
        scores = eval_data.get('evaluation', {})
        clarity = scores.get('clarity', {}).get('score', 0)
        correctness = scores.get('correctness', {}).get('score', 0)
        depth = scores.get('depth', {}).get('score', 0)
        writer.writerow([item['question'], item['answer'], summary, clarity, correctness, depth])
        
    return output.getvalue()

# --- Session State Initialization ---
if 'status' not in st.session_state:
    st.session_state.status = 'setup'
    st.session_state.candidate_details = {}
    st.session_state.questions_to_ask = []
    st.session_state.notes = ""
    st.session_state.labeled_transcript = ""
    st.session_state.detailed_report = []
    st.session_state.holistic_summary = ""
    st.session_state.audio_bytes = None
    st.session_state.question_number = 0

# --- Helper Functions (start_new_interview, get_ai_response, generate_question) ---
# These functions remain unchanged from the last complete version.
def start_new_interview():
    # ...
    pass
def get_ai_response(prompt_text, model="gpt-4-turbo", as_json=False):
    # ...
    return ...
def generate_question(role_level, question_number):
    # ...
    return ...

# --- App Workflow ---

# --- STAGE 1 & 2: SETUP & QUESTION PREP ---
if st.session_state.status in ['setup', 'question_prep']:
    # This logic remains the same as the last complete version.
    # It ends when the user clicks "Proceed to Live Recording".
    pass

# --- STAGE 3: LIVE RECORDING ---
elif st.session_state.status == 'recording':
    # This logic remains the same.
    # It automatically navigates to 'processing' when recording stops.
    pass

# --- STAGE 4: PROCESSING & CONFIRMATION ---
elif st.session_state.status in ['processing', 'transcript_confirmation']:
    # This logic remains the same.
    # It ends when the user clicks "Confirm Transcript & Run Final Evaluation".
    pass

# --- STAGE 5: FINAL EVALUATION & REPORT ---
elif st.session_state.status in ['evaluating', 'report']:
    st.header(f"Stage 5: Final Report for {st.session_state.candidate_details['name']}")
    
    # This block runs the evaluation pipeline once.
    if st.session_state.status == 'evaluating':
        with st.spinner("Running detailed per-question evaluation..."):
            # ... (Per-question evaluation loop remains the same) ...
            st.session_state.detailed_report = ... # Assumes this list is populated

        with st.spinner("Generating final holistic assessment..."):
            # New AI call for the holistic summary
            summary_prompt = f"""You are an expert hiring manager. Based on the following per-question evaluations of a candidate, write a final, holistic summary (2-3 paragraphs) of their performance, highlighting strengths, weaknesses, and a final recommendation.
            
            EVALUATIONS:
            {json.dumps(st.session_state.detailed_report, indent=2)}
            """
            holistic_summary = get_ai_response(summary_prompt)
            if holistic_summary:
                st.session_state.holistic_summary = holistic_summary
            
        st.session_state.status = 'report'
        st.rerun()

    # This block displays the final report.
    if st.session_state.status == 'report':
        st.subheader("Overall Holistic Assessment")
        st.info(st.session_state.holistic_summary)
        st.markdown("---")
        
        # New Download Logic
        with st.popover("Download Report"):
            st.write("Select a format:")
            
            # PDF Download Button
            pdf_data = create_pdf(st.session_state.candidate_details, st.session_state.detailed_report, st.session_state.holistic_summary)
            if pdf_data:
                st.download_button(
                    label="Download as PDF",
                    data=pdf_data,
                    file_name=f"Report_{st.session_state.candidate_details['name']}.pdf"
                )
            
            # CSV Download Button
            csv_data = create_csv_string(st.session_state.candidate_details, st.session_state.detailed_report, st.session_state.holistic_summary)
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name=f"Report_{st.session_state.candidate_details['name']}.csv"
            )

        st.subheader("Detailed Question-by-Question Breakdown")
        if st.session_state.detailed_report:
            # ... (Logic to display the per-question report remains the same) ...
            pass
        else:
            st.error("Could not generate detailed report.")

        st.button("Start New Interview", on_click=start_new_interview)
