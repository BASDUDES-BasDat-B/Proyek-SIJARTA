# hijau/views.py

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
import psycopg2
from utils.db_connection import get_db_connection
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils.text import slugify
import json
import uuid
from datetime import datetime
from utils.decorators import custom_login_required
from django.views.decorators.csrf import csrf_exempt

# Configure logger
logger = logging.getLogger(__name__)

def homepage(request):
    """
    View untuk menampilkan halaman utama dengan daftar kategori dan subkategori jasa.
    Mendukung filter berdasarkan kategori dan pencarian subkategori.
    """
    logger.debug("homepage view called.")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil semua kategori jasa
            cursor.execute("""
                SELECT Id, NamaKategori
                FROM KATEGORI_JASA
                ORDER BY NamaKategori;
            """)
            categories = cursor.fetchall()
            logger.debug(f"Fetched categories: {categories}")

            categories_data = []
            for category in categories:
                category_id, nama_kategori = category
                category_slug = slugify(nama_kategori)
                logger.debug(f"Processing category: {nama_kategori} with slug: {category_slug}")

                # Ambil subkategori untuk setiap kategori
                cursor.execute("""
                    SELECT Id, NamaSubKategori
                    FROM SUBKATEGORI_JASA
                    WHERE KategoriJasaId = %s
                    ORDER BY NamaSubKategori;
                """, (category_id,))
                subcategories = cursor.fetchall()
                logger.debug(f"Fetched subcategories for category_id {category_id}: {subcategories}")

                subcategories_data = []
                for subcategory in subcategories:
                    sub_id, nama_subkategori = subcategory
                    sub_slug = slugify(nama_subkategori)
                    logger.debug(f"Processing subcategory: {nama_subkategori} with slug: {sub_slug}")
                    subcategories_data.append({
                        'id': sub_id,
                        'nama_subkategori': nama_subkategori,
                        'slug': sub_slug,
                    })

                categories_data.append({
                    'id': category_id,
                    'nama_kategori': nama_kategori,
                    'slug': category_slug,
                    'subcategories': subcategories_data,
                    'icon': 'fas fa-concierge-bell',  # Ikon default atau sesuai kebutuhan
                })

            # Filter berdasarkan kategori dan pencarian
            selected_category = request.GET.get('category', '')
            search_query = request.GET.get('q', '')
            logger.debug(f"Selected category: {selected_category}, Search query: {search_query}")

            if selected_category:
                categories_data = [cat for cat in categories_data if cat['slug'] == selected_category]
                logger.debug(f"Filtered categories_data by selected_category: {selected_category}")

            if search_query:
                for category in categories_data:
                    original_count = len(category['subcategories'])
                    category['subcategories'] = [
                        sub for sub in category['subcategories']
                        if search_query.lower() in sub['nama_subkategori'].lower()
                    ]
                    filtered_count = len(category['subcategories'])
                    logger.debug(f"Filtered subcategories for category_id {category['id']} by search_query: {search_query} (from {original_count} to {filtered_count})")

        context = {'categories': categories_data}
        logger.debug("Rendering homepage.html dengan context.")
        return render(request, 'homepage.html', context)
    except Exception as e:
        logger.exception("Error fetching homepage data.")
        messages.error(request, f"Error fetching homepage data: {str(e)}")
        return render(request, 'homepage.html', {'categories': []})
    finally:
        conn.close()
        logger.debug("Database connection closed in homepage view.")

