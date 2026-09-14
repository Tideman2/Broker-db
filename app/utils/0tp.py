import pyotp


OTP_INTERVAL = 300
OTP_DIGITS = 6


def generate_otp_secret() -> str:
    return pyotp.random_base32()


def generate_otp(secret: str) -> str:

    totp = pyotp.TOTP(
        secret,
        digits=OTP_DIGITS,
        interval=OTP_INTERVAL,
    )

    return totp.now()


def verify_otp(
    secret: str,
    otp: str,
) -> bool:

    totp = pyotp.TOTP(
        secret,
        digits=OTP_DIGITS,
        interval=OTP_INTERVAL,
    )

    return totp.verify(otp)
