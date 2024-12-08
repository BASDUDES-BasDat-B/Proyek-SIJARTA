from django.urls import path
from . import views

urlpatterns = [
    path('discount/', views.discount_view, name='discount'),
    path('purchase_voucher/', views.purchase_voucher, name='purchase_voucher'),
]
