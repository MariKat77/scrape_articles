from django.core.management.base import BaseCommand
from articles.models import Article
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlparse
import re

class Command(BaseCommand):
    help = 'Scrapes articles and stores them in the database'

    def handle(self, *args, **options):
        urls = [
            "https://galicjaexpress.pl/ford-c-max-jaki-silnik-benzynowy-wybrac-aby-zaoszczedzic-na-paliwie",
            "https://galicjaexpress.pl/bmw-e9-30-cs-szczegolowe-informacje-o-osiagach-i-historii-modelu",
            "https://take-group.github.io/example-blog-without-ssr/jak-kroic-piers-z-kurczaka-aby-uniknac-suchych-kawalkow-miesa",
            "https://take-group.github.io/example-blog-without-ssr/co-mozna-zrobic-ze-schabu-oprocz-kotletow-5-zaskakujacych-przepisow",
        ]
        total = len(urls)
        for idx, url in enumerate(urls, start=1):
            self.stdout.write(f"Scraping article {idx}/{total}: {url}")
            if Article.objects.filter(url=url).exists():
                self.stdout.write("Article exist in database. Skip.")
                continue
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except Exception as e:
                self.stderr.write(f"Download error {url}: {e}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else 'No title'

            content_elem = (
                soup.find('article') or
                soup.find('div', class_='post-content') or
                soup.find('div', class_='entry-content') or
                soup.find('main')
            )
            if content_elem:
                content_html = str(content_elem)
                content_text = content_elem.get_text(separator=' ', strip=True)
            else:

                content_html = response.text
                content_text = soup.get_text(separator=' ', strip=True)

            date_text = None

            text = soup.get_text(separator=' ', strip=True)

            polish_months = ['stycznia','lutego','marca','kwietnia','maja','czerwca',
                             'lipca','sierpnia','września','października','listopada','grudnia']
            pattern_pl = r'\d{1,2}\s+(?:' + '|'.join(polish_months) + r')\s+\d{4}'
            pattern_en = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
            match_pl = re.search(pattern_pl, text)
            match_en = re.search(pattern_en, text)
            match_iso = re.search(r'\d{4}-\d{2}-\d{2}', text)
            if match_pl:
                date_text = match_pl.group()
            elif match_en:
                date_text = match_en.group()
            elif match_iso:
                date_text = match_iso.group()
            else:

                match_rel = re.search(r'(\d+)\s+(seconds|minutes|hours|days)\s+ago', text, re.IGNORECASE)
                if match_rel:
                    date_text = match_rel.group()
                elif 'yesterday' in text.lower():
                    date_text = 'yesterday'

            published_date = None
            if date_text:
                try:
                    date_text = date_text.strip()
                    now = datetime.now()
                    if 'ago' in date_text or date_text.lower() == 'yesterday':
                        if 'yesterday' in date_text.lower():
                            published_date = now - timedelta(days=1)
                        else:
                            num, unit, _ = date_text.split()
                            num = int(num)
                            if unit.startswith('second'):
                                published_date = now - timedelta(seconds=num)
                            elif unit.startswith('minute'):
                                published_date = now - timedelta(minutes=num)
                            elif unit.startswith('hour'):
                                published_date = now - timedelta(hours=num)
                            elif unit.startswith('day'):
                                published_date = now - timedelta(days=num)
                    else:
                        from dateutil import parser
                        published_date = parser.parse(date_text)

                    if published_date and (published_date.hour == 0 and published_date.minute == 0 and published_date.second == 0):
                        published_date = published_date.replace(hour=0, minute=0, second=0, microsecond=0)
                except Exception as e:
                    self.stderr.write(f"Parse date fail '{date_text}': {e}")
            if not published_date:

                published_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


            source = urlparse(url).netloc

            try:
                Article.objects.create(
                    title=title,
                    content_html=content_html,
                    content_text=content_text,
                    url=url,
                    source=source,
                    published_date=published_date
                )
                self.stdout.write("Sucessfull save in database.")
            except Exception as e:
                self.stderr.write(f"Article save error {url}: {e}")
