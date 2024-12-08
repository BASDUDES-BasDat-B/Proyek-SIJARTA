from django.shortcuts import render, redirect
from django.contrib import messages
import psycopg2
from utils.db_connection import get_db_connection
from django.contrib.auth.decorators import login_required

def main_view(request):
    return render(request, 'main.html')

def format_bank_name(bank_name):
    BANK_NAME_MAPPING = {
        "gopay": "GoPay",
        "ovo": "OVO",
        "bca": "BCA",
        "bni": "BNI",
        "mandiri": "Mandiri",
    }
    return BANK_NAME_MAPPING.get(bank_name.lower(), bank_name)

def get_job_categories(phone):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Query untuk mengambil kategori jasa berdasarkan nomor telepon
            cursor.execute("""
                SELECT kj.NamaKategori
                FROM PEKERJA p
                JOIN "USER" u ON p.Id = u.Id
                JOIN PEKERJA_KATEGORI_JASA pkj ON p.Id = pkj.PekerjaId
                JOIN KATEGORI_JASA kj ON pkj.KategoriJasaId = kj.Id
                WHERE u.NoHP = %s;
            """, (phone,))
            # Ambil semua hasil dan ubah menjadi daftar string
            categories = [row[0] for row in cursor.fetchall()]
            return categories
    except Exception as e:
        print(f"Error fetching job categories: {e}")
        return []
    finally:
        conn.close()

