import hmac, hashlib, base64
from django.conf import settings

def encode_chat_id(chat_id: str) -> str:
    secret = settings.SECRET_KEY.encode()
    sig = hmac.new(secret, chat_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(chat_id.encode() + b"." + sig).decode()

def decode_chat_id(token: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).split(b".", 1)
        chat_id, sig = raw[0], raw[1]
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), chat_id, hashlib.sha256).digest()
        if hmac.compare_digest(sig, expected_sig):
            return chat_id.decode()
    except Exception:
        return None
    return None