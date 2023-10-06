#
# import sys
# if "/config/pyscript_modules" not in sys.path:
#     sys.path.append("/config/pyscript_modules")
# import inspect
import json
import asyncio
import time
from enum import Enum, Flag, auto
from collections import deque
from queue import Queue, Empty
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
Action = Flag('Action', ['Press', 'Hold', 'TerminateHold', 'Indeterminate', 'Up', 'Down', 'Left', 'Right', 'Center'])
Act_InLR = Action.Indeterminate | Action.Left | Action.Right
Act_HoldL = Action.Hold | Action.Left
Act_HoldR = Action.Hold | Action.Right
HELPER_BOOLEAN_MAP = {'on': True, 'off': False, True: 'on', False: 'off'}
TEMP = 1
ACTION_QUEUE = Queue(maxsize=10)

def turn_on_light(entity_id: str, brightness=None, get_attribute='brightness'):
    light.turn_on(entity_id=entity_id)
    count = 10
    while(count > 0):
        try:
            state = state.get(f'{entity_id}.{get_attribute}')
            break
        except AttributeError:
            asyncio.sleep(0.2)
            pass
        count -= 1
    # time.sleep(10)
    # log.info(f"here: {ACTION_QUEUE.get()}")
    return state

class Action_Map():
    """
    To add functionality for a specific remote, add it to the below defined map.
    map (remote_model
            (press)
            (hold)
    )
    """
    map = (
    ('E2001', # 4 button silver remote, on desktop
        (   ('on', '[]', Action.Up), ('move_with_on_off', '[<MoveMode.Up: 0>, 83]', Action.Up | Action.Hold), ('stop_with_on_off', '[]', Action.Up | Action.TerminateHold),
            ('off', '[]', Action.Down), ('move', '[<MoveMode.Down: 1>, 83, <bitmap8: 0>, <bitmap8: 0>]', Action.Down | Action.Hold), ('stop_with_on_off', '[]', Action.Down | Action.TerminateHold),
            ('press', '[257, 13, 0]', Action.Left),
            ('press', '[256, 13, 0]', Action.Right),
        ),
        (
            ('release', '[0]', Act_InLR), ('on', '[]', Act_InLR), ('press', '[2, 0, 0]', Act_InLR),
            ('hold', '[3329, 0]', Act_HoldL), ('release', '[<ms time>]', Action.TerminateHold),
            ('hold', '[3328, 0]', Act_HoldR), ('release', '[<ms time>]', Action.TerminateHold),
        )
    ),
    ('E1810', # 5 button rubber puck
        ()
    )
    )
    len_map = len(map)
    
    def _get_map_index_from_model(self, model: str) -> int:
        """ given a device model name, returns index of that device's map in the static self.map variable"""
        for i in range(self.len_map):
            if self.map[i][0] == model:
                return i
        raise Exception
    def get_action_from_command_args_by_model(self, command: str, args: str, model: str) -> Action:
        """ given a command, args, and model, returns the understood action that device is giving """
        model_index = self._get_map_index_from_model(model)
        for i in self.map[model_index][1]:
            if i[0] == command and i[1] == args:
                return i[2]

class Device_History():
    """ Stores history of actions received from a device """
    # history is list of tuples, where [0] is the device's locale_name, and [1] is a deque with some max length
    def __init__(self):
        self.history = []
    def _get_device_history(self, locale_name: str, maxlen: int = None) -> list[str, deque[Action]]:
        """ returns action history for a device, given a locale_name """
        len_history = len(self.history)
        for i in range(len_history):
            if self.history[i][0] == locale_name:
                return self.history[i][1]
        new_deque = deque([], maxlen=maxlen)
        self.history.append((locale_name, new_deque,))
        return self.history[len_history][1]

    def add_action(self, config: Config_Field, action: Action, maxlen: int = 5) -> None:
        """ adds an action to the history of a devices based on config.locale_name """
        device_history = self._get_device_history(config.locale_name, maxlen=maxlen)
        device_history.append(action)
    
    def clear_history(self, config: Config_Field) -> None:
        """ clears history for a devices based on config.locale_name """
        device_history = self._get_device_history(config.locale_name)
        device_history.clear()
    
    def get_history(self, config: Config_Field) -> list[Action]:
        """ returns action history as a list, based on config.locale_name """
        device_history = self._get_device_history(config.locale_name)
        return list(device_history)
    
    def get_last_action(self, config: Config_Field) -> Action:
        """ returns last Action based on config.locale_name """
        device_history = self._get_device_history(config.locale_name)
        if len(device_history) == 0:
            return Action(0)
        else:
            return device_history[-1]

