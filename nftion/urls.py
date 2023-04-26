from django.urls import path

from .views import NFTCollectionsView, NFTList, NftTypeListAPIView

urlpatterns = [
    path('nft-collections/', NFTCollectionsView.as_view(), name='nft_collections'),
    path('nft/', NFTList.as_view(), name='nft-list'),
    path('nft-types/', NftTypeListAPIView.as_view(), name='nft-types'),
]
