# Celery is optional until Phase 4 (async workers).
try:
    from .celery import app as celery_app

    __all__ = ("celery_app",)
except ImportError:  # pragma: no cover
    celery_app = None
    __all__ = ()
