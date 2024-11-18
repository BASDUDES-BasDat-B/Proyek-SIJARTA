--Function untuk mengembalikan saldo
CREATE OR REPLACE FUNCTION trigger_pengembalian_saldo()
RETURNS TRIGGER AS $$
DECLARE
    v_id_pelanggan UUID;
    v_nominal DECIMAL;
BEGIN
    -- Ambil informasi terkait pesanan
    SELECT IdPelanggan, TotalBiaya
    INTO v_id_pelanggan, v_nominal
    FROM TR_PEMESANAN_JASA
    WHERE Id = NEW.IdTrPemesanan;

    -- Pastikan pesanan dalam status "Mencari Pekerja Terdekat"
    IF EXISTS (
        SELECT 1
        FROM TR_PEMESANAN_STATUS tps
        JOIN STATUS_PEMESANAN sp ON tps.IdStatus = sp.Id
        WHERE tps.IdTrPemesanan = NEW.IdTrPemesanan
          AND sp.Status = 'Mencari Pekerja Terdekat'
    ) THEN
        -- Kembalikan saldo ke pelanggan
        UPDATE "USER"
        SET SaldoMyPay = SaldoMyPay + v_nominal
        WHERE Id = v_id_pelanggan;
    ELSE
        RAISE EXCEPTION 'Pesanan tidak dapat dibatalkan karena tidak dalam status "Mencari Pekerja Terdekat".';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

--Trigger untuk memanggil function diatas
CREATE TRIGGER after_status_dibatalkan
AFTER INSERT ON TR_PEMESANAN_STATUS
FOR EACH ROW
WHEN (NEW.IdStatus = (SELECT Id FROM STATUS_PEMESANAN WHERE Status = 'Dibatalkan'))
EXECUTE FUNCTION trigger_pengembalian_saldo();
