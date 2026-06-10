# Gladiatus Automation Bot

Python + Selenium tabanlı bir Gladiatus otomasyon aracıdır. Oyuna giriş yapar, aktif sekmeyi yönetir ve seçili mekanikleri sırayla dener.

## Yetenekler
- Giriş yapma ve tarayıcı oturumunu yönetme
- Aktif oyun sekmesini bulma ve öne alma
- Expedition hazırsa ilgili aksiyonu tetikleme
- Dungeon hazırsa rastgele bir saldırı başlatma
- Circus Turma hazırsa en düşük seviyeli hedefi seçme
- HP yüzdesi eşik altındaysa can yenileme
- GUI üzerinden mekanikleri seçip çalıştırma
- Komut satırından çalıştırma ve parametrelerle override etme

## Gereksinimler
- Python 3.10+
- Google Chrome veya uyumlu bir tarayıcı

## Kurulum
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Kullanım
Önce `.env` dosyasını doldur, örnek için `env.example` dosyasına bak.

Komut satırından çalıştırmak için:
```bash
python -m src.main
```

GUI ile başlatmak için:
```bash
python gui_main.py
```

## CLI Seçenekleri
- `--username`: Kullanıcı adını geçersiz kılar
- `--password`: Şifreyi geçersiz kılar
- `--base-url`: Hedef oyun adresini geçersiz kılar
- `--headless true|false`: Tarayıcıyı headless modda açar ya da kapatır
- `--no-close`: Hata durumunda tarayıcıyı açık bırakır

## Notlar
- Oyun içi selector ve akışlar `src/selenium_bot.py` içinde tutulur.
- GUI, aynı bot sınıfını kullanır ve mekanikleri tek panelden yönetmeyi sağlar.

