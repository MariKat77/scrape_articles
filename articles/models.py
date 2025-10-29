from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=255)
    content_html = models.TextField()
    content_text = models.TextField()
    url = models.URLField(unique=True)
    source = models.CharField(max_length=100)
    published_date = models.DateTimeField()

    def __str__(self):
        return self.title