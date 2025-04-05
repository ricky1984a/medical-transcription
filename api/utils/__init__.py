"""
Utils package initialization
"""
# Import flask_limiter components
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    # Provide stubs if flask_limiter is not available
    class Limiter:
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator

        def init_app(self, app):
            pass


    def get_remote_address():
        return '127.0.0.1'

# Export only what's needed
__all__ = ['Limiter', 'get_remote_address']