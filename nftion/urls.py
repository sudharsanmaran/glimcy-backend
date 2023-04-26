from django.urls import path

from .views import start_parsing_collection_table, NFTCollectionsView, start_parsing_collection_file, NFTList, NftTypeListAPIView

urlpatterns = [
    path('start-parsing/', start_parsing_collection_table, name='start_parsing'),
    path('start-parsing_1/', start_parsing_collection_file, name='start_parsing_1'),
    path('nft-collections/', NFTCollectionsView.as_view(), name='nft_collections'),
    path('nft/', NFTList.as_view(), name='nft-list'),
    path('nft-types/', NftTypeListAPIView.as_view(), name='nft-types'),
]
