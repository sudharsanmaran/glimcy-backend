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

class NFTListLimitOffsetPagination(LimitOffsetPagination):

    def paginate_queryset(self, queryset, request, view=None):

        self.limit = self.get_limit(request)
        self.count = self.get_count(queryset)
        self.offset = self.get_offset(request)
        self.request = request

        if not request.user.subscription_end or request.user.subscription_end < datetime.utcnow().replace(tzinfo=pytz.utc):
            self.limit = 5
            self.offset = 0

        if self.limit is None:
            return None


        if self.count > self.limit:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []


        return list(queryset[self.offset:self.offset + self.limit])


class NFTList(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Nft.objects.all()
    pagination_class = NFTListLimitOffsetPagination
    serializer_class = NFTSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = NFTFilter
    serializer_class_filter = NFTListFilterSerializer

    def filter_queryset(self, queryset):
        filter_serializer = self.serializer_class_filter(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        filter_data = filter_serializer.validated_data

        user = self.request.user
        offer = self.request.query_params.get('offer', None)

        if not user.subscription_end or user.subscription_end < datetime.utcnow().replace(tzinfo=pytz.utc):
            ordering = self.request.query_params.get('ordering', '-id')
            FINAL_MESSAGE = constants.NFT_LIMIT_MESSAGE
        else:
            ordering = self.request.query_params.get('ordering', '-update_time')
            FINAL_MESSAGE = constants.NFT_MESSAGE

        price_max = self.request.query_params.get('price__lte', None)
        price_min = self.request.query_params.get('price__gte', None)
        deals_number_max = self.request.query_params.get('deals_number__lte', None)
        deals_number_min = self.request.query_params.get('deals_number__gte', None)
        nft_type_ids = self.request.query_params.get('nft_type_ids')
        ordering = filter_data.get('ordering', '-update_time')
        price_max = filter_data.get('price__lte', None)
        price_min = filter_data.get('price__gte', None)
        deals_number_max = filter_data.get('deals_number__lte', None)
        deals_number_min = filter_data.get('deals_number__gte', None)
        nft_type_ids = filter_data.get('nft_type_ids')

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
        return queryset, FINAL_MESSAGE

    def list(self, request, *args, **kwargs):

        queryset, FINAL_MESSAGE = self.filter_queryset(self.get_queryset())

        pagination = self.paginate_queryset(queryset)
        if pagination is not None:
            serializer = self.get_serializer(pagination, many=True)

            context_data = {
                'message': FINAL_MESSAGE,
                'data': serializer.data,
            }
            return self.get_paginated_response(context_data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({'message': FINAL_MESSAGE, 'data':serializer})


class NftTypeListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = NftType.objects.all()
    serializer_class = NftTypeSerializer
