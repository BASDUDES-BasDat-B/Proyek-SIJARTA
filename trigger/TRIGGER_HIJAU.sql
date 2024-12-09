-- fungsi trigger_pengembalian_saldo
CREATE OR REPLACE FUNCTION trigger_pengembalian_saldo()
RETURNS TRIGGER AS $$
DECLARE
    v_id_pelanggan UUID;
    v_nominal DECIMAL;
    v_status_dibatalkan UUID;
    v_status_mencari UUID;
    v_latest_status UUID;
BEGIN
    -- Ambil ID status 'Dibatalkan'
    SELECT Id INTO v_status_dibatalkan
    FROM STATUS_PEMESANAN
    WHERE Status = 'Dibatalkan'
    LIMIT 1;

    -- Ambil ID status 'Mencari Pekerja Terdekat'
    SELECT Id INTO v_status_mencari
    FROM STATUS_PEMESANAN
    WHERE Status = 'Mencari Pekerja Terdekat'
    LIMIT 1;

    -- Periksa apakah NEW.IdStatus adalah 'Dibatalkan'
    IF NEW.IdStatus = v_status_dibatalkan THEN
        -- Ambil status terakhir sebelum insert
        SELECT IdStatus INTO v_latest_status
        FROM TR_PEMESANAN_STATUS
        WHERE IdTrPemesanan = NEW.IdTrPemesanan
          AND TglWaktu < NEW.TglWaktu
        ORDER BY TglWaktu DESC
        LIMIT 1;

        -- Jika status terakhir adalah 'Mencari Pekerja Terdekat'
        IF v_latest_status = v_status_mencari THEN
            -- Ambil informasi terkait pesanan
            SELECT IdPelanggan, TotalBiaya
            INTO v_id_pelanggan, v_nominal
            FROM TR_PEMESANAN_JASA
            WHERE Id = NEW.IdTrPemesanan;

            -- Kembalikan saldo ke pelanggan
            UPDATE "USER"
            SET SaldoMyPay = SaldoMyPay + v_nominal
            WHERE Id = v_id_pelanggan;
        ELSE
            RAISE EXCEPTION 'Pesanan tidak dapat dibatalkan karena tidak dalam status "Mencari Pekerja Terdekat".';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Membuat ulang trigger tanpa kondisi WHEN
CREATE TRIGGER after_status_dibatalkan
AFTER INSERT ON TR_PEMESANAN_STATUS
FOR EACH ROW
EXECUTE FUNCTION trigger_pengembalian_saldo();