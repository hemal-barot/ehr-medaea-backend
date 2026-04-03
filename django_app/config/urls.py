from django.contrib import admin
from django.urls import path

admin.site.site_header = "Medaea EHR Admin"
admin.site.site_title = "Medaea Admin Portal"
admin.site.index_title = "Clinical Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
]
