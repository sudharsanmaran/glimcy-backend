from django.db import models


class Nft(models.Model):
    """ Model for parser """
    name = models.CharField(max_length=255, verbose_name='Nft name')
    img_link = models.CharField(max_length=255, verbose_name='Link to nft image')
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Nft price")
    nft_type = models.ForeignKey('NftType', on_delete=models.CASCADE, verbose_name='Type of nft',
                                 related_name='nft_type')
    offer = models.CharField(max_length=155)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2)
    opensea_link = models.CharField(max_length=255, unique=True)
    deals_number = models.IntegerField()
    monthly_roi = models.DecimalField(max_digits=14, decimal_places=2)
    # last_sale -> event_timestamp if event type successful
    last_sale_date = models.DateTimeField()
    max_profit_per_sale = models.DecimalField(max_digits=14, decimal_places=2)
    min_profit_sale = models.DecimalField(max_digits=14, decimal_places=2)
    average_sale_duration = models.DurationField(null=True)
    average_hold_duration = models.DurationField(null=True)
    # fees -> seller fees
    royalty = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Royalty percent')

    buy_link = models.CharField(max_length=255, verbose_name='Link to buy nft')

    update_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_opensea_link(self):
        return self.opensea_link


class NftType(models.Model):
    """ Types of Nft model """
    name = models.CharField(max_length=255, verbose_name='Type name')

    def __str__(self):
        return self.name


class HistoryPrice(models.Model):
    """ Model for storing historical price of tickers """
    ticker = models.CharField(max_length=155)
    price = models.FloatField(null=True, blank=True)
    date = models.DateField(auto_now_add=False, null=True, blank=True)

    class Meta:
        unique_together = ('ticker', 'date')

    def __str__(self):
        return ''.join(str(self.date.isoformat()))


class Collection(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, blank=True)
    logo = models.CharField(max_length=200, blank=True)
    contracts = models.JSONField()
    timestamp = models.DateTimeField(auto_now=True)
    verified = models.BooleanField(default=True)

    @classmethod
    def update_or_create_from_api(cls, data):
        collection_id = data['id']
        defaults = {
            'name': data.get('name', ''),
            'logo': data.get('logo', ''),
            'contracts': data['contracts']
        }
        obj, created = cls.objects.update_or_create(
            id=collection_id,
            defaults=defaults
        )
        return obj, created
