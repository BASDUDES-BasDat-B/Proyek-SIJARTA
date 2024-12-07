# hijau/urls.py
from django.urls import path
from . import views

urlpatterns = [
     path('homepage/', views.homepage, name='homepage'),
     path('kategori/<str:category_slug>/<str:subcategory_slug>/', views.subcategory_jasa, name='subcategory_jasa'),
     path('pesanan/', views.view_pesanan, name='view_pesanan'),
     path('pesanan/buat/', views.create_order, name='create_order'),
     path('api/calculate-total/', views.calculate_total, name='calculate_total'),
     path('api/join-service/<str:subcategory_slug>/', views.join_service, name='join_service'),
     path('api/buat-testimoni/', views.create_testimonial, name='create_testimonial'),
     path('api/batalkan-pesanan/<uuid:order_id>/', views.cancel_order, name='cancel_order'),
]
