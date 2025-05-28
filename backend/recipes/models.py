from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# ────────────────────────────  КОНСТАНТЫ  ────────────────────────────
MIN_VALUE = 1
MAX_VALUE = 32_000
User = settings.AUTH_USER_MODEL
# ─────────────────────────────────────────────────────────────────────


class Ingredient(models.Model):
    name = models.CharField(
        max_length=256,
        verbose_name=_('Название'),
    )
    measurement_unit = models.CharField(
        max_length=32,
        verbose_name=_('Ед. измерения'),
    )

    # ↓↓↓  Django-style: Meta перед __str__
    class Meta:
        verbose_name = _('Ингредиент')
        verbose_name_plural = _('Ингредиенты')
        ordering = ('id',)
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient',
            ),
        ]
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name=_('Автор'),
    )
    # ↓↓↓ два M2M для фильтров
    favorite_recipes = models.ManyToManyField(
        User,
        through='Favorite',
        related_name='favorite_recipes',
        verbose_name=_('В избранном у'),
    )
    cart_recipes = models.ManyToManyField(
        User,
        through='ShoppingCart',
        related_name='cart_recipes',
        verbose_name=_('В корзине у'),
    )

    name = models.CharField(max_length=256, verbose_name=_('Название'))
    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name=_('Фото блюда'),
    )
    text = models.TextField(verbose_name=_('Описание'))
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name=_('Время приготовления (мин)'),
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE),
        ],
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='+',   # обратная связь не нужна
        verbose_name=_('Ингредиенты'),
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата публикации'),
    )

    class Meta:
        verbose_name = _('Рецепт')
        verbose_name_plural = _('Рецепты')
        ordering = ('-pub_date',)

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name=_('Рецепт'),
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
        verbose_name=_('Ингредиент'),
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name=_('Количество'),
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE),
        ],
    )

    class Meta:
        verbose_name = _('Ингредиент в рецепте')
        verbose_name_plural = _('Ингредиенты в рецепте')
        ordering = ('id',)
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            ),
        ]

    def __str__(self):
        return f'{self.ingredient} × {self.amount}'


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name=_('Пользователь'),
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name=_('Рецепт'),
    )

    class Meta:
        verbose_name = _('Избранный рецепт')
        verbose_name_plural = _('Избранные рецепты')
        ordering = ('id',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite',
            ),
        ]

    def __str__(self):
        return f'{self.user} → {self.recipe}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name=_('Пользователь'),
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_carts',
        verbose_name=_('Рецепт'),
    )

    class Meta:
        verbose_name = _('Запись в корзине')
        verbose_name_plural = _('Корзина')
        ordering = ('id',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_cart',
            ),
        ]

    def __str__(self):
        return f'{self.user} → {self.recipe}'
