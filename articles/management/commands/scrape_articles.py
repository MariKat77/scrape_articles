from django.core.management.base import BaseCommand
from articles.models import Article
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlparse
from django.utils import timezone
from dateutil import parser
import re


class Command(BaseCommand):
    help = 'Scrapes articles and stores them in the database'

    def parse_date(self, soup, text):

        now = timezone.now()
        
        meta_dates = [
            soup.find('meta', property='article:published_time'),
            soup.find('meta', {'name': 'publish-date'}),
            soup.find('meta', {'name': 'date'}),
            soup.find('time')
        ]
        
        for meta in meta_dates:
            if meta:
                date_str = meta.get('content') or meta.get('datetime') or meta.get_text()
                if date_str:
                    try:
                        parsed = parser.parse(date_str)
                        if parsed.tzinfo is None:
                            return timezone.make_aware(parsed)
                        return parsed
                    except:
                        pass
        
        polish_months = {
            'stycznia': '01', 'lutego': '02', 'marca': '03', 'kwietnia': '04',
            'maja': '05', 'czerwca': '06', 'lipca': '07', 'sierpnia': '08',
            'września': '09', 'października': '10', 'listopada': '11', 'grudnia': '12'
        }
        
        pattern_pl = r'(\d{1,2})\s+(' + '|'.join(polish_months.keys()) + r')\s+(\d{4})'
        match_pl = re.search(pattern_pl, text, re.IGNORECASE)
        if match_pl:
            day, month_name, year = match_pl.groups()
            month = polish_months[month_name.lower()]
            date_str = f"{year}-{month}-{day.zfill(2)}"
            try:
                parsed = parser.parse(date_str)
                return timezone.make_aware(parsed.replace(hour=0, minute=0, second=0))
            except:
                pass
        
        pattern_en = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'
        match_en = re.search(pattern_en, text, re.IGNORECASE)
        if match_en:
            try:
                date_str = match_en.group()
                parsed = parser.parse(date_str)
                return timezone.make_aware(parsed.replace(hour=0, minute=0, second=0))
            except:
                pass
        
        match_iso = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
        if match_iso:
            try:
                date_str = match_iso.group()
                parsed = parser.parse(date_str)
                return timezone.make_aware(parsed.replace(hour=0, minute=0, second=0))
            except:
                pass
        
        match_rel = re.search(r'(\d+)\s+(second|minute|hour|day)s?\s+ago', text, re.IGNORECASE)
        if match_rel:
            num = int(match_rel.group(1))
            unit = match_rel.group(2).lower()
            
            if unit == 'second':
                return now - timedelta(seconds=num)
            elif unit == 'minute':
                return now - timedelta(minutes=num)
            elif unit == 'hour':
                return now - timedelta(hours=num)
            elif unit == 'day':
                return now - timedelta(days=num)
        
        if re.search(r'\byesterday\b', text, re.IGNORECASE):
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    def clean_text(self, text):
        if not text:
            return ""
        return text.replace('\x00', '').encode('utf-8', errors='ignore').decode('utf-8')

    def handle(self, *args, **options):
        urls = [
            "https://galicjaexpress.pl/ford-c-max-jaki-silnik-benzynowy-wybrac-aby-zaoszczedzic-na-paliwie",
            "https://galicjaexpress.pl/bmw-e9-30-cs-szczegolowe-informacje-o-osiagach-i-historii-modelu",
            "https://take-group.github.io/example-blog-without-ssr/jak-kroic-piers-z-kurczaka-aby-uniknac-suchych-kawalkow-miesa",
            "https://take-group.github.io/example-blog-without-ssr/co-mozna-zrobic-ze-schabu-oprocz-kotletow-5-zaskakujacych-przepisow",
        ]
        
        total = len(urls)
        
        for idx, url in enumerate(urls, start=1):
            self.stdout.write(f"\nScraping article {idx}/{total}: {url}")
            
            if Article.objects.filter(url=url).exists():
                self.stdout.write(self.style.WARNING("Article already exists in database. Skipping."))
                continue
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': '*/*',
                    'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                response = requests.get(url, timeout=10, headers=headers)
                response.raise_for_status()
                response.encoding = response.apparent_encoding
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Download error: {e}"))
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else 'No title'
            title = self.clean_text(title)

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

            content_html = self.clean_text(content_html)
            content_text = self.clean_text(content_text)

            text = soup.get_text(separator=' ', strip=True)
            published_date = self.parse_date(soup, text)

            source = urlparse(url).netloc

            try:
                article = Article.objects.create(
                    title=title,
                    content_html=content_html,
                    content_text=content_text,
                    url=url,
                    source=source,
                    published_date=published_date
                )

                date_formatted = published_date.strftime('%d.%m.%Y %H:%M:%S')
                self.stdout.write(self.style.SUCCESS(f"Successfully saved article"))
                self.stdout.write(f"  Title: {title[:60]}...")
                self.stdout.write(f"  Date: {date_formatted}")
                self.stdout.write(f"  Source: {source}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Database save error: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"Scraping completed!"))
        self.stdout.write(self.style.SUCCESS(f"Total articles in database: {Article.objects.count()}"))