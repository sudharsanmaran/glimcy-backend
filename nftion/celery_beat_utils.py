from django_celery_beat.models import IntervalSchedule, PeriodicTask


def populate_intervals_and_periodic_tasks():
    intervals = [
        {'every': 1, 'period': IntervalSchedule.MINUTES},
        {'every': 5, 'period': IntervalSchedule.MINUTES},
        {'every': 1, 'period': IntervalSchedule.HOURS},
        {'every': 5, 'period': IntervalSchedule.HOURS},
        {'every': 10, 'period': IntervalSchedule.HOURS},
        {'every': 1, 'period': IntervalSchedule.DAYS},
        {'every': 2, 'period': IntervalSchedule.DAYS},
        {'every': 3, 'period': IntervalSchedule.DAYS},
    ]

    for interval in intervals:
        obj, created = IntervalSchedule.objects.update_or_create(
            every=interval['every'], period=interval['period']
        )

    periodic_tasks = [
        {
            'name': 'get_collection_name_from_blockdaemon',
            'task': 'nftion.tasks.get_nft_collections_from_block_daemon',
            'interval': IntervalSchedule.objects.get(every=5, period=IntervalSchedule.MINUTES),
        },
        {
            'name': 'start_parsing_collection_file',
            'task': 'nftion.tasks.start_parsing_collection_file',
            'interval': IntervalSchedule.objects.get(every=1, period=IntervalSchedule.HOURS),
            'one_off': True,
        },
        {
            'name': 'start_parsing_collection_table',
            'task': 'nftion.tasks.start_parsing_collection_table',
            'interval': IntervalSchedule.objects.get(every=10, period=IntervalSchedule.HOURS),
        },
        {
            'name': 'update_existing_nft',
            'task': 'nftion.tasks.update_existing_nft',
            'interval': IntervalSchedule.objects.get(every=1, period=IntervalSchedule.HOURS),
        },
        {
            'name': 'update_auto',
            'task': 'nftion.tasks.update_auto',
            'interval': IntervalSchedule.objects.get(every=1, period=IntervalSchedule.DAYS),
        },
        {
            'name': 'update_old',
            'task': 'nftion.tasks.update_old',
            'interval': IntervalSchedule.objects.get(every=1, period=IntervalSchedule.DAYS),
        },
        {
            'name': 'delete_scam',
            'task': 'nftion.tasks.delete_scam',
            'interval': IntervalSchedule.objects.get(every=1, period=IntervalSchedule.DAYS),
        },
    ]

    for task in periodic_tasks:
        obj, created = PeriodicTask.objects.update_or_create(
            name=task['name'], defaults={
                'task': task['task'], 'interval': task['interval'],
                'one_off': task.get('one_off', False)
            }
        )
