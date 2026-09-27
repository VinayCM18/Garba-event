import qrcode
import io
import base64
from app.utils.security import generate_secure_token, hash_qr_token

class QRService:
    @staticmethod
    def generate_token_pair() -> tuple[str, str]:
        """Returns (raw_secret_token, sha256_hash)."""
        raw_token = generate_secure_token(prefix="GN26")
        token_hash = hash_qr_token(raw_token)
        return raw_token, token_hash

    @staticmethod
    def generate_qr_base64(data_payload: str) -> str:
        """Generate high-contrast QR code image as base64 string."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(data_payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0f0c20", back_color="#ffffff")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"

    @staticmethod
    def generate_qr_bytes(data_payload: str) -> bytes:
        """Generate QR code image bytes for PDF or email attachments."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(data_payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0f0c20", back_color="#ffffff")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return buffered.getvalue()

qr_service = QRService()
