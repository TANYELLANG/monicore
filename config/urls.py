from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('monicore-dashboard/', admin.site.urls),
    path('', include('api.urls_pages')),
]