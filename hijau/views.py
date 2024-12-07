# views.py
from django.shortcuts import render
from utils.db_connection import get_db_connection
import json
import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from psycopg2.extras import RealDictCursor

def homepage(request):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Query untuk mengambil semua kategori dan subkategori
        query = """
            SELECT 
                kj.id AS kategori_id, 
                kj.nama_kategori, 
                kj.slug AS kategori_slug, 
                kj.icon,
                skj.id AS subkategori_id, 
                skj.nama_subkategori, 
                skj.slug AS subkategori_slug, 
                skj.deskripsi
            FROM 
                KATEGORI_JASA kj
            LEFT JOIN 
                SUBKATEGORI_JASA skj ON kj.id = skj.kategori_jasa_id
            ORDER BY 
                kj.nama_kategori, skj.nama_subkategori;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Mengorganisir data menjadi dictionary
        categories = {}
        for row in results:
            kategori_id = row['kategori_id']
            if kategori_id not in categories:
                categories[kategori_id] = {
                    'nama_kategori': row['nama_kategori'],
                    'slug': row['kategori_slug'],
                    'icon': row['icon'],
                    'subcategories': []
                }
            if row['subkategori_id']:
                categories[kategori_id]['subcategories'].append({
                    'nama_subkategori': row['nama_subkategori'],
                    'slug': row['subkategori_slug'],
                    'deskripsi': row['deskripsi']
                })
        
        cursor.close()
        conn.close()
        
        # Mendapatkan filter dari request GET
        category_slug = request.GET.get('category')
        search_query = request.GET.get('q')
        
        # Filter berdasarkan kategori
        if category_slug:
            categories = {k: v for k, v in categories.items() if v['slug'] == category_slug}
        
        # Filter berdasarkan search query
        if search_query:
            for kategori in categories.values():
                kategori['subcategories'] = [
                    sub for sub in kategori['subcategories']
                    if search_query.lower() in sub['nama_subkategori'].lower()
                ]
            # Menghapus kategori tanpa subkategori setelah filter
            categories = {k: v for k, v in categories.items() if v['subcategories']}
        
        context = {
            'categories': categories.values(),
        }
        
        return render(request, 'hijau/homepage.html', context)
    
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse("Terjadi kesalahan saat memuat halaman.", status=500)
    
    finally:
        if not cursor.closed:
            cursor.close()
        if not conn.closed:
            conn.close()

@login_required
def view_pesanan(request):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            messages.error(request, 'Anda harus login terlebih dahulu.')
            return redirect('login')
        
        # Fetch all categories for filter dropdown
        query_categories = """
            SELECT id, nama_kategori FROM KATEGORI_JASA ORDER BY nama_kategori;
        """
        cursor.execute(query_categories)
        categories = cursor.fetchall()
        
        # Fetch all orders for the current user
        query_orders = """
            SELECT
                tpj.id,
                skj.nama_subkategori,
                skl.sesi AS service_session_name,
                tpj.total_biaya AS total_payment,
                p.nama AS worker_name,
                ts.nama_status AS status,
                (SELECT COUNT(*) FROM TESTIMONI WHERE id_tr_pemesanan = tpj.id) > 0 AS has_testimonial
            FROM
                TR_PEMESANAN_JASA tpj
            LEFT JOIN
                SUBKATEGORI_JASA skj ON tpj.id_kategori_jasa = skj.id
            LEFT JOIN
                SESI_LAYANAN skl ON tpj.sesi = skl.sesi AND skl.subkategori_id = skj.id
            LEFT JOIN
                PEKERJA p ON tpj.id_pekerja = p.id
            LEFT JOIN
                STATUS ts ON tpj.status_id = ts.id
            WHERE
                tpj.id_pelanggan = %s
            ORDER BY
                tpj.tgl_pemesanan DESC;
        """
        cursor.execute(query_orders, (user_id,))
        orders = cursor.fetchall()
        
        context = {
            'categories': categories,
            'orders': orders,
        }
        
        return render(request, 'hijau/view_pemesanan.html', context)
    
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse("Terjadi kesalahan saat memuat halaman.", status=500)
    
    finally:
        if not cursor.closed:
            cursor.close()
        if not conn.closed:
            conn.close()

@csrf_exempt
@login_required
def cancel_order(request, order_id):
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'success': False, 'error': 'User not authenticated.'})

            # Memastikan order_id valid dan terkait dengan pengguna
            query_order = """
                SELECT status_id
                FROM TR_PEMESANAN_JASA
                WHERE id = %s AND id_pelanggan = %s
                LIMIT 1;
            """
            cursor.execute(query_order, (order_id, user_id))
            order = cursor.fetchone()
            if not order:
                return JsonResponse({'success': False, 'error': 'Pesanan tidak ditemukan.'})

            current_status_id = order[0]

            # Mendapatkan id_status untuk 'Mencari Pekerja Terdekat' dan 'Dibatalkan'
            cursor.execute("SELECT id FROM STATUS_PEMESANAN WHERE status = 'Mencari Pekerja Terdekat'")
            searching_worker_status = cursor.fetchone()
            if not searching_worker_status:
                return JsonResponse({'success': False, 'error': 'Status "Mencari Pekerja Terdekat" tidak ditemukan.'})
            searching_worker_status_id = searching_worker_status[0]

            cursor.execute("SELECT id FROM STATUS_PEMESANAN WHERE status = 'Dibatalkan'")
            cancelled_status = cursor.fetchone()
            if not cancelled_status:
                return JsonResponse({'success': False, 'error': 'Status "Dibatalkan" tidak ditemukan.'})
            cancelled_status_id = cancelled_status[0]

            # Cek apakah pesanan dalam status "Mencari Pekerja Terdekat"
            if current_status_id != searching_worker_status_id:
                return JsonResponse({'success': False, 'error': 'Pesanan tidak dapat dibatalkan karena tidak dalam status "Mencari Pekerja Terdekat".'})

            # Insert ke TR_PEMESANAN_STATUS dengan status 'Dibatalkan'
            insert_status = """
                INSERT INTO TR_PEMESANAN_STATUS (id_tr_pemesanan, id_status, tgl_waktu)
                VALUES (%s, %s, CURRENT_TIMESTAMP);
            """
            cursor.execute(insert_status, (order_id, cancelled_status_id))
            conn.commit()

            return JsonResponse({'success': True})

        except Exception as e:
            conn.rollback()
            return JsonResponse({'success': False, 'error': str(e)})

        finally:
            cursor.close()
            conn.close()
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})


@csrf_exempt
@login_required
def create_testimonial(request):
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            data = json.loads(request.body)
            order_id = data.get('order_id')
            teks = data.get('testimonial', '').strip()
            rating = int(data.get('rating', 0))
            
            if not teks or not (1 <= rating <= 5):
                return JsonResponse({'success': False, 'error': 'Data tidak valid.'})
            
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'success': False, 'error': 'User not authenticated.'})
            
            # Memastikan order_id valid dan terkait dengan pengguna
            query_order = """
                SELECT id_pekerja, status_id
                FROM TR_PEMESANAN_JASA
                WHERE id = %s AND id_pelanggan = %s
                LIMIT 1;
            """
            cursor.execute(query_order, (order_id, user_id))
            order = cursor.fetchone()
            if not order:
                return JsonResponse({'success': False, 'error': 'Pesanan tidak ditemukan.'})
            
            status_id = order[1]
            # Asumsikan status_id '5' adalah 'completed'
            if status_id != 5:
                return JsonResponse({'success': False, 'error': 'Testimoni hanya dapat dibuat untuk pesanan yang telah selesai.'})
            
            # Memastikan bahwa pengguna belum membuat testimoni untuk pesanan ini
            query_testimoni = """
                SELECT COUNT(*) FROM TESTIMONI
                WHERE id_tr_pemesanan = %s;
            """
            cursor.execute(query_testimoni, (order_id,))
            testimoni_count = cursor.fetchone()[0]
            if testimoni_count > 0:
                return JsonResponse({'success': False, 'error': 'Testimoni sudah dibuat untuk pesanan ini.'})
            
            # Menambahkan testimoni
            insert_testimoni = """
                INSERT INTO TESTIMONI (id_tr_pemesanan, tgl, teks, rating)
                VALUES (%s, CURRENT_DATE, %s, %s);
            """
            cursor.execute(insert_testimoni, (order_id, teks, rating))
            conn.commit()
            
            return JsonResponse({'success': True})
        
        except Exception as e:
            conn.rollback()
            return JsonResponse({'success': False, 'error': str(e)})
        
        finally:
            cursor.close()
            conn.close()
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
@login_required
def create_order(request):
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                messages.error(request, 'Anda harus login terlebih dahulu.')
                return redirect('login')
            
            session_id = request.POST.get('session_id')
            order_date = request.POST.get('order_date')  # Format: 'd/m/Y'
            discount_code = request.POST.get('discount_code', '').strip()
            payment_method = request.POST.get('payment_method')
            
            # Parsing tanggal pemesanan
            tgl_pemesanan_date = datetime.datetime.strptime(order_date, '%d/%m/%Y').date()
            tgl_pekerjaan = tgl_pemesanan_date + datetime.timedelta(days=1)
            waktu_pekerjaan = datetime.datetime.combine(tgl_pekerjaan, datetime.time(10, 0))  # Contoh waktu
            
            # Mendapatkan subkategori_jasa_id dan harga berdasarkan session_id
            query_sesi = """
                SELECT subkategori_id, harga
                FROM SESI_LAYANAN
                WHERE sesi = %s
                LIMIT 1;
            """
            cursor.execute(query_sesi, (session_id,))
            sesi = cursor.fetchone()
            if not sesi:
                messages.error(request, "Sesi layanan tidak ditemukan.")
                return redirect('homepage')
            
            subkategori_id, harga = sesi
            total_biaya = harga
            
            # Menghitung diskon jika ada
            if discount_code:
                query_diskon = """
                    SELECT potongan, min_tr_pemesanan
                    FROM DISKON
                    WHERE kode = %s
                    LIMIT 1;
                """
                cursor.execute(query_diskon, (discount_code,))
                diskon = cursor.fetchone()
                if not diskon:
                    messages.error(request, "Kode diskon tidak valid.")
                    return redirect('subcategory_jasa', category_slug='', subcategory_slug='')
                
                potongan, min_tr_pemesanan = diskon
                # Asumsikan min_tr_pemesanan terpenuhi. Jika perlu, tambahkan logika untuk memeriksa ini.
                total_biaya -= (harga * potongan)
                if total_biaya < 0:
                    total_biaya = 0
            
            # Menentukan pekerja yang akan menangani pesanan (rating tertinggi)
            query_pekerja = """
                SELECT p.id
                FROM PEKERJA p
                JOIN PEKERJA_KATEGORI_JASA pkj ON p.id = pkj.pekerja_id
                WHERE pkj.kategori_jasa_id = %s
                ORDER BY p.rating DESC
                LIMIT 1;
            """
            cursor.execute(query_pekerja, (subkategori_id,))
            pekerja = cursor.fetchone()
            if not pekerja:
                messages.error(request, "Tidak ada pekerja yang tersedia untuk layanan ini.")
                return redirect('subcategory_jasa', category_slug='', subcategory_slug='')
            
            pekerja_id = pekerja[0]
            
            # Membuat entry di TR_PEMESANAN_JASA
            query_insert_order = """
                INSERT INTO TR_PEMESANAN_JASA (
                    id, 
                    tgl_pemesanan, 
                    tgl_pekerjaan, 
                    waktu_pekerjaan, 
                    total_biaya, 
                    id_pelanggan, 
                    id_pekerja, 
                    id_kategori_jasa, 
                    sesi, 
                    id_diskon, 
                    id_metode_bayar,
                    status_id
                ) VALUES (
                    uuid_generate_v4(), 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s, 
                    %s,
                    %s
                )
                RETURNING id;
            """
            # Asumsikan status_id '1' adalah 'waiting_payment'
            waiting_payment_status_id = 1
            cursor.execute(query_insert_order, (
                tgl_pemesanan_date,
                tgl_pekerjaan,
                waktu_pekerjaan,
                total_biaya,
                user_id,
                pekerja_id,
                subkategori_id,
                session_id,
                discount_code if discount_code else None,
                payment_method,
                waiting_payment_status_id
            ))
            order_id = cursor.fetchone()[0]
            conn.commit()
            
            messages.success(request, "Pesanan berhasil dibuat.")
            return redirect('view_pesanan')
        
        except Exception as e:
            conn.rollback()
            messages.error(request, f"Terjadi kesalahan: {e}")
            return redirect('homepage')
        
        finally:
            cursor.close()
            conn.close()
    else:
        return redirect('homepage')
    
@login_required
def subcategory_jasa(request, category_slug, subcategory_slug):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Mengambil informasi kategori dan subkategori
        query = """
            SELECT 
                kj.id AS kategori_id,
                kj.nama_kategori,
                skj.id AS subkategori_id,
                skj.nama_subkategori,
                skj.deskripsi
            FROM 
                KATEGORI_JASA kj
            JOIN 
                SUBKATEGORI_JASA skj ON kj.id = skj.kategori_jasa_id
            WHERE 
                kj.slug = %s AND skj.slug = %s;
        """
        cursor.execute(query, (category_slug, subcategory_slug))
        subcategory = cursor.fetchone()
        
        if not subcategory:
            return HttpResponse("Subkategori tidak ditemukan.", status=404)
        
        # Mengambil layanan terkait subkategori
        query_services = """
            SELECT 
                layanan.id,
                layanan.nama_layanan,
                layanan.deskripsi,
                layanan.harga
            FROM 
                LAYANAN layanan
            WHERE 
                layanan.subkategori_jasa_id = %s;
        """
        cursor.execute(query_services, (subcategory['subkategori_id'],))
        services = cursor.fetchall()
        
        context = {
            'kategori': {
                'id': subcategory['kategori_id'],
                'nama': subcategory['nama_kategori'],
                'slug': category_slug,
            },
            'subkategori': {
                'id': subcategory['subkategori_id'],
                'nama': subcategory['nama_subkategori'],
                'deskripsi': subcategory['deskripsi'],
                'slug': subcategory_slug,
            },
            'services': services,
        }
        
        return render(request, 'hijau/subcategory_jasa.html', context)
    
    except Exception as e:
        print(f"Error: {e}")
        return HttpResponse("Terjadi kesalahan saat memuat subkategori.", status=500)
    
    finally:
        if not cursor.closed:
            cursor.close()
        if not conn.closed:
            conn.close()

@csrf_exempt
@login_required
def calculate_total(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            discount_code = data.get('discount_code', '').strip()
            
            if not session_id:
                return JsonResponse({'error': 'Session ID diperlukan.'}, status=400)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Mendapatkan harga dari sesi layanan
            query_harga = """
                SELECT harga
                FROM SESI_LAYANAN
                WHERE sesi = %s
                LIMIT 1;
            """
            cursor.execute(query_harga, (session_id,))
            sesi = cursor.fetchone()
            if not sesi:
                return JsonResponse({'error': 'Sesi layanan tidak ditemukan.'}, status=404)
            harga = sesi[0]
            
            total = harga
            
            # Menghitung diskon jika ada
            if discount_code:
                query_diskon = """
                    SELECT potongan, min_tr_pemesanan
                    FROM DISKON
                    WHERE kode = %s
                    LIMIT 1;
                """
                cursor.execute(query_diskon, (discount_code,))
                diskon = cursor.fetchone()
                if not diskon:
                    return JsonResponse({'error': 'Kode diskon tidak valid.'}, status=400)
                potongan, min_tr_pemesanan = diskon
                total -= (harga * potongan)
                if total < 0:
                    total = 0
            
            return JsonResponse({'total': total})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
        finally:
            cursor.close()
            conn.close()
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
    
@csrf_exempt
@login_required
def join_service(request, subcategory_slug):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'User not authenticated.'}, status=401)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Mendapatkan subkategori_jasa_id berdasarkan slug
            query_subkategori = """
                SELECT id
                FROM SUBKATEGORI_JASA
                WHERE slug = %s
                LIMIT 1;
            """
            cursor.execute(query_subkategori, (subcategory_slug,))
            subkategori = cursor.fetchone()
            if not subkategori:
                return JsonResponse({'error': 'Subkategori tidak ditemukan.'}, status=404)
            subkategori_id = subkategori[0]
            
            # Mendapatkan pekerja yang terhubung dengan subkategori
            query_pekerja = """
                SELECT p.id
                FROM PEKERJA p
                JOIN PEKERJA_KATEGORI_JASA pkj ON p.id = pkj.pekerja_id
                WHERE pkj.kategori_jasa_id = %s
                ORDER BY p.rating DESC
                LIMIT 1;
            """
            cursor.execute(query_pekerja, (subkategori_id,))
            pekerja = cursor.fetchone()
            if not pekerja:
                return JsonResponse({'error': 'Tidak ada pekerja yang tersedia untuk subkategori ini.'}, status=404)
            pekerja_id = pekerja[0]
            
            # Logika tambahan untuk bergabung dengan layanan bisa ditambahkan di sini
            
            return JsonResponse({'success': 'Berhasil bergabung dengan layanan.'})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        
        finally:
            cursor.close()
            conn.close()
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)
