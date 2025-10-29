from django.shortcuts import render
from rest_framework import generics
from .models import Article
from .serializers import ArticleSerializer

class ArticleList(generics.ListAPIView):

    serializer_class = ArticleSerializer

    def get_queryset(self):
        queryset = Article.objects.all()
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source__icontains=source)
        return queryset

class ArticleDetail(generics.RetrieveAPIView):
    
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

