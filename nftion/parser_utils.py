import gc
import os

import requests

from .NFT_parser import NftParser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nftion.settings")

import cloudscraper
from django.conf import settings
import django

from datetime import timedelta
from django.utils.timezone import make_aware, utc

django.setup()
from .models import Nft, NftType

scraper = cloudscraper.create_scraper()
headers = {
    "accept": "application/json",
    "X-API-KEY": settings.API_KEY
}

def to_timedelta(value):
    if isinstance(value, str) and ':' in value:
        hours, minutes, seconds = value.split(':')
        return timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))
    elif isinstance(value, str) and 'days' in value:
        days = int(value.split()[0])
        return timedelta(days=days)
    else:
        return value


def start_parser(urls: list):
    session = requests.Session()
    for nft in urls:
        nft_parser = NftParser(settings.API_KEY, nft, session=session)
        try:
            got = nft_parser.get_info()
            if not got:
                continue
            category, created = NftType.objects.get_or_create(
                name=got['category']
            )

            nft_id, _ = Nft.objects.update_or_create(
                opensea_link=got['opensea_link'],
                defaults={
                    'name': got['name'],
                    'price': float(got['price']),
                    'img_link': got['img_link'],
                    'nft_type': category,
                    'offer': got['type'],
                    'total_profit': got['total_profit'],
                    'monthly_roi': got['monthly_roi'],
                    'deals_number': got['deals_number'],
                    'last_sale_date': make_aware(got['last_sale_date'], timezone=utc),
                    'max_profit_per_sale': got['max_profit_per_sale'],
                    'min_profit_sale': got['min_profit_per_sale'],
                    'average_hold_duration': to_timedelta(got['average_hold_duration']),
                    'average_sale_duration': to_timedelta(got['average_sale_duration']),
                    'buy_link': got['buy_link'],
                    'royalty': got['royalty'],
                }
            )
            print(f'saved {nft_id.id}')
        except Exception as e:
            print(e)
        nft_id = None
        nft = None
        nft_parser = None
        got = None
        category = None
        created = None
        gc.collect()
    urls = None
    return True


def delete_scam_parser(urls: list):
    session = requests.Session()
    for nft in urls:
        nft_parser = NftParser(settings.API_KEY, nft, session=session)
        try:
            got = nft_parser.get_scam()
            if got:
                nft_object = Nft.objects.get(opensea_link=nft)
                print(f'deleted {nft_object.id}')
                nft_object.delete()

        except Exception as e:
            print(e)
        nft = None
        nft_parser = None
        got = None
        gc.collect()
    urls = None
    return True


def get_links(collections, col_id, some_list=None, counter=0, cursor='', direction=False):
    if some_list is None:
        some_list = []
    get_url = scraper.get(
        f'https://api.opensea.io/api/v1/assets?collection={collections[col_id]}&limit=200&{cursor}format=json&include_orders=false').json()
    next_url = None
    if get_url['next']:
        next_url = get_url['next']

    for i in get_url['assets']:
        if i['num_sales'] > 3:
            some_list.append(i['permalink'])

    get_url = None

    if next_url is not None:
        next_url = 'cursor=' + next_url + '&'
        print(f'next_url in collection {collections[col_id]}')
        if direction:
            get_links(collections, col_id=col_id, direction=True)
        else:
            get_links(collections, col_id, some_list, counter, cursor=next_url)

    else:
        print(f'saving hft, {some_list}')
        if start_parser(some_list):
            some_list = None
            print(direction)
            if direction:
                get_links(collections, col_id=col_id - 1, direction=True)
            else:
                get_links(collections, col_id=col_id + 1)
