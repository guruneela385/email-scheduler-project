# Digital Time Capsule – Future Message Locker

This project is an email scheduling application that allows users to schedule emails to be sent at a future date and time. It consists of two main components: a Streamlit web interface for scheduling and managing messages, and a Python backend script that periodically checks for and sends scheduled emails.

## Features

* Schedule emails with recipient, subject, message body, and a specific date/time.
* Optionally attach files (images, PDFs, videos, documents) to emails.
* View all scheduled messages.
* Cancel pending scheduled messages.
* Edit pending scheduled messages (subject, message, new attachment).
* Uses a MySQL database to store message details.
* Emails are sent securely via Gmail SMTP.

## Technologies Used

* **Backend:** Python 3, `APScheduler`, `smtplib`, `mysql-connector-python`, `python-dotenv`
* **Frontend:** Streamlit
* **Database:** MySQL

## Setup Instructions

Follow these steps to set up and run the project locally.

### 1. Clone the Repository

First, clone this repository to your local machine:
```bash
git clone https://github.com/guruneela385/email-scheduler-project.git
cd email-scheduler-project