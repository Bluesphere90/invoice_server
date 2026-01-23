-- Migration: Add missing columns to invoices table
-- Run this if the invoices table was created with a simpler schema

-- Add columns from the original detailed schema
DO $$
BEGIN
    -- Core fields that might be missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='cqt') THEN
        ALTER TABLE invoices ADD COLUMN cqt TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='cttkhac') THEN
        ALTER TABLE invoices ADD COLUMN cttkhac TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='dvtte') THEN
        ALTER TABLE invoices ADD COLUMN dvtte TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdon') THEN
        ALTER TABLE invoices ADD COLUMN hdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hsgcma') THEN
        ALTER TABLE invoices ADD COLUMN hsgcma TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hsgoc') THEN
        ALTER TABLE invoices ADD COLUMN hsgoc TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hthdon') THEN
        ALTER TABLE invoices ADD COLUMN hthdon INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='htttoan') THEN
        ALTER TABLE invoices ADD COLUMN htttoan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='idtbao') THEN
        ALTER TABLE invoices ADD COLUMN idtbao TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='khdon') THEN
        ALTER TABLE invoices ADD COLUMN khdon INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='khhdgoc') THEN
        ALTER TABLE invoices ADD COLUMN khhdgoc TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='khmshdgoc') THEN
        ALTER TABLE invoices ADD COLUMN khmshdgoc TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='lhdgoc') THEN
        ALTER TABLE invoices ADD COLUMN lhdgoc TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='mhdon') THEN
        ALTER TABLE invoices ADD COLUMN mhdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='mtdiep') THEN
        ALTER TABLE invoices ADD COLUMN mtdiep TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='mtdtchieu') THEN
        ALTER TABLE invoices ADD COLUMN mtdtchieu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbdchi') THEN
        ALTER TABLE invoices ADD COLUMN nbdchi TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='chma') THEN
        ALTER TABLE invoices ADD COLUMN chma TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='chten') THEN
        ALTER TABLE invoices ADD COLUMN chten TEXT;
    END IF;

    -- Nhiều cột khác...
    -- Thêm tất cả các cột còn thiếu

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbhdktngay') THEN
        ALTER TABLE invoices ADD COLUMN nbhdktngay TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbhdktso') THEN
        ALTER TABLE invoices ADD COLUMN nbhdktso TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbhdso') THEN
        ALTER TABLE invoices ADD COLUMN nbhdso TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nblddnbo') THEN
        ALTER TABLE invoices ADD COLUMN nblddnbo TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbptvchuyen') THEN
        ALTER TABLE invoices ADD COLUMN nbptvchuyen TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbstkhoan') THEN
        ALTER TABLE invoices ADD COLUMN nbstkhoan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbtnhang') THEN
        ALTER TABLE invoices ADD COLUMN nbtnhang TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbtnvchuyen') THEN
        ALTER TABLE invoices ADD COLUMN nbtnvchuyen TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbttkhac') THEN
        ALTER TABLE invoices ADD COLUMN nbttkhac TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ncma') THEN
        ALTER TABLE invoices ADD COLUMN ncma TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ncnhat') THEN
        ALTER TABLE invoices ADD COLUMN ncnhat TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ngcnhat') THEN
        ALTER TABLE invoices ADD COLUMN ngcnhat TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nky') THEN
        ALTER TABLE invoices ADD COLUMN nky TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmdchi') THEN
        ALTER TABLE invoices ADD COLUMN nmdchi TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmmst') THEN
        ALTER TABLE invoices ADD COLUMN nmmst TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmstkhoan') THEN
        ALTER TABLE invoices ADD COLUMN nmstkhoan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmtnhang') THEN
        ALTER TABLE invoices ADD COLUMN nmtnhang TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmtnmua') THEN
        ALTER TABLE invoices ADD COLUMN nmtnmua TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmttkhac') THEN
        ALTER TABLE invoices ADD COLUMN nmttkhac TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ntao') THEN
        ALTER TABLE invoices ADD COLUMN ntao TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ntnhan') THEN
        ALTER TABLE invoices ADD COLUMN ntnhan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='pban') THEN
        ALTER TABLE invoices ADD COLUMN pban TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ptgui') THEN
        ALTER TABLE invoices ADD COLUMN ptgui INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='shdgoc') THEN
        ALTER TABLE invoices ADD COLUMN shdgoc INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tchat') THEN
        ALTER TABLE invoices ADD COLUMN tchat INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tgia') THEN
        ALTER TABLE invoices ADD COLUMN tgia DOUBLE PRECISION;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tgtttbchu') THEN
        ALTER TABLE invoices ADD COLUMN tgtttbchu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tgtttbso') THEN
        ALTER TABLE invoices ADD COLUMN tgtttbso DOUBLE PRECISION;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='thdon') THEN
        ALTER TABLE invoices ADD COLUMN thdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='thlap') THEN
        ALTER TABLE invoices ADD COLUMN thlap TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='thttlphi') THEN
        ALTER TABLE invoices ADD COLUMN thttlphi TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='thttltsuat') THEN
        ALTER TABLE invoices ADD COLUMN thttltsuat TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tlhdon') THEN
        ALTER TABLE invoices ADD COLUMN tlhdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ttcktmai') THEN
        ALTER TABLE invoices ADD COLUMN ttcktmai DOUBLE PRECISION;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ttkhac') THEN
        ALTER TABLE invoices ADD COLUMN ttkhac TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tttbao') THEN
        ALTER TABLE invoices ADD COLUMN tttbao TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ttttkhac') THEN
        ALTER TABLE invoices ADD COLUMN ttttkhac TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tvandnkntt') THEN
        ALTER TABLE invoices ADD COLUMN tvandnkntt TEXT;
    END IF;

    -- Phần còn lại từ schema
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='mhso') THEN
        ALTER TABLE invoices ADD COLUMN mhso TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ladhddt') THEN
        ALTER TABLE invoices ADD COLUMN ladhddt TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='mkhang') THEN
        ALTER TABLE invoices ADD COLUMN mkhang TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbsdthoai') THEN
        ALTER TABLE invoices ADD COLUMN nbsdthoai TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbdctdtu') THEN
        ALTER TABLE invoices ADD COLUMN nbdctdtu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbfax') THEN
        ALTER TABLE invoices ADD COLUMN nbfax TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbwebsite') THEN
        ALTER TABLE invoices ADD COLUMN nbwebsite TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbcks') THEN
        ALTER TABLE invoices ADD COLUMN nbcks TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmsdthoai') THEN
        ALTER TABLE invoices ADD COLUMN nmsdthoai TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmdctdtu') THEN
        ALTER TABLE invoices ADD COLUMN nmdctdtu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmcmnd') THEN
        ALTER TABLE invoices ADD COLUMN nmcmnd TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmcks') THEN
        ALTER TABLE invoices ADD COLUMN nmcks TEXT;
    END IF;

    -- Thêm các trường bổ sung
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='bhphap') THEN
        ALTER TABLE invoices ADD COLUMN bhphap TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hddunlap') THEN
        ALTER TABLE invoices ADD COLUMN hddunlap TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='gchdgoc') THEN
        ALTER TABLE invoices ADD COLUMN gchdgoc TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tbhgtngay') THEN
        ALTER TABLE invoices ADD COLUMN tbhgtngay TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='bhpldo') THEN
        ALTER TABLE invoices ADD COLUMN bhpldo TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='bhpcbo') THEN
        ALTER TABLE invoices ADD COLUMN bhpcbo TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='bhpngay') THEN
        ALTER TABLE invoices ADD COLUMN bhpngay TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tdlhdgoc') THEN
        ALTER TABLE invoices ADD COLUMN tdlhdgoc TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tgtphi') THEN
        ALTER TABLE invoices ADD COLUMN tgtphi DOUBLE PRECISION;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='unhiem') THEN
        ALTER TABLE invoices ADD COLUMN unhiem TEXT;
    END IF;

    -- Các trường còn lại
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='mstdvnunlhdon') THEN
        ALTER TABLE invoices ADD COLUMN mstdvnunlhdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tdvnunlhdon') THEN
        ALTER TABLE invoices ADD COLUMN tdvnunlhdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbmdvqhnsach') THEN
        ALTER TABLE invoices ADD COLUMN nbmdvqhnsach TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbsqdinh') THEN
        ALTER TABLE invoices ADD COLUMN nbsqdinh TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbncqdinh') THEN
        ALTER TABLE invoices ADD COLUMN nbncqdinh TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbcqcqdinh') THEN
        ALTER TABLE invoices ADD COLUMN nbcqcqdinh TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbhtban') THEN
        ALTER TABLE invoices ADD COLUMN nbhtban TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmmdvqhnsach') THEN
        ALTER TABLE invoices ADD COLUMN nmmdvqhnsach TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmddvchden') THEN
        ALTER TABLE invoices ADD COLUMN nmddvchden TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmtgvchdtu') THEN
        ALTER TABLE invoices ADD COLUMN nmtgvchdtu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmtgvchdden') THEN
        ALTER TABLE invoices ADD COLUMN nmtgvchdden TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nbtnban') THEN
        ALTER TABLE invoices ADD COLUMN nbtnban TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='dcdvnunlhdon') THEN
        ALTER TABLE invoices ADD COLUMN dcdvnunlhdon TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='dksbke') THEN
        ALTER TABLE invoices ADD COLUMN dksbke TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='dknlbke') THEN
        ALTER TABLE invoices ADD COLUMN dknlbke TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='thtttoan') THEN
        ALTER TABLE invoices ADD COLUMN thtttoan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='msttcgp') THEN
        ALTER TABLE invoices ADD COLUMN msttcgp TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='cqtcks') THEN
        ALTER TABLE invoices ADD COLUMN cqtcks TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='gchu') THEN
        ALTER TABLE invoices ADD COLUMN gchu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='kqcht') THEN
        ALTER TABLE invoices ADD COLUMN kqcht TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdntgia') THEN
        ALTER TABLE invoices ADD COLUMN hdntgia TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tgtkcthue') THEN
        ALTER TABLE invoices ADD COLUMN tgtkcthue TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tgtkhac') THEN
        ALTER TABLE invoices ADD COLUMN tgtkhac TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmshchieu') THEN
        ALTER TABLE invoices ADD COLUMN nmshchieu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmnchchieu') THEN
        ALTER TABLE invoices ADD COLUMN nmnchchieu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmnhhhchieu') THEN
        ALTER TABLE invoices ADD COLUMN nmnhhhchieu TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='nmqtich') THEN
        ALTER TABLE invoices ADD COLUMN nmqtich TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ktkhthue') THEN
        ALTER TABLE invoices ADD COLUMN ktkhthue TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='qrcode') THEN
        ALTER TABLE invoices ADD COLUMN qrcode TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ttmstten') THEN
        ALTER TABLE invoices ADD COLUMN ttmstten TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='ladhddtten') THEN
        ALTER TABLE invoices ADD COLUMN ladhddtten TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdxkhau') THEN
        ALTER TABLE invoices ADD COLUMN hdxkhau TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdxkptquan') THEN
        ALTER TABLE invoices ADD COLUMN hdxkptquan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdgktkhthue') THEN
        ALTER TABLE invoices ADD COLUMN hdgktkhthue TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdonLquans') THEN
        ALTER TABLE invoices ADD COLUMN "hdonLquans" TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='tthdclquan') THEN
        ALTER TABLE invoices ADD COLUMN tthdclquan TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='pdndungs') THEN
        ALTER TABLE invoices ADD COLUMN pdndungs TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdtbssrses') THEN
        ALTER TABLE invoices ADD COLUMN hdtbssrses TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='hdTrung') THEN
        ALTER TABLE invoices ADD COLUMN "hdTrung" TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='invoices' AND column_name='isHDTrung') THEN
        ALTER TABLE invoices ADD COLUMN "isHDTrung" TEXT;
    END IF;

END $$;
