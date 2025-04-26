from django.conf import settings

def logo_url(request):
    return {
        'LOGO_URL': settings.LOGO_URL
    }
