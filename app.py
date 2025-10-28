import streamlit as st
import random, string, smtplib, re, io, base64, httpx, uuid
from datetime import datetime
from azure.data.tables import TableServiceClient
from openai import AzureOpenAI
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PyPDF2 import PdfReader, PdfWriter
import io
import base64
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import streamlit as st

def show_steps(current_step):
    steps = ["Input Details", "Generate Letter", "Preview Letter", "Upload & Verify Document", "Admin Approval", "Preview & Download"]
    cols = st.columns(len(steps))
    for index, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if current_step > index:
                st.markdown(f'<span style="background:#11c26d; color:#fff; padding:5px 10px; border-radius:10px;">&#10003; {step}</span>', unsafe_allow_html=True)
            elif current_step == index:
                st.markdown(f'<span style="border:2px solid #11c26d; padding:5px 10px; border-radius:10px; color:#11c26d; font-weight:bold;">{step}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:#888;">{step}</span>', unsafe_allow_html=True)

def create_text_overlay(text, x=45, y=660, width=520, height=180, font_size=14, line_spacing=5):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    style = ParagraphStyle('custom', fontName='Helvetica', fontSize=font_size, leading=font_size+line_spacing, alignment=4)
    para = Paragraph(text, style)
    frame = Frame(x, y - height, width, height, showBoundary=0)
    frame.addFromList([para], can)
    can.save()
    packet.seek(0)
    return packet

def pdf_viewer(pdf_bytes, height=650):
    b64 = base64.b64encode(pdf_bytes).decode()
    iframe = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}px" frameborder="0"></iframe>'
    st.markdown(iframe, unsafe_allow_html=True)

# ---- Settings ----
connection_string = "DefaultEndpointsProtocol=https;AccountName=cloudcomputingteam24;AccountKey=mlPs4Lp4gUiYPJ/veus/d59mGC53o9bjsQBKpGphtxZ6UU45Tu58fBOboJNEu3YHeT73M6ImT4dd+ASt8yxG2Q==;EndpointSuffix=core.windows.net"
user_table_name = "StudentLogin"
bonafide_table_name = "BonafideRequests"
service = TableServiceClient.from_connection_string(conn_str=connection_string)
user_table_client = service.create_table_if_not_exists(table_name=user_table_name)
bonafide_table_client = service.create_table_if_not_exists(table_name=bonafide_table_name)
ADMIN_EMAIL = "admin@rec.edu.in"
ADMIN_PASSWORD = "rec@admin"
certificate_template = '''
This is to certify that Mr./Ms. [Student Name], son/daughter of Mr./Mrs. [Parent's Name], is a bonafide student of Rajalakshmi Engineering College, Chennai, enrolled in the [Department Name] for the [Course Name] program during the academic year [Start Year] to [End Year].
He/She has completed/ is currently pursuing his/her studies in the [Year/Semester] of the course.
This certificate is issued to him/her on request for the purpose of [Purpose, e.g., Higher Studies, Bank Loan, Passport, etc.].
'''

ai_endpoint = "https://skee-mff5fbkc-eastus2.cognitiveservices.azure.com/"
ai_api_key = "F7UGRXFhkjG9JIsUm3s2FXx089ON7lBfruo87vCnJAEzR165MgCYJQQJ99BIACHYHv6XJ3w3AAAAACOGpbGy"
deployment_name = "Letter-generator"
ai_api_version = "2025-01-01-preview"
client = AzureOpenAI(api_version=ai_api_version, azure_endpoint=ai_endpoint, api_key=ai_api_key, timeout=httpx.Timeout(30.0))
doc_endpoint = "https://documentverifier.cognitiveservices.azure.com/"
doc_api_key = "LFiuyHgu5btJnQkmoWybnX3JEa1tgRBbs9jMbgpicvpmoVC7EPrHJQQJ99BIACGhslBXJ3w3AAALACOGMc9l"
doc_client = DocumentAnalysisClient(endpoint=doc_endpoint, credential=AzureKeyCredential(doc_api_key))

def send_otp_email(to_email, otp):
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "k44423759@gmail.com"
    SMTP_PASSWORD = "nlgo qefn cuyr pije"
    subject = "Your OTP for REC Bonafide Portal"
    body = f"Dear Student,\n\nYour OTP for password reset is: {otp}\n\nRegards,\nREC Digital Desk"
    message = f"Subject: {subject}\n\n{body}"
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, to_email, message)

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))
def check_student_login(email, password):
    entities = user_table_client.query_entities(f"PartitionKey eq '{email}'")
    for entity in entities:
        if entity.get("Password") == password:
            return True
    return False
