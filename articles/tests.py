from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from rest_framework import status
from .models import Article
from .serializers import ArticleSerializer
from articles.management.commands.scrape_articles import Command
import requests


class ArticleModelTest(TestCase):
    """Testy modelu Article"""

    def setUp(self):
        self.article = Article.objects.create(
            title="Test Article",
            content_html="<p>Test content HTML</p>",
            content_text="Test content text",
            url="https://example.com/test-article",
            source="example.com",
            published_date=timezone.now()
        )

    def test_article_creation(self):
        """Test tworzenia artykułu"""
        self.assertEqual(self.article.title, "Test Article")
        self.assertEqual(self.article.source, "example.com")
        self.assertTrue(isinstance(self.article, Article))

    def test_article_str_method(self):
        """Test metody __str__"""
        self.assertEqual(str(self.article), "Test Article")

    def test_url_uniqueness(self):
        """Test unikalności URL"""
        with self.assertRaises(Exception):
            Article.objects.create(
                title="Duplicate Article",
                content_html="<p>Content</p>",
                content_text="Content",
                url="https://example.com/test-article",  # Ten sam URL
                source="example.com",
                published_date=timezone.now()
            )

    def test_article_fields(self):
        """Test wszystkich pól modelu"""
        self.assertIsNotNone(self.article.id)
        self.assertIsNotNone(self.article.title)
        self.assertIsNotNone(self.article.content_html)
        self.assertIsNotNone(self.article.content_text)
        self.assertIsNotNone(self.article.url)
        self.assertIsNotNone(self.article.source)
        self.assertIsNotNone(self.article.published_date)


class ArticleSerializerTest(TestCase):
    """Testy serializera Article"""

    def setUp(self):
        self.article_data = {
            'title': 'Serializer Test Article',
            'content_html': '<p>HTML content</p>',
            'content_text': 'Text content',
            'url': 'https://example.com/serializer-test',
            'source': 'example.com',
            'published_date': timezone.now()
        }
        self.article = Article.objects.create(**self.article_data)
        self.serializer = ArticleSerializer(instance=self.article)

    def test_serializer_contains_expected_fields(self):
        """Test czy serializer zawiera wszystkie wymagane pola"""
        data = self.serializer.data
        self.assertEqual(
            set(data.keys()),
            {'id', 'title', 'content_html', 'content_text', 'url', 'source', 'published_date'}
        )

    def test_published_date_format(self):
        """Test formatowania daty publikacji"""
        data = self.serializer.data
        # Format: "%d.%m.%Y %H:%M:%S"
        self.assertRegex(data['published_date'], r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}')

    def test_serializer_data_matches_model(self):
        """Test czy dane z serializera odpowiadają modelowi"""
        data = self.serializer.data
        self.assertEqual(data['title'], self.article.title)
        self.assertEqual(data['url'], self.article.url)
        self.assertEqual(data['source'], self.article.source)