def subcategory_jasa(request, category_slug, subcategory_slug):
    """
    View untuk menampilkan detail subkategori jasa, sesi layanan, pekerja, dan testimoni.
    """
    logger.debug(f"subcategory_jasa view called with category_slug='{category_slug}', subcategory_slug='{subcategory_slug}'")
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil semua kategori jasa
            cursor.execute("""
                SELECT Id, NamaKategori
                FROM KATEGORI_JASA
            """)
            categories = cursor.fetchall()
            logger.debug(f"Fetched categories: {categories}")

            category = None
            for cat in categories:
                cat_id, nama_kategori = cat
                cat_slug = slugify(nama_kategori).lower()
                logger.debug(f"Checking category: {nama_kategori} with slug: {cat_slug}")
                if cat_slug == category_slug.lower():
                    category = cat
                    logger.debug(f"Matched category: {cat}")
                    break

            if not category:
                logger.error(f"Category dengan slug '{category_slug}' tidak ditemukan.")
                messages.error(request, "Kategori tidak ditemukan.")
                return redirect('homepage')

            category_id, nama_kategori = category
            logger.debug(f"Category ID: {category_id}, Nama Kategori: {nama_kategori}")

            # Ambil semua subkategori untuk kategori ini
            cursor.execute("""
                SELECT Id, NamaSubKategori, Deskripsi
                FROM SUBKATEGORI_JASA
                WHERE KategoriJasaId = %s
            """, (category_id,))
            subcategories = cursor.fetchall()
            logger.debug(f"Fetched subcategories for category_id {category_id}: {subcategories}")

            subcategory = None
            for sub in subcategories:
                sub_id, nama_subkategori, deskripsi = sub
                sub_slug = slugify(nama_subkategori).lower()
                logger.debug(f"Checking subcategory: {nama_subkategori} with slug: {sub_slug}")
                if sub_slug == subcategory_slug.lower():
                    subcategory = sub
                    subcategory_slug = sub_slug  # Ensure slug consistency
                    logger.debug(f"Matched subcategory: {sub}")
                    break

            if not subcategory:
                logger.error(f"Subkategori dengan slug '{subcategory_slug}' tidak ditemukan.")
                messages.error(request, "Subkategori tidak ditemukan.")
                return redirect('homepage')

            sub_id, nama_subkategori, deskripsi = subcategory
            logger.debug(f"Subcategory ID: {sub_id}, Nama Subkategori: {nama_subkategori}, Deskripsi: {deskripsi}")

            # Ambil sesi layanan untuk subkategori
            cursor.execute("""
                SELECT Sesi, Harga
                FROM SESI_LAYANAN
                WHERE SubKategoriId = %s
                ORDER BY Sesi;
            """, (sub_id,))
            service_sessions = cursor.fetchall()
            logger.debug(f"Fetched service sessions for SubKategoriId {sub_id}: {service_sessions}")
            service_sessions_data = [
                {'sesi': sesi, 'harga': float(harga)}
                for sesi, harga in service_sessions
            ]

            # Ambil pekerja yang terkait dengan subkategori
            cursor.execute("""
                SELECT p.Id, u.Nama, p.Rating, p.JmlPesananSelesai, p.linkfoto
                FROM PEKERJA p
                JOIN "USER" u ON p.Id = u.Id
                JOIN PEKERJA_KATEGORI_JASA pkj ON p.Id = pkj.PekerjaId
                WHERE pkj.KategoriJasaId = %s
                ORDER BY p.Rating DESC;
            """, (category_id,))
            workers = cursor.fetchall()
            logger.debug(f"Fetched workers for KategoriJasaId {category_id}: {workers}")
            workers_data = [
                {
                    'id': pekerja_id,
                    'name': nama_pekerja,
                    'rating': rating,
                    'jml_pesanan_selesai': jml_pesanan,
                    'profile_picture': link_foto,
                }
                for pekerja_id, nama_pekerja, rating, jml_pesanan, link_foto in workers
            ]

            # Ambil testimoni terkait subkategori
            cursor.execute("""
                SELECT t.Tgl, t.Teks, t.Rating, u.Nama
                FROM TESTIMONI t
                JOIN TR_PEMESANAN_JASA tpj ON t.IdTrPemesanan = tpj.Id
                JOIN "USER" u ON tpj.IdPelanggan = u.Id
                WHERE tpj.IdKategoriJasa = %s
                ORDER BY t.Tgl DESC;
            """, (sub_id,))
            testimonials = cursor.fetchall()
            logger.debug(f"Fetched testimonials for KategoriJasaId {category_id}: {testimonials}")
            testimonials_data = [
                {
                    'date': tgl.strftime('%d %b %Y'),
                    'text': teks,
                    'rating': rating,
                    'user_name': nama_user,
                }
                for tgl, teks, rating, nama_user in testimonials
            ]
            
            # Ambil metode pembayaran
            cursor.execute("""
                SELECT Id, Nama FROM METODE_BAYAR
            """)
            metode_bayar = cursor.fetchall()
            metode_bayar_data = [
                {'Id': metode_id, 'Nama': nama}
                for metode_id, nama in metode_bayar
            ]

            # Cek apakah pengguna adalah pekerja
            user = request.session.get('user')
            logger.debug(f"User session data: {user}")
            is_worker = False
            is_joined = False
            if user and user.get('role') == 'pekerja':
                is_worker = True
                pekerja_id = user.get('Id')
                logger.debug(f"Pekerja ID: {pekerja_id}")
                # Cek apakah pekerja sudah bergabung dengan kategori ini
                cursor.execute("""
                    SELECT 1
                    FROM PEKERJA_KATEGORI_JASA
                    WHERE PekerjaId = %s AND KategoriJasaId = %s
                """, (pekerja_id, category_id))
                is_joined = cursor.fetchone() is not None
                logger.debug(f"Is joined: {is_joined}")

    except Exception as e:
        logger.exception("Error fetching subcategory data.")
        messages.error(request, f"Error fetching subcategory data: {str(e)}")
        return redirect('homepage')
    finally:
        conn.close()
        logger.debug("Database connection closed in subcategory_jasa view.")

    context = {
        'subcategory': {
            'id': sub_id,
            'name': nama_subkategori,
            'description': deskripsi,
            'slug': subcategory_slug,  # Added slug here
        },
        'category': {
            'id': category_id,
            'name': nama_kategori,
            'slug': slugify(nama_kategori).lower(),
        },
        'service_sessions': service_sessions_data,
        'workers': workers_data,
        'is_worker': is_worker,
        'is_joined': is_joined,
        'testimonials': testimonials_data,
        'metode_bayar': metode_bayar_data,
    }
    logger.debug(f"Context data prepared: {context}")

    return render(request, 'subkategori_jasa.html', context)

