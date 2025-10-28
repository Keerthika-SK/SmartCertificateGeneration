import streamlit as st
import random
import string
import smtplib
from azure.data.tables import TableServiceClient

# Azure Table Storage config
connection_string = "DefaultEndpointsProtocol=https;AccountName=cloudcomputingteam24;AccountKey=mlPs4Lp4gUiYPJ/veus/d59mGC53o9bjsQBKpGphtxZ6UU45Tu58fBOboJNEu3YHeT73M6ImT4dd+ASt8yxG2Q==;EndpointSuffix=core.windows.net"
table_name = "StudentLogin"

service = TableServiceClient.from_connection_string(conn_str=connection_string)
table_client = service.get_table_client(table_name)

# Admin credentials
ADMIN_EMAIL = "admin@rec.edu.in"
ADMIN_PASSWORD = "rec@admin"

# Helper: send OTP email (configure SMTP accordingly)
def send_otp_email(to_email, otp):
    # Configure SMTP securely for your email provider
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "k44423759@gmail.com"
    SMTP_PASSWORD = "nlgo qefn cuyr pije"

    subject = "Your OTP for Bonafide System Login"
    body = f"Your OTP code is: {otp}"

    message = f"Subject: {subject}\n\n{body}"

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, to_email, message)

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def check_student_login(email, password):
    entities = table_client.query_entities(f"PartitionKey eq '{email}'")
    for entity in entities:
        if entity.get("Password") == password:
            return True
    return False

def login():
    st.title("Bonafide System Login")

    role = st.radio("Select your role", ["Student", "Admin"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if role == "Student":
        forgot_pw = st.checkbox("Forgot Password?")
        if forgot_pw:
            otp_sent = st.session_state.get("otp_sent", False)
            if not otp_sent and st.button("Send OTP"):
                otp = generate_otp()
                try:
                    send_otp_email(email, otp)
                    st.session_state["otp"] = otp
                    st.session_state["otp_sent"] = True
                    st.success("OTP sent to your email.")
                except Exception as e:
                    st.error("Failed to send OTP. Check email config.")
            if st.session_state.get("otp_sent", False):
                user_otp = st.text_input("Enter OTP")
                if st.button("Verify OTP"):
                    if user_otp == st.session_state.get("otp"):
                        st.success("OTP verified! You can now login by entering password.")
                    else:
                        st.error("Invalid OTP.")
        else:
            if st.button("Login"):
                if check_student_login(email, password):
                    st.success("Student login successful!")
                    st.session_state["role"] = "student"
                    st.session_state["user"] = email
                    st.session_state["logged_in"] = True
                else:
                    st.error("Invalid student credentials.")
    else:  # Admin login
        if st.button("Login"):
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                st.success("Admin login successful!")
                st.session_state["role"] = "admin"
                st.session_state["user"] = email
                st.session_state["logged_in"] = True
            else:
                st.error("Invalid admin credentials.")


def main():
    if not st.session_state.get("logged_in", False):
        login()
    else:
        if st.session_state["role"] == "student":
            st.write(f"Welcome Student: {st.session_state['user']}")
            # Load your student workflow here
        elif st.session_state["role"] == "admin":
            st.write(f"Welcome Admin: {st.session_state['user']}")
            # Load your admin dashboard here

if __name__ == "__main__":
    main()
