from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    # Transforma os objetos Group em uma lista de strings: ['Professores', 'Coordenacao']
    groups = serializers.SlugRelatedField(
        many=True, 
        read_only=True, 
        slug_field='name'
    )

    class Meta:
        model = User
        # Garanta que 'groups' está na lista, além dos campos padrão
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups', 'is_superuser']