@custom_login_required
def view_pesanan(request):
    """
    View untuk menampilkan daftar pesanan pengguna saat ini dengan fitur filter dan search.
    """
    logger.debug("view_pesanan view called.")
    user = request.session.get('user')
    if not user:
        logger.error("User not logged in.")
        messages.error(request, "Anda harus login untuk melihat pesanan.")
        return redirect('login')

    user_id = user.get('Id')
    logger.debug(f"Viewing orders for user_id: {user_id}")

    # Ambil parameter filter dan search dari GET
    filter_subcategory = request.GET.get('subcategory', '').strip()
    filter_status = request.GET.get('status', '').strip()
    search_query = request.GET.get('q', '').strip()

    logger.debug(f"Filter parameters - Subcategory: {filter_subcategory}, Status: {filter_status}, Search Query: {search_query}")

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:

            # Ambil semua subkategori yang tersedia untuk pengguna
            cursor.execute("""
                SELECT DISTINCT sj.Id, sj.NamaSubKategori
                FROM TR_PEMESANAN_JASA tpj
                JOIN SUBKATEGORI_JASA sj ON tpj.IdKategoriJasa = sj.Id
                WHERE tpj.IdPelanggan = %s
                ORDER BY sj.NamaSubKategori;
            """, (user_id,))
            subcategories = cursor.fetchall()
            subcategories_data = [{'id': sub[0], 'nama_subkategori': sub[1]} for sub in subcategories]
            logger.debug(f"Available subcategories for filtering: {subcategories_data}")

            # Definisikan status yang tersedia
            status_options = [
                {'value': '', 'label': 'Semua Status'},
                {'value': 'Menunggu Pembayaran', 'label': 'Menunggu Pembayaran'},
                {'value': 'Mencari Pekerja Terdekat', 'label': 'Mencari Pekerja Terdekat'},
                {'value': 'Sedang Dikerjakan', 'label': 'Sedang Dikerjakan'},
                {'value': 'Pesanan Selesai', 'label': 'Pesanan Selesai'},
                {'value': 'Dibatalkan', 'label': 'Dibatalkan'},
            ]

            # Bangun query dasar
            query = """
                SELECT DISTINCT ON (tpj.Id) 
                    tpj.Id, 
                    sj.NamaSubKategori, 
                    tpj.TotalBiaya, 
                    u.Nama AS WorkerName, 
                    sp.Status, 
                    EXISTS (
                        SELECT 1 FROM TESTIMONI t WHERE t.IdTrPemesanan = tpj.Id
                    ) AS has_testimonial,
                    sl.Sesi AS service_session_name
                FROM TR_PEMESANAN_JASA tpj
                LEFT JOIN "USER" u ON tpj.IdPekerja = u.Id
                JOIN SUBKATEGORI_JASA sj ON tpj.IdKategoriJasa = sj.Id
                LEFT JOIN TR_PEMESANAN_STATUS tps ON tpj.Id = tps.IdTrPemesanan
                LEFT JOIN STATUS_PEMESANAN sp ON tps.IdStatus = sp.Id
                JOIN SESI_LAYANAN sl ON tpj.Sesi = sl.Sesi AND sl.SubKategoriId = tpj.IdKategoriJasa
                WHERE tpj.IdPelanggan = %s
            """

            params = [user_id]

            # Tambahkan filter subkategori jika dipilih
            if filter_subcategory:
                query += " AND sj.Id = %s"
                params.append(filter_subcategory)
                logger.debug(f"Applying subcategory filter: {filter_subcategory}")

            # Tambahkan filter status jika dipilih
            if filter_status:
                query += " AND sp.Status = %s"
                params.append(filter_status)
                logger.debug(f"Applying status filter: {filter_status}")

            # Tambahkan pencarian jika ada
            if search_query:
                query += " AND sj.NamaSubKategori ILIKE %s"
                params.append(f"%{search_query}%")
                logger.debug(f"Applying search filter: {search_query}")

            # Tambahkan ORDER BY untuk DISTINCT ON
            query += " ORDER BY tpj.Id, tps.TglWaktu DESC;"

            logger.debug(f"Final SQL Query: {query}")
            logger.debug(f"Query Parameters: {params}")

            cursor.execute(query, tuple(params))
            orders = cursor.fetchall()
            logger.debug(f"Fetched orders: {orders}")

            orders_data = []
            for order in orders:
                order_id, nama_subkategori, total_biaya, worker_name, status_label, has_testimonial, service_session_name = order

                logger.debug(f"Processing order_id: {order_id}, nama_subkategori: {nama_subkategori}, status_label: {status_label}")

                orders_data.append({
                    'id': order_id,
                    'nama_subkategori': nama_subkategori,
                    'service_session_name': service_session_name,
                    'total_payment': float(total_biaya),
                    'worker_name': worker_name or "Belum ada pekerja",
                    'status': status_label,  # Use status_label directly without mapping
                    'has_testimonial': has_testimonial,
                })
                
            # print(orders)

            context = {
                'orders': orders_data,
                'subcategories': subcategories_data,
                'status_options': status_options,
                'current_filters': {
                    'subcategory': filter_subcategory,
                    'status': filter_status,
                    'q': search_query,
                }
            }
            logger.debug(f"Context data prepared: {context}")

            return render(request, 'view_pesanan.html', context)
    except Exception as e:
        logger.exception("Error fetching orders.")
        messages.error(request, f"Error fetching orders: {str(e)}")
        return render(request, 'view_pesanan.html', {'orders': []})
    finally:
        conn.close()
        logger.debug("Database connection closed in view_pesanan view.")