class Config_Field():
    """
    Contains:
    - static x/y button press mapping
    - locale/remote's device_id mapping
    - locale/scene loops
    - methods used to action on those mappings
    
    Locales are areas of a house, i.e. bedroom, livingroom
    """
    locale_remotes = ( # converts device_id to a locale name
        ('7ee43bd41acce677bfab03490646da7f', 'bedroom_r1', 'E2001'), # 4 button silver remote, on desktop
        ('00c04379e359490503e9e1a44b339774', 'livingroom_r1', 'E2001'), # 4 button silver remove, on monitor
        ('57e51d8c188866311bec9fa8f217c28c', 'livingroom_r2', 'E1810'), # 5 button rubber puck
    )
    brightness_maps = [('bedroom_r1',
        [1,2,3],
        [4,5,6],
        [64,128,255]),
        ('livingroom_r1',
        [1,2,3],
        [4,5,6],
        [64,128,255]),
        ('livingroom_r2',
        ('light.signify_netherlands_b_v_lca005_huelight_2', 'light.signify_netherlands_b_v_lca005_huelight'),
        '
        )
    ]
    locale_scenes = [('bedroom_r1',{
            'loop': [
                "scene.sleep_1",
                "scene.sleep_2",
                "scene.night_normal",
                "scene.night_bright"
                ],
            'on': 'scene.bedroom_on',
            'off': 'scene.bedroom_off'
        }),
    ]
    def __init__(self, trigger_event: str, device_id: str):
        self.trigger_event = trigger_event
        # self.device_id = trigger_event.split(',')[6].strip(' \'').split('=')[1]
        self.device_id = device_id
        self.locale_name = None
        self.remote_model = None
        self.get_locale_name_from_device_id()
        self.brightness_map = None
        self.scene_map = None

    def get_state(self, key, return_type='xy'):
        try:
            state = state.get(f"string.{self.device_id}_{key}")
        except NameError:
            state.set(key)
            return -1, -1
        return state

    def set_state(self, key):
        state.set(f"string.{self.device_id}_{key}")

    def delete_state(self, key):
        state.delete(f"string.{self.device_id}_{key}")

    def get_locale_name_from_device_id(self) -> None:
        """ resolves locale_name from stored device_id """
        for local_remote in self.locale_remotes:
            if local_remote[0] == self.device_id:
                self.locale_name = local_remote[1]
                self.remote_model = local_remote[2]
                break
        if self.locale_name is None:
            raise Exception

    def get_scene_map(self) -> dict:
        """ Returns scene map based on locale """
        if self.scene_map is None:
            self.scene_map = self._get_map_by_locale(self.locale_scenes)
        return self.scene_map

    def get_brightness_maps(device_id: str) -> dict:
        """ Returns  brightness map from stored device_id """
        if self.brightness_map is None:
            self.brightness_map = self._get_map_by_locale(self.brightness_maps)
        return self.brightness_map

    def _get_map_by_locale(self, map_object: list[str, str|list|dict]) -> dict:
        """ Returns item from passed in list, where first element matches self.locale_name
        On failure raises exception"""
        for map in map_object:
            if map[0] == self.locale_name:
                return map[1]
        raise Exception

    def get_remote():
        pass

ACTION_MAP = Action_Map()
DEVICE_HISTORY = Device_History()



