from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.safestring import mark_safe

from .models import CustomUser, Subscription


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id', 'username', 'full_name', 'email', 'avatar_tag',
        'recipes_count', 'subscriptions_count', 'followers_count',
        'is_staff'
    )
    search_fields = (
        'username', 'email', 'first_name', 'last_name'
    )
    list_filter = (
        'is_staff', 'is_active'
    )

    @admin.display(description='Аватар')
    @mark_safe
    def avatar_tag(self, obj):
        """Отображает аватар пользователя в виде тега <img>."""
        if obj.avatar:
            return (
                f'<img src="{obj.avatar.url}" width="50" '
                'height="50" style="border-radius:50%;" />'
            )
        return ''

    @admin.display(description='ФИО')
    def full_name(self, obj):
        """Сочетание имени и фамилии пользователя."""
        return f'{obj.first_name} {obj.last_name}'

    @admin.display(description='Рецептов')
    def recipes_count(self, obj):
        """Сколько рецептов создал пользователь."""
        return obj.recipes.count()

    @admin.display(description='Подписок')
    def subscriptions_count(self, obj):
        """Сколько авторов подписано этим пользователем."""
        return Subscription.objects.filter(
            user=obj
        ).count()

    @admin.display(description='Подписчиков')
    def followers_count(self, obj):
        """Сколько подписчиков у пользователя."""
        return Subscription.objects.filter(
            author=obj
        ).count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')
