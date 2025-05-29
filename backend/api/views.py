from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
import base64
import uuid
import imghdr
from api.permissions import IsAuthorOrReadOnly
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from api.serializers import (
    SubscriptionSerializer,
    SubscribeActionSerializer,
    IngredientSerializer, RecipeReadSerializer,
    RecipeWriteSerializer, RecipeShortSerializer,
)
from django.db.models import Sum
from django.http import FileResponse
from django.utils.crypto import get_random_string
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from api.pagination import PageLimitPagination
from recipes.models import Ingredient, Recipe, Favorite, ShoppingCart
from recipes.utils import render_pdf_shopping_cart

__all__ = ['CustomUserViewSet', 'IngredientViewSet', 'RecipeViewSet']

SHORT_CODE_LENGTH = 3
SHORT_LINK_PATH = '/recipes/s/'


class CustomUserViewSet(DjoserUserViewSet):
    """
    /api/users/…  + кастомные:
        • /api/users/<id>/subscribe/
        • /api/users/subscriptions/
        • /api/users/me/avatar/
    """
    lookup_value_regex = r'\d+'

    # ---------- /me ----------------------------------------------------
    @action(detail=False, methods=('get',), permission_classes=(IsAuthenticated,))
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    # ---------- /subscribe --------------------------------------------
    @action(detail=True, methods=('post', 'delete'),
            permission_classes=(IsAuthenticated,), url_path='subscribe')
    def subscribe(self, request, id=None):
        author = get_object_or_404(self.get_queryset(), pk=id)

        if request.method == 'POST':
            SubscribeActionSerializer(
                data={}, context={'request': request, 'author': author}
            ).is_valid(raise_exception=True)

            request.user.subscriptions.create(author=author)

            data = SubscriptionSerializer(
                author, context=self.get_serializer_context()
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        deleted, _ = request.user.subscriptions.filter(author=author).delete()
        if not deleted:
            return Response({'errors': 'Подписки не существует'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ---------- /subscriptions ----------------------------------------
    @action(detail=False, methods=('get',), permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        authors = self.get_queryset().filter(subscribers__user=request.user)
        page = self.paginate_queryset(authors.order_by('-id'))
        serializer = SubscriptionSerializer(
            page, many=True, context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)

    # ---------- /me/avatar --------------------------------------------
    @action(detail=False, methods=('put', 'delete'),
            url_path='me/avatar', permission_classes=(IsAuthenticated,))
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            raw = request.data.get('avatar')
            if not raw:
                return Response({'errors': 'avatar — обязательное поле'},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                if raw.startswith('data:image'):
                    header, b64 = raw.split(';base64,')
                    ext = header.split('/')[-1]
                else:
                    b64, ext = raw, 'png'

                binary = base64.b64decode(b64)
                ext = imghdr.what(None, binary) or ext
                user.avatar.save(f'{uuid.uuid4()}.{ext}',
                                 ContentFile(binary), save=True)
            except Exception:
                return Response({'errors': 'Некорректный формат изображения'},
                                status=status.HTTP_400_BAD_REQUEST)

            return Response(
                {'avatar': request.build_absolute_uri(user.avatar.url)},
                status=status.HTTP_200_OK,
            )

        # DELETE
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get('name')
        return (self.queryset
                .filter(name__istartswith=name) if name else self.queryset)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related(
        'author').prefetch_related('ingredients')
    pagination_class = PageLimitPagination
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    # ------------- фильтрация --------------------
    def get_queryset(self):
        qs = (Recipe.objects.select_related('author')
              .prefetch_related('ingredients', 'favorite_recipes', 'cart_recipes'))

        params, user = self.request.query_params, self.request.user
        if author := params.get('author'):
            qs = qs.filter(author__id=author)
        if params.get('is_favorited') == '1' and user.is_authenticated:
            qs = qs.filter(favorite_recipes=user)
        if params.get('is_in_shopping_cart') == '1' and user.is_authenticated:
            qs = qs.filter(cart_recipes=user)
        return qs.order_by('-id')

    # ------------- сериалайзер -------------------
    def get_serializer_class(self):
        return (RecipeReadSerializer
                if self.request.method == 'GET'
                else RecipeWriteSerializer)

    # ------------- delete only author ------------
    def destroy(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            raise PermissionDenied('Нельзя удалить чужой рецепт')
        return super().destroy(request, *args, **kwargs)

    # ------------- избранное / корзина -----------
    def _toggle(self, model, request, recipe):
        link = model.objects.filter(user=request.user, recipe=recipe).first()

        if request.method == 'POST':
            if link:
                return Response({'errors': 'Уже добавлено'},
                                status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=request.user, recipe=recipe)
            data = RecipeShortSerializer(
                recipe, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        if not link:
            return Response({'errors': 'Этого рецепта там нет'},
                            status=status.HTTP_400_BAD_REQUEST)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=('post', 'delete'), permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk=None):
        return self._toggle(Favorite, request, self.get_object())

    @action(detail=True, methods=('post', 'delete'), permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk=None):
        return self._toggle(ShoppingCart, request, self.get_object())

    # ------------- PDF список покупок ------------
    @action(detail=False, methods=('get',), permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        rows = (Ingredient.objects
                .filter(ingredient_recipes__recipe__cart_recipes=request.user)
                .values('name', 'measurement_unit')
                .annotate(total=Sum('ingredient_recipes__amount'))
                .order_by('name'))
        pdf = render_pdf_shopping_cart(
            request.user,
            [{'name': r['name'], 'unit': r['measurement_unit'], 'amount': r['total']}
             for r in rows]
        )
        return FileResponse(pdf, as_attachment=True,
                            filename='shopping_list.pdf',
                            content_type='application/pdf')

    # ------------- короткая ссылка ---------------
    @action(detail=True, methods=('get',), url_path='get-link',
            permission_classes=(AllowAny,))
    def get_link(self, request, pk=None):
        code = get_random_string(SHORT_CODE_LENGTH)
        short_url = request.build_absolute_uri(f'{SHORT_LINK_PATH}{code}')
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)
