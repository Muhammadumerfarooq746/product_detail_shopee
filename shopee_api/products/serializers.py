from rest_framework import serializers

from products.models import ProductRecord, Region, ScrapeJob
from scrapers.registry import available_regions


class ScrapeCreateSerializer(serializers.Serializer):
    region = serializers.ChoiceField(choices=Region.choices)
    shop_id = serializers.RegexField(regex=r"^\d+$")
    item_id = serializers.RegexField(regex=r"^\d+$")
    force = serializers.BooleanField(default=False, required=False)

    def validate_region(self, value: str) -> str:
        value = value.upper()
        if value not in available_regions():
            raise serializers.ValidationError(f"Unsupported region: {value}")
        return value


class BulkScrapeSerializer(serializers.Serializer):
    items = ScrapeCreateSerializer(many=True)
    force = serializers.BooleanField(default=False, required=False)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("items must not be empty")
        if len(value) > 500:
            raise serializers.ValidationError("max 500 items per bulk request")
        return value


class ScrapeJobSerializer(serializers.ModelSerializer):
    product_url = serializers.CharField(read_only=True)

    class Meta:
        model = ScrapeJob
        fields = [
            "id",
            "region",
            "shop_id",
            "item_id",
            "status",
            "force",
            "error_message",
            "json_path",
            "product_url",
            "created_at",
            "updated_at",
            "finished_at",
        ]
        read_only_fields = fields


class ProductRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRecord
        fields = [
            "id",
            "region",
            "shop_id",
            "item_id",
            "json_path",
            "last_job",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
