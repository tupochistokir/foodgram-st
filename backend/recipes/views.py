from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import FileResponse
from api.pagination import PageLimitPagination
from recipes.models import Ingredient, Recipe, Favorite, ShoppingCart
from recipes.serializers import (
    IngredientSerializer, RecipeReadSerializer,
    RecipeWriteSerializer, RecipeShortSerializer
)
from .utils import render_pdf_shopping_cart  # Функция для PDF
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.utils.crypto import get_random_string


class IsAuthorOrReadOnly(IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return obj.author == request.user


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get("name")
        return self.queryset.filter(name__istartswith=name) if name else self.queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related(
        'author').prefetch_related('ingredients')
    pagination_class = PageLimitPagination
    permission_classes = (IsAuthorOrReadOnly,)

    # ---------------- filters ----------------

    def get_queryset(self):
        qs = Recipe.objects.select_related('author').prefetch_related(
            'ingredients', 'favorite_recipes', 'cart_recipes'
        )

        p, user = self.request.query_params, self.request.user
        if author := p.get('author'):
            qs = qs.filter(author__id=author)
        if p.get('is_favorited') == '1' and not user.is_anonymous:
            qs = qs.filter(favorite_recipes=user)
        if p.get('is_in_shopping_cart') == '1' and not user.is_anonymous:
            qs = qs.filter(cart_recipes=user)
        return qs.order_by('-id')

    # ---------- override destroy ----------
    def destroy(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            raise PermissionDenied('Нельзя удалить чужой рецепт')
        return super().destroy(request, *args, **kwargs)

    def get_serializer_class(self):
        return (RecipeReadSerializer
                if self.request.method in ('GET',)
                else RecipeWriteSerializer)

    # ---------------- toggles ----------------
    def _toggle_relation(self, through_model, request, recipe):
        link = through_model.objects.filter(
            user=request.user, recipe=recipe
        ).first()

        if request.method == 'POST':
            if link:                      # уже есть
                return Response({'errors': 'Уже добавлено'},
                                status=status.HTTP_400_BAD_REQUEST)
            through_model.objects.create(user=request.user, recipe=recipe)
            data = RecipeShortSerializer(recipe,
                                         context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        if not link:
            return Response({'errors': 'Этого рецепта там нет'},
                            status=status.HTTP_400_BAD_REQUEST)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["POST", "DELETE"], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._toggle_relation(Favorite, request, self.get_object())

    @action(detail=True, methods=["POST", "DELETE"], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._toggle_relation(ShoppingCart, request, self.get_object())

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        rows = (Ingredient.objects
                .filter(ingredient_recipes__recipe__cart_recipes=request.user)
                .values('name', 'measurement_unit')
                .annotate(total=Sum('ingredient_recipes__amount'))
                .order_by('name'))
        items = [{'name': r['name'],
                  'unit': r['measurement_unit'],
                  'amount': r['total']} for r in rows]
        pdf = render_pdf_shopping_cart(request.user, items)
        return FileResponse(
            pdf,
            as_attachment=True,
            filename='shopping_list.pdf',
            content_type='application/pdf',
        )

    @action(detail=True, methods=['GET'], url_path='get-link',
            permission_classes=[])
    def get_link(self, request, pk=None):
        code = get_random_string(3)         
        short = request.build_absolute_uri(f'/recipes/s/{code}')
        return Response({'short-link': short})