@service
def resolve_button_press(action=None, id=None, trigger_event=None, idx=None, alias=None, platform=None, description=None, device_id=None, command=None, args=None):
    """hello_world example using pyscript."""
    if type(args) != str:
        # Sometimes button press comes through as 'homeassistant.helpers.template.gen_result_wrapper.<locals>.Wrapper'
        # E1810 Down: [<StepMode.Down: 1>, 43, 5, <bitmap8: 0>, <bitmap8: 0>] 
        args = str(args)
    log.info("\n")
    config = Config_Field(trigger_event, device_id)
    action = ACTION_MAP.get_action_from_command_args_by_model(command, args, config.remote_model)

    log.info(f"{command} {args} {device_id}, {config.locale_name}")
    log.info(f"Last Action: {DEVICE_HISTORY.get_last_action(config)}")
    DEVICE_HISTORY.add_action(config, action)
    log.info(f"This Action: {action}")

    # config.set_state('pos')
    # log.info(config.get_state('pos'))
    # state.delete('string.57e51d8c188866311bec9fa8f217c28c_pos')
    return
    
    #####
    #####
    if config.locale_name == 'livingroom_r2':
        # log.info('IN IF STATEMENT')
        # a = state.get('input_text.ikea_r1_text')
        # log.info(f"helper text: {a}")
        # a = state.set('input_text.ikea_r1_text', json.dumps([0,0,'hello']))
        # log.info(f"helper text: {a}")
        # a = state.get('input_text.ikea_r1_text')
        # a = json.loads(a)
        # log.info(f"helper text: {a}")
        
        entity_id = 'light.signify_netherlands_b_v_lca005_huelight_2'
        entity_id = 'light.lamp'
        # log.info(f"brightness: {state.get(f'{entity_id}.brightness')}")
        # # log.info(state.names())
        # a = state.setattr(f"{entity_id}.brightness", value=1)
        # log.info(f"a: {a}")
        if state.get(entity_id) == 'on':
            log.info(f"brightness: {state.get(f'{entity_id}.brightness')}")
            light.turn_off(entity_id=entity_id)
        else:
            # brightness = turn_on_light(entity_id)
            ACTION_QUEUE.put('hello')
            task.executor(turn_on_light(entity_id))
            log.info(f"brightness: {brightness}")
            # light.turn_on(entity_id=entity_id)
            # asyncio.sleep(0.1)
            # log.info(f"brightness: {state.get(f'{entity_id}.brightness')}")


        # log.info(light.turn_on(entity_id=entity_id, brightness=300))
        
        if command in ['move_with_on_off', 'stop_with_on_off']:
            ACTION_QUEUE.put(command)

        
        # entity_reg = er.async_get_registry(hass)
        # entry = entity_reg.async_get(entity_id)
        # log.info(entry)

        # entity_light_state = state.get(f"{entity_id}")
        # log.info(f"light state: {entity_light_state}")
        # if entity_light_state == 'on':
        #     log.info(state.get(f"{entity_id}.brightness")) # does not work if lamp is off
        #     log.info(state.get(f"{entity_id}.color_temp_kelvin"))
        #     log.info(state.get(f"{entity_id}.min_color_temp_kelvin"))
        #     log.info(state.get(f"{entity_id}.xy_color"))
        #     log.info(state.get(f"{entity_id}.brightness"))
        # else:
        #     pass # light is off

        # log.info(trigger_event)
        log.info(f"id: {id}")
        # log.info(f"event: {trigger_event}")
        log.info(f"command: '{command}'")
        log.info(f"args: '{args}'")
        # log.info(Action.Up)
        
        # current_value = 0
        # light.turn_on(entity_id=entity_id, brightness=current_value)

        # return



    # idx_map = {0:'up', 1:'down', 2:'left', 3:'right', 4:'down_l', 5:'up_l'}
    # m_idx = idx_map[idx]
    counter_name = 'counter.ikea_r1_counter'
    boolean_name = 'input_boolean.ikea_r1_down_held'
    counter_max = 4
    def get_counter(counter_name):
        return int(state.get(counter_name))
    def change_counter(direction):
        '''
        <class 'custom_components.pyscript.state.StateVal'>
        {   'editable': True,
            'initial': 0,
            'step': 1,
            'minimum': 0,
            'maximum': 4,
            'icon': 'mdi:cached',
            'friendly_name': 'Ikea r1 Counter',
            'last_updated': datetime.datetime(2022, 10, 29, 0, 49, 5, 490131, tzinfo=datetime.timezone.utc),
            'last_changed': datetime.datetime(2022, 10, 29, 0, 49, 5, 490131, tzinfo=datetime.timezone.utc)
        }
        :arg direction: char, + or -
        :return: int, counter value
        '''
        assert direction in '-+'
        counter_state = get_counter(counter_name)
        if direction == '+':
            counter_state += 1
        elif direction == '-':
            counter_state -= 1
        counter_state %= (counter_max)
        state.set(counter_name, counter_state)
        return counter_state
    def get_boolean_state():
        boolean_state = state.get(boolean_name)
        if boolean_state not in HELPER_BOOLEAN_MAP:
            return False
        return HELPER_BOOLEAN_MAP[boolean_state]
    def toggle_boolean():
        boolean_state = get_boolean_state()
        new_boolean_state = not boolean_state
        state.set(boolean_name, HELPER_BOOLEAN_MAP[new_boolean_state])
        return new_boolean_state
    def set_boolean(boolean_state):
        assert type(boolean_state) == bool
        state.set(boolean_name, HELPER_BOOLEAN_MAP[boolean_state])
    def get_scene_by_index(counter_val):
        return config.get_scene_map()['loop'][counter_val]
    def get_scene_by_counter_name():
        counter_val = get_counter(counter_name)
        return get_scene_by_index(counter_val)

    # log.info(trigger_event)
    # log.info(f"command: {command}")


    if action == Action.Left:
        counter_val = change_counter('-')
        selected_scene = get_scene_by_index(counter_val)
        scene.turn_on(entity_id=selected_scene)
        log.info(f"Setting scene to '{selected_scene}', count: {counter_val}")
    if action == Action.Right:
        counter_val = change_counter('+')
        selected_scene = get_scene_by_index(counter_val)
        scene.turn_on(entity_id=selected_scene)
        log.info(f"Setting scene to '{selected_scene}', count: {counter_val}")

    if action == Action.Down:
        # light_state = state.get('light.signify_netherlands_b_v_lca005_huelight') # 'Rear Left Table'
        # log.info(f"light_state: {light_state.__dict__}")
        current_scene = get_scene_by_counter_name()
        scene.turn_on(entity_id=config.get_scene_map()['off'])
    if action == Action.Up:
        current_scene = get_scene_by_counter_name()
        scene.turn_on(entity_id=current_scene)
    # if command == 'move':
    #     set_boolean(True)

    # OLD
    # if command == 'press':
    #     log.info(f"Press with idx: {m_idx}")
    #     if m_idx == 'left':
    #         counter_val = change_counter('-')
    #         selected_scene = get_scene_by_index(counter_val)
    #         scene.turn_on(entity_id=selected_scene)
    #         log.info(f"Setting scene to '{selected_scene}', count: {counter_val}")
    #     if m_idx == 'right':
    #         counter_val = change_counter('+')
    #         selected_scene = get_scene_by_index(counter_val)
    #         scene.turn_on(entity_id=selected_scene)
    #         log.info(f"Setting scene to '{selected_scene}', count: {counter_val}")
    # if command == 'off' or command == 'on':
    #     if m_idx =='down':
    #         # light_state = state.get('light.signify_netherlands_b_v_lca005_huelight') # 'Rear Left Table'
    #         # log.info(f"light_state: {light_state.__dict__}")
    #         current_scene = get_scene_by_counter_name()
    #         scene.turn_on(entity_id=config.get_scene_map()['off'])
    #     if m_idx =='up':
    #         current_scene = get_scene_by_counter_name()
    #         scene.turn_on(entity_id=current_scene)
    # if command == 'move':
    #     set_boolean(True)
    # if command == 'stop_with_on_off':
    #     boolean_state = get_boolean_state()
    #     if boolean_state == True:
    #         boolean_state = toggle_boolean()
    #     else:
    #         pass
    
    if command == 'off':
        global TEMP
        TEMP += 1
        log.info(TEMP)

    log.info(".")
    #



