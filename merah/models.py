from django.db import models
from django.contrib.auth.models import User

class Transaksi(models.Model):
    nominal = models.CharField(max_length=100)
    tanggal = models.DateField()
    kategori = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nominal} - {self.tanggal} - {self.kategori}"

class KategoriJasa(models.Model):
    nama = models.CharField(max_length=100)

    def __str__(self):
        return self.nama

class SubkategoriJasa(models.Model):
    nama = models.CharField(max_length=100)
    kategori = models.ForeignKey(KategoriJasa, on_delete=models.CASCADE, related_name="subkategori")

    def __str__(self):
        return self.nama

class PesananJasa(models.Model):
    STATUS_CHOICES = [
        ("Mencari Pekerja Terdekat", "Mencari Pekerja Terdekat"),
        ("Menunggu Pekerja Berangkat", "Menunggu Pekerja Berangkat"),
        ("Pekerja Tiba Di Lokasi", "Pekerja Tiba Di Lokasi"),
        ("Pelayanan Jasa Sedang Dilakukan", "Pelayanan Jasa Sedang Dilakukan"),
        ("Pesanan Selesai", "Pesanan Selesai"),
        ("Pesanan Dibatalkan", "Pesanan Dibatalkan"),
    ]

    subkategori = models.ForeignKey(SubkategoriJasa, on_delete=models.CASCADE)
    nama_pelanggan = models.CharField(max_length=100)
    tanggal_pemesanan = models.DateTimeField()
    tanggal_pekerjaan = models.DateTimeField()
    total_biaya = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Mencari Pekerja Terdekat")
    pekerja = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pekerjaan")

    def __str__(self):
        return f"{self.subkategori.nama} - {self.nama_pelanggan} ({self.status})"