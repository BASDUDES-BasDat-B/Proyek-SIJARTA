from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from utils.db_connection import get_db_connection
from django.conf import settings
from django.contrib.auth.decorators import login_required
import uuid
from datetime import datetime, timedelta
import logging
from utils.decorators import custom_login_required

logger = logging.getLogger(__name__)

def execute_query(sql_query, params=None):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, params or [])
            return cursor.fetchall()
        

@custom_login_required
def transaksi_list(request):
    user_id = request.session['user']['Id']  # Get the currently logged-in user's ID

    # user_id = "f02cceac-7781-4652-9780-cacf74680211"
    
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
# def execute_transaction(sql_query, params=None):
#     with get_db_connection() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(sql_query, params or [])
#             conn.commit()

def execute_transaction(sql_query, params=None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                print(f"Executing query: {sql_query}")  # Debug print
                print(f"With parameters: {params}")     # Debug print
                cursor.execute(sql_query, params or [])
                conn.commit()
                print("Transaction committed successfully") # Debug print
                return True
    except Exception as e:
        print(f"Error in execute_transaction: {str(e)}")  # Debug print
        return False

def transaksi_form(request):
    # Assuming you get the user ID from the logged-in user
    user_id = request.session['user']['Id']
    #logging.info(f"User ID: {user_id}")  # Debug print
    user_type = check_user_type(user_id)

    # Mendapatkan daftar pesanan jasa untuk dropdown State 2 jika user adalah pelanggan
    jasa_list = []
    if user_type == 'pelanggan':
        jasa_query = """
                SELECT DISTINCT pj.id, 
            sj.namasubkategori,
            pj.totalbiaya,
            COALESCE(d.potongan, 0) AS potongan
        FROM tr_pemesanan_jasa pj
        JOIN tr_pemesanan_status pjs ON pj.id = pjs.idtrpemesanan
        JOIN status_pemesanan sp ON pjs.idstatus = sp.id
        JOIN metode_bayar mb ON pj.idmetodebayar = mb.id
        JOIN subkategori_jasa sj ON pj.idkategorijasa = sj.id
        LEFT JOIN diskon d ON pj.iddiskon = d.kode
        WHERE pj.idpelanggan = %s 
        AND pjs.idstatus = (
            SELECT ps2.idstatus 
            FROM tr_pemesanan_status ps2
            WHERE ps2.idtrpemesanan = pj.id
            ORDER BY ps2.tglwaktu DESC 
            LIMIT 1
        )
        AND sp.status = 'Menunggu Pembayaran'
        AND mb.nama = 'MyPay'
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

        if kategori == "Top Up":
            try:
                nominal_amount = float(nominal) 
                print(f"User ID: {user_id}")              # Debug print
                print(f"Nominal amount: {nominal_amount}") # Debug print
                execute_transaction(
                    "UPDATE \"USER\" SET saldomypay = saldomypay + %s WHERE id = %s",
                    [nominal_amount, user_id]
                )
                tr_mypay_id = str(uuid.uuid4())
                execute_transaction(
                    """
                    INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [tr_mypay_id, user_id, tgl_transaksi, nominal_amount, kategori_id]
                )
                messages.success(request, 'Top Up MyPay berhasil dilakukan.')
            except ValueError:
                messages.error(request, 'Nominal tidak valid.')

        elif kategori == "Pembayaran Jasa" and user_type == 'pelanggan':
            jasa_id = request.POST.get('jasa_id')
            logger.debug(f"Jasa ID: {jasa_id}")

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

                # Dapatkan status terakhir pesanan ini
                current_status_query = """
                    SELECT sp.id, sp.status
                    FROM tr_pemesanan_status tps
                    JOIN status_pemesanan sp ON tps.idstatus = sp.id
                    WHERE tps.idtrpemesanan = %s
                    ORDER BY tps.tglwaktu DESC
                    LIMIT 1
                """
                current_status = execute_query(current_status_query, [jasa_id])
                logger.debug(f"Current status: {current_status}")
                
                if current_status and current_status[0][1] == 'Menunggu Pembayaran':
                    # Insert status baru
                    execute_transaction(
                        """
                        INSERT INTO tr_pemesanan_status (idtrpemesanan, idstatus, tglwaktu)
                        VALUES (%s, %s, %s)
                        """,
                        [jasa_id, '2075e2c6-fe5f-4f26-8984-9616e9683617', datetime.now()]  # ID untuk 'Mencari Pekerja Terdekat'
                    )
                    messages.success(request, 'Pembayaran Jasa berhasil dilakukan.')
                else:
                    logger.error(f"Status pesanan tidak sesuai: {current_status}")
                    logger.error(f"ID pesanan: {jasa_id}")
                    messages.error(request, 'Terjadi kesalahan dalam memproses status pesanan.')
            else:
                # Tambahkan pesan error: saldo tidak cukup
                context = {
                    'error': 'Saldo MyPay Anda tidak cukup untuk melakukan pembayaran ini.',
                    'jasa_list': jasa_list,
                    'bank_list': bank_list,
                }
                return render(request, 'transaksi_form.html', context)
            
        elif kategori == "Transfer":
            nohp = request.POST.get('nohp')
            nominal_transfer = request.POST.get('nominal-transfer')
            nominal_transfer = float(nominal_transfer)

            target_user = execute_query(
                "SELECT id FROM \"USER\" WHERE nohp = %s",
                [nohp]
            )
            if not target_user:
                return JsonResponse({'error': 'Nomor HP tidak ditemukan'}, status=400)
            
            target_user_id = target_user[0][0]
            
            execute_transaction(
                'UPDATE "USER" SET saldomypay = saldomypay - %s WHERE id = %s',
                [nominal_transfer, user_id]
            )
            execute_transaction(
                'UPDATE "USER" SET saldomypay = saldomypay + %s WHERE id = %s',
                [nominal_transfer, target_user_id]
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

        elif kategori == "Withdraw":
            nominal_withdraw = request.POST.get('nominal-withdraw')
            nominal_withdraw = float(nominal_withdraw)
            execute_transaction(
                'UPDATE "USER" SET saldomypay = saldomypay - %s WHERE id = %s',
                [nominal_withdraw, user_id]
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


    # In the transaksi_form view
    categories = [
        ('Top Up', 'Top Up'),
        ('Pembayaran Jasa', 'Pembayaran Jasa'),
        ('Transfer', 'Transfer'),
        ('Withdraw', 'Withdraw'),
    ]

    # Menyiapkan konteks untuk template
    context = {
        'categories': categories,
        'jasa_list': jasa_list,
        'bank_list': bank_list,
    }
    return render(request, 'transaksi_form.html', context)

def pekerjaan_jasa(request):
    try:
        kategori_list = execute_query("SELECT id, namakategori FROM kategori_jasa")
    except Exception as e:
        logging.error(f"Error fetching kategori_jasa: {e}")
        kategori_list = []

    kategori_id = request.GET.get("kategori")
    logging.info(f"Kategori ID: {kategori_id}")
    subkategori_id = request.GET.get("subkategori")
    logging.debug(f"Subkategori ID: {subkategori_id}")

    # Prepare the basic query for fetching pesanan_list
    base_query = """
        SELECT 
            t.id, 
            s.namasubkategori, 
            u.nama AS nama_pelanggan, 
            t.tglpemesanan, 
            t.sesi, 
            t.totalbiaya, 
            sp.status
        FROM tr_pemesanan_jasa t
        JOIN subkategori_jasa s ON t.idkategorijasa = s.id
        JOIN pelanggan p ON t.idpelanggan = p.id
        JOIN "USER" u ON p.id = u.id
        JOIN tr_pemesanan_status ts ON ts.idtrpemesanan = t.id
        JOIN status_pemesanan sp ON ts.idstatus = sp.id
        WHERE ts.tglwaktu = (
            SELECT MAX(ts2.tglwaktu)
            FROM tr_pemesanan_status ts2
            WHERE ts2.idtrpemesanan = t.id
        )
        AND sp.status = 'Mencari Pekerja Terdekat'
    """

    # Initialize query parameters
    params = []

    # Check if kategori_id is provided
    if kategori_id:
        # Modify the query to filter by kategori_id
        base_query += " AND s.kategorijasaid = %s"
        params.append(kategori_id)

        # If subkategori_id is provided, add the subkategori filter
        if subkategori_id:
            base_query += " AND s.id = %s"
            params.append(subkategori_id)

        # Fetch subkategori_list based on kategori_id
        subkategori_list = execute_query(
            "SELECT id, namasubkategori, kategorijasaid FROM subkategori_jasa WHERE kategorijasaid = %s",
            [kategori_id]
        )
    else:
        # Fetch all subkategori_list if kategori_id is not provided
        subkategori_list = execute_query("SELECT id, namasubkategori, kategorijasaid FROM subkategori_jasa")

        # If subkategori_id is provided, add the subkategori filter
        if subkategori_id:
            base_query += " AND s.id = %s"
            params.append(subkategori_id)

    # Execute the final query to get pesanan_list
    pesanan_result = execute_query(base_query, params)
    # print("-----------------------")
    # print(pesanan_result)

    # Konversi list of tuples menjadi list of dicts
    pesanan_list = [
        {
            'id': pesanan[0],
            'subkategori': pesanan[1],
            'nama_pelanggan': pesanan[2],
            'tanggal_pemesanan': pesanan[3],
            'sesi': pesanan[4],
            'total_biaya': pesanan[5],
            'status': pesanan[6],
        }
        for pesanan in pesanan_result
    ]

    context = {
        "kategori_list": kategori_list,
        "subkategori_list": subkategori_list,
        "pesanan_list": pesanan_list,
        "selected_kategori": kategori_id,
        "selected_subkategori": subkategori_id,
    }

    return render(request, "pekerjaan_jasa.html", context)

def get_status_id(status_name):
    query = "SELECT id FROM status_pemesanan WHERE status = %s"
    result = execute_query(query, [status_name])
    return result[0][0] if result else None


def kerjakan_pesanan(request, pesanan_id):
    if request.method == "POST":
        try:
            logger.debug("Processing 'kerjakan_pesanan' for pesanan_id: %s", pesanan_id)
            pekerja_id = request.session['user']['Id']
            logger.debug("Pekerja ID: %s", pekerja_id)
            tgl_pekerjaan = datetime.now().date()

            # Pastikan ID sebagai string
            pesanan_id = str(pesanan_id)
            pekerja_id = str(pekerja_id)

            # Cek apakah pekerja memiliki kategori yang sesuai dengan pesanan
            kategori_check_query = """
                SELECT 1
                FROM tr_pemesanan_jasa tj
                JOIN subkategori_jasa sj ON tj.idkategorijasa = sj.id
                JOIN pekerja_kategori_jasa pk ON sj.kategorijasaid = pk.kategorijasaid
                WHERE tj.id = %s AND pk.pekerjaid = %s
            """
            kategori_match = execute_query(kategori_check_query, [pesanan_id, pekerja_id])
            logger.debug("Kategori match: %s", kategori_match)

            if not kategori_match:
                messages.error(request, "Anda tidak memiliki kategori yang sesuai untuk mengambil pesanan ini.")
                logger.warning("Kategori tidak cocok untuk pesanan_id: %s oleh pekerja_id: %s", pesanan_id, pekerja_id)
                return redirect('pekerjaan_jasa')

            # Ambil sesi untuk pesanan ini
            sesi_result = execute_query("""
                SELECT sesi 
                FROM tr_pemesanan_jasa 
                WHERE id = %s
            """, [pesanan_id])
            logger.debug("Sesi result: %s", sesi_result)

            if not sesi_result:
                messages.error(request, "Pesanan tidak ditemukan.")
                logger.warning("Pesanan_id: %s tidak ditemukan.", pesanan_id)
                return redirect('pekerjaan_jasa')

            sesi = sesi_result[0][0] 
            logger.debug("Sesi untuk pesanan_id %s: %s", pesanan_id, sesi)

            # Hitung waktu_pekerjaan sebagai tgl_pekerjaan + sesi (1 sesi = 1 hari)
            waktu_pekerjaan = datetime.combine(tgl_pekerjaan, datetime.min.time()) + timedelta(days=sesi)
            logger.debug("Waktu pekerjaan: %s", waktu_pekerjaan)

            # Update tr_pemesanan_jasa
            update_success = execute_transaction("""
                UPDATE tr_pemesanan_jasa
                SET tglpekerjaan = %s, 
                    idpekerja = %s, 
                    waktupekerjaan = %s
                WHERE id = %s
            """, [tgl_pekerjaan, pekerja_id, waktu_pekerjaan, pesanan_id])
            logger.debug("Update success: %s", update_success)

            if not update_success:
                messages.error(request, "Gagal mengupdate data pesanan. Pastikan pesanan masih dapat diproses.")
                logger.error("Update gagal untuk pesanan_id: %s", pesanan_id)
                return redirect('pekerjaan_jasa')

            # **Change Status to a New Value Here**
            new_status_name = "Menunggu Pekerja Terdekat"
            status_id = get_status_id(new_status_name)
            if not status_id:
                messages.error(request, f"Status '{new_status_name}' tidak ditemukan.")
                logger.error(f"Status '{new_status_name}' tidak ditemukan di database.")
                return redirect('pekerjaan_jasa')

            logger.debug("Using status_id: %s", status_id)

            # Insert status baru
            status_success = execute_transaction("""
                INSERT INTO tr_pemesanan_status (idtrpemesanan, idstatus, tglwaktu)
                VALUES (%s, %s, %s)
            """, [pesanan_id, status_id, datetime.now()])
            logger.debug("Status insert success: %s", status_success)

            if not status_success:
                messages.error(request, "Gagal mengupdate status pesanan.")
                logger.error("Status insert gagal untuk pesanan_id: %s", pesanan_id)
                return redirect('pekerjaan_jasa')

            messages.success(request, "Pesanan berhasil diambil dan status diperbarui.")
            logger.info("Pesanan_id: %s berhasil diproses oleh pekerja_id: %s", pesanan_id, pekerja_id)
            return redirect('pekerjaan_jasa')

        except Exception as e:
            logger.error(f"Error in kerjakan_pesanan: {str(e)}")
            messages.error(request, f"Terjadi kesalahan: {str(e)}")
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
    user_id = request.session['user']['Id']
    
    # Ambil filter dari GET request
    nama_jasa = request.GET.get("nama_jasa", "").strip()
    status_filter = request.GET.get("status", "").strip()
    
    # Query untuk mengambil pesanan jasa pekerja saat ini
    pesanan_query = """
        SELECT 
            pj.id, 
            sj.namasubkategori, 
            u.nama AS nama_pelanggan, 
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
              SELECT MAX(ts_inner.tglwaktu)
              FROM tr_pemesanan_status ts_inner
              WHERE ts_inner.idtrpemesanan = pj.id
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
        ("Menunggu Pekerja Terdekat", "Menunggu Pekerja Terdekat"),
        ("Pekerja Tiba di Lokasi", "Pekerja Tiba di Lokasi"),
        ("Pelayanan Jasa Sedang Dilakukan", "Pelayanan Jasa Sedang Dilakukan"),
        ("Pemesanan Selesai", "Pemesanan Selesai"),
        ("Pesanan Dibatalkan", "Pesanan Dibatalkan"),
    ]
    
    context = {
        "pesanan_list": pesanan_list,
        "status_choices": status_choices,
    }
    return render(request, "status_pekerjaan_jasa.html", context)


def ubah_status_pesanan(request, pesanan_id, status_baru):
    if request.method != "POST":
        logger.warning("Invalid request method for ubah_status_pesanan.")
        messages.error(request, "Metode permintaan tidak diizinkan.")
        return redirect('status_pekerjaan_jasa')
    
    user_id = request.session.get('user', {}).get('Id')
    if not user_id:
        logger.error("User not authenticated.")
        messages.error(request, "Anda harus login untuk mengubah status pesanan.")
        return redirect('login')
    
    pesanan_id_str = str(pesanan_id)
    
    # Cek apakah pesanan memang dimiliki oleh pekerja ini
    cek_pesanan_query = """
        SELECT pj.id
        FROM tr_pemesanan_jasa pj
        WHERE pj.id = %s AND pj.idpekerja = %s
    """
    cek_pesanan = execute_query(cek_pesanan_query, [pesanan_id_str, user_id])
    
    if not cek_pesanan:
        logger.warning(f"Pesanan_id {pesanan_id_str} tidak ditemukan atau bukan milik pekerja_id {user_id}.")
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
    current_status_result = execute_query(current_status_query, [pesanan_id_str])
    current_status = current_status_result[0][0].strip() if current_status_result else None
    
    logger.debug(f"Current status for pesanan_id {pesanan_id_str}: {current_status}")
    
    # Update status_transitions to reflect correct transitions
    status_transitions = {
        "Menunggu Pekerja Terdekat": "Pekerja Tiba di Lokasi",
        "Pekerja Tiba di Lokasi": "Pelayanan Jasa Sedang Dilakukan",
        "Pelayanan Jasa Sedang Dilakukan": "Pemesanan Selesai",
    }
    
    # Verifikasi bahwa status_baru sesuai dengan transisi
    expected_status = status_transitions.get(current_status)
    logger.debug(f"Expected status untuk {current_status}: {expected_status}")
    if expected_status != status_baru:
        logger.warning(f"Perubahan status tidak valid: {current_status} -> {status_baru}")
        messages.error(request, "Perubahan status tidak valid.")
        return redirect('status_pekerjaan_jasa')
    
    # Ambil ID status_baru
    status_id_query = "SELECT id FROM status_pemesanan WHERE status = %s"
    status_id_result = execute_query(status_id_query, [status_baru])
    if not status_id_result:
        logger.error(f"Status baru tidak ditemukan: {status_baru}")
        messages.error(request, "Status baru tidak ditemukan.")
        return redirect('status_pekerjaan_jasa')
    status_id_baru = status_id_result[0][0]
    
    logger.debug(f"Status ID baru untuk '{status_baru}': {status_id_baru}")
    
    # Insert status baru ke tr_pemesanan_status
    insert_status_query = """
        INSERT INTO tr_pemesanan_status (idtrpemesanan, idstatus, tglwaktu)
        VALUES (%s, %s, %s)
    """
    status_success = execute_transaction(insert_status_query, [pesanan_id_str, status_id_baru, datetime.now()])
    
    if not status_success:
        logger.error(f"Insert status baru gagal untuk pesanan_id: {pesanan_id_str}")
        messages.error(request, "Gagal mengupdate status pesanan.")
        return redirect('status_pekerjaan_jasa')
    
    logger.info(f"Status pesanan_id {pesanan_id_str} berhasil diubah menjadi '{status_baru}'.")
    messages.success(request, f"Status pesanan berhasil diubah menjadi '{status_baru}'.")
    return redirect('status_pekerjaan_jasa')
