from django.urls import path

from products import views

urlpatterns = [
    path("regions/", views.RegionsView.as_view(), name="regions"),
    path("scrape/", views.ScrapeCreateView.as_view(), name="scrape-create"),
    path("scrape/bulk/", views.BulkScrapeView.as_view(), name="scrape-bulk"),
    path("jobs/<int:job_id>/", views.JobStatusView.as_view(), name="job-status"),
    path(
        "products/<str:region>/<str:item_id>/",
        views.ProductDetailView.as_view(),
        name="product-detail",
    ),
    path(
        "products/<str:region>/",
        views.ProductListByRegionView.as_view(),
        name="product-list",
    ),
]
