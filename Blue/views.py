# views.py

import psycopg2
from psycopg2 import sql
from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
from utils.db_connection import get_db_connection
from utils.decorators import custom_login_required
import logging

# Configure logger using your app's name
logger = logging.getLogger('your_app_name')  # Replace with your actual app name

def execute_query(sql_query, params=None, fetchone=False):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, params or [])
            if fetchone:
                return cursor.fetchone()
            return cursor.fetchall()

# @login_required
def discount_view(request):
    """
    View to display vouchers and promos.
    """
    user_id = request.user.id  # Assuming you have a custom user model linked to the "user" table

    # Fetch vouchers
    voucher_query = """
        SELECT v.kode, v.jmlhariberlaku, v.kuotapenggunaan, v.harga, d.potongan, d.mintrpemesanan
        FROM voucher v
        JOIN diskon d ON v.kode = d.kode
    """
    vouchers = execute_query(voucher_query)
    voucher_list = [
        {
            'kode': row[0],
            'potongan': f"{Decimal(row[4]) * 100:.2f}",
            'minimum_transaksi': row[5],
            'hari_berlaku': row[1],
            'jumlah_kuota_penggunaan': row[2],
            'harga_voucher': row[3]
        }
        for row in vouchers
    ]

    # Fetch promos
    promo_query = """
        SELECT p.kode, p.tglakhirberlaku, d.potongan, d.mintrpemesanan
        FROM promo p
        JOIN diskon d ON p.kode = d.kode
    """
    promos = execute_query(promo_query)
    promo_list = [
        {
            'kode': row[0],
            'tanggal_akhir_berlaku': row[1],
            'potongan': f"{Decimal(row[2]) * 100:.2f}",
            'minimum_transaksi': row[3],
        }
        for row in promos
    ]

    # Fetch available payment methods
    payment_method_query = """
        SELECT id, nama
        FROM metode_bayar
    """
    payment_methods = execute_query(payment_method_query)
    payment_method_list = [
        {
            'id': row[0],
            'nama': row[1]
        }
        for row in payment_methods
    ]

    context = {
        'vouchers': voucher_list,
        'promos': promo_list,
        'payment_methods': payment_method_list
    }

    return render(request, 'discount.html', context)


