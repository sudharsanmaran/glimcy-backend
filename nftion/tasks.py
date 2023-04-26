from datetime import datetime, timedelta
from typing import List
import requests
from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import Collection, Nft
from .parser_utils import get_links, delete_scam_parser, start_parser
from celery import shared_task


def update_or_create_from_api(api_data: dict):
    api_data["name"] = api_data["name"].lower().replace(" ", "-")
    collection, created = Collection.objects.update_or_create(
        id=api_data["id"],
        defaults={**api_data, "timestamp": timezone.now()},
    )
    return collection, created


def update_existing_nft(*args, **kwargs):
    checking_list = []

    print('ТАСКА АПДЕЙТ НАЧИНАЕТСЯ', f'ВОТ КВАРГИ {kwargs}')

    nft_objects = Nft.objects.all().order_by('id')
    if 'closing_position' in kwargs.keys():

        print(f'БЫЛО ОБНАРУЖЕНО КЛОСИНГ ПОЗИШН ОТ {kwargs.get("position")} ДО {kwargs.get("closing_position")}')

        for nft in nft_objects[int(kwargs.get('position')):int(kwargs.get('closing_position'))]:
            checking_list.append(nft.get_opensea_link())

    elif 'position' in kwargs.keys() and len(kwargs.keys()) == 1:

        print(f'ОБНАРУЖЕН ОБЫЧНЫЙ ПОЗИШН')

        for nft in nft_objects[int(kwargs.get('position')):]:
            checking_list.append(nft.get_opensea_link())

    else:
        print('ПОЗИШНОВ НЕТ, ПАРШУ ВСЕ ПОДРЯД')
        for nft in nft_objects:
            checking_list.append(nft.get_opensea_link())

    start_parser(checking_list)

    return


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
def start_parsing_collection_table():
    collections = Collection.objects.all()
    paginator = Paginator(collections, 100)

    for page_num in range(1, paginator.num_pages + 1):
        page = paginator.get_page(page_num)
        collections_list = [col.name for col in page]

        x = -1
        while abs(x) < len(collections_list):
            try:
                get_links(collections_list, x)
            except Exception as e:
                print(e)
            x -= 1

    return JsonResponse({'message': 'Parsing started'})


@shared_task
def delete_scam(*args, **kwargs):
    nfts = Nft.objects.filter(name__contains='warning')
    list_with_nft = [link.get_opensea_link() for link in nfts]

    delete_scam_parser(list_with_nft)


@shared_task
def update_old(*args, **kwargs):
    nft_objs = Nft.objects.filter(update_time__lt=datetime.now() - timedelta(days=1))
    objs_list = [link.get_opensea_link() for link in nft_objs]
    print(objs_list)
    start_parser(objs_list)


@shared_task
def update_auto(*args, **kwargs):
    third_part = round(Nft.objects.all().count() / 3)

    update_existing_nft.apply_async(
        kwargs={'position': 0, "closing_position": third_part}
    )
    update_existing_nft.apply_async(
        kwargs={'position': third_part, "closing_position": third_part * 2}
    )
    update_existing_nft.apply_async(
        kwargs={'position': third_part * 2}
    )
