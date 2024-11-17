from django.db import models

class Voucher(models.Model):
    kode = models.CharField(max_length=50, unique=True)  # Voucher code, should be unique
    potongan = models.DecimalField(max_digits=10, decimal_places=2)  # Discount amount (e.g., in currency)
    minimum_transaksi = models.PositiveIntegerField()   # Minimum transaction required to apply the voucher
    jumlah_kuota_penggunaan = models.PositiveIntegerField()  # Total available usage quota for the voucher
    hari_berlaku = models.PositiveIntegerField()  # Expiration date for the voucher
    harga_voucher = models.PositiveIntegerField()  # Price for the voucher itself, if applicable


class Promo(models.Model):
    kode = models.CharField(max_length=50, unique=True)  # Unique code for the promo
    potongan = models.DecimalField(max_digits=10, decimal_places=2)  # Discount amount (e.g., in currency)
    minimum_transaksi =models.PositiveIntegerField()   # Minimum transaction amount to apply the promo
    tanggal_akhir_berlaku = models.DateField()  # End date for the promo validity


