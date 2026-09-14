import os

from app.services.email_service import (
    EmailService,
    EmailConfig
)

email_config = EmailConfig(
    smtp_host=os.getenv(
        "SMTP_HOST"
    ),
    smtp_port=int(
        os.getenv(
            "SMTP_PORT",
            "587"
        )
    ),
    username=os.getenv(
        "SMTP_USERNAME"
    ),
    password=os.getenv(
        "SMTP_PASSWORD"
    ),
    use_tls=True
)

email_service = EmailService(
    config=email_config,
    max_workers=3
)
