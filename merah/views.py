from django.shortcuts import render
from utils.db_connection import get_db_connection
from django.conf import settings
from django.contrib.auth.decorators import login_required


def execute_query(sql_query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, params or [])
            return cursor.fetchall()
        

@login_required(login_url='/login/')
def transaksi_list(request):
    user_id = request.user.id  # Get the currently logged-in user's ID
    
    # Query to fetch saldo_mypay (balance)
    saldo_query = "SELECT saldomypay FROM \"USER\" WHERE id = %s"
    saldo_result = execute_query(saldo_query, (user_id,))
    saldo_mypay = saldo_result[0][0] if saldo_result else 0

    # Query to fetch transaction history
    transactions_query = """
        SELECT t.nominal, t.tgl, k.nama as kategori
        FROM tr_mypay t
        JOIN kategori_tr_mypay k ON t.kategoriid = k.id
        WHERE t.userid = %s
        ORDER BY t.tgl DESC
    """
    transactions_result = execute_query(transactions_query, (user_id,))

    # Prepare the transaction data
    transactions_data = [
        {
            'nominal': trans[0],
            'tanggal': trans[1],
            'kategori': trans[2],
        }
        for trans in transactions_result
    ]

    # Prepare the context for the template
    context = {
        'saldo_mypay': saldo_mypay,
        'transactions': transactions_data,
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

