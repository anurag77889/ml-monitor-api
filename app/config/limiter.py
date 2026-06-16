from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

default_limits = [] if settings.testing else ["100/minute"]
limiter = Limiter(key_func=get_remote_address, default_limits=default_limits)
