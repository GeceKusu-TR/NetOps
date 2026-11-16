---
name: Hesap_Makinesi
description: Karmaşık matematiksel işlemleri, denklemleri ve sayısal hesaplamaları güvenli yerel hesaplayıcıya yönlendirir.
---

# Hesap Makinesi

Kullanıcı karmaşık bir matematik işlemi, denklem veya hesaplama istediğinde
bu skill’i seç. İşlemi yalnızca matematik sembolleri, sayılar, parantezler ve
izin verilen fonksiyonlarla sınırlandır; Python kodu veya serbest `eval`
çalıştırma.

Çalıştırma çağrısı tam olarak şu biçimde üretilir:

`[CALL_MATH: "yapilacak_islem"]`

Sonucu uydurma. İşlem geçersiz veya belirsizse çağrı üretmek yerine
kullanıcıdan işlemi netleştirmesini iste.
