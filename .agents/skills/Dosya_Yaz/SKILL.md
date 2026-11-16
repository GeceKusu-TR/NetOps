---
name: Dosya_Yaz
description: Kullanıcının açıkça istediği notu kaydetme, günlük tutma, dosyaya yazma veya dosya oluşturma işlemlerini güvenli onay akışıyla hazırlar.
---

# Dosya Yaz

Kullanıcı açıkça bir notu kaydetmek, günlük tutmak veya bilgisayarda dosya
oluşturmak istediğinde bu skill’i seç.

Çalıştırma çağrısı tam olarak şu biçimde üretilir:

`[CALL_WRITE_FILE: "dosya_adi.txt", icerik: "yazılacak metin"]`

Dosya yolunu çalışma alanı içinde tut. Kullanıcı açıkça istemeden mevcut
dosyanın üzerine yazma, dosya silme veya hassas veriyi kalıcılaştırma. İşlem
uygulanmadan önce dosya adı ve içeriği kullanıcıya görünür onay akışından
geçmelidir.
