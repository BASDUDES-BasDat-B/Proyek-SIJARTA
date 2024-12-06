from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from utils.db_connection import get_db_connection
from django.conf import settings
from django.contrib.auth.decorators import login_required
import uuid
from datetime import datetime, timedelta


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
    kategori_list = []
    subkategori_list = []
    pesanan_list = []

    kategori_list = execute_query("SELECT id, namakategori FROM kategori_jasa")
    kategori_id = request.GET.get("kategori")
    subkategori_id = request.GET.get("subkategori")

    if kategori_id:
        subkategori_list = execute_query(
            """
            SELECT id, namasubkategori, kategorijasaid 
            FROM subkategori_jasa 
            WHERE kategorijasaid = %s
            """,
            [kategori_id]
            )
        
        pesanan_list = execute_query(
            """
            SELECT 
                t.id, 
                s.namasubkategori, 
                u.name AS nama_pelanggan, 
                t.tglpemesanan, 
                t.sesi, 
                t.totalbiaya, 
                st.status
            FROM tr_pemesanan_jasa t
            JOIN subkategori_jasa s ON t.idkategorijasa = s.kategorijasaid
            JOIN pelanggan p ON t.idpelanggan = p.id
            JOIN "USER" u ON p.id = u.id
            JOIN tr_pemesanan_status ts ON ts.idtrpemesanan = t.id
            JOIN status_pemesanan st ON ts.idstatus = st.id
            WHERE st.status = 'Mencari Pekerja Terdekat' 
                AND s.kategorijasaid = %s
            """, [kategori_id]
        )

    else: 
        subkategori_list = execute_query("SELECT id, namasubkategori, kategorijasaid FROM subkategori_jasa")

        # Ambil semua pesanan dengan status "Mencari Pekerja Terdekat"
        pesanan_list = execute_query("""
            SELECT 
                t.id, 
                s.namasubkategori, 
                u.name AS nama_pelanggan, 
                t.tglpemesanan, 
                t.sesi, 
                t.totalbiaya, 
                st.status
            FROM tr_pemesanan_jasa t
            JOIN subkategori_jasa s ON t.idkategorijasa = s.kategorijasaid
            JOIN pelanggan p ON t.idpelanggan = p.id
            JOIN "USER" u ON p.id = u.id
            JOIN tr_pemesanan_status ts ON ts.idtrpemesanan = t.id
            JOIN status_pemesanan st ON ts.idstatus = st.id
            WHERE st.status = 'Mencari Pekerja Terdekat'
        """)

    context = {
        "kategori_list": kategori_list,
        "subkategori_list": subkategori_list,
        "pesanan_list": pesanan_list,
        "selected_kategori": kategori_id,
        "selected_subkategori": subkategori_id,
    }
    return render(request, "pekerjaan_jasa.html", context)

def kerjakan_pesanan(request, pesanan_id):
    if request.method == "POST":
        pekerja_id = "f02cceac-7781-4652-9780-cacf74680211"
        tgl_pekerjaan = datetime.now().date()

        # Ambil sesi untuk pesanan ini
        sesi_result = execute_query("""
            SELECT sesi 
            FROM tr_pemesanan_jasa 
            WHERE id = %s
        """, [pesanan_id])

        if not sesi_result:
            messages.error(request, "Pesanan tidak ditemukan.")
            return redirect('pekerjaan_jasa')

        sesi = sesi_result[0][0] 

        # Hitung waktu_pekerjaan sebagai tgl_pekerjaan + sesi (1 sesi = 1 hari)
        waktu_pekerjaan = datetime.combine(tgl_pekerjaan, datetime.min.time()) + timedelta(days=sesi)

        # Update tr_pemesanan_jasa
        execute_query("""
            UPDATE tr_pemesanan_jasa
            SET tglpekerjaan = %s, idpekerja = %s, waktupekerjaan = %s
            WHERE id = %s
        """, [tgl_pekerjaan, pekerja_id, waktu_pekerjaan, pesanan_id])

        # Ambil id status "Menunggu Pekerja Terdekat"
        status_result = execute_query("""
            SELECT id FROM status_pemesanan WHERE status = 'Menunggu Pekerja Terdekat'
        """)

        if not status_result:
            messages.error(request, "Status 'Menunggu Pekerja Terdekat' tidak ditemukan.")
            return redirect('pekerjaan_jasa')

        status_id = status_result[0][0]

        # Insert row baru ke tr_pemesanan_status
        execute_query("""
            INSERT INTO tr_pemesanan_status (idtrpemesanan, idstatus, tglwaktu)
            VALUES (%s, %s, %s)
        """, [pesanan_id, status_id, datetime.now()])

        messages.success(request, "Pesanan berhasil diambil dan status diperbarui.")
        return redirect('pekerjaan_jasa')
    else:
        messages.error(request, "Metode permintaan tidak diizinkan.")
        return redirect('pekerjaan_jasa')
    
def get_latest_status(pesanan_id):
    status_query = """
        SELECT sp.status
        FROM tr_pemesanan_status tps
        JOIN status_pemesanan sp ON tps.idstatus = sp.id
        WHERE tps.idtrpemesanan = %s
        ORDER BY tps.tglwaktu DESC
        LIMIT 1
    """
    result = execute_query(status_query, [pesanan_id])
    return result[0][0] if result else None


