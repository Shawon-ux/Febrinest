from django.contrib import admin

from .models import Category, Order, OrderItem, Product, ProductSize, SiteSettings


class SizeInline(admin.TabularInline):
    model = ProductSize
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active")
    list_filter = ("category", "is_active")
    inlines = [SizeInline]


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "total", "payment_method", "payment_status", "status")
    list_filter = ("status", "payment_status", "payment_method")
    inlines = [ItemInline]


admin.site.register(Category)
admin.site.register(SiteSettings)
