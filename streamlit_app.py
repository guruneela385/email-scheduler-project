# streamlit_app.py
import streamlit as st
import mysql.connector
import re
import os
from datetime import datetime, date, time
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

# Ensure upload directory exists
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Connection ---
def connect_db():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            recipient_email VARCHAR(255),
            message_text TEXT,
            subject VARCHAR(255),
            scheduled_date DATETIME,
            status ENUM('pending', 'sent') DEFAULT 'pending',
            attachment_path VARCHAR(500) NULL
        )
    """)
    conn.commit()
    return conn

# Load Messages from Database
def load_messages():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, recipient_email, subject, message_text, scheduled_date, status, attachment_path FROM messages ORDER BY scheduled_date DESC")
    messages = cursor.fetchall()
    conn.close()
    return messages

# --- Main Application Logic ---
def run_main_app():
    st.title("Digital Time Capsule – Future Message Locker")
    menu = ["Schedule Message", "View Messages", "Back to Landing"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Schedule Message":
        st.subheader("Schedule a New Message")
        recipient = st.text_input("Recipient Email")
        MAX_SUBJECT_LENGTH = 60
        subject = st.text_input("Subject", max_chars=MAX_SUBJECT_LENGTH)
        MAX_MESSAGE_LENGTH = 5000
        message = st.text_area("Message", max_chars=MAX_MESSAGE_LENGTH)

        col1, col2 = st.columns(2)
        with col1:
            scheduled_date = st.date_input("Scheduled Date", min_value=date.today())
        with col2:
            scheduled_time = st.time_input("Scheduled Time", value=time(datetime.now().hour, datetime.now().minute + 1))

        uploaded_file = st.file_uploader("Attach File (Optional)", type=["jpg", "png", "pdf", "mp4", "docx"])

        if st.button("Schedule Message"):
            if not recipient.strip() or not subject.strip() or not message.strip() or not scheduled_date or not scheduled_time:
                st.error("All fields (Recipient, Subject, Message, Date, Time) are required!")
                return

            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", recipient):
                st.error("Invalid email address! Please enter a valid email.")
                return

            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
            if scheduled_datetime < datetime.now():
                st.error("Cannot schedule messages in the past! Please select a future date and time.")
                return

            attachment_path = None
            if uploaded_file:
                original_filename = uploaded_file.name
                base_original_filename = os.path.basename(original_filename)
                unique_filename = f"{uuid.uuid4()}_{base_original_filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                attachment_path = file_path

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (recipient_email, subject, message_text, scheduled_date, status, attachment_path) VALUES (%s, %s, %s, %s, %s, %s)",
                (recipient, subject, message, scheduled_datetime, 'pending', attachment_path)
            )
            conn.commit()
            conn.close()
            st.success("Message scheduled successfully! It will be sent at the specified time.")
            st.rerun()

    elif choice == "View Messages":
        st.subheader("Your Scheduled Messages")
        messages = load_messages()

        if not messages:
            st.info("No messages scheduled yet. Use the 'Schedule Message' tab to add one!")
        else:
            for msg in messages:
                msg_id, recipient, subject, message_text, scheduled_date, status, attachment_path = msg
                st.markdown(f"**To:** `{recipient}`")
                st.markdown(f"**Subject:** `{subject}`")
                st.markdown(f"**Message:**")
                st.info(message_text)
                st.write(f"**Scheduled for:** {scheduled_date.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Status:** {status.capitalize()}")

                if attachment_path:
                    display_filename = os.path.basename(attachment_path)
                    st.write(f"📎 **Attachment:** `{display_filename}`")

                if status == 'pending':
                    if "edit_mode" not in st.session_state:
                        st.session_state["edit_mode"] = {}
                    if msg_id not in st.session_state["edit_mode"]:
                        st.session_state["edit_mode"][msg_id] = False

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(f"Cancel Message {msg_id}", key=f"cancel_{msg_id}"):
                            conn = connect_db()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM messages WHERE id = %s", (msg_id,))
                            conn.commit()
                            conn.close()
                            st.success(f"Message {msg_id} has been canceled!")
                            if attachment_path and os.path.exists(attachment_path):
                                try:
                                    os.remove(attachment_path)
                                    st.info(f"Attachment {os.path.basename(attachment_path)} deleted.")
                                except OSError as e:
                                    st.warning(f"Could not delete attachment: {e}")
                            st.rerun()

                    with col2:
                        if not st.session_state["edit_mode"][msg_id]:
                            if st.button(f"Edit Message {msg_id}", key=f"edit_{msg_id}"):
                                st.session_state["edit_mode"][msg_id] = True
                                st.rerun()
                        else:
                            st.subheader(f"Edit Message {msg_id}")
                            new_subject = st.text_input("New Subject", value=subject, key=f"new_subject_{msg_id}")
                            new_message = st.text_area("New Message", value=message_text, key=f"new_message_{msg_id}")
                            new_attachment = st.file_uploader("New Attachment (Optional)", type=["jpg", "png", "pdf", "mp4", "docx"], key=f"new_attachment_{msg_id}")

                            if attachment_path and not new_attachment:
                                if st.checkbox(f"Remove current attachment: {os.path.basename(attachment_path)}", key=f"remove_attachment_{msg_id}"):
                                    new_attachment_path = None
                                else:
                                    new_attachment_path = attachment_path
                            else:
                                new_attachment_path = attachment_path

                            if new_attachment:
                                if attachment_path and os.path.exists(attachment_path) and attachment_path != new_attachment_path:
                                    try:
                                        os.remove(attachment_path)
                                    except OSError as e:
                                        st.warning(f"Could not delete old attachment: {e}")

                                original_filename = new_attachment.name
                                base_original_filename = os.path.basename(original_filename)
                                unique_filename = f"{uuid.uuid4()}_{base_original_filename}"
                                new_file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                                with open(new_file_path, "wb") as f:
                                    f.write(new_attachment.getbuffer())
                                new_attachment_path = new_file_path

                            if st.button(f"Save Changes {msg_id}", key=f"save_changes_{msg_id}"):
                                conn = connect_db()
                                cursor = conn.cursor()
                                cursor.execute(
                                    "UPDATE messages SET subject = %s, message_text = %s, attachment_path = %s WHERE id = %s",
                                    (new_subject, new_message, new_attachment_path, msg_id)
                                )
                                conn.commit()
                                conn.close()

                                st.success(f"Message {msg_id} has been updated!")
                                st.session_state["edit_mode"][msg_id] = False
                                st.rerun()

                            if st.button(f"Cancel Edit {msg_id}", key=f"cancel_edit_{msg_id}"):
                                st.session_state["edit_mode"][msg_id] = False
                                st.rerun()
                st.write("---")
    elif choice == "Back to Landing":
        st.session_state.show_main_app = False
        st.rerun()

# --- Landing Page Logic ---
def landing_page():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        html, body, [class*="st-emotion"] {
            font-family: 'Poppins', sans-serif;
            color: #333;
            background: linear-gradient(135deg, #f0f2f5 0%, #e0e4eb 100%);
        }
        .landing-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            padding: 20px;
            box-sizing: border-box;
        }
        .landing-title {
            font-size: 3.5em;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 0.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .landing-subtitle {
            font-size: 1.5em;
            color: #555;
            margin-bottom: 2em;
            max-width: 700px;
            line-height: 1.6;
        }
        .get-started-button {
            background-color: #4CAF50;
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.2em;
            cursor: pointer;
            transition: background-color 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .get-started-button:hover {
            background-color: #45a049;
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.3);
        }
        .get-started-button:active {
            transform: translateY(0);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown("<div class='landing-container'>", unsafe_allow_html=True)
        st.markdown("<h1 class='landing-title'>Welcome to Digital Time Capsule</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p class='landing-subtitle'>Your secure locker for future messages. Schedule emails with attachments to be delivered precisely when you want them to be seen.</p>",
            unsafe_allow_html=True
        )
        if st.button("Get Started", key="get_started_button", on_click=lambda: setattr(st.session_state, 'show_main_app', True)):
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- Entry Point ---
if __name__ == "__main__":
    if 'show_main_app' not in st.session_state:
        st.session_state.show_main_app = False

    if st.session_state.show_main_app:
        run_main_app()
    else:
        landing_page()
