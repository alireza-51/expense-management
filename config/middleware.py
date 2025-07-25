from django.utils.translation import activate, get_language
from django.conf import settings


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