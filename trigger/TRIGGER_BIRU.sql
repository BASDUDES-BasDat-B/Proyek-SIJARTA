CREATE OR REPLACE FUNCTION validate_voucher_usage_and_expiry()
RETURNS TRIGGER AS $$
DECLARE
    v_voucher RECORD;
    v_pembelian RECORD;
BEGIN
    -- If no voucher is used, just return
    IF NEW.IdDiskon IS NULL THEN
        RETURN NEW;
    END IF;

    -- Check if IdDiskon corresponds to a valid voucher
    SELECT * INTO v_voucher
    FROM VOUCHER
    WHERE Kode = NEW.IdDiskon;

    IF NOT FOUND THEN
        -- Not a valid voucher code
        RAISE EXCEPTION 'Invalid voucher code "%"', NEW.IdDiskon;
    END IF;

    -- Find a corresponding purchased voucher for the customer that is currently valid
    SELECT * INTO v_pembelian
    FROM TR_PEMBELIAN_VOUCHER
    WHERE IdPelanggan = NEW.IdPelanggan
      AND IdVoucher = NEW.IdDiskon
      AND CURRENT_DATE <= TglAkhir
      AND (v_voucher.KuotaPenggunaan IS NULL OR TelahDigunakan < v_voucher.KuotaPenggunaan)
    ORDER BY TglAwal DESC
    LIMIT 1;

    IF NOT FOUND THEN
        -- Either voucher not purchased by this customer,
        -- expired, or usage limit exceeded
        RAISE EXCEPTION 'The voucher "%" is either not purchased, expired, or has exceeded its usage limit.', NEW.IdDiskon;
    END IF;

    -- If valid, increment the usage count
    UPDATE TR_PEMBELIAN_VOUCHER
    SET TelahDigunakan = TelahDigunakan + 1
    WHERE Id = v_pembelian.Id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_validate_voucher_usage_and_expiry
BEFORE INSERT OR UPDATE ON TR_PEMESANAN_JASA
FOR EACH ROW
EXECUTE FUNCTION validate_voucher_usage_and_expiry();
