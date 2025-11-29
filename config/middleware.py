from django.utils.translation import activate, get_language
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class LanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = None
        valid_languages = [lang[0] for lang in settings.LANGUAGES]
        
        # For API requests, check query parameter or header first
        if request.path.startswith('/api/'):
            # Check query parameter 'lang' or 'language'
            language = request.GET.get('lang') or request.GET.get('language')
            # If not in query params, check Accept-Language header
            if not language:
                accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
                if accept_language:
                    # Parse Accept-Language header (e.g., "fa-IR,fa;q=0.9,en;q=0.8")
                    # Extract first language code
                    lang_code = accept_language.split(',')[0].split(';')[0].strip().lower()
                    # Check if it's a valid language (e.g., 'fa' from 'fa-ir')
                    if lang_code in valid_languages:
                        language = lang_code
                    elif lang_code.startswith('fa'):
                        language = 'fa'
                    elif lang_code.startswith('en'):
                        language = 'en'
        
        # Fall back to session if no language found in API params/headers
        if not language:
            # Django's default language cookie name is 'django_language'
            language_cookie_name = getattr(settings, 'LANGUAGE_COOKIE_NAME', 'django_language')
            language = request.session.get(language_cookie_name)
        
        # Activate language if valid
        if language and language in valid_languages:
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
        # Only process JWT authentication for API routes
        # For non-API routes, skip JWT authentication entirely (use session only)
        if request.path.startswith('/api/'):
            # For API routes, JWT token takes precedence over session authentication
            # This allows API clients to authenticate as different users even if session exists
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