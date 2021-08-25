import os
import configparser

from client import GoogleCloudClient, GradecardClient
from constants import (
    ROSTER_SHEET_NAME,
    ROSTER_SHEET_RANGE_W,
    ROSTER_HEADER,
    EXPORT_SHEET_NAME,
    EXPORT_HEADER,
    EXPORT_SHEET_RANGE_R,
    EXPORT_SHEET_RANGE_W,
    CARD_SHEETS,
    EXPORT_SHEET_RANGE_HEADER,
    DATA_SHEET_NAME,
    CONFIG_PATH,
)
from secrets import (
    BASE_STUDENT_SPREADSHEET_ID,
    STUDENT_CARDS_FOLDER_ID,
    TA_CARDS_FOLDER_ID,
    GRADECARD_SPREADSHEET_ID,
)
from util import (
    get_entry,
    get_entries_across,
    get_entries,
    set_entry,
    set_entries_across,
    now,
    truncate_values,
)


class GoogleCloudService:
    def __init__(self):
        self.spreadsheet_id = GRADECARD_SPREADSHEET_ID
        self.client = GoogleCloudClient()

    def add_students(self, roster):
        # Create roster sheet in spreadsheet, if it does not exist
        sheets = self.client.get_sheets_from_spreadsheet(
            spreadsheet_id=self.spreadsheet_id
        )
        if ROSTER_SHEET_NAME not in sheets:
            print("[INFO] Creating roster sheet in spreadsheet...")
            self.client.create_sheet_in_spreadsheet(
                spreadsheet_id=self.spreadsheet_id,
                sheet_name=ROSTER_SHEET_NAME,
                header=ROSTER_HEADER,
            )

        # Get list of existing students
        values = self.client.get_values_from_sheet(
            sheet_range=ROSTER_SHEET_RANGE_W, spreadsheet_id=self.spreadsheet_id
        )
        andrew_ids = set(get_entries(values, "Andrew ID", ROSTER_HEADER))

        # Get list of new students
        new_students = []
        for student in roster:
            if get_entry(student, "Andrew ID", ROSTER_HEADER) not in andrew_ids:
                new_students.append(list(student))

        # Append new students to roster sheet
        if new_students:
            print("[INFO] Adding new students to spreadsheet...")
            values.extend(new_students)
            self.client.set_values_in_sheet(
                sheet_range=ROSTER_SHEET_RANGE_W,
                spreadsheet_id=self.spreadsheet_id,
                values=values,
            )

    def create_cards(self, agents):
        # Create export sheet in spreadsheet, if it does not exist
        sheets = self.client.get_sheets_from_spreadsheet(
            spreadsheet_id=self.spreadsheet_id
        )
        if EXPORT_SHEET_NAME not in sheets:
            print("[INFO] Creating export sheet in spreadsheet...")
            self.client.create_sheet_in_spreadsheet(
                spreadsheet_id=self.spreadsheet_id,
                sheet_name=EXPORT_SHEET_NAME,
                header=EXPORT_HEADER,
            )

        # Get list of students in export sheet
        values = self.client.get_values_from_sheet(
            sheet_range=EXPORT_SHEET_RANGE_R, spreadsheet_id=self.spreadsheet_id
        )
        andrew_ids = set(get_entries(values, "andrew_id", EXPORT_HEADER))

        # Get list of students in roster sheet
        roster = self.client.get_values_from_sheet(
            sheet_range=ROSTER_SHEET_RANGE_W, spreadsheet_id=self.spreadsheet_id
        )

        # Get list of new students
        new_students = []
        for student in roster:
            # Get fields from record
            andrew_id = get_entry(student, "Andrew ID", ROSTER_HEADER)
            email_id = get_entry(student, "Email", ROSTER_HEADER)

            if andrew_id not in andrew_ids:
                entries_dict = {
                    "andrew_id": andrew_id,
                    "email": email_id,
                    "last_updated": now(),
                }

                # Create student card
                if "student" in agents:
                    print(f"[INFO] Creating student card for {andrew_id}...")
                    ssid = self.client.create_new_spreadsheet(
                        f"[15-251] Student Card ({andrew_id})",
                        CARD_SHEETS,
                        STUDENT_CARDS_FOLDER_ID,
                        [email_id],
                    )
                    entries_dict["ssid"] = ssid

                # Create TA card
                if "ta" in agents:
                    print(f"[INFO] Creating TA card for {andrew_id}...")
                    _ssid = self.client.create_new_spreadsheet(
                        andrew_id, CARD_SHEETS, TA_CARDS_FOLDER_ID
                    )
                    entries_dict["_ssid"] = _ssid

                # Create new record
                record = ["" for _ in EXPORT_HEADER]
                set_entries_across(record, entries_dict, EXPORT_HEADER)
                new_students.append(record)

            if len(new_students) >= 5:
                print("[INFO] Adding new cards IDs to spreadsheet...")
                values.extend(new_students)
                self.client.set_values_in_sheet(
                    sheet_range=EXPORT_SHEET_RANGE_W,
                    spreadsheet_id=self.spreadsheet_id,
                    values=truncate_values(values, EXPORT_HEADER),
                )
                new_students = []

        if new_students:
            print("[INFO] Adding new cards IDs to spreadsheet...")
            values.extend(new_students)
            self.client.set_values_in_sheet(
                sheet_range=EXPORT_SHEET_RANGE_W,
                spreadsheet_id=self.spreadsheet_id,
                values=truncate_values(values, EXPORT_HEADER),
            )

    def update_views(self, views, agents, permitlist=None, onwards_andrew_id=None):
        # Get list of students in export sheet
        values = self.client.get_values_from_sheet(
            sheet_range=EXPORT_SHEET_RANGE_R, spreadsheet_id=self.spreadsheet_id
        )

        onwards_flag = onwards_andrew_id is None

        for record in values:
            andrew_id = get_entry(record, "andrew_id", EXPORT_HEADER)
            onwards_flag = onwards_flag or andrew_id == onwards_andrew_id
            if permitlist is not None and andrew_id not in permitlist:
                continue
            if not onwards_flag:
                continue

            # Update student card view
            if "student" in agents:
                print(f"[INFO] Updating student view for {andrew_id}...")
                ssid = get_entry(record, "ssid", EXPORT_HEADER)
                self.client.copy_sheets_to_spreadsheet(
                    BASE_STUDENT_SPREADSHEET_ID, views, ssid, views
                )

            # Update TA card view
            if "ta" in agents:
                print(f"[INFO] Updating TA view for {andrew_id}...")
                _ssid = get_entry(record, "_ssid", EXPORT_HEADER)
                self.client.copy_sheets_to_spreadsheet(
                    BASE_STUDENT_SPREADSHEET_ID, views, _ssid, views
                )

            set_entry(record, now(), "last_updated", EXPORT_HEADER)

        self.client.set_values_in_sheet(
            sheet_range=EXPORT_SHEET_RANGE_W,
            spreadsheet_id=self.spreadsheet_id,
            values=truncate_values(values, EXPORT_HEADER),
        )

    def sync_data(self, agents, permitlist=None, onwards_andrew_id=None):
        # Get list of variables
        variables = self.client.get_values_from_sheet(
            sheet_range=EXPORT_SHEET_RANGE_HEADER, spreadsheet_id=self.spreadsheet_id
        )[0]

        # Get list of students in export sheet
        values = self.client.get_values_from_sheet(
            sheet_range=EXPORT_SHEET_RANGE_R, spreadsheet_id=self.spreadsheet_id
        )

        onwards_flag = onwards_andrew_id is None

        for record in values:
            andrew_id = get_entry(record, "andrew_id", EXPORT_HEADER)
            onwards_flag = onwards_flag or andrew_id == onwards_andrew_id
            if permitlist is not None and andrew_id not in permitlist:
                continue
            if not onwards_flag:
                continue

            # Sync student card data
            if "student" in agents:
                print(f"[INFO] Syncing student data for {andrew_id}...")

                public_variables = []
                for variable in variables:
                    if variable == "STOP":
                        # Stop syncing variables after this point
                        break
                    if variable[0] != "_":
                        public_variables.append(variable)

                entries = get_entries_across(record, public_variables, variables)
                data = list(zip(public_variables, entries))

                ssid = get_entry(record, "ssid", EXPORT_HEADER)
                self.client.set_values_in_sheet(
                    sheet_range=DATA_SHEET_NAME,
                    spreadsheet_id=ssid,
                    values=data,
                    clear_range=True,
                )

            # Sync TA card data
            if "ta" in agents:
                print(f"[INFO] Syncing TA data for {andrew_id}...")

                data = list(zip(variables, record))

                _ssid = get_entry(record, "_ssid", EXPORT_HEADER)
                self.client.set_values_in_sheet(
                    sheet_range=DATA_SHEET_NAME,
                    spreadsheet_id=_ssid,
                    values=data,
                    clear_range=True,
                )

            set_entry(record, now(), "last_updated", EXPORT_HEADER)

        self.client.set_values_in_sheet(
            sheet_range=EXPORT_SHEET_RANGE_W,
            spreadsheet_id=self.spreadsheet_id,
            values=truncate_values(values, EXPORT_HEADER),
        )


class GradescopeService:
    def __init__(self):
        self.client = GradecardClient()

    def get_configs(self):
        # Fetch list of config files
        try:
            config_files = [i for i in os.listdir(CONFIG_PATH) if i.endswith(".ini")]
        except FileNotFoundError:
            return []

        # Get names for config files
        configs = []
        for config_file in config_files:
            config = configparser.ConfigParser()
            config.read(os.path.join(CONFIG_PATH, config_file))
            try:
                name = config["names"]["homework"]
            except KeyError:
                continue

            configs.append({"name": name, "value": config_file})

        # Sort configs
        configs.sort(
            key=lambda config: map(
                lambda s: int(s) if s.isdigit() else s, config["name"].split(" ")
            )
        )

        return configs

    def load_data_from_config(self, config):
        pass
