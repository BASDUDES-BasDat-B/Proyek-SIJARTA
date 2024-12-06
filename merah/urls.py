from django.urls import path
from .views import transaksi_form, transaksi_list, pekerjaan_jasa, status_pekerjaan_jasa, kerjakan_pesanan, ubah_status_pesanan

urlpatterns = [
    path('transaksi-mypay/', transaksi_list, name='transaksi_list'),
    path('transaksi-form/', transaksi_form, name='transaksi_form'),
    path('pekerjaan-jasa/', pekerjaan_jasa, name='pekerjaan_jasa'),
    path('kerjakan_pesanan/<uuid:pesanan_id>/', kerjakan_pesanan, name='kerjakan_pesanan'),
    path('status-pekerjaan-jasa/', status_pekerjaan_jasa, name='status_pekerjaan_jasa'),
    path('ubah-status-pesanan/<uuid:pesanan_id>/<str:status_baru>/', ubah_status_pesanan, name='ubah_status_pesanan'),
]

