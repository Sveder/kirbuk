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
from kirbuk.views import hello_world, submit_form

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('', hello_world, name='hello_world'),
    path('submit', submit_form, name='submit_form'),
    path('sentry-debug/', trigger_error),
]