@require_POST
@custom_login_required
def create_order(request):
    """
    View untuk membuat pesanan baru.
    Memastikan total_payment disimpan dalam satuan ribuan rupiah.
    """
    logger.debug("create_order view called.")
    if request.method != 'POST':
        logger.warning("Non-POST request made to create_order.")
        return redirect('homepage')

    user = request.session.get('user')
    if not user:
        logger.error("User not logged in.")
        messages.error(request, "Anda harus login untuk membuat pesanan.")
        return redirect('login')

    user_id = user.get('Id')
    session_id = request.POST.get('session_id')
    subkategori_id = request.POST.get('subkategori_id')  # Field yang dikirim dari form
    order_date_str = request.POST.get('order_date')
    discount_code = request.POST.get('discount_code', '').strip()
    total_payment_str = request.POST.get('total_payment')
    payment_method = request.POST.get('payment_method', '').strip()

    logger.debug(f"Order details - session_id: {session_id}, subkategori_id: {subkategori_id}, order_date: {order_date_str}, discount_code: {discount_code}, total_payment_str: {total_payment_str}, payment_method: {payment_method}")

    # Validasi input
    if not subkategori_id:
        logger.error("SubKategoriId tidak diberikan.")
        messages.error(request, "Subkategori tidak valid.")
        return redirect('homepage')

    try:
        order_date = datetime.strptime(order_date_str, '%d/%m/%Y').date()
        logger.debug(f"Parsed order_date: {order_date}")
    except ValueError:
        logger.error("Invalid order_date format.")
        messages.error(request, "Format tanggal pemesanan tidak valid.")
        return redirect('homepage')

    try:
        total_payment = float(total_payment_str.replace('Rp ', '').replace(',', ''))
        if total_payment < 1000:
            total_payment *= 1000
        logger.debug(f"Parsed total_payment: {total_payment}")
    except ValueError:
        logger.error("Invalid total_payment format.")
        messages.error(request, "Format total pembayaran tidak valid.")
        return redirect('homepage')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Mengambil informasi kategori dan subkategori berdasarkan session_id dan subkategori_id
            cursor.execute("""
                SELECT 
                    s.SubKategoriId,
                    sj.KategoriJasaId,
                    sj.NamaSubKategori
                FROM SESI_LAYANAN s
                JOIN SUBKATEGORI_JASA sj ON s.SubKategoriId = sj.Id
                WHERE s.Sesi = %s AND s.SubKategoriId = %s
            """, (session_id, subkategori_id))
            result = cursor.fetchone()
            if not result:
                logger.error("Sesi layanan atau SubKategoriId tidak ditemukan.")
                messages.error(request, "Sesi layanan atau subkategori tidak ditemukan.")
                return redirect('homepage')

            subkategori_id_db, kategori_jasa_id, nama_subkategori = result
            logger.debug(f"Identified SubKategoriId: {subkategori_id_db}, KategoriJasaId: {kategori_jasa_id}, NamaSubKategori: {nama_subkategori}")

            # Validasi metode pembayaran
            cursor.execute("""
                SELECT Nama FROM METODE_BAYAR WHERE Id = %s
            """, (payment_method,))
            metode = cursor.fetchone()
            if not metode:
                logger.error("Metode pembayaran tidak valid.")
                messages.error(request, "Metode pembayaran tidak valid.")
                return redirect('homepage')
            metode_bayar_id = payment_method
            logger.debug(f"Validated MetodeBayarId: {metode_bayar_id}")

            # Validasi dan ambil ID diskon
            id_diskon = None
            if discount_code:
                cursor.execute("""
                    SELECT Potongan FROM DISKON WHERE Kode = %s
                """, (discount_code,))
                diskon = cursor.fetchone()
                if not diskon:
                    logger.error("Kode diskon tidak valid.")
                    messages.error(request, "Kode diskon tidak valid.")
                    return redirect('homepage')
                potongan = float(diskon[0])
                total_payment = max(total_payment - potongan, 0)
                id_diskon = discount_code
                logger.debug(f"Applied discount: {potongan}, New total_payment: {total_payment}")

            # Insert pesanan baru dengan menggunakan IdKategoriJasa sebagai SubKategoriId
            cursor.execute("""
                INSERT INTO TR_PEMESANAN_JASA (
                    Id, TglPemesanan, TglPekerjaan, WaktuPekerjaan, TotalBiaya,
                    IdPelanggan, IdPekerja, IdKategoriJasa, Sesi, IdDiskon, IdMetodeBayar
                )
                VALUES (
                    uuid_generate_v4(), %s, %s, %s, %s,
                    %s, NULL, %s, %s, %s, %s
                )
                RETURNING Id;
            """, (
                order_date,
                order_date,
                datetime.now(),
                total_payment,
                user_id,
                subkategori_id_db,    # Menggunakan SubKategoriId sebagai IdKategoriJasa
                session_id,
                id_diskon,
                metode_bayar_id,
            ))
            order_id = cursor.fetchone()[0]
            logger.debug(f"Inserted order dengan Id: {order_id}")

            # Set status awal pesanan
            cursor.execute("""
                SELECT Id FROM STATUS_PEMESANAN WHERE Status = 'Menunggu Pembayaran'
            """)
            status = cursor.fetchone()
            if not status:
                logger.error("Status 'Menunggu Pembayaran' tidak ditemukan.")
                messages.error(request, "Status pesanan tidak valid.")
                return redirect('homepage')
            status_id = status[0]
            logger.debug(f"Status ID untuk 'Menunggu Pembayaran': {status_id}")

            cursor.execute("""
                INSERT INTO TR_PEMESANAN_STATUS (IdTrPemesanan, IdStatus, TglWaktu)
                VALUES (%s, %s, %s)
            """, (
                order_id,
                status_id,
                datetime.now(),
            ))
            logger.debug(f"Inserted TR_PEMESANAN_STATUS untuk Order Id: {order_id}")

            conn.commit()
            logger.debug("Order berhasil dibuat.")
            messages.success(request, "Pesanan berhasil dibuat!")
            return redirect('view_pesanan')
    except Exception as e:
        conn.rollback()
        logger.exception("Error creating order.")
        messages.error(request, f"Error creating order: {str(e)}")
        return redirect('homepage')
    finally:
        conn.close()
        logger.debug("Database connection closed in create_order view.")

