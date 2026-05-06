# fabricator/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("calculate/", views.calculate, name="calculate"),
    path("download/pdf/", views.download_pdf, name="download_pdf"),
    path("download/excel/", views.download_excel, name="download_excel"),
    
    # New Auth & DB URLs
    path("api/register/", views.api_register, name="api_register"),
    path("api/login/", views.api_login, name="api_login"),
    path("api/logout/", views.api_logout, name="api_logout"),
    path("api/save_project/", views.save_project, name="save_project"),
    # HTML Pages
    path("login/", views.login_page, name="login_page"),
    path("register/", views.register_page, name="register_page"),
    path("api/get_projects/", views.api_get_projects, name="api_get_projects"),
]