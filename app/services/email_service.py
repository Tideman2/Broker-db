import threading
import queue
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = "your_email@gmail.com"
    password: str = "your_password"
    use_tls: bool = True


@dataclass
class Email:
    to: str
    subject: str
    body: str
    from_email: Optional[str] = None
    html_body: Optional[str] = None


class EmailService:
    def __init__(self, config: EmailConfig, max_workers: int = 3):
        self.config = config
        self.queue = queue.Queue()
        self.workers = []
        self.running = False
        self.max_workers = max_workers

    def _send_single_email(self, email: Email):
        """Send one email with retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create message
                msg = MIMEMultipart() if email.html_body else MIMEText(email.body)
                msg['Subject'] = email.subject
                msg['To'] = email.to
                msg['From'] = email.from_email or self.config.username

                if email.html_body:
                    msg.attach(MIMEText(email.body, 'plain'))
                    msg.attach(MIMEText(email.html_body, 'html'))
                else:
                    msg = MIMEText(email.body)
                    msg['Subject'] = email.subject
                    msg['To'] = email.to
                    msg['From'] = email.from_email or self.config.username

                # Send
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    if self.config.use_tls:
                        server.starttls()
                    server.login(self.config.username, self.config.password)
                    server.send_message(msg)

                logger.info(f"Email sent to {email.to}")
                return True

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1} failed for {email.to}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to send to {email.to} after {max_retries} attempts")
                    return False

    def _worker(self, worker_id: int):
        """Background worker thread"""
        logger.info(f"Worker {worker_id} started")
        while self.running:
            try:
                email = self.queue.get(timeout=1)
                self._send_single_email(email)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        logger.info(f"Worker {worker_id} stopped")

    def start(self):
        """Start background workers"""
        if self.running:
            return

        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker,
                args=(i,),
                daemon=True,
                name=f"EmailWorker-{i}"
            )
            worker.start()
            self.workers.append(worker)

        logger.info(f"Email service started with {self.max_workers} workers")

    def stop(self, wait: bool = True):
        """Stop background workers"""
        self.running = False

        # Wait for queue to empty
        if wait:
            self.queue.join()

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=2)

        self.workers.clear()
        logger.info("Email service stopped")

    def send_email(self, to: str, subject: str, body: str, html_body: Optional[str] = None):
        """Queue an email to be sent"""
        email = Email(to=to, subject=subject, body=body, html_body=html_body)
        self.queue.put(email)
        logger.info(
            f"Email queued for {to} (queue size: {self.queue.qsize()})")

    def send_bulk(self, emails: list):
        """Queue multiple emails"""
        for email in emails:
            self.queue.put(email)
        logger.info(f"Email queued for {len(emails)} recipients")


# Usage
if __name__ == "__main__":
    config = EmailConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="your_email@gmail.com",
        password="your_password"
    )

    email_service = EmailService(config, max_workers=3)
    email_service.start()

    # Send emails
    email_service.send_email(
        to="user@example.com",
        subject="Welcome!",
        body="Welcome to our service!",
        html_body="<h1>Welcome!</h1><p>Welcome to our service!</p>"
    )

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        email_service.stop()
