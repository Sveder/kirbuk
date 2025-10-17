"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from kirbuk.views import hello_world, submit_form, submission_status, check_status

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('', hello_world, name='hello_world'),
    path('submit', submit_form, name='submit_form'),
    path('submission/<str:submission_id>', submission_status, name='submission_status'),
    path('api/status/<str:submission_id>', check_status, name='check_status'),
    path('sentry-debug/', trigger_error),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'kirbuk' / 'static')
