import psycopg2
from psycopg2 import sql
from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import uuid
from datetime import datetime, timedelta
from utils.db_connection import get_db_connection
import uuid  # Ensure uuid is imported

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
    user_id = request.user.id  # Assuming you have a custom user model linked to the "USER" table
    
    # Fetch vouchers
    voucher_query = """
        SELECT v.Kode, v.JmlHariBerlaku, v.KuotaPenggunaan, v.Harga, d.Potongan, d.MinTrPemesanan
        FROM VOUCHER v
        JOIN DISKON d ON v.Kode = d.Kode
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
        SELECT p.Kode, p.TglAkhirBerlaku, d.Potongan, d.MinTrPemesanan
        FROM PROMO p
        JOIN DISKON d ON p.Kode = d.Kode
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
        SELECT Id, Nama
        FROM METODE_BAYAR
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



@login_required
@require_POST
def purchase_voucher(request):
    """
    View to handle voucher purchase.
    Expects 'voucher_code' and 'payment_method_id' in POST data.
    Returns JSON response indicating success or failure.
    """
    user_id = request.user.id  # Ensure the user is authenticated
    voucher_code = request.POST.get('voucher_code')
    payment_method_id = request.POST.get('payment_method_id')

    if not voucher_code or not payment_method_id:
        return JsonResponse({'status': 'error', 'message': 'Invalid request parameters.'}, status=400)

    try:
        # Fetch voucher details
        voucher_query = """
            SELECT v.JmlHariBerlaku, v.KuotaPenggunaan, v.Harga, d.Potongan, d.MinTrPemesanan
            FROM VOUCHER v
            JOIN DISKON d ON v.Kode = d.Kode
            WHERE v.Kode = %s
        """
        voucher = execute_query(voucher_query, (voucher_code,), fetchone=True)
        if not voucher:
            return JsonResponse({'status': 'error', 'message': 'Voucher not found.'}, status=404)

        jml_hari_berlaku, kuota_penggunaan, harga_voucher, potongan, min_tr_pemesanan = voucher

        # Check if user exists in PELANGGAN
        pelanggan_query = """
            SELECT Id, SaldoMyPay
            FROM PELANGGAN
            WHERE Id = %s
        """
        pelanggan = execute_query(pelanggan_query, (user_id,), fetchone=True)
        if not pelanggan:
            return JsonResponse({'status': 'error', 'message': 'User not found as Pelanggan.'}, status=404)

        pelanggan_id, saldo_mypay = pelanggan

        # Fetch selected payment method name
        payment_method_query = """
            SELECT Nama
            FROM METODE_BAYAR
            WHERE Id = %s
        """
        payment_method = execute_query(payment_method_query, (payment_method_id,), fetchone=True)
        if not payment_method:
            return JsonResponse({'status': 'error', 'message': 'Payment method not found.'}, status=404)

        payment_method_name = payment_method[0]  # Correctly fetch the first element

        # Initialize variables for transaction
        transaction_success = False
        failure_message = ''

        if payment_method_name == 'MyPay':
            # Check if user has sufficient balance
            if saldo_mypay >= harga_voucher:
                # Deduct saldo
                new_saldo = saldo_mypay - Decimal(harga_voucher)
                update_saldo_query = """
                    UPDATE "USER"
                    SET SaldoMyPay = %s
                    WHERE Id = %s
                """
                execute_query(update_saldo_query, (new_saldo, user_id))

                # Insert into TR_PEMBELIAN_VOUCHER
                tgl_awal = datetime.now().date()
                tgl_akhir = tgl_awal + timedelta(days=jml_hari_berlaku)
                insert_voucher_query = """
                    INSERT INTO TR_PEMBELIAN_VOUCHER (Id, TglAwal, TglAkhir, TelahDigunakan, IdPelanggan, IdVoucher, IdMetodeBayar)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                execute_query(insert_voucher_query, (
                    str(uuid.uuid4()),
                    tgl_awal,
                    tgl_akhir,
                    0,  # TelahDigunakan
                    pelanggan_id,
                    voucher_code,
                    payment_method_id
                ))

                transaction_success = True
            else:
                # Insufficient balance
                failure_message = 'Saldo MyPay Anda tidak cukup untuk melakukan pembelian voucher ini.'
        else:
            # For other payment methods, proceed without balance check
            tgl_awal = datetime.now().date()
            tgl_akhir = tgl_awal + timedelta(days=jml_hari_berlaku)
            insert_voucher_query = """
                INSERT INTO TR_PEMBELIAN_VOUCHER (Id, TglAwal, TglAkhir, TelahDigunakan, IdPelanggan, IdVoucher, IdMetodeBayar)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            execute_query(insert_voucher_query, (
                str(uuid.uuid4()),
                tgl_awal,
                tgl_akhir,
                0,  # TelahDigunakan
                pelanggan_id,
                voucher_code,
                payment_method_id
            ))

            transaction_success = True

        if transaction_success:
            return JsonResponse({'status': 'success', 'message': 'Voucher berhasil dibeli.', 'kode': voucher_code, 'hari_berlaku': jml_hari_berlaku, 'kuota': kuota_penggunaan})
        else:
            return JsonResponse({'status': 'failure', 'message': failure_message}, status=400)

    except Exception as e:
        print(f"Error processing voucher purchase: {e}")
        return JsonResponse({'status': 'error', 'message': 'Terjadi kesalahan saat memproses pembelian.'}, status=500)
