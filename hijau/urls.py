from django.urls import path
from .views import homepage, subcategory_detail, view_pesanan, create_order, calculate_total, create_testimonial, cancel_order

urlpatterns = [
    path('homepage/', homepage, name='homepage'),
    path('kategori/<str:category_slug>/<str:subcategory_slug>/', 
         subcategory_detail, 
         name='subcategory_detail'),
    path('pesanan/', view_pesanan, name='view_pesanan'),
    path('pesanan/buat/', create_order, name='create_order'),
    path('api/hitung-total/', calculate_total, name='calculate_total'),
    path('api/buat-testimoni/', create_testimonial, name='create_testimonial'),
    path('api/batalkan-pesanan/<int:order_id>/', 
         cancel_order, 
         name='cancel_order'),
]