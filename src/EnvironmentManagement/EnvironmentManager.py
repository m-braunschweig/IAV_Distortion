# Copyright 2024 IAV GmbH
#
# This file is part of the IAV-Distortion project an interactive
# and educational showcase designed to demonstrate the need
# of automotive cybersecurity in a playful, engaging manner.
# and is released under the "Apache 2.0". Please see the LICENSE
# file that should have been included as part of this package.
#
import logging
from DataModel.Vehicle import Vehicle
from VehicleManagement.FleetController import FleetController
from VehicleManagement.VehicleController import VehicleController


class EnvironmentManager:

    def __init__(self, fleet_ctrl: FleetController):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        self.logger.addHandler(console_handler)
        self._fleet_ctrl = fleet_ctrl
        self._player_uuid_map = {}
        self._active_anki_cars = []
        self.staff_ui = None

        # self.find_unpaired_anki_cars()

    def set_staff_ui(self, staff_ui):
        self.staff_ui = staff_ui
        return

    def get_player_uuid_mapping(self):
        return self._player_uuid_map

    def set_player_uuid_mapping(self, player_id: str, uuid: str):
        self.logger.info(f"Adding player UUID mapping: player_id={player_id}, uuid={uuid}")
        self._player_uuid_map.update({player_id: uuid})
        self.logger.debug("Updated player UUID map: %s", self._player_uuid_map)
        self._update_staff_ui()

    def connect_all_anki_cars(self) -> list[Vehicle]:
        self.logger.info('Connecting to all Anki cars')
        try:
            found_anki_cars = self.find_unpaired_anki_cars()
            for vehicle_uuid in found_anki_cars:
                self.logger.info(f'Connecting to vehicle {vehicle_uuid}')
                self.add_vehicle(vehicle_uuid)
        except Exception as e:
            self.logger.error(f'Failed to connect to all Anki cars: {str(e)}')
        return self.get_vehicle_list()

    def find_unpaired_anki_cars(self) -> list[str]:
        # Funktion zum Fahrzeuge Suchen und Verbinden
        # BLE device suchen
        # mit Device verbinden, wenn bekannt, sonst via web interface
        self.logger.info("Searching for unpaired Anki cars")
        # vehicle initialisieren
        found_devices = self._fleet_ctrl.scan_for_anki_cars()
        # remove already active uuids:
        new_devices = [device for device in found_devices if device not in self._player_uuid_map.values()]

        if new_devices:
            self.logger.info(f"Found new devices: {new_devices}")
        else:
            self.logger.info("No new devices found")

        return new_devices

    def get_vehicle_list(self) -> list[Vehicle]:
        return self._active_anki_cars

    def remove_vehicle(self, uuid_to_remove: str):
        self.logger.info(f"Removing vehicle with UUID {uuid_to_remove}")
        player_to_remove = ''
        for player, uuid in self._player_uuid_map.items():
            if uuid == uuid_to_remove:
                player_to_remove = player

        if player_to_remove != '':
            del self._player_uuid_map[player_to_remove]
            self._update_staff_ui()

        self._active_anki_cars = [vehicle for vehicle in self._active_anki_cars if vehicle.uuid != uuid_to_remove]
        self.logger.debug("Updated list of active vehicles: %s", self._active_anki_cars)
        return

    def add_vehicle(self, uuid: str):
        self.logger.debug(f"Adding vehicle with UUID {uuid}")
        if uuid in self._player_uuid_map.values():
            print('UUID already exists!')
            return
        else:
            players_as_ints = [int(player) for player in self._player_uuid_map.keys()]
            if not players_as_ints:
                max_player = 0
                smallest_available_num = '1'
            else:
                max_player = max(players_as_ints)

            # find smallest available player
            for i in range(1, max_player+1):
                if i not in players_as_ints:
                    smallest_available_num = str(i)
                    break
                else:
                    smallest_available_num = str(max_player + 1)

            # print(f'Player: {smallest_available_num}, UUID: {uuid}')
            anki_car_controller = VehicleController()
            try:
                temp_vehicle = Vehicle(uuid, anki_car_controller)
            except ConnectionError as e:
                print(f"Failed to add vehicle: {e.message}")
                return
            if temp_vehicle:
                self.set_player_uuid_mapping(player_id=smallest_available_num, uuid=uuid)

                temp_vehicle.player = smallest_available_num
                self._active_anki_cars.append(temp_vehicle)
            return

    def _update_staff_ui(self):
        if self.staff_ui is not None:
            self.staff_ui.update_map_of_uuids(self._player_uuid_map)
        else:
            print("staff_ui instance is not yet set!")
        return
