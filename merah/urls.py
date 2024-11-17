from django.urls import path
from .views import transaksi_form, transaksi_list, pekerjaan_jasa, status_pekerjaan_jasa

urlpatterns = [
    path('transaksi-mypay/', transaksi_list, name='transaksi_list'),
    path('transaksi-form/', transaksi_form, name='transaksi_form'),
    path('pekerjaan-jasa/', pekerjaan_jasa, name='pekerjaan_jasa'),
    path('status-pekerjaan-jasa/', status_pekerjaan_jasa, name='status_pekerjaan_jasa'),
]

