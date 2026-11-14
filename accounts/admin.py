from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class FebrinestUserAdmin(UserAdmin):
    list_display = ("full_name", "phone", "email", "is_staff")
    search_fields = ("full_name", "phone", "email")
    fieldsets = UserAdmin.fieldsets + (("Febrinest", {"fields": ("full_name", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Febrinest", {"fields": ("full_name", "email", "phone")}),
    )
