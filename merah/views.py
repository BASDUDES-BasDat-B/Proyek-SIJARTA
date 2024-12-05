from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from utils.db_connection import get_db_connection
from django.conf import settings
from django.contrib.auth.decorators import login_required
import uuid
from datetime import datetime


def execute_query(sql_query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, params or [])
            return cursor.fetchall()
        

#@login_required(login_url='/login/')
def transaksi_list(request):
    # user_id = request.user.id  # Get the currently logged-in user's ID

    user_id = "f02cceac-7781-4652-9780-cacf74680211"
    
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

def check_user_type(user_id):
    pekerja_query = "SELECT id FROM pekerja WHERE id = %s"
    result = execute_query(pekerja_query, [user_id])
    return 'pekerja' if result else 'pelanggan'

# Method helper untuk transaksi (commit query)
def execute_transaction(sql_query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, params or [])
            conn.commit()


def transaksi_form(request):
    # Assuming you get the user ID from the logged-in user
    user_id = "f02cceac-7781-4652-9780-cacf74680211"
    user_type = check_user_type(user_id)

    # Mendapatkan daftar pesanan jasa untuk dropdown State 2 jika user adalah pelanggan
    jasa_list = []
    if user_type == 'pelanggan':
        jasa_query = """
            SELECT 
                pj.id, 
                sj.namasubkategori, 
                sl.harga, 
                d.potongan
            FROM 
                tr_pemesanan_jasa pj
            JOIN 
                tr_pemesanan_status pjs ON pj.id = pjs.idtrpemesanan
            JOIN 
                status_pemesanan sp ON pjs.idstatus = sp.id
            JOIN 
                metode_bayar mb ON pj.idmetodebayar = mb.id
            JOIN 
                sesi_layanan sl ON pj.idkategorijasa = sl.subkategoriid
            JOIN 
                subkategori_jasa sj ON sl.subkategoriid = sj.id
            JOIN 
                diskon d ON pj.iddiskon = d.kode
            WHERE 
                pj.idpelanggan = %s AND
                sp.status = 'Menunggu Pembayaran' AND
                mb.nama = 'MyPay'
            GROUP BY 
                pj.id, sj.namasubkategori, sl.harga, d.potongan
        """
        jasa_result = execute_query(jasa_query, [user_id])
        # Menghitung harga setelah diskon
        for row in jasa_result:
            jasa_id = row[0]
            nama_jasa = row[1]
            harga = row[2]
            potongan = row[3]
            harga_setelah_diskon = harga * (1 - potongan)
            jasa_list.append({
                'id': jasa_id,
                'nama': nama_jasa,
                'harga_setelah_diskon': int(harga_setelah_diskon)  # Ubah sesuai kebutuhan format
            })

    bank_list = ['BCA', 'BNI', 'BRI', 'Mandiri']

    if request.method == 'POST':
        kategori = request.POST.get('kategori')
        nominal = request.POST.get('nominal')

        kategori_id = execute_query(
            "SELECT id FROM kategori_tr_mypay WHERE nama = %s", 
            [kategori]
        )[0][0]

        # Mendapatkan waktu transaksi
        tgl_transaksi = datetime.now()

        if kategori == "TopUp MyPay":
            execute_transaction(
                "UPDATE \"USER\" SET saldomypay = saldomypay + %s WHERE id = %s",
                [nominal, user_id]
            )
            tr_mypay_id = str(uuid.uuid4())
            execute_transaction(
                """
                INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [tr_mypay_id, user_id, tgl_transaksi, nominal, kategori_id]
            )

            # Tambahkan pesan sukses
            messages.success(request, 'Top Up MyPay berhasil dilakukan.')

        elif kategori == "Bayar Jasa" and user_type == 'pelanggan':
            jasa_id = request.POST.get('jasa_id')

            # Mendapatkan total biaya dari tr_pemesanan_jasa
            biaya_query = "SELECT totalbiaya FROM tr_pemesanan_jasa WHERE id = %s"
            biaya_result = execute_query(biaya_query, [jasa_id])
            total_biaya = biaya_result[0][0] if biaya_result else 0

            # Memeriksa saldo MyPay
            saldo_query = "SELECT saldomypay FROM \"USER\" WHERE id = %s"
            saldo_result = execute_query(saldo_query, (user_id,))
            saldo_mypay = saldo_result[0][0] if saldo_result else 0

            if saldo_mypay >= total_biaya:
                # Kurangi saldo
                execute_transaction(
                    "UPDATE \"USER\" SET saldomypay = saldomypay - %s WHERE id = %s",
                    [total_biaya, user_id]
                )

                tr_mypay_id = str(uuid.uuid4())
                execute_transaction(
                    """
                    INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [tr_mypay_id, user_id, tgl_transaksi, total_biaya, kategori_id]
                )

                # Update status pemesanan menjadi "Mencari Pekerja Terdekat"
                # Mendapatkan id status "Mencari Pekerja Terdekat"
                status_query = "SELECT id FROM status_pemesanan WHERE status = 'Mencari Pekerja Terdekat'"
                status_result = execute_query(status_query)
                status_id = status_result[0][0] if status_result else None

                if status_id:
                    execute_transaction(
                        """
                        INSERT INTO tr_pemesanan_status (idtrpemesanan, idstatus, tglwaktu)
                        VALUES (%s, %s, NOW())
                        """,
                        [jasa_id, status_id]
                    )
                messages.success(request, 'Pembayaran Jasa berhasil dilakukan.')
            else:
                # Tambahkan pesan error: saldo tidak cukup
                context = {
                    'error': 'Saldo MyPay Anda tidak cukup untuk melakukan pembayaran ini.',
                    'jasa_list': jasa_list,
                    'bank_list': bank_list,
                }
                return render(request, 'transaksi_form.html', context)
            
        elif kategori == "Transfer MyPay":
            nohp = request.POST.get('nohp')
            nominal_transfer = request.POST.get('nominal-transfer')

            target_user = execute_query(
                "SELECT id FROM \"USER\" WHERE nohp = %s",
                [nohp]
            )
            if not target_user:
                return JsonResponse({'error': 'Nomor HP tidak ditemukan'}, status=400)
            
            target_user_id = target_user[0][0]
            
            execute_transaction(
                'UPDATE "USER" SET saldomypay = saldomypay - %s WHERE id = %s',
                [nominal, user_id]
            )
            execute_transaction(
                'UPDATE "USER" SET saldomypay = saldomypay + %s WHERE id = %s',
                [nominal, target_user_id]
            )

            # Insert ke tr_mypay untuk pengirim
            tr_mypay_id_sender = str(uuid.uuid4())
            execute_transaction(
                """
                INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [tr_mypay_id_sender, user_id, tgl_transaksi, -nominal_transfer, kategori_id]
            )
            # Insert ke tr_mypay untuk penerima
            tr_mypay_id_receiver = str(uuid.uuid4())
            execute_transaction(
                """
                INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [tr_mypay_id_receiver, target_user_id, tgl_transaksi, nominal_transfer, kategori_id]
            )
            # Tambahkan pesan sukses
            messages.success(request, 'Transfer MyPay berhasil dilakukan.')

        elif kategori == "Withdrawal":
            nominal_withdraw = request.POST.get('nominal-withdraw')
            execute_transaction(
                'UPDATE "USER" SET saldomypay = saldomypay - %s WHERE id = %s',
                [nominal, user_id]
            )

            # Insert ke tr_mypay
            tr_mypay_id = str(uuid.uuid4())
            execute_transaction(
                """
                INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [tr_mypay_id, user_id, tgl_transaksi, -nominal_withdraw, kategori_id]
            )
            # Tambahkan pesan sukses
            messages.success(request, 'Withdrawal berhasil dilakukan.')


    # Mendapatkan daftar kategori transaksi
    categories = [
        ('TopUp MyPay', 'TopUp MyPay'),
        ('Bayar Jasa', 'Bayar Jasa'),
        ('Transfer MyPay', 'Transfer MyPay'),
        ('Withdrawal', 'Withdrawal'),
    ]

    # Menyiapkan konteks untuk template
    context = {
        'categories': categories,
        'jasa_list': jasa_list,
        'bank_list': bank_list,
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

