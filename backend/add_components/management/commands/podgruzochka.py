# add_components/management/commands/load_ingredients.py
import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from CSV file "name,measurement_unit"'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)

    def handle(self, *args, **kwargs):
        csv_path = Path(kwargs['csv_path'])
        created, skipped = 0, 0
        with csv_path.open(encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                name, unit = row
                obj, is_created = Ingredient.objects.get_or_create(
                    name=name.strip(), measurement_unit=unit.strip()
                )
                created += int(is_created)
                skipped += int(not is_created)
        self.stdout.write(
            self.style.SUCCESS(
                f'Loaded: {created} ingredients, skipped duplicates: {skipped}')
        )
