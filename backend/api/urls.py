from django.urls import include, path
from rest_framework.routers import DefaultRouter
from api.views import CustomUserViewSet, IngredientViewSet, RecipeViewSet

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='users')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'recipes', RecipeViewSet, basename='recipe')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
