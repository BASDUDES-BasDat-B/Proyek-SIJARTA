-- Trigger untuk mengecek no hp pengguna
CREATE OR REPLACE FUNCTION check_user_phone() 
RETURNS TRIGGER AS
$$
BEGIN
IF (EXISTS (SELECT * FROM USER WHERE NoHP = NEW.NoHP)) THEN
RAISE EXCEPTION 'Nomor HP % sudah terdaftar.', NEW.NoHP;
END IF;
RETURN NEW;
END;
$$
LANGUAGE plpgsql;

-- Membuat trigger untuk memanggil function sebelum insert data ke tabel USER
CREATE TRIGGER check_user_phone
BEFORE INSERT OR UPDATE ON USER
FOR EACH ROW
EXECUTE FUNCTION check_user_phone();

-- Trigger untuk mengecek no bank dan rekening pada saat insert data ke tabel PEKERJA
CREATE OR REPLACE FUNCTION check_worker_bank() 
RETURNS TRIGGER AS
$$
BEGIN
IF (EXISTS (SELECT * FROM PEKERJA WHERE NamaBank = NEW.NamaBank AND NomorRekening = NEW.NomorRekening)) THEN
RAISE EXCEPTION 'Nomor Rekening % dari Bank % sudah terdaftar.', NEW.NomorRekening, NEW.NamaBank;
END IF;
RETURN NEW;
END;
$$
LANGUAGE plpgsql;

-- Membuat trigger untuk memanggil function sebelum insert data ke tabel PEKERJA
CREATE TRIGGER check_worker_bank
BEFORE INSERT OR UPDATE ON PEKERJA
FOR EACH ROW
EXECUTE FUNCTION check_worker_bank();