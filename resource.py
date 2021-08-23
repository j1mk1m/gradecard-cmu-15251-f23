import csv

from cli import prompt_roster, prompt_views, prompt_students
from service import GoogleCloudService


class GoogleCloudResource:
    def __init__(self):
        self.service = GoogleCloudService()

    def post_add_new_students(self):
        try:
            roster_path = prompt_roster()
        except IndexError:
            raise FileNotFoundError("No CSV rosters found.") from None

        with open(roster_path) as f:
            roster = csv.reader(f)
            next(roster)  # ignore header
            self.service.add_students(roster)

    def post_create_cards(self):
        agents = ["student"]
        self.service.create_cards(agents)

    def post_update_card_data(self):
        agents = ["student"]
        students, onwards = prompt_students()
        self.service.sync_data(agents, students, onwards)

    def post_update_card_views(self):
        views = prompt_views()
        agents = ["student"]
        students, onwards = prompt_students()
        self.service.update_views(views, agents, students, onwards)