def login_view(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        
        conn = get_db_connection()
        
        try:
            with conn.cursor() as cursor:
                # Dapatkan data dari tabel USER
                cursor.execute("""
                    SELECT Id, Nama, JenisKelamin, NoHP, Pwd, TglLahir, Alamat, SaldoMyPay
                    FROM "USER"
                    WHERE NoHP = %s
                """, (phone,))
                user = cursor.fetchone()

                if user and user[4] == password: 
                    user_id = str(user[0]) 
                    user_name = user[1]
                    gender = user[2]
                    tgl_lahir = user[5]
                    Alamat = user[6]
                    saldo = user[7]
                    job_categories = []

                    # Tentukan role berdasarkan data pelanggan atau pekerja
                    cursor.execute("""
                        SELECT Level FROM PELANGGAN WHERE Id = %s
                    """, (user_id,))
                    pelanggan = cursor.fetchone()

                    role = None
                    additional_data = {}
                    level = None

                    if pelanggan:
                        level = pelanggan[0]
                        role = 'pelanggan'
                    else:
                        cursor.execute("""
                            SELECT NamaBank, NomorRekening, NPWP, LinkFoto, Rating, JmlPesananSelesai
                            FROM PEKERJA
                            WHERE Id = %s
                        """, (user_id,))
                        pekerja = cursor.fetchone()

                        if pekerja:
                            role = 'pekerja'
                            job_categories = get_job_categories(phone)
                            additional_data.update({
                                'bank': pekerja[0],  # Nama bank
                                'account_number': pekerja[1],  # Nomor rekening
                                'npwp': pekerja[2],  # NPWP
                                'photo_link': pekerja[3],  # Link foto
                                'rating': pekerja[4],  # Rating pekerja
                                'completed_orders': pekerja[5],
                            })
                        else:
                            role = 'unknown'
                            job_categories = []

                    # Simpan data ke session
                    request.session["user"] = {
                        "Id": user_id,
                        "Nama": user_name,
                        "gender": gender,
                        "phone": phone,
                        "TglLahir": str(tgl_lahir),
                        "alamat": Alamat,
                        "saldo": float(saldo) if saldo else 0.0,
                        "role": role,
                        "job_categories": job_categories,
                        "level": level,
                        **additional_data, 
                    }
                    return redirect('homepage')
                else:
                    messages.error(request, 'Nomor HP atau Password salah!')
                    return render(request, 'login.html')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        finally:
            conn.close()

    return render(request, 'login.html')

# Fungsi untuk register
def register_view(request):
    if request.method == "POST":
        role = request.POST.get("role")
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if role == 'pengguna':
                    name = request.POST.get("pengguna_name")
                    password = request.POST.get("pengguna_password")
                    gender = request.POST.get("pengguna_gender")
                    phone = request.POST.get("pengguna_phone")
                    birthdate = request.POST.get("pengguna_birthdate")
                    address = request.POST.get("pengguna_address")
                elif role == 'pekerja':
                    name = request.POST.get("pekerja_name")
                    password = request.POST.get("pekerja_password")
                    gender = request.POST.get("pekerja_gender")
                    phone = request.POST.get("pekerja_phone")
                    birthdate = request.POST.get("pekerja_birthdate")
                    address = request.POST.get("pekerja_address")
                    bank_name = request.POST.get("pekerja_bank")
                    if bank_name:
                        bank_name = format_bank_name(bank_name)
                    account_number = request.POST.get("pekerja_account_number")
                    npwp = request.POST.get("pekerja_npwp")
                    photo_link = request.POST.get("pekerja_photo_link")
                else:
                    messages.error(request, "Role tidak valid.")
                    return render(request, 'registration.html')

                # Insert ke tabel "USER"
                cursor.execute("""
                    INSERT INTO "USER" (Nama, NoHp, Pwd, JenisKelamin, TglLahir, Alamat, SaldoMyPay)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (name, phone, password, gender, birthdate, address, 0.00))
                conn.commit()

                cursor.execute("""
                    SELECT Id FROM "USER" WHERE NoHp = %s
                """, (phone,))
                user = cursor.fetchone()
                if user:
                    user_id = user[0]
                else:
                    messages.error(request, "Terjadi kesalahan saat mengambil ID pengguna.")
                    return render(request, 'registration.html')

                if role == 'pengguna':
                    cursor.execute("""
                        INSERT INTO PELANGGAN (Id, Level)
                        VALUES (%s, %s)
                    """, (user_id, 'Basic'))
                    conn.commit()

                elif role == 'pekerja':
                    cursor.execute("""
                        INSERT INTO PEKERJA (Id, NamaBank, NomorRekening, NPWP, LinkFoto, Rating, JmlPesananSelesai)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, bank_name, account_number, npwp, photo_link, 0.00, 0))
                    conn.commit()

                messages.success(request, 'Pendaftaran berhasil! Silahkan login.')
                return redirect('main')

        except psycopg2.IntegrityError as e:
            conn.rollback()
            error = e.pgerror.lower()

            if 'nomor hp' in error:
                messages.error(request, f"Error: Nomor HP {phone} sudah terdaftar.")
                return render(request, 'main.html')
            if 'nomor rekening' in error:
                messages.error(request, f"Error: Nomor Rekening {account_number} dari Bank {bank_name} sudah terdaftar.")
                return render(request, 'main.html')
            if 'npwp' in error:
                messages.error(request, f"Error: Nomor NPWP {npwp} sudah terdaftar.")
                return render(request, 'main.html')
            else:
                messages.error(request, "Terjadi kesalahan saat pendaftaran. Silakan coba lagi.")
        except Exception as e:
            conn.rollback()
            messages.error(request, f"Error: {str(e)}")
        finally:
            conn.close()

    return render(request, 'registration.html')

