-- Trigger Nomor 4 (Merah)
-- Membuat Stored Procedure yang akan dijalankan ketika ada trigger
CREATE OR REPLACE FUNCTION proses_pembayaran_pekerja() 
RETURNS TRIGGER AS $$
DECLARE
    v_total_biaya DECIMAL;
    v_id_pekerja UUID;
    v_kategori_tr UUID;
BEGIN
    IF NEW.status = 'Pesanan selesai' THEN  -- Lanjutkan jika status adalah "Pesanan selesai"
    
        -- Select total biaya dan id pekerja dari TR_PEMESANAN_JASA dan masukkan ke variabel total biaya dan id pekerja
        SELECT TR_J.TotalBiaya, TR_J.IdPekerja INTO v_total_biaya, v_id_pekerja
        FROM STATUS_PESANAN AS S
        LEFT JOIN TR_PEMESANAN_STATUS AS TR_S
            ON S.Id = TR_S.IdStatus
        LEFT JOIN TR_PEMESANAN_JASA AS TR_J
            ON TR_S.IdTrPemesanan = TR_J.Id
        WHERE S.Id = NEW.Id;

        -- Select id kategori transaksi dari KATEGORI_TR_MYPAY dan masukkan ke variabel kategori transaksi
        SELECT Id INTO v_kategori_tr
        FROM KATEGORI_TR_MYPAY
        WHERE Nama = 'menerima honor transaksi jasa';

        -- Masukkan transaksi ke TR_MYPAY
        INSERT INTO TR_MYPAY (Id, UserId, Tgl, Nominal, KategoriId)
        VALUES (gen_random_uuid(), v_id_pekerja, CURRENT_DATE, v_total_biaya, v_kategori_tr);

        -- Update saldo MyPay pekerja
        UPDATE USER
        SET SaldoMyPay = SaldoMyPay + v_total_biaya
        WHERE Id = v_id_pekerja;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Membuat trigger ketika adanya update status pesanan dengan mengeksekusi Stored Procedure
CREATE TRIGGER trg_status_update
AFTER INSERT ON STATUS_PESANAN
FOR EACH ROW
EXECUTE FUNCTION proses_pembayaran_pekerja();
