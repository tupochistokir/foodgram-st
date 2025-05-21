from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
import base64
import uuid
import imghdr
from django.core.files.base import ContentFile
from .models import Subscription
from .serializers import SubscriptionSerializer


class CustomUserViewSet(DjoserUserViewSet):
    """Наследник Djoser для подписок и списка подписок"""

    lookup_value_regex = r'\d+'

    @action(detail=False, methods=('get',), permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        """
        Возвращает профиль текущего пользователя.
        Для анонимных возвращаем 401 – так требуют автотесты.
        """
        return super().me(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(self.get_queryset(), pk=id)
        user = request.user
        if user == author:
            return Response({'errors': 'Нельзя подписаться на себя'},
                            status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'POST':
            sub, created = Subscription.objects.get_or_create(
                user=user, author=author
            )
            if not created:
                return Response({'errors': 'Уже подписаны'},
                                status=status.HTTP_400_BAD_REQUEST)
            data = SubscriptionSerializer(
                author, context=self.get_serializer_context()
            ).data
            return Response(data, status=status.HTTP_201_CREATED)

        # DELETE
        deleted, _ = Subscription.objects.filter(
            user=user, author=author
        ).delete()
        if not deleted:
            return Response({'errors': 'Подписки не существует'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['GET'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        authors_qs = self.get_queryset().filter(subscribers__user=request.user)
        page = self.paginate_queryset(authors_qs.order_by('-id'))
        serializer = SubscriptionSerializer(page, many=True,
                                            context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['PUT', 'DELETE'],
            url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            raw = request.data.get('avatar')
            if not raw:
                return Response({'errors': 'avatar — обязательное поле'},
                                status=status.HTTP_400_BAD_REQUEST)

            # ---- превращаем base-64 в Django-файл ----
            try:
                if raw.startswith('data:image'):
                    header, b64 = raw.split(';base64,')
                    ext = header.split('/')[-1]
                else:
                    b64, ext = raw, 'png'

                binary = base64.b64decode(b64)
                # проверим реальный тип
                ext = imghdr.what(None, binary) or ext
                fname = f'{uuid.uuid4()}.{ext}'
                user.avatar.save(fname, ContentFile(binary), save=True)
            except Exception:
                return Response({'errors': 'Некорректный формат изображения'},
                                status=status.HTTP_400_BAD_REQUEST)

            url = request.build_absolute_uri(user.avatar.url)
            return Response({'avatar': url}, status=status.HTTP_200_OK)

        # ---- DELETE ----
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
