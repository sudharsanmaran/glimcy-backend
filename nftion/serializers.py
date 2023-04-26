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
        price_lte = data.get('price_lte')
        price_gte = data.get('price_gte')
        if price_lte is not None and price_gte is not None and price_lte < price_gte:
            raise serializers.ValidationError("Price max should be greater than price min.")
        
        deals_number_lte = data.get('deals_number_lte')
        deals_number_gte = data.get('deals_number_gte')
        if deals_number_lte is not None and deals_number_gte is not None and deals_number_lte < deals_number_gte:
            raise serializers.ValidationError("Deals number max should be greater than deals number min.")
        
        if data.get('ordering') and not hasattr(Nft, data.get('ordering').lstrip('-')):
            raise serializers.ValidationError('Invalid ordering field')
        

        return data