from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

from .tasks import get_nft_collections_from_block_daemon, start_parsing_collection_table, start_parsing_collection_file
from .models import Collection, Nft, NftType
from .serializers import NFTSerializer, NftTypeSerializer, NFTListFilterSerializer
from .parser_utils import get_links
from django_filters import FilterSet, CharFilter

from datetime import datetime, timedelta
import pytz
from accounts import constants


class NFTCollectionsView(View):
    def get(self, request, *args, **kwargs):
        get_nft_collections_from_block_daemon()
        return JsonResponse({'message': 'Task to retrieve NFT collections has been scheduled.'})


class NFTFilter(FilterSet):
    nft_type_ids = CharFilter(required=False)

    class Meta:
        model = Nft
        fields = {
            'offer': ['exact'],
            'price': ['gte', 'lte'],
            'deals_number': ['gte', 'lte'],
        }


class NFTList(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Nft.objects.all()
    pagination_class = LimitOffsetPagination
    serializer_class = NFTSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = NFTFilter
    serializer_class_filter = NFTListFilterSerializer

    def filter_queryset(self, queryset):
        filter_serializer = self.serializer_class_filter(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        filter_data = filter_serializer.validated_data

        offer = self.request.query_params.get('offer', None)
        ordering = self.request.query_params.get('ordering', '-update_time')
        price_max = self.request.query_params.get('price__lte', None)
        price_min = self.request.query_params.get('price__gte', None)
        deals_number_max = self.request.query_params.get('deals_number__lte', None)
        deals_number_min = self.request.query_params.get('deals_number__gte', None)
        nft_type_ids = self.request.query_params.get('nft_type_ids')

        if nft_type_ids is not None and nft_type_ids != '':
            type_ids_list = [int(ids) for ids in nft_type_ids.split(',')]
            queryset = queryset.filter(nft_type_id__in=type_ids_list)

        if offer == 'true':
            queryset = queryset.filter(offer='Offer Available')
        elif offer == 'false':
            queryset = queryset.exclude(offer='Offer Available')

        if price_min is not None and price_max is not None:
            queryset = queryset.filter(price__range=[price_min, price_max])
        elif price_min is not None:
            queryset = queryset.filter(price__gte=price_min)
        elif price_max is not None:
            queryset = queryset.filter(price__lte=price_max)

        if deals_number_min is not None and deals_number_max is not None:
            queryset = queryset.filter(deals_number__range=[deals_number_min, deals_number_max])
        elif deals_number_min is not None:
            queryset = queryset.filter(deals_number__gte=deals_number_min)
        elif deals_number_max is not None:
            queryset = queryset.filter(deals_number__lte=deals_number_max)

        queryset = queryset.order_by(ordering)
        return queryset

    def list(self, request, *args, **kwargs):
        user = self.request.user
        if not user.subscription_end or user.subscription_end < datetime.utcnow().replace(tzinfo=pytz.utc):
            return Response({'error': constants.NFT_ERROR_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.filter_queryset(self.get_queryset())

        pagination = self.paginate_queryset(queryset)
        if pagination is not None:
            serializer = self.get_serializer(pagination, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NftTypeListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = NftType.objects.all()
    serializer_class = NftTypeSerializer
