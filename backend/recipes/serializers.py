# backend/recipes/serializers.py
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from django.db import transaction
from recipes.models import (
    Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart,
)

# ────────────────────────────  КОНСТАНТЫ  ────────────────────────────
MIN_AMOUNT = 1          # для количества ингредиента
MAX_AMOUNT = 32_000

MIN_TIME = 1            # для времени приготовления (мин)
MAX_TIME = 32_000
# ─────────────────────────────────────────────────────────────────────


# ---------- INGREDIENTS ---------- #
class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = fields


class IngredientAmountSerializer(serializers.ModelSerializer):
    """
    Объект: «ингредиент + количество» для записи рецепта.
    """
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT,
        max_value=MAX_AMOUNT,
        error_messages={
            'min_value': f'Минимум {MIN_AMOUNT}',
            'max_value': f'Максимум {MAX_AMOUNT}',
        },
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


# ---------- РЕЦЕПТЫ (чтение) ---------- #
class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeShortSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url)


class RecipeReadSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time',
        )

    # ── Вспомогательные ──────────────────────────────────────────
    def get_author(self, obj):
        from users.serializers import UserSerializer
        return UserSerializer(obj.author, context=self.context).data

    def _relation(self, model, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return model.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_favorited(self, obj):
        return self._relation(Favorite, obj)

    def get_is_in_shopping_cart(self, obj):
        return self._relation(ShoppingCart, obj)


# ---------- РЕЦЕПТЫ (создание / изменение) ---------- #
class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientAmountSerializer(many=True)
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(
        min_value=MIN_TIME,
        max_value=MAX_TIME,
        error_messages={
            'min_value': f'Минимум {MIN_TIME} минута',
            'max_value': f'Максимум {MAX_TIME} минут',
        },
    )

    class Meta:
        model = Recipe
        fields = ('ingredients', 'image', 'name', 'text', 'cooking_time')

    # ── ВАЛИДАЦИЯ ────────────────────────────────────────────────
    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError('Нужен хотя бы один ингредиент.')
        ids = [item['id'].id for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Ингредиенты повторяются.')
        return value

    def validate_image(self, img):
        if img is None:
            raise serializers.ValidationError(
                'Изображение не может быть пустым.')
        return img

    def validate(self, attrs):
        """
        При **обновлении** (instance уже существует) требуем присутствие поля
        `ingredients` — иначе 400.
        """
        if self.instance and 'ingredients' not in self.initial_data:
            raise serializers.ValidationError(
                {'ingredients': 'Это поле обязательно при обновлении рецепта.'}
            )
        return attrs

    # ── Служебные методы ────────────────────────────────────────
    @transaction.atomic
    def _set_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount'],
            )
            for item in ingredients
        ])

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )
        self._set_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        # остальные поля
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if ingredients is not None:
            instance.recipe_ingredients.all().delete()
            self._set_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data