# @task_unique('background_pyscript', kill_me=False)
# @time_trigger('startup')
# def async_foo():
#     """
#     'kill_me=False' kills old tasks, and allows new tasks to run
#     """
#     entity_id = 'light.lamp'
#     count = 0
#     action_count = 0
#     last_action = ''
#     while(True):
#         if count % 10 == 0:
#             log.info(f'async task on {count}')
#         count += 1
        
#         try:
#             action = ACTION_QUEUE.get(block=False, timeout=5)
#         except Empty:
#             # asyncio.sleep(1)
#             # continue
#             log.info('exception')
#             action = last_action
        
#         if action != '':
#             log.info(f"action: {action}")
#         if action == 'move_with_on_off':
#             asyncio.sleep(0.5)
#             light.turn_on(entity_id=entity_id, brightness=action_count)
#             action_count += 15
#             if state.get(entity_id) == 'on':
#                 log.info(f"brightness: {state.get('light.lamp.brightness')}")
#             last_action = action
#             log.info('here')
#             continue
#         if action == 'stop_with_on_off':
#             action = ''
#             action_count = 0
#             last_action = action
#             log.info("end of move_on_with_off")
#         asyncio.sleep(1)
#         if count > 100:
#             break

@event_trigger(EVENT_CALL_SERVICE)
def monitor_service_calls(**kwargs):
    # log.info(f"got EVENT_CALL_SERVICE with kwargs={kwargs}")
    # if kwargs
    pass