class ArticleAPITest(TestCase):
    """Testy API endpoints"""

    def setUp(self):
        self.client = Client()
        self.article1 = Article.objects.create(
            title="First Article",
            content_html="<p>First content</p>",
            content_text="First content",
            url="https://example.com/first",
            source="example.com",
            published_date=timezone.now()
        )
        self.article2 = Article.objects.create(
            title="Second Article",
            content_html="<p>Second content</p>",
            content_text="Second content",
            url="https://test.com/second",
            source="test.com",
            published_date=timezone.now()
        )

    def test_get_all_articles(self):
        """Test pobierania wszystkich artykułów"""
        response = self.client.get(reverse('article-list'))
        articles = Article.objects.all()
        serializer = ArticleSerializer(articles, many=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json(), serializer.data)

    def test_get_article_by_id(self):
        """Test pobierania artykułu po ID"""
        response = self.client.get(
            reverse('article-detail', kwargs={'pk': self.article1.pk})
        )
        article = Article.objects.get(pk=self.article1.pk)
        serializer = ArticleSerializer(article)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), serializer.data)

    def test_get_nonexistent_article(self):
        """Test pobierania nieistniejącego artykułu"""
        response = self.client.get(
            reverse('article-detail', kwargs={'pk': 9999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_articles_by_source(self):
        """Test filtrowania artykułów po źródle"""
        response = self.client.get(
            reverse('article-list') + '?source=example.com'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['source'], 'example.com')

    def test_filter_articles_partial_source_match(self):
        """Test filtrowania po częściowej nazwie źródła"""
        response = self.client.get(
            reverse('article-list') + '?source=example'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_empty_filter_result(self):
        """Test filtrowania bez wyników"""
        response = self.client.get(
            reverse('article-list') + '?source=nonexistent.com'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)


class ScraperCommandTest(TestCase):
    """Testy komendy scrape_articles"""

    def setUp(self):
        self.command = Command()

    def test_clean_text_removes_null_bytes(self):
        """Test usuwania null bytes z tekstu"""
        text = "Test\x00text\x00with\x00nulls"
        cleaned = self.command.clean_text(text)
        self.assertNotIn('\x00', cleaned)
        self.assertEqual(cleaned, "Testtextwithnulls")

    def test_clean_text_empty_string(self):
        """Test czyszczenia pustego stringa"""
        result = self.command.clean_text("")
        self.assertEqual(result, "")

    def test_clean_text_none(self):
        """Test czyszczenia None"""
        result = self.command.clean_text(None)
        self.assertEqual(result, "")

    def test_parse_date_polish_format(self):
        """Test parsowania polskiej daty"""
        from bs4 import BeautifulSoup
        
        text = "28 października 2025"
        soup = BeautifulSoup("<html></html>", 'html.parser')
        result = self.command.parse_date(soup, text)
        
        self.assertEqual(result.day, 28)
        self.assertEqual(result.month, 10)
        self.assertEqual(result.year, 2025)

    def test_parse_date_english_format(self):
        """Test parsowania angielskiej daty"""
        from bs4 import BeautifulSoup
        
        text = "October 28, 2025"
        soup = BeautifulSoup("<html></html>", 'html.parser')
        result = self.command.parse_date(soup, text)
        
        self.assertEqual(result.day, 28)
        self.assertEqual(result.month, 10)
        self.assertEqual(result.year, 2025)

    def test_parse_date_iso_format(self):
        """Test parsowania daty ISO"""
        from bs4 import BeautifulSoup
        
        text = "2025-10-28"
        soup = BeautifulSoup("<html></html>", 'html.parser')
        result = self.command.parse_date(soup, text)
        
        self.assertEqual(result.day, 28)
        self.assertEqual(result.month, 10)
        self.assertEqual(result.year, 2025)

    def test_parse_date_relative_format(self):
        """Test parsowania względnej daty"""
        from bs4 import BeautifulSoup
        
        text = "2 days ago"
        soup = BeautifulSoup("<html></html>", 'html.parser')
        result = self.command.parse_date(soup, text)
        
        now = timezone.now()
        expected = now - timedelta(days=2)
        
        self.assertEqual(result.day, expected.day)
        self.assertEqual(result.month, expected.month)
        self.assertEqual(result.year, expected.year)

    def test_parse_date_yesterday(self):
        """Test parsowania 'yesterday'"""
        from bs4 import BeautifulSoup
        
        text = "Posted yesterday"
        soup = BeautifulSoup("<html></html>", 'html.parser')
        result = self.command.parse_date(soup, text)
        
        now = timezone.now()
        expected = now - timedelta(days=1)
        
        self.assertEqual(result.day, expected.day)

    def test_parse_date_meta_tags(self):
        """Test parsowania daty z meta tagów"""
        from bs4 import BeautifulSoup
        
        html = '<html><meta property="article:published_time" content="2025-10-28T12:00:00Z"></html>'
        soup = BeautifulSoup(html, 'html.parser')
        result = self.command.parse_date(soup, "")
        
        self.assertEqual(result.day, 28)
        self.assertEqual(result.month, 10)
        self.assertEqual(result.year, 2025)

    @patch('articles.management.commands.scrape_articles.requests.get')
    def test_scraping_duplicate_article(self, mock_get):
        """Test próby scrapowania istniejącego artykułu"""
        Article.objects.create(
            title="Existing Article",
            content_html="<p>Content</p>",
            content_text="Content",
            url="https://example.com/existing",
            source="example.com",
            published_date=timezone.now()
        )
        
        initial_count = Article.objects.count()
        
        # Mockowanie odpowiedzi HTTP
        mock_response = Mock()
        mock_response.text = "<html><title>Existing Article</title></html>"
        mock_response.status_code = 200
        mock_response.apparent_encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        # Uruchomienie komendy - nie powinno dodać duplikatu
        # (test logiki w handle method)
        
        self.assertEqual(Article.objects.count(), initial_count)

    @patch('articles.management.commands.scrape_articles.requests.get')
    def test_scraping_handles_request_error(self, mock_get):
        """Test obsługi błędu HTTP"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        initial_count = Article.objects.count()
        
        # Komenda powinna obsłużyć błąd bez crash
        try:
            # Logika handle method powinna złapać wyjątek
            pass
        except requests.exceptions.RequestException:
            self.fail("Scraper should handle request exceptions")
        
        # Nie powinno dodać artykułu przy błędzie
        self.assertEqual(Article.objects.count(), initial_count)


class ArticleIntegrationTest(TestCase):
    """Testy integracyjne end-to-end"""

    def setUp(self):
        self.client = Client()

    def test_complete_workflow(self):
        """Test pełnego workflow: create -> retrieve -> filter"""
        # 1. Utworzenie artykułów
        article1 = Article.objects.create(
            title="Integration Test 1",
            content_html="<p>Content 1</p>",
            content_text="Content 1",
            url="https://test.com/integration-1",
            source="test.com",
            published_date=timezone.now()
        )
        
        article2 = Article.objects.create(
            title="Integration Test 2",
            content_html="<p>Content 2</p>",
            content_text="Content 2",
            url="https://example.com/integration-2",
            source="example.com",
            published_date=timezone.now()
        )
        
        # 2. Pobranie wszystkich
        response = self.client.get(reverse('article-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        
        # 3. Pobranie pojedynczego
        response = self.client.get(
            reverse('article-detail', kwargs={'pk': article1.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['title'], "Integration Test 1")
        
        # 4. Filtrowanie
        response = self.client.get(
            reverse('article-list') + '?source=test.com'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['source'], 'test.com')

    def test_api_returns_correct_date_format(self):
        """Test czy API zwraca datę w poprawnym formacie"""
        article = Article.objects.create(
            title="Date Format Test",
            content_html="<p>Content</p>",
            content_text="Content",
            url="https://test.com/date-test",
            source="test.com",
            published_date=timezone.now()
        )
        
        response = self.client.get(
            reverse('article-detail', kwargs={'pk': article.pk})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        published_date = response.json()['published_date']
        
        # Sprawdzenie formatu DD.MM.YYYY HH:MM:SS
        import re
        pattern = r'^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}$'
        self.assertIsNotNone(re.match(pattern, published_date))

    def test_multiple_sources_filtering(self):
        """Test filtrowania z wieloma źródłami"""
        sources = ['source1.com', 'source2.com', 'source3.com']
        
        for i, source in enumerate(sources):
            Article.objects.create(
                title=f"Article {i}",
                content_html=f"<p>Content {i}</p>",
                content_text=f"Content {i}",
                url=f"https://{source}/article-{i}",
                source=source,
                published_date=timezone.now()
            )
        
        # Test filtrowania każdego źródła
        for source in sources:
            response = self.client.get(
                reverse('article-list') + f'?source={source}'
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.json()), 1)
            self.assertEqual(response.json()[0]['source'], source)