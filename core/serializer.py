from rest_framework import serializers
from core.models import Livro

# serializa o model livro para json nas respostas da api
class LivroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livro
        fields = '__all__' 