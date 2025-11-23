from django.utils.translation import activate, get_language
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class LanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get language from session
        language = request.session.get(settings.LANGUAGE_COOKIE_NAME)
        if language and language in [lang[0] for lang in settings.LANGUAGES]:
            # Activate the language from session
            activate(language)
            request.LANGUAGE_CODE = language
        
        response = self.get_response(request)
        return response


class JWTAuthenticationMiddleware:
    """
    Middleware to authenticate users from JWT tokens early in the request cycle.
    This allows other middleware (like WorkspaceMiddleware) to access authenticated users
    before DRF processes the authentication.
    
    Should be placed after AuthenticationMiddleware to complement session-based auth.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_authenticator = JWTAuthentication()

    def _authenticate_jwt(self, request):
        """
        Authenticate user from JWT token if present.
        
        Returns:
            User object if authentication successful, None otherwise
        """
        # Check if Authorization header exists
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        try:
            # Extract token and authenticate
            token = auth_header.split(' ')[1]
            validated_token = self.jwt_authenticator.get_validated_token(token)
            user = self.jwt_authenticator.get_user(validated_token)
            return user
        except (InvalidToken, TokenError, IndexError, ValueError):
            # Token is invalid, malformed, or expired
            return None

    def __call__(self, request):
        # Only authenticate if user is not already authenticated (session-based auth takes precedence)
        if not request.user.is_authenticated:
            jwt_user = self._authenticate_jwt(request)
            if jwt_user:
                request.user = jwt_user
        
        response = self.get_response(request)
        return response


class CSRFExemptAPIMiddleware(CsrfViewMiddleware):
    """
    Custom CSRF middleware that exempts API routes from CSRF checks.
    API routes use JWT authentication which is stateless and doesn't require CSRF protection.
    """
    def process_request(self, request):
        # Exempt all API routes from CSRF checks
        if request.path.startswith('/api/'):
            # Set a flag to skip CSRF validation
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Exempt all API routes from CSRF checks
        if request.path.startswith('/api/'):
            # Set the flag again to ensure it's set
            setattr(request, '_dont_enforce_csrf_checks', True)
            return None  # Skip CSRF check for API routes
        # For non-API routes, use the default CSRF behavior
        return super().process_view(request, callback, callback_args, callback_kwargs)
    
    def _reject(self, request, reason):
        # Don't reject API routes
        if request.path.startswith('/api/'):
            return None
        return super()._reject(request, reason)