from django.contrib import admin

from products.models import ProductRecord, ScrapeJob

admin.site.register(ScrapeJob)
admin.site.register(ProductRecord)
