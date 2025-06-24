# scheduler.py
import os
import mysql.connector
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv # Make sure you've installed python-dotenv: pip install python-dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging for better tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection
def connect_db():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return conn
    except mysql.connector.Error as e:
        logging.error(f"❌ Database Connection Error: {e}")
        return None

# Retrieve email credentials from environment variables
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Function to send an email with optional attachments
def send_email(recipient_email, subject, message_text, attachment_path=None):
    try:
        logging.info(f"📨 Attempting to send email to {recipient_email}...")

        # Create a multipart email
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = recipient_email

        # Attach email body
        msg.attach(MIMEText(message_text, "plain"))

        # Attach file if provided
        if attachment_path and os.path.exists(attachment_path):
            logging.info(f"📎 Attaching file: {attachment_path}")
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
                msg.attach(part)

        # Create secure SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())

        logging.info(f"✅ Email successfully sent to {recipient_email}")
        return True

    except smtplib.SMTPException as e:
        logging.error(f"❌ SMTP Error: {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Unexpected error while sending email: {e}")
        return False

# Function to check and send scheduled emails
def check_scheduled_messages():
    logging.info("🔎 Checking scheduled messages...")

    conn = connect_db()
    if conn is None:
        logging.warning("❌ Could not connect to the database. Retrying in the next cycle...")
        return

    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, recipient_email, subject, message_text, scheduled_date, attachment_path FROM messages WHERE status = 'pending'")
        messages = cursor.fetchall()

        if not messages:
            logging.info("✅ No pending emails. Waiting for new messages...")
            return

        for msg in messages:
            message_id, recipient_email, subject, message_text, scheduled_date, attachment_path = msg

            logging.info(f"🔹 Processing Message ID {message_id}: {recipient_email} | Scheduled: {scheduled_date}")

            if datetime.now() >= scheduled_date:
                logging.info(f"📨 Sending Message ID {message_id} to {recipient_email}...")

                if send_email(recipient_email, subject, message_text, attachment_path):
                    cursor.execute("UPDATE messages SET status = 'sent' WHERE id = %s", (message_id,))
                    conn.commit()
                    logging.info(f"✅ Message ID {message_id} marked as 'sent'")

    except mysql.connector.Error as e:
        logging.error(f"❌ Database error: {e}")
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Scheduler
scheduler = BlockingScheduler()
scheduler.add_job(check_scheduled_messages, "interval", minutes=1)

if __name__ == "__main__":
    logging.info("📨 Email scheduler is running...")
    check_scheduled_messages()  # Run once at startup
    scheduler.start()