def edit_profile(request):
    if 'user' not in request.session:
        return redirect('login')

    user_id = request.session['user']['Id']
    conn = get_db_connection()

    if request.method == 'POST':
        phone = request.POST.get("phone")
        name = request.POST.get("name")
        address = request.POST.get("address")
        gender = request.POST.get("gender")
        birth = request.POST.get("birthdate")

        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT Nama, NoHp, Alamat, JenisKelamin, TglLahir
                    FROM "USER"
                    WHERE Id = %s
                """, (user_id,))
                user_data = cursor.fetchone()
                if not user_data:
                    messages.error(request, "Data pengguna tidak ditemukan.")
                    return redirect('homepage')

                old_name, old_phone, old_address, old_gender, old_birth = user_data

                # Perbarui jika ada perubahan
                if (name, phone, address, gender, birth) != (old_name, old_phone, old_address, old_gender, old_birth):
                    cursor.execute("""
                        UPDATE "USER"
                        SET Nama = %s, NoHp = %s, Alamat = %s, JenisKelamin = %s, TglLahir = %s
                        WHERE Id = %s
                    """, (name, phone, address, gender, birth, user_id))

                if request.session['user']['role'] == 'pelanggan':
                    cursor.execute("""
                        SELECT Level
                        FROM PELANGGAN
                        WHERE Id = %s
                    """, (user_id,))
                    pelanggan_data = cursor.fetchone()
                    level = pelanggan_data[0] if pelanggan_data else None

                elif request.session['user']['role'] == 'pekerja':
                    bank = request.POST.get("bank")
                    if bank:
                        bank = format_bank_name(bank)
                    account_number = request.POST.get("account_number")
                    npwp = request.POST.get("npwp")
                    photo_link = request.POST.get("photo_link")

                    cursor.execute("""
                        SELECT NamaBank, NomorRekening, NPWP, LinkFoto, Rating, JmlPesananSelesai
                        FROM PEKERJA
                        WHERE Id = %s
                    """, (user_id,))
                    pekerja_data = cursor.fetchone()

                    if not pekerja_data:
                        messages.error(request, "Data pekerja tidak ditemukan.")
                        return redirect('homepage')

                    old_bank, old_account_number, old_npwp, old_photo_link, rating, completed_orders = pekerja_data

                    # Perbarui data jika ada perubahan
                    if (bank, account_number, npwp, photo_link) != (old_bank, old_account_number, old_npwp, old_photo_link):
                        cursor.execute("""
                            UPDATE PEKERJA
                            SET NamaBank = %s, NomorRekening = %s, NPWP = %s, LinkFoto = %s
                            WHERE Id = %s
                        """, (bank, account_number, npwp, photo_link, user_id))

                # Simpan perubahan ke database
                conn.commit()

                # Ambil data terbaru
                cursor.execute("""
                    SELECT Nama, NoHp, Alamat, JenisKelamin, TglLahir, SaldoMyPay
                    FROM "USER"
                    WHERE Id = %s
                """, (user_id,))
                updated_user_data = cursor.fetchone()

                context = {
                    "name": updated_user_data[0],
                    "phone": updated_user_data[1],
                    "address": updated_user_data[2],
                    "gender": updated_user_data[3],
                    "birthdate": updated_user_data[4].strftime('%Y-%m-%d') if updated_user_data[4] else '',
                    "saldo": float(updated_user_data[5]),
                    'is_own_profile': True,
                }

                updated_session_user = {
                    'Id': user_id,
                    'Nama': updated_user_data[0],
                    'phone': updated_user_data[1],
                    'alamat': updated_user_data[2],
                    'gender': updated_user_data[3],
                    'TglLahir': updated_user_data[4].strftime('%Y-%m-%d') if updated_user_data[4] else '',
                    'saldo': float(updated_user_data[5]),
                    'role': request.session['user']['role'],
                }

                if request.session['user']['role'] == 'pelanggan':
                    context["level"] = level
                    updated_session_user["level"] = level

                elif request.session['user']['role'] == 'pekerja':
                    categories = get_job_categories(updated_user_data[1])  # Assuming 'phone' is at index 1
                    context.update({
                        "bank_name": old_bank,
                        "account_number": old_account_number,
                        "npwp": old_npwp,
                        "photo_link": old_photo_link,
                        "job_categories": categories,
                        "rating": rating,
                        "completed_orders": completed_orders,
                    })
                    updated_session_user.update({
                        "bank_name": old_bank,
                        "account_number": old_account_number,
                        "npwp": old_npwp,
                        "photo_link": old_photo_link,
                        "job_categories": categories,
                        "rating": rating,
                        "completed_orders": completed_orders,
                    })

                request.session['user'] = updated_session_user
                request.session.modified = True

                messages.success(request, 'Profil berhasil diperbarui!')
                return render(request, 'profile.html', context)

        except psycopg2.IntegrityError as e:
            conn.rollback()
            if 'Nomor HP' in str(e):
                error_message = f"Error: Nomor HP {phone} sudah terdaftar."
            elif 'Nomor Rekening' in str(e):
                error_message = f"Error: Nomor Rekening {account_number} dari Bank {bank} sudah terdaftar."
            elif 'npwp' in str(e):
                error_message = f"Error: Nomor NPWP {npwp} sudah terdaftar."
            else:
                error_message = "Terjadi error saat menyimpan data."
            messages.error(request, error_message)
        except Exception as e:
            conn.rollback()
            messages.error(request, f"Error: {str(e)}")
        finally:
            conn.close()

    else:
        try:
            with conn.cursor() as cursor:
                # Ambil data pengguna
                cursor.execute("""
                    SELECT Nama, NoHp, JenisKelamin, TglLahir, Alamat, SaldoMyPay
                    FROM "USER"
                    WHERE Id = %s
                """, (user_id,))
                user_data = cursor.fetchone()

                if user_data:
                    context = {
                        "name": user_data[0],
                        "phone": user_data[1],
                        "gender": user_data[2],
                        "birthdate": user_data[3].strftime('%Y-%m-%d') if user_data[3] else '',
                        "address": user_data[4],
                        "saldo": float(user_data[5]),
                        'is_own_profile': True,
                    }

                    updated_session_user = {
                        'Id': user_id,
                        'Nama': user_data[0],
                        'phone': user_data[1],
                        'gender': user_data[2],
                        'TglLahir': user_data[3].strftime('%Y-%m-%d') if user_data[3] else '',
                        'alamat': user_data[4],
                        'saldo': float(user_data[5]),
                        'role': request.session['user']['role'],
                    }

                    if request.session['user']['role'] == 'pelanggan':
                        cursor.execute("""
                            SELECT Level
                            FROM PELANGGAN
                            WHERE Id = %s
                        """, (user_id,))
                        pelanggan_data = cursor.fetchone()
                        level = pelanggan_data[0] if pelanggan_data else None
                        context["level"] = level
                        updated_session_user["level"] = level

                    elif request.session['user']['role'] == 'pekerja':
                        cursor.execute("""
                            SELECT NamaBank, NomorRekening, NPWP, LinkFoto, Rating, JmlPesananSelesai
                            FROM PEKERJA
                            WHERE Id = %s
                        """, (user_id,))
                        pekerja_data = cursor.fetchone()

                        if pekerja_data:
                            bank_name, account_number, npwp, photo_link, rating, completed_orders = pekerja_data
                            categories = get_job_categories(user_data[1])  # Assuming 'phone' is at index 1

                            context.update({
                                "bank_name": bank_name,
                                "account_number": account_number,
                                "npwp": npwp,
                                "photo_link": photo_link,
                                "job_categories": categories,
                                "rating": rating,
                                "completed_orders": completed_orders,
                            })
                            updated_session_user.update({
                                "bank_name": bank_name,
                                "account_number": account_number,
                                "npwp": npwp,
                                "photo_link": photo_link,
                                "job_categories": categories,
                                "rating": rating,
                                "completed_orders": completed_orders,
                            })

                    request.session['user'] = updated_session_user
                    request.session.modified = True
                    return render(request, 'profile.html', context)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        finally:
            conn.close()

    return redirect('homepage')

def logout_view(request):
    if 'user' in request.session:
        del request.session['user']
    messages.success(request, "Anda telah berhasil logout!")
    return redirect('main')