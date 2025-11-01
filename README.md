# Scrape Articles - System scrapowania i zarządzania artykułami

## Opis projektu

Scrape Articles to aplikacja Django służąca do automatycznego scrapowania artykułów z wybranych stron internetowych i udostępniania ich przez REST API. System pobiera treść artykułów, ekstrahuje metadane (tytuł, datę publikacji, źródło) i przechowuje je w bazie danych PostgreSQL.

Aplikacja oferuje:

- Automatyczne scrapowanie artykułów z zadanych URL
- Inteligentne rozpoznawanie dat publikacji (formaty polskie, angielskie, ISO, relative)
- REST API do przeglądania i filtrowania artykułów
- Przechowywanie wersji HTML oraz tekstowej treści artykułów

## Użyte technologie

- **Django 5.2.7** - framework webowy
- **Django REST Framework** - tworzenie REST API
- **PostgreSQL** - baza danych
- **psycopg2-binary** - adapter PostgreSQL dla Pythona
- **BeautifulSoup4** - parsowanie HTML
- **requests** - pobieranie stron internetowych
- **python-dateutil** - zaawansowane parsowanie dat

## Wymagania systemowe

- Python 3.10+
- PostgreSQL 12+
- pip (menedżer pakietów Python)
- Docker

## Instrukcja instalacji

### 1. Sklonuj repozytorium

```bash
git clone <url-repozytorium>
cd scrape_articles
```

### 2. Utwórz wirtualne środowisko

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# lub
.venv\Scripts\activate  # Windows
```

### 3. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 4. Skonfiguruj bazę danych PostgreSQL

Utwórz bazę danych i użytkownika:

```sql
CREATE DATABASE articlesDB;
CREATE USER user WITH PASSWORD 'password';
ALTER ROLE user SET client_encoding TO 'utf8';
ALTER ROLE user SET default_transaction_isolation TO 'read committed';
ALTER ROLE user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE articlesDB TO user;
```

**Uwaga:** W środowisku produkcyjnym zmień domyślne dane dostępowe w pliku `scrape_articles/settings.py`.

### 5. Wykonaj migracje

```bash
python manage.py makemigrations
python manage.py migrate
```

## Instrukcja uruchomienia

### Uruchomienie serwera deweloperskiego

```bash
python manage.py runserver
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8000/`

### Scrapowanie artykułów

Aby uruchomić proces scrapowania artykułów:

```bash
python manage.py scrape_articles
```

Komenda pobiera artykuły z URL-i zdefiniowanych w pliku `articles/management/commands/scrape_articles.py` i zapisuje je w bazie danych.

### Uruchomienie docker-compose

Budowanie i uruchomienie w tle

```bash
docker-compose up -d --build
```

Urchomienie scrapowania

```bash
docker-compose exec web python manage.py scrape_articles
```

Aplikacja będzie dostępna pod adresem: `http://localhost:8000/`

## Struktura API

### Endpoints

#### Lista wszystkich artykułów

```
GET /articles/
```

**Parametry zapytania:**

- `source` - filtrowanie po źródle (np. `?source=galicjaexpress.pl`)

**Przykładowa odpowiedź:**

```json
[
  {
    "id": 1,
    "title": "Tytuł artykułu",
    "content_html": "<article>...</article>",
    "content_text": "Treść artykułu...",
    "url": "https://example.com/article",
    "source": "example.com",
    "published_date": "28.10.2025 20:30:00"
  }
]
```

#### Szczegóły pojedynczego artykułu

```
GET /articles/<id>/
```

**Przykład:**

```
GET /articles/1/
```

### Przykłady użycia API

```bash
# Pobranie wszystkich artykułów
curl http://localhost:8000/articles/

# Filtrowanie po źródle
curl http://localhost/articles/?source=galicjaexpress.pl

# Pobranie szczegółów artykułu o ID=1
curl http://localhost:8000/articles/1/
```

## Struktura projektu

```
scrape_articles/
├── articles/                          # Główna aplikacja
│   ├── management/
│   │   └── commands/
│   │       └── scrape_articles.py    # Komenda scrapująca
│   ├── migrations/                    # Migracje bazy danych
│   ├── models.py                      # Model Article
│   ├── serializers.py                 # Serializery DRF
│   ├── views.py                       # Widoki API
│   └── urls.py                        # Routing aplikacji
├── scrape_articles/                   # Konfiguracja projektu
│   ├── settings.py                    # Ustawienia Django
│   └── urls.py                        # Główny routing
├── manage.py                          # Skrypt zarządzania Django
├── requirements.txt                   # Zależności projektu
└── .gitignore                         # Ignorowane pliki
```

## Model danych

### Article

| Pole           | Typ            | Opis                    |
| -------------- | -------------- | ----------------------- |
| id             | BigAutoField   | Klucz główny            |
| title          | CharField(255) | Tytuł artykułu          |
| content_html   | TextField      | Treść HTML artykułu     |
| content_text   | TextField      | Treść tekstowa artykułu |
| url            | URLField       | Unikalny URL artykułu   |
| source         | CharField(100) | Źródło (domena)         |
| published_date | DateTimeField  | Data publikacji         |

## Konfiguracja

### Dodawanie nowych URL-i do scrapowania

Edytuj plik `articles/management/commands/scrape_articles.py` i dodaj nowe URL-e do listy `urls`:

```python
urls = [
    "https://example.com/article1",
    "https://example.com/article2",
    # Dodaj nowe URL-e tutaj
]
```

### Zmiana konfiguracji bazy danych

Edytuj sekcję `DATABASES` w pliku `scrape_articles/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nazwa_bazy',
        'USER': 'uzytkownik',
        'PASSWORD': 'haslo',
        'HOST': 'host',
        'PORT': 'port',
    }
}
```

## Funkcjonalności scrapera

- **Automatyczne wykrywanie struktury strony** - scraper szuka elementów `<article>`, `.post-content`, `.entry-content` lub `<main>`
- **Parsowanie dat** w różnych formatach:
  - Polski: "28 października 2025"
  - Angielski: "October 28, 2025"
  - ISO: "2025-10-28"
  - Relative: "2 days ago", "yesterday"
- **Zabezpieczenie przed duplikatami** - artykuły z tym samym URL nie są ponownie scrapowane
- **Obsługa błędów** - logowanie problemów z pobieraniem i parsowaniem
