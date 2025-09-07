import hmac, hashlib, base64
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

# def encode_chat_id(chat_id: str) -> str:
#     secret = settings.SECRET_KEY.encode()
#     sig = hmac.new(secret, chat_id.encode(), hashlib.sha256).digest()
#     logger.info(f"encode_chat_id: chat_id={chat_id}, sig={base64.urlsafe_b64encode(sig).decode()}")
#     return base64.urlsafe_b64encode(chat_id.encode() + b"." + sig).decode()

# def decode_chat_id(token: str) -> str | None:
#     try:
#         raw = base64.urlsafe_b64decode(token.encode()).split(b".", 1)
#         chat_id, sig = raw[0], raw[1]
#         expected_sig = hmac.new(settings.SECRET_KEY.encode(), chat_id, hashlib.sha256).digest()
#         logger.info(f"decode_chat_id: token={token}, chat_id={chat_id.decode()}, sig={base64.urlsafe_b64encode(sig).decode()}, expected_sig={base64.urlsafe_b64encode(expected_sig).decode()}")
#         if hmac.compare_digest(sig, expected_sig):
#             return chat_id.decode()
#     except Exception:
#         return None
#     return None

def encode_chat_id(chat_id: str) -> str:
    secret = settings.SECRET_KEY.encode()
    sig = hmac.new(secret, chat_id.encode(), hashlib.sha256).digest()

    chat_b64 = base64.urlsafe_b64encode(chat_id.encode()).decode().rstrip("=")
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")

    return f"{chat_b64}.{sig_b64}"


def decode_chat_id(token: str) -> str | None:
    try:
        chat_b64, sig_b64 = token.split(".", 1)

        # fix padding for both
        chat_b64 += "=" * (-len(chat_b64) % 4)
        sig_b64 += "=" * (-len(sig_b64) % 4)

        chat_id = base64.urlsafe_b64decode(chat_b64.encode()).decode()
        sig = base64.urlsafe_b64decode(sig_b64.encode())

        expected_sig = hmac.new(settings.SECRET_KEY.encode(), chat_id.encode(), hashlib.sha256).digest()

        if hmac.compare_digest(sig, expected_sig):
            return chat_id
        return None
    except Exception as e:
        import logging
        logging.error(f"decode_chat_id failed: {e}")
        return None