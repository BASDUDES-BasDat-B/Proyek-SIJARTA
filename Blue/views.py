from django.shortcuts import render

from datetime import date

def discount_view(request):
    # Dummy data for vouchers
    vouchers = [
        {
            "kode": "VOUCHER10",
            "potongan": 10.00,
            "minimum_transaksi": 50.00,
            "jumlah_kuota_penggunaan": 100,
            "hari_berlaku": date(2024, 12, 31),
            "harga_voucher": 5.00
        },
        {
            "kode": "VOUCHER20",
            "potongan": 20.00,
            "minimum_transaksi": 100.00,
            "jumlah_kuota_penggunaan": 50,
            "hari_berlaku": date(2025, 1, 31),
            "harga_voucher": 10.00
        }
    ]

    # Dummy data for promos
    promos = [
        {
            "kode": "PROMO15",
            "potongan": 15.00,
            "minimum_transaksi": 75.00,
            "tanggal_akhir_berlaku": date(2024, 11, 30)
        },
        {
            "kode": "PROMO25",
            "potongan": 25.00,
            "minimum_transaksi": 150.00,
            "tanggal_akhir_berlaku": date(2024, 12, 31)
        }
    ]

    # Pass dummy data to the template
    return render(request, 'discount.html', {'vouchers': vouchers, 'promos': promos})

