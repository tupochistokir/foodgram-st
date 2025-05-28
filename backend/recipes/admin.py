# backend/recipes/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_editable = ('measurement_unit',)
    search_fields = ('name',)
    list_per_page = 20

    def get_model_perms(self, request):
        """
        Показывать ингредиенты в меню только тем, у кого есть права.
        """
        return super().get_model_perms(request)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    fk_name = 'recipe'
    verbose_name = _('Ингредиент в рецепте')
    verbose_name_plural = _('Ингредиенты в рецепте')
    autocomplete_fields = ('ingredient',)
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = (RecipeIngredientInline,)

    list_display = (
        'id', 'name', 'author', 'cooking_time', 'likes_count', 'in_cart_count'
    )
    list_filter = ('author', 'ingredients', 'pub_date')
    search_fields = ('name', 'author__username')
    readonly_fields = ('pub_date',)
    list_per_page = 10

    # вместо fieldsets с проблемным M2M просто перечисляем поля
    fields = (
        'name',
        'author',
        'image',
        'text',
        'cooking_time',
        'pub_date',
    )

    @admin.display(description=_('Добавили в избранное'))
    def likes_count(self, obj):
        return obj.favorites.count()

    @admin.display(description=_('Добавили в корзину'))
    def in_cart_count(self, obj):
        return obj.carts.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user__email', 'recipe__name')
    autocomplete_fields = ('user', 'recipe')
    readonly_fields = ('id',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user__email', 'recipe__name')
    autocomplete_fields = ('user', 'recipe')
    readonly_fields = ('id',)
