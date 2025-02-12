from bleak import BleakClient
from flask_socketio import SocketIO

from DataModel.Vehicle import Vehicle
from LocationService.Trigo import Angle, Position
from VehicleManagement.AnkiController import AnkiController
from VehicleManagement.VehicleController import Turns, VehicleController

from LocationService.LocationService import LocationService
from LocationService.Track import FullTrack


class ModelCar(Vehicle):
    """
    Base Car implementation that reacts to hacking effects and forwards speed/offset changes to
    the controller, if appropriate
    """
    def __init__(self, vehicle_id: str, controller: VehicleController, track: FullTrack, socketio: SocketIO) -> None:
        super().__init__(vehicle_id, socketio)
        self._controller = controller
        self._location_service: LocationService = LocationService(track, self.__on_location_service_update)

        self.__speed: int = 0
        self.__speed_request: int = 0
        self.__speed_factor: float = 1.0
        self.__min_speed_thr = 20

        self.__lane_change: int = 0
        self.__lane_change_request: int = 0
        self.__lange_change_blocked: bool = False

        self.__turn: int = 0
        self.__turn_request: int = 0
        self.__turn_blocked: bool = False

        self.__is_light_on: bool = False
        self.__is_light_inverted: bool = False
        self.__is_safemode_on: bool = True

        self._road_piece: int = 0
        self._prev_road_piece: int = 0
        self._road_location: int = 0
        self._offset_from_center: float = 0.0
        self._speed_actual: int = 0
        self._direction: int = 0
        self._battery: str = ""
        self._version: str = ""

        self._model_car_not_reachable_callback = None
        return

    def __del__(self) -> None:
        self._controller.__del__()
        self._location_service.__del__()
        return

    def get_typ_of_controller(self):
        return type(self._controller)

    def set_model_car_not_reachable_callback(self, function_name) -> None:
        self._model_car_not_reachable_callback = function_name
        return

    def _on_model_car_not_reachable(self, err_msg: str) -> None:
        if self._model_car_not_reachable_callback is not None:
            self._model_car_not_reachable_callback(self.vehicle_id, self.player, err_msg)
        return

    def _on_driving_data_change(self) -> None:
        if self._driving_data_callback is not None:
            self._driving_data_callback(self.get_driving_data())
        return

    @property
    def speed_request(self) -> float:
        return self.__speed_request

    @speed_request.setter
    def speed_request(self, value: float) -> None:
        if not value == self.__speed_request:
            self.__speed_request = value
            self.__calculate_speed()
        return

    @property
    def speed_factor(self) -> float:
        return self.__speed_factor

    @speed_factor.setter
    def speed_factor(self, value: float) -> None:
        if not value == self.__speed_factor:
            self.__speed_factor = value
            self.__calculate_speed()
        return

    @property
    def speed(self) -> float:
        return self.__speed

    def __calculate_speed(self) -> None:
        speed_calculated = self.__speed_request * self.__speed_factor
        if speed_calculated > self.__min_speed_thr:
            self.__speed = speed_calculated
        else:
            self.__speed = 0
            self._speed_actual = 0
            self._on_driving_data_change()

        self._location_service.set_speed_percent(self.__speed)
        self._controller.change_speed_to(int(self.__speed))
        return

    @property
    def lane_change_request(self) -> int:
        return self.__lane_change_request

    @lane_change_request.setter
    def lane_change_request(self, value: int) -> None:
        self.__lane_change_request = value
        self.__calculate_lane_change()
        return

    @property
    def lange_change_blocked(self) -> bool:
        return self.__lange_change_blocked

    @lange_change_blocked.setter
    def lange_change_blocked(self, value: bool) -> None:
        self.__lange_change_blocked = value
        return

    @property
    def lane_change(self) -> int:
        return self.__lane_change

    def __update_own_langechane(self):
        """
        Updates the own current lane on the track. Needed to ensure
        a lane change will go to the right offset
        """
        if self._offset_from_center > 55.625:
            self.__lane_change = 3
        elif self._offset_from_center > 33.375:
            self.__lane_change = 2
        elif self._offset_from_center > 11.125:
            self.__lane_change = 1
        elif self._offset_from_center > -11.125:
            self.__lane_change = 0
        elif self._offset_from_center > -33.375:
            self.__lane_change = -1
        elif self._offset_from_center > -55.625:
            self.__lane_change = -2
        else:
            self.__lane_change = -3

    def __calculate_lane_change(self) -> None:
        if self.__lange_change_blocked:
            return

        self.__update_own_langechane()
        self.__lane_change += self.__lane_change_request

        if self.__lane_change < -3:
            self.__lane_change = -3
        elif self.__lane_change > 3:
            self.__lane_change = 3

        self._location_service.set_offset_int(self.__lane_change)
        self._location_service.set_speed_percent(self.__speed)
        self._controller.change_lane_to(self.__lane_change, self.__speed)
        return

    @property
    def turn_request(self) -> int:
        return self.__turn_request

    @turn_request.setter
    def turn_request(self, value: int) -> None:
        self.__turn_request = value
        self.__calculate_turn()

    @property
    def turn_blocked(self) -> bool:
        return self.__turn_blocked

    @turn_request.setter
    def turn_blocked(self, value: bool) -> None:
        self.__turn_blocked = value

    @property
    def turn(self):
        return self.__turn

    def __calculate_turn(self) -> None:
        if self.__turn_blocked:
            return

        self._location_service.do_uturn()
        self._controller.do_turn_with(Turns.A_UTURN)
        return

    def switch_lights(self, value: bool) -> None:
        self.__is_light_on = value
        return

    def set_safemode(self, value: bool) -> None:
        self.__is_safemode_on = value

    def get_driving_data(self) -> dict:
        driving_info_dic = {
            'vehicle_id': self.vehicle_id,
            'player': self.player,
            'speed_request': self.__speed_request,
            'lane_change_blocked': self.__lange_change_blocked,
            'is_light_on': self.__is_light_on,
            'is_safemode_on': self.__is_safemode_on,
            'active_hacking_scenario': self._active_hacking_scenario,
            'road_piece': self._road_piece,
            'road_location': self._road_location,
            'offset_from_center': self._offset_from_center,
            'speed_actual': self._speed_actual,
            'direction': self._direction,
            'battery': self._battery,
            'version': self._version
        }
        return driving_info_dic

    def _receive_location(self, value_tuple) -> None:
        location, piece, offset, speed, clockwise = value_tuple
        self._road_location = location
        self._road_piece = piece
        self._offset_from_center = offset
        if self.__speed == 0:
            self._speed_actual = 0
        else:
            self._speed_actual = speed
        self._direction = clockwise

        self._on_driving_data_change()
        return

    def _receive_transition(self, value_tuple) -> None:
        piece, piece_prev, offset, direction = value_tuple
        self._road_piece = piece
        self._prev_road_piece = piece_prev
        self._offset_from_center = offset
        self._direction = direction
        return

    def _receive_offset_update(self, value_tuple) -> None:
        offset = value_tuple[0]
        self._offset_from_center = offset
        return

    def _receive_version(self, value_tuple) -> None:
        self._version = str(value_tuple)
        return

    def _receive_battery(self, value_tuple) -> None:
        self._battery = str(value_tuple)

        self._on_driving_data_change()
        return

    def __on_location_service_update(self, pos: Position, angle: Angle, _: dict):
        self._send_location_via_socketio(pos, angle)

    def _send_location_via_socketio(self, pos: Position, angle: Angle) -> None:
        data = { 'car': self.vehicle_id, 'position': pos.to_dict(), 'angle': angle.get_deg() }
        self._socketio.emit("car_positions", data)
        return