@custom_login_required
@require_POST
def purchase_voucher(request):
    """
    View to handle voucher purchase.
    Expects 'voucher_code' and 'payment_method_id' in POST data.
    Returns JSON response indicating success or failure.
    """
    logger.debug("purchase_voucher view called.")

    # Retrieve user from session
    user = request.session.get('user')
    if not user:
        logger.error("User not found in session.")
        return JsonResponse({'status': 'error', 'message': 'Anda harus login untuk membeli voucher.'}, status=403)

    user_id = request.session['user']['Id']  # Assuming 'id' is in lowercase in session data
    if not user_id:
        logger.error("User ID not found in session data.")
        return JsonResponse({'status': 'error', 'message': 'Data pengguna tidak valid.'}, status=400)

    voucher_code = request.POST.get('voucher_code')
    payment_method_id = request.POST.get('payment_method_id')

    logger.debug(f"Voucher purchase details - voucher_code: {voucher_code}, payment_method_id: {payment_method_id}")

    if not voucher_code or not payment_method_id:
        logger.warning("Invalid request parameters.")
        return JsonResponse({'status': 'error', 'message': 'Parameter permintaan tidak valid.'}, status=400)



    # Fetch voucher details
    voucher_query = """
        SELECT v.jmlhariberlaku, v.kuotapenggunaan, v.harga, d.potongan, d.mintrpemesanan
        FROM voucher v
        JOIN diskon d ON v.kode = d.kode
        WHERE v.kode = %s
    """
    voucher = execute_query(voucher_query, (voucher_code,), fetchone=True)
    if not voucher:
        logger.error(f"Voucher not found: {voucher_code}")
        return JsonResponse({'status': 'error', 'message': 'Voucher tidak ditemukan.'}, status=404)

    jml_hari_berlaku, kuota_penggunaan, harga_voucher, potongan, min_tr_pemesanan = voucher
    logger.debug(f"Fetched voucher details - JmlHariBerlaku: {jml_hari_berlaku}, KuotaPenggunaan: {kuota_penggunaan}, Harga: {harga_voucher}")

    # Check if user exists in pelanggan
    pelanggan_query = """
        SELECT u.id, u.saldomypay
        FROM pelanggan p
        JOIN "USER" u ON p.id = u.id
        WHERE p.id = %s
    """
    pelanggan = execute_query(pelanggan_query, (user_id,), fetchone=True)
    if not pelanggan:
        logger.error(f"User not found as Pelanggan: {user_id}")
        return JsonResponse({'status': 'error', 'message': 'Pengguna tidak ditemukan sebagai Pelanggan.'}, status=404)

    pelanggan_id, saldo_mypay = pelanggan
    logger.debug(f"Pelanggan details - Id: {pelanggan_id}, SaldoMyPay: {saldo_mypay}")

    # Fetch selected payment method name
    payment_method_query = """
        SELECT nama
        FROM metode_bayar
        WHERE id = %s
    """
    payment_method = execute_query(payment_method_query, (payment_method_id,), fetchone=True)
    if not payment_method:
        logger.error(f"Payment method not found: {payment_method_id}")
        return JsonResponse({'status': 'error', 'message': 'Metode pembayaran tidak ditemukan.'}, status=404)

    payment_method_name = payment_method[0]
    logger.debug(f"Selected payment method: {payment_method_name}")

    # Initialize transaction variables
    transaction_success = False
    failure_message = ''

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if payment_method_name.lower() == 'mypay':
                # Check if user has sufficient balance
                if saldo_mypay >= harga_voucher:
                    new_saldo = saldo_mypay - Decimal(harga_voucher)
                    logger.debug(f"Deducting SaldoMyPay: {saldo_mypay} - {harga_voucher} = {new_saldo}")

                    # Update SaldoMyPay
                    update_saldo_query = """
                        UPDATE "USER"
                        SET saldomypay = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_saldo_query, (new_saldo, user_id))
                    logger.debug("SaldoMyPay updated successfully.")

                    # Insert into tr_pembelian_voucher
                    tgl_awal = datetime.now().date()
                    tgl_akhir = tgl_awal + timedelta(days=jml_hari_berlaku)
                    insert_voucher_query = """
                        INSERT INTO tr_pembelian_voucher (id, tglawal, tglakhir, telahdigunakan, idpelanggan, idvoucher, idmetodebayar)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_voucher_query, (
                        str(uuid.uuid4()),
                        tgl_awal,
                        tgl_akhir,
                        0,  # TelahDigunakan
                        pelanggan_id,
                        voucher_code,
                        payment_method_id
                    ))
                    logger.debug("TR_PEMBELIAN_VOUCHER inserted successfully.")
                    transaction_success = True
                else:
                    logger.warning(f"Insufficient SaldoMyPay: {saldo_mypay} < {harga_voucher}")
                    failure_message = 'Saldo MyPay Anda tidak cukup untuk membeli voucher ini.'
            else:
                # For other payment methods, proceed without balance check
                logger.debug("Processing voucher purchase with non-MyPay payment method.")

                tgl_awal = datetime.now().date()
                tgl_akhir = tgl_awal + timedelta(days=jml_hari_berlaku)
                insert_voucher_query = """
                    INSERT INTO tr_pembelian_voucher (id, tglawal, tglakhir, telahdigunakan, idpelanggan, idvoucher, idmetodebayar)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_voucher_query, (
                    str(uuid.uuid4()),
                    tgl_awal,
                    tgl_akhir,
                    0,  # TelahDigunakan
                    pelanggan_id,
                    voucher_code,
                    payment_method_id
                ))
                logger.debug("TR_PEMBELIAN_VOUCHER inserted successfully with non-MyPay method.")
                transaction_success = True

            if transaction_success:
                conn.commit()
                logger.info(f"Voucher purchased successfully by user {user_id}: {voucher_code}")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Voucher berhasil dibeli.',
                    'kode': voucher_code,
                    'hari_berlaku': jml_hari_berlaku,
                    'kuota': kuota_penggunaan
                })
            else:
                conn.rollback()
                logger.warning(f"Voucher purchase failed for user {user_id}: {failure_message}")
                return JsonResponse({'status': 'failure', 'message': failure_message}, status=400)

    except Exception as e:
        conn.rollback()
        logger.exception(f"Error processing voucher purchase for user {user_id}: {e}")
        return JsonResponse({'status': 'error', 'message': 'Terjadi kesalahan saat memproses pembelian.'}, status=500)
    finally:
        conn.close()
        logger.debug("Database connection closed in purchase_voucher view.")
