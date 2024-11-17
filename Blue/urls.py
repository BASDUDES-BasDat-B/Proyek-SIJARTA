from django.urls import path
from .views import discount_view

urlpatterns = [
    path('discount/', discount_view, name='discount'),
]
