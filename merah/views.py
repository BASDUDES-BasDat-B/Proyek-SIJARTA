from django.shortcuts import render

def transaksi_list(request):
    transactions = [
        {"nominal": "+500,000", "tanggal": "2024-11-01", "kategori": "TopUp MyPay"},
        {"nominal": "-100,000", "tanggal": "2024-11-02", "kategori": "Bayar Jasa"},
        {"nominal": "+200,000", "tanggal": "2024-11-03", "kategori": "TopUp MyPay"},
        {"nominal": "-300,000", "tanggal": "2024-11-04", "kategori": "Transfer MyPay"},
        {"nominal": "-150,000", "tanggal": "2024-11-05", "kategori": "Withdrawal"},
        {"nominal": "+100,000", "tanggal": "2024-11-06", "kategori": "TopUp MyPay"},
        {"nominal": "-50,000", "tanggal": "2024-11-07", "kategori": "Bayar Jasa"},
        {"nominal": "-75,000", "tanggal": "2024-11-08", "kategori": "Withdrawal"},
        {"nominal": "-125,000", "tanggal": "2024-11-09", "kategori": "Transfer MyPay"},
        {"nominal": "+500,000", "tanggal": "2024-11-10", "kategori": "TopUp MyPay"},
    ]

    context = {
        'transactions': transactions,
    }
    return render(request, 'transaksi_mypay.html', context)

def transaksi_form(request):
    kategori = request.GET.get('kategori', '')  
    jasa_list = ["Jasa Cleaning", "Jasa Design", "Jasa Programming"]  
    bank_list = ["Bank BCA", "Bank BRI", "Bank BNI"]  

    context = {
        "kategori": kategori,
        "jasa_list": jasa_list,
        "bank_list": bank_list,
    }
    return render(request, 'transaksi_form.html', context)

def pekerjaan_jasa(request):
    # Dummy Data
    kategori_list = [
        {"id": 1, "nama": "Home Cleaning"},
        {"id": 2, "nama": "Massage"},
    ]

    subkategori_list = [
        {"id": 1, "nama": "Setrika", "kategori_id": 1},
        {"id": 2, "nama": "Daily Cleaning", "kategori_id": 1},
        {"id": 3, "nama": "Pembersihan Dapur", "kategori_id": 1},
        {"id": 4, "nama": "Relaksasi", "kategori_id": 2},
    ]

    pesanan_list = [
        {
            "id": 1,
            "subkategori": "Setrika",
            "nama_pelanggan": "John Doe",
            "tanggal_pemesanan": "2024-11-18",
            "tanggal_pekerjaan": "2024-11-20",
            "total_biaya": 100000,
            "status": "Mencari Pekerja Terdekat",
        },
        {
            "id": 2,
            "subkategori": "Daily Cleaning",
            "nama_pelanggan": "Jane Smith",
            "tanggal_pemesanan": "2024-11-15",
            "tanggal_pekerjaan": "2024-11-19",
            "total_biaya": 200000,
            "status": "Mencari Pekerja Terdekat",
        },
        {
            "id": 3,
            "subkategori": "Relaksasi",
            "nama_pelanggan": "Alice Brown",
            "tanggal_pemesanan": "2024-11-16",
            "tanggal_pekerjaan": "2024-11-22",
            "total_biaya": 150000,
            "status": "Mencari Pekerja Terdekat",
        },
    ]

    # Filter kategori dan subkategori
    kategori_id = request.GET.get("kategori")
    if kategori_id:
        subkategori_list = [s for s in subkategori_list if str(s["kategori_id"]) == kategori_id]
    else:
        kategori_id = None

    context = {
        "kategori_list": kategori_list,
        "subkategori_list": subkategori_list,
        "pesanan_list": pesanan_list,
        "selected_kategori": kategori_id,
    }
    return render(request, "pekerjaan_jasa.html", context)

def status_pekerjaan_jasa(request):
    # Dummy Data
    pesanan_list = [
        {
            "id": 1,
            "subkategori": "Setrika",
            "nama_pelanggan": "John Doe",
            "tanggal_pemesanan": "2024-11-18",
            "tanggal_pekerjaan": "2024-11-20",
            "total_biaya": 100000,
            "status": "Menunggu Pekerja Berangkat",
        },
        {
            "id": 2,
            "subkategori": "Daily Cleaning",
            "nama_pelanggan": "Jane Smith",
            "tanggal_pemesanan": "2024-11-15",
            "tanggal_pekerjaan": "2024-11-19",
            "total_biaya": 200000,
            "status": "Pekerja Tiba Di Lokasi",
        },
        {
            "id": 3,
            "subkategori": "Relaksasi",
            "nama_pelanggan": "Alice Brown",
            "tanggal_pemesanan": "2024-11-16",
            "tanggal_pekerjaan": "2024-11-22",
            "total_biaya": 150000,
            "status": "Pelayanan Jasa Sedang Dilakukan",
        },
    ]

    status_choices = [
        ("Menunggu Pekerja Berangkat", "Menunggu Pekerja Berangkat"),
        ("Pekerja Tiba Di Lokasi", "Pekerja Tiba Di Lokasi"),
        ("Pelayanan Jasa Sedang Dilakukan", "Pelayanan Jasa Sedang Dilakukan"),
        ("Pesanan Selesai", "Pesanan Selesai"),
        ("Pesanan Dibatalkan", "Pesanan Dibatalkan"),
    ]

    # Filter berdasarkan nama jasa dan status
    nama_jasa = request.GET.get("nama_jasa", "")
    status_filter = request.GET.get("status", "")
    if nama_jasa:
        pesanan_list = [p for p in pesanan_list if nama_jasa.lower() in p["subkategori"].lower()]
    if status_filter:
        pesanan_list = [p for p in pesanan_list if p["status"] == status_filter]

    context = {
        "pesanan_list": pesanan_list,
        "status_choices": status_choices,
    }
    return render(request, "status_pekerjaan_jasa.html", context)

