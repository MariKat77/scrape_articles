from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
    
    published_date = serializers.DateTimeField(format="%d.%m.%Y %H:%M:%S")
    
    class Meta:
        model = Article
        fields = ['id', 'title', 'content_html', 'content_text', 'url', 'source', 'published_date']
