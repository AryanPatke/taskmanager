from django.contrib import admin
from django.urls import path, include
from accounts import routing
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
]