def store_bonafide_request(email, entries, letter, doc_status):
    row_key = str(uuid.uuid4())
    entity = {
        "PartitionKey": email,
        "RowKey": row_key,
        "StudentName": entries["Student Name"],
        "RegNo": entries["Reg No"],
        "Purpose": entries["Purpose"],
        "GeneratedLetter": letter,
        "DocumentVerification": doc_status,
        "AdminApproval": "Pending",
        "RequestDate": datetime.utcnow().isoformat()
    }
    bonafide_table_client.create_entity(entity=entity)
def update_bonafide_status(rowkey, status):
    entity = next(e for e in bonafide_table_client.list_entities() if e["RowKey"] == rowkey)
    entity["AdminApproval"] = status
    bonafide_table_client.update_entity(entity)
def college_branding():
    st.markdown("""
    <div style="text-align:center;">
      <img src="https://www.rajalakshmi.org/images/logo.png" style="width:180px; margin-bottom:0.8em;" />
      <h1 style="font-size:2.7em;color:#6f2ca3;">Rajalakshmi Engineering College</h1>
      <p style="font-size:1.20em;color:#222;">Bonafide Certificate Request Portal</p>
    </div>
    <hr style="margin-bottom:2em;">
    """, unsafe_allow_html=True)

def extract_text(uploaded_file):
    poller = doc_client.begin_analyze_document("prebuilt-document", document=uploaded_file)
    result = poller.result()
    text = " ".join(line.content for page in result.pages for line in page.lines)
    return text
def verify_fields(extracted_text, expected_name, expected_regno):
    name_ok = expected_name.lower() in extracted_text.lower()
    regno_ok = expected_regno.lower() in extracted_text.lower()
    col_ok = "rajalakshmi engineering college" in extracted_text.lower()
    return name_ok, regno_ok, col_ok
def login():
    college_branding()
    with st.form("login_form"):
        role = st.radio("🔑 Select your role", ["Student", "Admin"], horizontal=True)
        email = st.text_input("College Email", placeholder="e.g. 220701001@rajalakshmi.edu.in")
        password = st.text_input("Password", type="password")
        forgot_pw = st.checkbox("Forgot Password?", key="forgot_pw")
        login_clicked = st.form_submit_button("Login", use_container_width=True)
        if login_clicked and not forgot_pw:
            if role == "Admin":
                if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                    st.session_state["role"] = "admin"
                    st.session_state["user"] = email
                    st.session_state["logged_in"] = True
                    st.success("Admin login successful!")
                else:
                    st.error("Invalid admin credentials.")
            else:
                if check_student_login(email, password):
                    st.session_state["role"] = "student"
                    st.session_state["user"] = email
                    st.session_state["logged_in"] = True
                    st.success("Student login successful!")
                else:
                    st.error("Invalid student credentials.")

