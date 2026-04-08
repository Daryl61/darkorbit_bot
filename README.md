# DarkOrbit Kaynak Toplama Botu

Ekran görüntüsü yakalama ve bilgisayarlı görü (OpenCV) kullanarak DarkOrbit'te bonus box, cargo box ve palladium gibi kaynakları otomatik toplayan bot.

## Kurulum

```bash
cd darkorbit_bot
pip install -r requirements.txt
```

## Kullanım

### 1. Template Görselleri Hazırla

Botu çalıştırmadan önce, oyun içinden kutu görsellerini yakalamanız gerekir:

```bash
python -m src.template_capture
```

Bu araç ekranın bir bölgesini seçmenize ve template olarak kaydetmenize olanak tanır.

### 2. Ayarları Düzenle

`config/settings.json` dosyasını kendi ekran çözünürlüğünüze göre ayarlayın:
- `screen_region`: Oyun penceresinin ekrandaki konumu ve boyutu
- `safety.hp_bar_region`: HP barının ekrandaki konumu

### 3. Botu Başlat

```bash
python -m src.main
```

### Kısayol Tuşları

| Tuş | İşlev |
|-----|-------|
| F6  | Başlat / Durdur |
| F7  | Duraklat / Devam |