def status_pekerjaan_jasa(request):
    user_id = "f02cceac-7781-4652-9780-cacf74680211"  # Ganti dengan request.user.id jika sudah implementasi autentikasi
    
    # Ambil filter dari GET request
    nama_jasa = request.GET.get("nama_jasa", "").strip()
    status_filter = request.GET.get("status", "").strip()
    
    # Query untuk mengambil pesanan jasa pekerja saat ini
    pesanan_query = """
        SELECT 
            pj.id, 
            sj.namasubkategori, 
            u.name AS nama_pelanggan, 
            pj.tglpemesanan, 
            pj.tglpekerjaan, 
            pj.totalbiaya,
            sp.status
        FROM tr_pemesanan_jasa pj
        JOIN subkategori_jasa sj ON pj.idkategorijasa = sj.id
        JOIN pelanggan p ON pj.idpelanggan = p.id
        JOIN "USER" u ON p.id = u.id
        JOIN tr_pemesanan_status tps ON tps.idtrpemesanan = pj.id
        JOIN status_pemesanan sp ON tps.idstatus = sp.id
        WHERE pj.idpekerja = %s
          AND tps.tglwaktu = (
              SELECT MAX(tps_inner.tglwaktu)
              FROM tr_pemesanan_status tps_inner
              WHERE tps_inner.idtrpemesanan = pj.id
          )
    """
    
    params = [user_id]
    
    # Tambahkan filter nama_jasa jika ada
    if nama_jasa:
        pesanan_query += " AND LOWER(sj.namasubkategori) LIKE %s"
        params.append(f"%{nama_jasa.lower()}%")
    
    # Tambahkan filter status jika ada
    if status_filter:
        pesanan_query += " AND sp.status = %s"
        params.append(status_filter)
    
    pesanan_query += " ORDER BY pj.tglpemesanan DESC"
    
    pesanan_result = execute_query(pesanan_query, params)
    
    # Siapkan data pesanan
    pesanan_list = []
    for pesanan in pesanan_result:
        pesanan_id = pesanan[0]
        latest_status = pesanan[6]
        pesanan_list.append({
            "id": pesanan_id,
            "subkategori": pesanan[1],
            "nama_pelanggan": pesanan[2],
            "tanggal_pemesanan": pesanan[3],
            "tanggal_pekerjaan": pesanan[4],
            "total_biaya": int(pesanan[5]),
            "status": latest_status,
        })
    
    # Daftar pilihan status
    status_choices = [
        ("Menunggu Pekerja Berangkat", "Menunggu Pekerja Berangkat"),
        ("Pekerja Tiba Di Lokasi", "Pekerja Tiba Di Lokasi"),
        ("Pelayanan Jasa Sedang Dilakukan", "Pelayanan Jasa Sedang Dilakukan"),
        ("Pesanan Selesai", "Pesanan Selesai"),
        ("Pesanan Dibatalkan", "Pesanan Dibatalkan"),
    ]
    
    context = {
        "pesanan_list": pesanan_list,
        "status_choices": status_choices,
    }
    return render(request, "status_pekerjaan_jasa.html", context)

def ubah_status_pesanan(request, pesanan_id, status_baru):
    if request.method != "GET":
        messages.error(request, "Metode permintaan tidak diizinkan.")
        return redirect('status_pekerjaan_jasa')
    
    user_id = "f02cceac-7781-4652-9780-cacf74680211"  # Ganti dengan request.user.id jika sudah implementasi autentikasi
    
    # Cek apakah pesanan memang dimiliki oleh pekerja ini
    cek_pesanan_query = """
        SELECT pj.id
        FROM tr_pemesanan_jasa pj
        WHERE pj.id = %s AND pj.idpekerja = %s
    """
    cek_pesanan = execute_query(cek_pesanan_query, [pesanan_id, user_id])
    
    if not cek_pesanan:
        messages.error(request, "Pesanan tidak ditemukan atau Anda tidak berwenang untuk mengubahnya.")
        return redirect('status_pekerjaan_jasa')
    
    # Ambil status saat ini
    current_status_query = """
        SELECT sp.status
        FROM tr_pemesanan_status tps
        JOIN status_pemesanan sp ON tps.idstatus = sp.id
        WHERE tps.idtrpemesanan = %s
        ORDER BY tps.tglwaktu DESC
        LIMIT 1
    """
    current_status_result = execute_query(current_status_query, [pesanan_id])
    current_status = current_status_result[0][0] if current_status_result else None
    
    # Tentukan status yang valid untuk diubah
    status_transitions = {
        "Mencari Pekerja Terdekat": "Pekerja Menuju Lokasi",
        "Pekerja Menuju Lokasi": "Pekerja Mulai Pekerjaan",
        "Pekerja Mulai Pekerjaan": "Pemesanan Selesai",
    }
    
    # Verifikasi bahwa status_baru sesuai dengan transisi
    expected_status = status_transitions.get(current_status)
    if expected_status != status_baru:
        messages.error(request, "Perubahan status tidak valid.")
        return redirect('status_pekerjaan_jasa')
    
    # Ambil ID status_baru
    status_id_query = "SELECT id FROM status_pemesanan WHERE status = %s"
    status_id_result = execute_query(status_id_query, [status_baru])
    if not status_id_result:
        messages.error(request, "Status baru tidak ditemukan.")
        return redirect('status_pekerjaan_jasa')
    status_id_baru = status_id_result[0][0]
    
    # Insert status baru ke tr_pemesanan_status
    insert_status_query = """
        INSERT INTO tr_pemesanan_status (idtrpemesanan, idstatus, tglwaktu)
        VALUES (%s, %s, NOW())
    """
    execute_transaction(insert_status_query, [pesanan_id, status_id_baru])
    
    messages.success(request, f"Status pesanan berhasil diubah menjadi '{status_baru}'.")
    return redirect('status_pekerjaan_jasa')

