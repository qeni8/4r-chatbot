from app.waste_lookup import answer, by_code


def test_bilinen_tehlikeli_kod():
    r = by_code("060101")
    assert r is not None
    assert r["tehlikeli"] is True
    assert set(r["tesisler"]) == {"Merkez", "Kapaklı"}


def test_kabul_cevabi_tanim_icerir():
    a = answer("06 01 01")
    assert "alıyoruz" in a
    assert "Sülfürik" in a  # tanım cevaba dahil edilmeli


def test_kabul_edilmeyen_kod():
    a = answer("20 03 01")
    assert "kabul edemiyoruz" in a


def test_bulunamayan_kod_devir():
    a = answer("99 99 99")
    assert "bulamadım" in a
    assert "282 652 30 90" in a  # insana devir iletişimi


def test_grup_listesi():
    a = answer("01 05")
    assert "01 05 04" in a and "01 05 06" in a


def test_kod_ve_miktar():
    # kod dışında sayı (miktar) olması yapısal cevabı bozmamalı
    a = answer("06 01 01 kodlu 5 ton atık alıyor musunuz")
    assert "06 01 01" in a and "alıyoruz" in a


def test_coklu_kod():
    a = answer("06 01 01 ve 20 03 01 alıyor musunuz")
    assert "06 01 01" in a and "20 03 01" in a


def test_telefon_kod_sanilmaz():
    # telefon numarası atık grubu olarak yorumlanmamalı (bölüm > 20)
    assert answer("0282 652 30 90") == ""
    assert answer("telefonum 0532 111 22 33") == ""
