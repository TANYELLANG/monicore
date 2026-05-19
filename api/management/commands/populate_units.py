from django.core.management.base import BaseCommand
from api.models import Tower, Unit

class Command(BaseCommand):
    help = 'Populates towers and units'

    def handle(self, *args, **kwargs):
        towers = ['C1', 'C2', 'C3', 'C4']
        floors = range(1, 19)
        letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N']

        for tower_name in towers:
            tower, _ = Tower.objects.get_or_create(name=tower_name)
            for floor in floors:
                for letter in letters:
                    Unit.objects.get_or_create(tower=tower, floor=floor, letter=letter)

        self.stdout.write(self.style.SUCCESS('Created towers and units!'))