from rest_framework import serializers
from .models import Nft, NftType


class NftTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NftType
        fields = ['id', 'name']


class NFTSerializer(serializers.ModelSerializer):
    nft_type = NftTypeSerializer()

    class Meta:
        model = Nft
        fields = '__all__'


class NFTListFilterSerializer(serializers.Serializer):
    offer = serializers.BooleanField(required=False)
    ordering = serializers.CharField(max_length=100, required=False)
    price_lte = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)
    price_gte = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)
    deals_number_lte = serializers.IntegerField(required=False)
    deals_number_gte = serializers.IntegerField(required=False)
    nft_type_ids = serializers.RegexField(r'^\d+(,\d+)*$', required=False)

    def validate(self, data):
        data = self.initial_data
        price_lte = data.get('price__lte')
        price_gte = data.get('price__gte')
        if price_lte and not price_lte.isdigit():
            raise serializers.ValidationError("Price max should be float type")
        if price_lte:
            price_lte = float(data.get('price__lte'))
        if price_gte and not price_gte.isdigit():
            raise serializers.ValidationError("Price min should be float type")
        if price_gte:
            price_gte = float(data.get('price__gte'))
        if price_lte and price_gte and price_lte < price_gte:
            raise serializers.ValidationError("Price max should be greater than price min.")

        deals_number_lte = data.get('deals_number__lte')
        deals_number_gte = data.get('deals_number__gte')
        if deals_number_lte and not deals_number_lte.isdigit():
            raise serializers.ValidationError("Deals number min should be int type")
        if deals_number_lte:
            deals_number_lte = int(data.get('deals_number__lte'))
        if deals_number_gte and not deals_number_gte.isdigit():
            raise serializers.ValidationError("Deals number max should be int type")
        if deals_number_gte:
            deals_number_gte = int(data.get('deals_number__gte'))
        if deals_number_lte and deals_number_gte and deals_number_lte < deals_number_gte:
            raise serializers.ValidationError("Deals number max should be greater than deals number min.")

        if data.get('ordering') and not hasattr(Nft, data.get('ordering').lstrip('-')):
            raise serializers.ValidationError('Invalid ordering field')
        if data.get('offset') and not data.get('offset').isdigit():
            raise serializers.ValidationError('offset should be int type')
        if data.get('limit') and not data.get('limit').isdigit():
            raise serializers.ValidationError('limit should be int type')
        return data
