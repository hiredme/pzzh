from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # 其他URL配置...
]

urlpatterns += [
    path("upload/", views.upload, name="upload"),
    path("register/", views.register, name="register"),
    path("submission_history/", views.submission_history, name="submission_history"),
    path(
        "submission/<int:submission_id>/",
        views.submission_detail,
        name="submission_detail",
    ),
]
