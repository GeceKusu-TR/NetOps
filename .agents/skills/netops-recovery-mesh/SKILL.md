---
name: netops-recovery-mesh
description: NetOps sistem hatalarını gözlemleyip risk sınıflandırması, yedek, doğrulama ve geri alma planı çıkarır.
---

# NetOps Recovery Mesh

Bu skill beş parçalı çalışır:

1. Gözlemci: log ve sağlık verilerini yalnızca okur.
2. Risk sınıflandırıcı: kritik, hata ve bilgi seviyelerini ayırır.
3. Geri dönüş koruması: değişiklikten önce doğrulanabilir yedek ister.
4. Doğrulayıcı: onarım sonrası test ve hata sayısını karşılaştırır.
5. Geri alma bekçisi: doğrulama başarısızsa onaylı yedeğe dönüş önerir.

Varsayılan mod `review` modudur. Dosya silme, rastgele shell komutu,
gizli değişiklik veya yönetici yetkisi kullanma yoktur. Onarım adımı ancak
kullanıcı açıkça onayladıktan, yedek doğrulandıktan ve güvenli kapsam kontrolü
geçtikten sonra mevcut NetOps operasyon izinleri üzerinden çalıştırılabilir.
