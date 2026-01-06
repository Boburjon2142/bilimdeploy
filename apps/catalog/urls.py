from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/home/", views.api_home, name="api_home"),
    path("api/categories/", views.api_categories, name="api_categories"),
    path("api/authors/", views.api_authors, name="api_authors"),
    path("api/books/", views.api_books, name="api_books"),
    path("api/books/<int:id>/", views.api_book_detail, name="api_book_detail"),
    path("api/about/", views.api_about, name="api_about"),
    path("kategoriyalar/", views.categories_list, name="categories_list"),
    path("mualliflar/", views.authors_list, name="authors_list"),
    path("muallif/<int:author_id>/", views.author_detail, name="author_detail"),
    path("biz-haqimizda/", views.about, name="about"),
    path("yangi/", views.new_books_list, name="new_books_list"),
    path("eng-kop-sotilgan/", views.best_selling_list, name="best_selling_list"),
    path("tavsiya-etilgan/", views.recommended_list, name="recommended_list"),
    path("kategoriya/<slug:slug>/", views.category_detail, name="category_detail"),
    path("kitob/<int:id>/<slug:slug>/", views.book_detail, name="book_detail"),
    path("qidiruv/", views.search, name="search"),
    path("sevimlilar/", views.favorites, name="favorites"),
    path("sevimlilar/qoshish/<int:book_id>/", views.add_favorite, name="add_favorite"),
    path("sevimlilar/ochirish/<int:book_id>/", views.remove_favorite, name="remove_favorite"),
]
