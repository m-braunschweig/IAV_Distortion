# Copyright 2024 IAV GmbH
#
# This file is part of the IAV-Distortion project an interactive
# and educational showcase designed to demonstrate the need
# of automotive cybersecurity in a playful, engaging manner.
# and is released under the "Apache 2.0". Please see the LICENSE
# file that should have been included as part of this package.
#
import logging
from typing import List
from collections import deque
from flask_socketio import SocketIO

from DataModel.ModelCar import ModelCar
from DataModel.Vehicle import Vehicle
from VehicleManagement.AnkiController import AnkiController
from VehicleManagement.FleetController import FleetController
from VehicleManagement.VehicleController import VehicleController


class EnvironmentManager:

    def __init__(self, fleet_ctrl: FleetController, socketio: SocketIO):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        self.logger.addHandler(console_handler)

        self._fleet_ctrl = fleet_ctrl
        self._socketio: SocketIO = socketio
        self._player_queue_list: deque[str] = deque()
        self._active_anki_cars: List[Vehicle] = []
        self.staff_ui = None

        # self.find_unpaired_anki_cars()


    def set_staff_ui(self, staff_ui):
        self.staff_ui = staff_ui
        return


    def connect_all_anki_cars(self) -> list[Vehicle]:
        """
        Connects all unpaired Anki cars.

        Returns:
            A list of `Vehicle` objects representing the connected Anki cars.
        """
        found_anki_cars = self.find_unpaired_anki_cars()
        for vehicle_uuid in found_anki_cars:
            self.logger.info(f'Connecting to vehicle {vehicle_uuid}')
            self.add_vehicle(vehicle_uuid)
        return self.get_vehicle_list()

    def find_unpaired_anki_cars(self) -> list[str]:
        """
        Finds unpaired Anki cars by scanning for devices and removing the ones that are already active.

        Returns:
            A list of strings representing the UUIDs of the unpaired Anki cars.
        """
        self.logger.info("Searching for unpaired Anki cars")
        found_devices = self._fleet_ctrl.scan_for_anki_cars()
        # remove already active uuids:
        new_devices = []
        connected_devices = []
        for v in self._active_anki_cars:
            connected_devices.append(v.get_vehicle_id())
        new_devices = [device for device in found_devices if device not in connected_devices]

        if new_devices:
            self.logger.info(f"Found new devices: {new_devices}")
        else:
            self.logger.info("No new devices found")

        return new_devices

    def get_vehicle_list(self) -> list[Vehicle]:
        return self._active_anki_cars

    def remove_vehicle(self, uuid_to_remove: str):
        """
        Remove both vehicle and the controlling player for a given vehicle
        """
        self.logger.info(f"Removing vehicle with UUID {uuid_to_remove}")

        found_vehicle = next((o for o in self._active_anki_cars if o.vehicle_id == uuid_to_remove), None)
        if found_vehicle is not None:
            player = found_vehicle.get_player()
            if player is not None:
                self._socketio.emit('player_removed', player)
            found_vehicle.remove_player()
            self._active_anki_cars.remove(found_vehicle)
            found_vehicle.__del__()

        self._assign_players_to_vehicles()
        self.logger.debug("Updated list of active vehicles: %s", self._active_anki_cars)

        self._update_staff_ui()
        return

    def update_queues_and_get_vehicle(self, player_id: str) -> Vehicle | None:
        """
        Updates the queues and attempts to get a vehicle for the given player.

        Parameters:
            player_id (str): The ID of the player.

        Returns:
            Vehicle | None: The vehicle associated with the player, if found. Otherwise, None.
        """
        self._add_player_to_queue_if_appropiate(player_id)
        self._assign_players_to_vehicles()
        self._update_staff_ui()
        for v in self._active_anki_cars:
            if v.get_player() == player_id:
                return v
        self._update_staff_ui()
        return None

    def _add_player_to_queue_if_appropiate(self, player_id: str) -> None:
        """
        Adds a player to the queue, if it's appropriate (as in the
            player isn't controlling a vehicle already and the player
            also isn't in the queue already)
        """
        for v in self._active_anki_cars:
            if v.get_player() == player_id:
                return
        for p in self._player_queue_list:
            if p == player_id:
                return
        self._player_queue_list.append(player_id)
        return

    def _assign_players_to_vehicles(self) -> None:
        """
        Assigns players to vehicles.

        Iterates over the list of active Anki cars and checks if each car is free.
        If a car is free, it checks if the player queue is empty. If the player queue is empty,
        it updates the staff UI and returns. Otherwise, it removes the player at the beginning of the
        player queue and emits a 'player_active' event using the SocketIO instance. It then sets the player
        on the car and continues to the next car. Finally, it updates the staff UI.

        """
        for v in self._active_anki_cars:
            if v.is_free():
                if len(self._player_queue_list) == 0:
                    self._update_staff_ui()
                    return
                p = self._player_queue_list.popleft()
                self._socketio.emit('player_active', p)
                v.set_player(p)
        self._update_staff_ui()
        return

    def add_player(self, player_id: str) -> None:
        """
        Adds a player to the player queue if they are not already in the queue.
        """
        if player_id in self._player_queue_list:
            print(f'Player {player_id} is already in the queue!')
            return
        else:
            self._player_queue_list.append(player_id)
            print(self._player_queue_list)
        self._update_staff_ui()
        return

    def remove_player_from_waitlist(self, player_id: str) -> None:
        """
        Removes a player from the waitlist and emits a 'player_removed' event.
        """
        if player_id in self._player_queue_list:
            self._player_queue_list.remove(player_id)
        # TODO: Show other page when the user gets removed from here
        self._socketio.emit('player_removed', player_id)
        self._update_staff_ui()
        return

    def remove_player_from_vehicle(self, player: str) -> None:
        """
        Removes a player from the waitlist and emits a 'player_removed' event.
        """
        self.logger.info(f"Removing player with UUID {player} from vehicle")
        for v in self._active_anki_cars:
            if v.get_player() == player:
                v.remove_player()
                self._socketio.emit('player_removed', player)
                # TODO: define how to control vehicle without player
        self._update_staff_ui()
        return

    def add_vehicle(self, uuid: str) -> None:
        """
        Adds a vehicle to the list of active Anki cars.
        """
        self.logger.debug(f"Adding vehicle with UUID {uuid}")

        anki_car_controller = AnkiController()
        temp_vehicle = ModelCar(uuid, anki_car_controller)
        temp_vehicle.initiate_connection(uuid)
        # TODO: add a check if connection was successful 

        self._active_anki_cars.append(temp_vehicle)
        self._assign_players_to_vehicles()
        self._update_staff_ui()
        return

    def _update_staff_ui(self) -> None:
        if self.staff_ui is not None:
            self.staff_ui.publish_new_data()
        else:
            print("staff_ui instance is not yet set!")
        return

    def get_controlled_cars_list(self) -> List[str]:
        """
        Returns a list of vehicle IDs for all active Anki cars that are currently controlled by a player.

        :return: A list of strings representing the vehicle IDs of the active Anki cars.
        :rtype: List[str]
        """
        l = []
        for v in self._active_anki_cars:
            if v.get_player() is not None:
                l.append(v.get_vehicle_id())
        return l

    def get_free_car_list(self) -> List[str]:
        """
        Returns a list of vehicle IDs for all active Anki cars that are currently free.

        :return: A list of strings representing the vehicle IDs of the active Anki cars.
        :rtype: List[str]
        """
        l = []
        for v in self._active_anki_cars:
            if v.get_player() is None:
                l.append(v.get_vehicle_id())
        return l

    def get_waiting_player_list(self) -> List[str]:
        """
        Returns a list of player IDs for all players in the player queue.

        :return: A list of strings representing the player IDs of the players in the player queue.
        :rtype: List[str]
        """
        tmp = []
        for p in self._player_queue_list:
            tmp.append(p)
        return tmp

    def get_car_from_player(self, player: str) -> Vehicle | None:
        """
        Returns the `Vehicle` object associated with the given `player` ID,
        or `None` if no vehicle is found.
        """
        for v in self._active_anki_cars:
            if v.get_player() == player:
                return v
        return None

    def get_mapped_cars(self) -> List[dict]:
        """
        Returns a list of dictionaries containing the player and car information
        for all active Anki cars that are currently controlled by a player.

        """
        tmp = []
        for v in self._active_anki_cars:
            if v.get_player() is not None:
                tmp.append({
                    'player': v.get_player(),
                    'car': v.get_vehicle_id()
                })
        return tmp
