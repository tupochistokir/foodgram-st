from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from recipes.serializers import RecipeShortSerializer
from .models import Subscription

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Регистрация: возвращаем только 5 полей, без is_subscribed/avatar."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name',
                  'email', 'password')
        # требуем оба имени, иначе DRF сам отдаст 400
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, data):
        return User.objects.create_user(**data)


class UserSerializer(serializers.ModelSerializer):
    """Карточка пользователя (везде)."""
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        # порядок полей важен для автотестов
        fields = (
            'id', 'username', 'first_name', 'last_name',
            'email', 'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(user=request.user,
                                           author=obj).exists()

    def get_avatar(self, obj):
        """null → null, файл → абсолютный URL-string"""
        if not obj.avatar:
            return None
        req = self.context.get('request')
        return req.build_absolute_uri(obj.avatar.url) if req else obj.avatar.url


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'avatar', 'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes(self, author):
        limit = self.context['request'].query_params.get('recipes_limit')
        qs = author.recipes.all().order_by('-id')
        if limit:
            qs = qs[: int(limit)]
        return RecipeShortSerializer(qs, many=True, context=self.context).data
