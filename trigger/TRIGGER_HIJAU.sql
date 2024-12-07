-- Function untuk mengembalikan saldo
CREATE OR REPLACE FUNCTION trigger_pengembalian_saldo()
RETURNS TRIGGER AS $$
DECLARE
    v_id_pelanggan UUID;
    v_nominal DECIMAL;
BEGIN
    -- Ambil informasi terkait pesanan
    SELECT id_pelanggan, total_biaya
    INTO v_id_pelanggan, v_nominal
    FROM TR_PEMESANAN_JASA
    WHERE id = NEW.id_tr_pemesanan;

    -- Pastikan pesanan dalam status "Mencari Pekerja Terdekat"
    IF EXISTS (
        SELECT 1
        FROM TR_PEMESANAN_STATUS tps
        JOIN STATUS_PEMESANAN sp ON tps.id_status = sp.id
        WHERE tps.id_tr_pemesanan = NEW.id_tr_pemesanan
          AND sp.status = 'Mencari Pekerja Terdekat'
    ) THEN
        -- Kembalikan saldo ke pelanggan
        UPDATE "USER"
        SET saldo_mypay = saldo_mypay + v_nominal
        WHERE id = v_id_pelanggan;
    ELSE
        RAISE EXCEPTION 'Pesanan tidak dapat dibatalkan karena tidak dalam status "Mencari Pekerja Terdekat".';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger untuk memanggil function di atas
CREATE TRIGGER after_status_dibatalkan
AFTER INSERT ON TR_PEMESANAN_STATUS
FOR EACH ROW
WHEN (NEW.id_status = (SELECT id FROM STATUS_PEMESANAN WHERE status = 'Dibatalkan'))
EXECUTE FUNCTION trigger_pengembalian_saldo();