def student_workflow(user_email):
    college_branding()

    if "step" not in st.session_state:
        st.session_state.step = 0
    if "approval_done" not in st.session_state:
        st.session_state.approval_done = False

    # Step 0: collect details
    if st.session_state.step == 0:
        st.header("Request Bonafide Certificate")
        st.session_state.entries = {}
        st.session_state.entries["Student Name"] = st.text_input("Student Name")
        st.session_state.entries["Parent's Name"] = st.text_input("Parent's Name")
        st.session_state.entries["Department Name"] = st.text_input("Department Name")
        st.session_state.entries["Course Name"] = st.text_input("Course Name")
        st.session_state.entries["Start Year"] = st.text_input("Start Year")
        st.session_state.entries["End Year"] = st.text_input("End Year")
        st.session_state.entries["Year/Semester"] = st.text_input("Year/Semester")
        st.session_state.entries["Purpose"] = st.text_input("Purpose")
        st.session_state.entries["Reg No"] = st.text_input("Reg No")
        if st.button("Generate Letter"):
            if all(st.session_state.entries.values()):
                prompt = f"""Write a formal Bonafide Certificate request letter:\n{st.session_state.entries}"""
                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=512,
                    temperature=0.7,
                )
                st.session_state.letter_text = response.choices[0].message.content
                st.session_state.step = 1
            else:
                st.error("Please fill all fields.")

    # Step 1: edit generated letter
    elif st.session_state.step == 1:
        st.header("Edit Letter")
        st.session_state.letter_text = st.text_area("Letter", value=st.session_state.letter_text, height=250)
        if st.button("Preview Letter"):
            if st.session_state.letter_text.strip():
                st.session_state.step = 2
            else:
                st.error("Letter can't be empty")

    # Step 2: preview letter
    elif st.session_state.step == 2:
        st.header("Preview Letter")
        st.write(st.session_state.letter_text)
        if st.button("Next: Upload Document"):
            st.session_state.step = 3

    # Step 3: document upload and verification
    elif st.session_state.step == 3:
        st.header("Upload Supporting Document")
        doc = st.file_uploader("Upload Document (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"])
        doc_status = None
        if doc:
            with st.spinner("Verifying document..."):
                try:
                    text = extract_text(doc)
                    name_ok, regno_ok, college_ok = verify_fields(text, st.session_state.entries["Student Name"], st.session_state.entries["Reg No"])
                    if name_ok and regno_ok and college_ok:
                        doc_status = "Verified"
                        st.success("Verification successful")
                        if st.button("Submit for Admin Approval"):
                            store_bonafide_request(user_email, st.session_state.entries, st.session_state.letter_text, doc_status)
                            st.session_state.step = 4
                            st.success("Request submitted, waiting for admin approval.")
                    else:
                        doc_status = "Verification Failed"
                        st.error("Verification failed. Check document.")
                except Exception as e:
                    doc_status = "Verification Error"
                    st.error(f"Verification error: {e}")

    # Step 4: wait for admin approval
    elif st.session_state.step == 4:
        st.header("Waiting for Admin Approval...")
        records = [e for e in bonafide_table_client.list_entities() if e["PartitionKey"] == user_email]
        if records:
            status = records[-1].get("AdminApproval", "Pending")
            if status == "Approved" or st.session_state.approval_done:
                st.session_state.step = 5
            else:
                st.info(f"Current status: {status}. Please refresh or check back later.")
        else:
            st.warning("No request found. Please submit request first.")

        if st.button("Check Status"):
            st.rerun()

    # Step 5: Certificate preview and download
    elif st.session_state.step == 5:
        st.header("Certificate Preview & Download")
        try:
            with open("template.pdf", "rb") as f:
                template_pdf_bytes = f.read()
            template_stream = io.BytesIO(template_pdf_bytes)
            template_pdf = PdfReader(template_stream)
            pairs = "\n".join(f"{k}: {v}" for k, v in st.session_state.entries.items())
            prompt = f"""Replace the brackets in the following certificate template with these values.
Template:
{certificate_template}
Field values:
{pairs}
Return ONLY the final certificate text formatted appropriately with all replacements."""
            with st.spinner("Generating certificate text..."):
                resp = client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a document automation assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=500,
                    temperature=0,
                )
                cert_text = resp.choices[0].message.content

            packet = create_text_overlay(cert_text)
            overlay_pdf = PdfReader(packet)
            template_page = template_pdf.pages[0]
            template_page.merge_page(overlay_pdf.pages[0])
            writer = PdfWriter()
            writer.add_page(template_page)
            out_bytes = io.BytesIO()
            writer.write(out_bytes)
            out_bytes.seek(0)

            st.markdown('<span style="font-size:1.5em">👁 <b>Preview Certificate</b></span>', unsafe_allow_html=True)
            pdf_viewer(out_bytes.read())

            st.download_button("Download Certificate PDF", out_bytes.getvalue(), "bonafide_certificate.pdf", "application/pdf")
            st.text_area("Certificate Text", cert_text, height=300)

        except FileNotFoundError:
            st.error("Certificate template file template.pdf not found in the current folder.")

def admin_dashboard():
    college_branding()
    st.header("Pending Bonafide Requests")
    requests = [e for e in bonafide_table_client.list_entities() if e["AdminApproval"] == "Pending"]
    for req in requests:
        st.markdown(f"**Name:** {req.get('StudentName', '')}")
        st.markdown(f"**Roll No:** {req.get('RegNo', '')}")
        st.markdown(f"**Purpose:** {req.get('Purpose', '')}")

        if st.button(f"View Letter - {req['RowKey']}"):
            st.text_area("Request Letter Preview", req.get("GeneratedLetter", ""), height=250)

        accept_key = f"accept_{req['RowKey']}"
        if st.button("Accept", key=accept_key):
            # Update status
            update_bonafide_status(req["RowKey"], "Approved")
            # Set approval done flag in session state
            st.session_state["approval_done"] = True
            st.success(f"Request approved for {req.get('StudentName', '')}")



def main():
    if not st.session_state.get("logged_in", False):
        login()
    else:
        if st.session_state.get("role") == "student":
            student_workflow(st.session_state.get("user"))
        elif st.session_state.get("role") == "admin":
            admin_dashboard()

if __name__ == "__main__":
    main()
