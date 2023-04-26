from typing import List
import requests
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import Collection
from .parser_utils import get_links
from celery import shared_task


def update_or_create_from_api(api_data: dict):
    api_data["name"] = api_data["name"].lower().replace(" ", "-")
    collection, created = Collection.objects.update_or_create(
        id=api_data["id"],
        defaults={**api_data, "timestamp": timezone.now()},
    )
    return collection, created


@shared_task
def get_nft_collections_from_block_daemon(
        page_size: int = 100,
        page_token: str = None,
        collections: List[dict] = None,
) -> List[Collection]:
    collections = collections or []
    headers = {"accept": "application/json", "authorization": f"Bearer {settings.BLOCK_DAEMON_API_KEY}"}
    url = f"https://svc.blockdaemon.com/nft/v1/ethereum/mainnet/collections?sort_by=name&page_size={page_size}&verified=true"
    if page_token:
        url += f"&page_token={page_token}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    for item in data["data"]:
        collection, created = update_or_create_from_api(item)
        if created:
            collections.append(collection)
    next_page_token = data.get("meta").get('paging').get('next_page_token')
    if next_page_token:
        get_nft_collections_from_block_daemon(page_size, next_page_token, collections)

    return collections


@shared_task
def start_parsing_collection_file(*args, **kwargs):
    with open('collections.txt', 'r') as file:
        collections_list = file.read().split('\n')

    if 'direction' in kwargs.keys():
        print('DIRECTION IN KWARGS')
        x = -1
        while abs(x) < len(collections_list) / 2:
            try:
                get_links(collections_list, x, direction=True)
            except:
                pass
            x -= 1
    else:
        get_links(collections=collections_list, col_id=0)


@shared_task
def start_parsing_collection_table(request):
    collections = Collection.objects.all()
    paginator = Paginator(collections, 100)

    if 'direction' in request.GET:
        direction = True
    else:
        direction = False

    for page_num in range(1, paginator.num_pages + 1):
        page = paginator.get_page(page_num)
        collections_list = [col.name for col in page]

        x = -1 if direction else 0
        while abs(x) < len(collections_list):
            try:
                get_links(collections_list, x, direction=True)
            except:
                pass
            x -= 1 if direction else 1

    return JsonResponse({'message': 'Parsing started'})