@csrf_exempt
def calculate_total(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_sesi = data.get('session_sesi')
            discount_code = data.get('discount_code', '').strip()

            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Ambil harga dari sesi layanan
                cursor.execute("""
                    SELECT harga FROM SESI_LAYANAN WHERE sesi = %s
                """, (session_sesi,))
                result = cursor.fetchone()
                if not result:
                    return JsonResponse({'success': False, 'error': 'Sesi layanan tidak ditemukan.'})

                harga = float(result[0])

                # Hitung diskon jika ada kode diskon
                if discount_code:
                    cursor.execute("""
                        SELECT persen_diskon FROM DISKON WHERE kode = %s AND aktif = TRUE
                    """, (discount_code,))
                    discount = cursor.fetchone()
                    if discount:
                        persen_diskon = float(discount[0])
                        discount_amount = harga * (persen_diskon / 100)
                        total_payment = harga - discount_amount
                    else:
                        return JsonResponse({'success': False, 'error': 'Kode diskon tidak valid.'})
                else:
                    total_payment = harga

                return JsonResponse({'success': True, 'total_payment': total_payment})

        except Exception as e:
            logger.exception("Error calculating total payment.")
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@require_POST
@custom_login_required
def join_service(request, subcategory_slug):
    """
    API View for a worker to join a category service.
    """
    logger.debug(f"join_service API called with subcategory_slug='{subcategory_slug}'")
    user = request.session.get('user')
    if not user:
        return JsonResponse({'success': False, 'error': 'User not authenticated.'})

    if user.get('role') != 'pekerja':
        return JsonResponse({'success': False, 'error': 'Only workers can join services.'})

    user_id = user.get('Id')
    logger.debug(f"Worker ID: {user_id} attempting to join service.")
    
    subcategory_name = subcategory_slug.replace('-', ' ').lower()

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil subkategori berdasarkan slug
            cursor.execute("""
                SELECT Id, NamaSubKategori, KategoriJasaId
                FROM SUBKATEGORI_JASA
                WHERE LOWER(namasubkategori) = %s
            """, (subcategory_name,))
            subcategory = cursor.fetchone()
            if not subcategory:
                logger.error(f"Subcategory dengan slug '{subcategory_slug}' tidak ditemukan.")
                return JsonResponse({'success': False, 'error': 'Subcategory not found.'})

            subkategori_id_db, nama_subkategori, kategori_jasa_id = subcategory
            logger.debug(f"Matched subcategory: {subkategori_id_db}, {nama_subkategori}, {kategori_jasa_id}")

            # Insert ke tabel PEKERJA_KATEGORI_JASA
            cursor.execute("""
                INSERT INTO PEKERJA_KATEGORI_JASA (PekerjaId, KategoriJasaId)
                VALUES (%s, %s)
            """, (user_id, kategori_jasa_id))
            conn.commit()
            logger.debug("Worker successfully joined the category service.")

        return JsonResponse({'success': True})
    except psycopg2.IntegrityError:
        conn.rollback()
        logger.exception("IntegrityError: Worker has already joined the category service.")
        return JsonResponse({'success': False, 'error': 'You have already joined this category service.'})
    except Exception as e:
        conn.rollback()
        logger.exception("Error joining service.")
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'})
    finally:
        conn.close()
        logger.debug("Database connection closed in join_service API.")
        
def worker_profile(request, worker_id):
    """
    View untuk menampilkan profil pekerja.
    """
    logger.debug(f"worker_profile view called with worker_id='{worker_id}'")
    worker_id = str(worker_id)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ambil informasi pekerja
            cursor.execute("""
                SELECT u.Nama, u.JenisKelamin, u.NoHP, u.TglLahir, u.Alamat,
                       p.NamaBank, p.NomorRekening, p.NPWP, p.LinkFoto, p.Rating, p.JmlPesananSelesai
                FROM PEKERJA p
                JOIN "USER" u ON p.Id = u.Id
                WHERE p.Id = %s
            """, (worker_id,))
            worker = cursor.fetchone()
            if not worker:
                logger.error(f"Worker with ID '{worker_id}' not found.")
                messages.error(request, "Worker not found.")
                return redirect('homepage')

            # Ambil kategori pekerjaan pekerja
            cursor.execute("""
                SELECT kj.NamaKategori
                FROM PEKERJA_KATEGORI_JASA pkj
                JOIN KATEGORI_JASA kj ON pkj.KategoriJasaId = kj.Id
                WHERE pkj.PekerjaId = %s
            """, (worker_id,))
            job_categories = cursor.fetchall()
            job_categories = [category[0] for category in job_categories]

        context = {
            'worker': {
                'name': worker[0],
                'gender': worker[1],
                'phone': worker[2],
                'birthdate': worker[3],
                'address': worker[4],
                'bank_name': worker[5],
                'account_number': worker[6],
                'npwp': worker[7],
                'photo_link': worker[8],
                'rating': worker[9],
                'completed_orders': worker[10],
                'job_categories': job_categories,
            },
            'is_own_profile': False,  # Menandakan ini bukan profil sendiri
        }
        return render(request, 'profile.html', context)
    except Exception as e:
        logger.exception("Error fetching worker profile.")
        # messages.error(request, "Error fetching worker profile.")
        return redirect('homepage')
    finally:
        conn.close()
        logger.debug("Database connection closed in worker_profile view.")

@require_POST
@custom_login_required
def create_testimonial(request):
    """
    View untuk membuat testimoni untuk pesanan tertentu.
    """
    logger.debug("create_testimonial called.")
    user = request.session.get('user')
    if not user:
        logger.warning("Unauthenticated user attempted to create testimonial.")
        messages.error(request, "Anda harus login untuk memberikan testimoni.")
        return redirect('login')
    
    user_id = user.get('Id')
    logger.debug(f"User ID: {user_id} attempting to create testimonial.")
    
    try:
        order_id = request.POST.get('order_id')
        rating = int(request.POST.get('rating', 0))
        testimonial_text = request.POST.get('testimonial', '').strip()
        logger.debug(f"Received testimonial data - order_id: {order_id}, rating: {rating}, testimonial_text: {testimonial_text}")
    
        if not order_id or not testimonial_text:
            logger.error("Incomplete testimonial data received.")
            messages.error(request, "Data testimoni tidak lengkap.")
            return redirect('view_pesanan')
    
        if rating < 1 or rating > 5:
            logger.error("Invalid rating value received.")
            messages.error(request, "Rating harus antara 1 dan 5.")
            return redirect('view_pesanan')
    
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Verifikasi pesanan
            cursor.execute("""
                SELECT tpj.IdPelanggan FROM TR_PEMESANAN_JASA tpj
                WHERE tpj.Id = %s AND tpj.IdPelanggan = %s AND (
                    SELECT sp.Status FROM TR_PEMESANAN_STATUS tps
                    JOIN STATUS_PEMESANAN sp ON tps.IdStatus = sp.Id
                    WHERE tps.IdTrPemesanan = tpj.Id ORDER BY tps.TglWaktu DESC LIMIT 1
                ) = 'Pemesanan Selesai'
            """, (order_id, user_id))
            pesanan = cursor.fetchone()
            if not pesanan:
                logger.error(f"Pesanan ID: {order_id} tidak valid atau belum selesai.")
                messages.error(request, "Pesanan tidak valid atau belum selesai.")
                return redirect('view_pesanan')
    
            # Cek apakah sudah ada testimoni
            cursor.execute("""
                SELECT 1 FROM TESTIMONI
                WHERE IdTrPemesanan = %s
            """, (order_id,))
            if cursor.fetchone():
                logger.info(f"Testimoni sudah dibuat untuk Pesanan ID: {order_id}")
                messages.error(request, "Anda sudah memberikan testimoni untuk pesanan ini.")
                return redirect('view_pesanan')
    
            # Insert testimoni
            cursor.execute("""
                INSERT INTO TESTIMONI (IdTrPemesanan, Tgl, Teks, Rating)
                VALUES (%s, %s, %s, %s)
            """, (order_id, datetime.now().date(), testimonial_text, rating))
            conn.commit()
            logger.debug(f"Testimoni berhasil dibuat untuk Pesanan ID: {order_id}")
            messages.success(request, "Testimoni berhasil dibuat.")
            return redirect('view_pesanan')
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.exception("Error creating testimonial.")
        messages.error(request, f"Terjadi kesalahan saat membuat testimoni: {str(e)}")
        return redirect('view_pesanan')
    finally:
        if 'conn' in locals():
            conn.close()
            logger.debug("Database connection closed in create_testimonial.")

@require_POST
@custom_login_required
def cancel_order(request, order_id):
    """
    API View untuk membatalkan pesanan tertentu.
    """
    logger.debug(f"cancel_order API called with order_id='{order_id}'")
    user = request.session.get('user')
    if not user:
        logger.warning("Unauthenticated user attempted to cancel order.")
        return JsonResponse({'success': False, 'error': 'User not authenticated'}, status=401)

    user_id = user.get('Id')
    logger.debug(f"User ID: {user_id} attempting to cancel order.")

    try:
        # order_id sudah berupa objek UUID, tidak perlu diparse ulang
        order_uuid = order_id

        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Ambil status terbaru dari TR_PEMESANAN_STATUS
            cursor.execute("""
                SELECT sp.Status
                FROM TR_PEMESANAN_STATUS tps
                JOIN STATUS_PEMESANAN sp ON tps.IdStatus = sp.Id
                WHERE tps.IdTrPemesanan = %s
                ORDER BY tps.TglWaktu DESC
                LIMIT 1;
            """, (str(order_uuid),))
            pesanan = cursor.fetchone()
            if not pesanan:
                logger.error(f"Pesanan ID: {order_uuid} tidak ditemukan.")
                return JsonResponse({'success': False, 'error': 'Pesanan tidak ditemukan'}, status=404)

            current_status = pesanan[0]
            logger.debug(f"Current status of Pesanan ID {order_uuid}: {current_status}")
            if current_status not in ['Menunggu Pembayaran', 'Mencari Pekerja Terdekat']:
                logger.error(f"Pesanan ID: {order_uuid} tidak dapat dibatalkan karena statusnya adalah '{current_status}'.")
                return JsonResponse({'success': False, 'error': 'Pesanan tidak dapat dibatalkan'}, status=400)

            # Ambil Id status 'Pemesanan Dibatalkan'
            cursor.execute("""
                SELECT Id FROM STATUS_PEMESANAN WHERE Status = 'Pemesanan Dibatalkan';
            """)
            status_id = cursor.fetchone()
            if not status_id:
                logger.error("Status 'Pemesanan Dibatalkan' tidak ditemukan dalam STATUS_PEMESANAN.")
                return JsonResponse({'success': False, 'error': 'Status pembatalan tidak valid'}, status=500)
            status_id = status_id[0]

            # Insert status baru 'Pemesanan Dibatalkan' ke TR_PEMESANAN_STATUS
            cursor.execute("""
                INSERT INTO TR_PEMESANAN_STATUS (IdTrPemesanan, IdStatus, TglWaktu)
                VALUES (%s, %s, %s);
            """, (str(order_uuid), status_id, datetime.now()))
            logger.debug(f"Inserted TR_PEMESANAN_STATUS untuk Pesanan ID: {order_uuid}.")

            conn.commit()
            logger.info(f"Pesanan ID: {order_uuid} berhasil dibatalkan.")
            return JsonResponse({'success': True})
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.exception("Error cancelling order.")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    finally:
        if 'conn' in locals():
            conn.close()
            logger.debug("Database connection closed in cancel_order API.")
