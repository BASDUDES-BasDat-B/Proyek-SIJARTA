-- Trigger Nomor 4 (Merah)
-- Membuat Stored Procedure yang akan dijalankan ketika ada trigger
CREATE OR REPLACE FUNCTION proses_pembayaran_pekerja() 
RETURNS TRIGGER AS $$
DECLARE
    v_total_biaya DECIMAL;
    v_id_pekerja UUID;
    v_kategori_tr UUID;
    status_name VARCHAR;
BEGIN
    -- Ambil nama status dari tabel status_pemesanan berdasarkan idstatus baru
    SELECT status INTO status_name 
    FROM status_pemesanan 
    WHERE id = NEW.idstatus;

    RAISE NOTICE 'Status name: %', status_name;

    -- Jika status adalah 'Pemesanan Selesai', lanjutkan proses pembayaran
    IF status_name = 'Pemesanan Selesai' THEN
        -- Ambil total biaya dan id pekerja dari tr_pemesanan_jasa berdasarkan idtrpemesanan
        SELECT tj.totalbiaya, tj.idpekerja INTO v_total_biaya, v_id_pekerja
        FROM tr_pemesanan_jasa tj
        WHERE tj.id = NEW.idtrpemesanan;

        RAISE NOTICE 'Total Biaya: %, ID Pekerja: %', v_total_biaya, v_id_pekerja;

        -- Ambil id kategori transaksi dari kategori_tr_mypay
        SELECT id INTO v_kategori_tr
        FROM kategori_tr_mypay
        WHERE nama = 'Menerima Honor';

        RAISE NOTICE 'Kategori Transaksi ID: %', v_kategori_tr;

        -- Masukkan transaksi ke tr_mypay
        INSERT INTO tr_mypay (id, userid, tgl, nominal, kategoriid)
        VALUES (gen_random_uuid(), v_id_pekerja, CURRENT_DATE, v_total_biaya, v_kategori_tr);

        RAISE NOTICE 'Inserted transaksi ke tr_mypay';

        -- Update saldo MyPay pekerja
        UPDATE "USER"
        SET saldomypay = saldomypay + v_total_biaya
        WHERE id = v_id_pekerja;

        RAISE NOTICE 'Updated SaldoMyPay untuk pekerja_id: %', v_id_pekerja;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trg_status_update
AFTER INSERT ON tr_pemesanan_status
FOR EACH ROW
EXECUTE FUNCTION proses_pembayaran_pekerja();
