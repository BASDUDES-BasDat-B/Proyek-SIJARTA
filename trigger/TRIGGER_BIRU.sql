CREATE OR REPLACE FUNCTION validate_voucher()
RETURNS TRIGGER AS $$
DECLARE
    v_KuotaPenggunaan INT;
    v_JmlHariBerlaku INT;
    v_TelahDigunakan INT;
    v_TglAwal DATE;
    v_TglAkhir DATE;
    current_date DATE := CURRENT_DATE;
BEGIN
    IF NEW.IdVoucher IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT KuotaPenggunaan, JmlHariBerlaku
    INTO v_KuotaPenggunaan, v_JmlHariBerlaku
    FROM VOUCHER
    WHERE Kode = NEW.IdVoucher;

    SELECT TelahDigunakan, TglAwal
    INTO v_TelahDigunakan, v_TglAwal
    FROM TR_PEMBELIAN_VOUCHER
    WHERE IdVoucher = NEW.IdVoucher;

    v_TglAkhir := v_TglAwal + v_JmlHariBerlaku;

    IF v_TelahDigunakan >= v_KuotaPenggunaan THEN
        RAISE EXCEPTION 'Voucher % has reached its usage limit.', NEW.IdVoucher;
    END IF;

    IF current_date > v_TglAkhir THEN
        RAISE EXCEPTION 'Voucher % has expired.', NEW.IdVoucher;
    END IF;

    -- asumsi TelahDigunakan adlaah variable counter
    UPDATE TR_PEMBELIAN_VOUCHER
    SET TelahDigunakan = TelahDigunakan + 1
    WHERE IdVoucher = NEW.IdVoucher;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_voucher_on_service
BEFORE INSERT OR UPDATE ON TR_PEMESANAN_JASA
FOR EACH ROW
EXECUTE FUNCTION validate_voucher_on_service();

