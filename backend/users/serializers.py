from django.contrib.auth import get_user_model
from rest_framework import serializers
from recipes.serializers import RecipeShortSerializer
from .models import Subscription

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    """Регистрация нового пользователя — без is_subscribed и avatar."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name',
            'email', 'password',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name',
            'email', 'is_subscribed', 'avatar',
        )

    # --- helpers -------------------------------------------------
    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        # читаем через related_name — subscriptions
        return request.user.subscriptions.filter(author=obj).exists()


class SubscribeActionSerializer(serializers.Serializer):
    """
    Пустой технический сериализатор.
    Проверяет:
      • нельзя подписаться на себя,
      • нельзя подписаться повторно.
    """

    def validate(self, attrs):
        request = self.context['request']
        author = self.context['author']

        if request.user == author:
            raise serializers.ValidationError('Нельзя подписаться на себя')

        if request.user.subscriptions.filter(author=author).exists():
            raise serializers.ValidationError('Уже подписаны')

        return attrs


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
