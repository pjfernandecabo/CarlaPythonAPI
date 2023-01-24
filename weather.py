'''

ClearNoon, CloudyNoon, WetNoon, WetCloudyNoon, SoftRainNoon, MidRainyNoon, 
HardRainNoon, ClearSunset, CloudySunset, WetSunset, WetCloudySunset, 
SoftRainSunset, MidRainSunset, HardRainSunset

'''


import math
import glob
import os
import sys
import argparse
import carla

#############################################################
#
# Dynamic weather
#
#############################################################

def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(value, maximum))


class Sun(object):
    def __init__(self, azimuth, altitude):
        self.azimuth = azimuth
        self.altitude = altitude
        self._t = 0.0

    def tick(self, delta_seconds):
        self._t += 0.008 * delta_seconds
        self._t %= 2.0 * math.pi
        self.azimuth += 0.25 * delta_seconds
        self.azimuth %= 360.0
        self.altitude = (70 * math.sin(self._t)) - 20

    def __str__(self):
        return 'Sun(alt: %.2f, azm: %.2f)' % (self.altitude, self.azimuth)


class Storm(object):
    def __init__(self, precipitation):
        self._t = precipitation if precipitation > 0.0 else -50.0
        self._increasing = True
        self.clouds = 0.0
        self.rain = 0.0
        self.wetness = 0.0
        self.puddles = 0.0
        self.wind = 0.0
        self.fog = 0.0

    def tick(self, delta_seconds):
        delta = (1.3 if self._increasing else -1.3) * delta_seconds
        self._t = clamp(delta + self._t, -250.0, 100.0)
        self.clouds = clamp(self._t + 40.0, 0.0, 90.0)
        self.rain = clamp(self._t, 0.0, 80.0)
        delay = -10.0 if self._increasing else 90.0
        self.puddles = clamp(self._t + delay, 0.0, 85.0)
        self.wetness = clamp(self._t * 5, 0.0, 100.0)
        self.wind = 5.0 if self.clouds <= 20 else 90 if self.clouds >= 70 else 40
        self.fog = clamp(self._t - 10, 0.0, 30.0)
        if self._t == -250.0:
            self._increasing = True
        if self._t == 100.0:
            self._increasing = False

    def __str__(self):
        return 'Storm(clouds=%d%%, rain=%d%%, wind=%d%%)' % (self.clouds, self.rain, self.wind)


class Weather(object):
    def __init__(self, weather):
        self.weather = weather
        self._sun = Sun(weather.sun_azimuth_angle, weather.sun_altitude_angle)
        self._storm = Storm(weather.precipitation)

    def tick(self, delta_seconds):
        self._sun.tick(delta_seconds)
        self._storm.tick(delta_seconds)
        self.weather.cloudiness = self._storm.clouds
        self.weather.precipitation = self._storm.rain
        self.weather.precipitation_deposits = self._storm.puddles
        self.weather.wind_intensity = self._storm.wind
        self.weather.fog_density = self._storm.fog
        self.weather.wetness = self._storm.wetness
        self.weather.sun_azimuth_angle = self._sun.azimuth
        self.weather.sun_altitude_angle = self._sun.altitude

    def __str__(self):
        return '%s %s' % (self._sun, self._storm)


#############################################################
#
# Static weather
#
#############################################################   

SUN_PRESETS = {
    'day': (45.0, 0.0),
    'night': (-90.0, 0.0),
    'sunset': (0.5, 0.0)}

WEATHER_PRESETS = {
    'clear': [10.0, 0.0, 0.0, 5.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0331],
    'overcast': [80.0, 0.0, 0.0, 50.0, 2.0, 0.75, 0.1, 10.0, 0.0, 0.03, 0.0331],
    'rain': [100.0, 80.0, 90.0, 100.0, 7.0, 0.75, 0.1, 100.0, 0.0, 0.03, 0.0331]}

CAR_LIGHTS = {
    'None' : [carla.VehicleLightState.NONE],
    'Position' : [carla.VehicleLightState.Position],
    'LowBeam' : [carla.VehicleLightState.LowBeam],
    'HighBeam' : [carla.VehicleLightState.HighBeam],
    'Brake' : [carla.VehicleLightState.Brake],
    'RightBlinker' : [carla.VehicleLightState.RightBlinker],
    'LeftBlinker' : [carla.VehicleLightState.LeftBlinker],
    'Reverse' : [carla.VehicleLightState.Reverse],
    'Fog' : [carla.VehicleLightState.Fog],
    'Interior' : [carla.VehicleLightState.Interior],
    'Special1' : [carla.VehicleLightState.Special1],
    'Special2' : [carla.VehicleLightState.Special2],
    'All' : [carla.VehicleLightState.All]}

LIGHT_GROUP = {
    'None' : [carla.LightGroup.NONE],
    # 'Vehicle' : [carla.LightGroup.Vehicle],
    'Street' : [carla.LightGroup.Street],
    'Building' : [carla.LightGroup.Building],
    'Other' : [carla.LightGroup.Other]}

def apply_sun_presets(args, weather):
    """Uses sun presets to set the sun position"""
    if args.sun is not None:
        if args.sun in SUN_PRESETS:
            weather.sun_altitude_angle = SUN_PRESETS[args.sun][0]
            weather.sun_azimuth_angle = SUN_PRESETS[args.sun][1]
        else:
            print("[ERROR]: Command [--sun | -s] '" + args.sun + "' not known")
            sys.exit(1)


def apply_weather_presets(args, weather):
    """Uses weather presets to set the weather parameters"""
    if args.weather is not None:
        if args.weather in WEATHER_PRESETS:
            weather.cloudiness = WEATHER_PRESETS[args.weather][0]
            weather.precipitation = WEATHER_PRESETS[args.weather][1]
            weather.precipitation_deposits = WEATHER_PRESETS[args.weather][2]
            weather.wind_intensity = WEATHER_PRESETS[args.weather][3]
            weather.fog_density = WEATHER_PRESETS[args.weather][4]
            weather.fog_distance = WEATHER_PRESETS[args.weather][5]
            weather.fog_falloff = WEATHER_PRESETS[args.weather][6]
            weather.wetness = WEATHER_PRESETS[args.weather][7]
            weather.scattering_intensity = WEATHER_PRESETS[args.weather][8]
            weather.mie_scattering_scale = WEATHER_PRESETS[args.weather][9]
            weather.rayleigh_scattering_scale = WEATHER_PRESETS[args.weather][10]
        else:
            print("[ERROR]: Command [--weather | -w] '" + args.weather + "' not known")
            sys.exit(1)


def apply_weather_values(args, weather):
    """Set weather values individually"""
    if args.azimuth is not None:
        weather.sun_azimuth_angle = args.azimuth
    if args.altitude is not None:
        weather.sun_altitude_angle = args.altitude
    if args.clouds is not None:
        weather.cloudiness = args.clouds
    if args.rain is not None:
        weather.precipitation = args.rain
    if args.puddles is not None:
        weather.precipitation_deposits = args.puddles
    if args.wind is not None:
        weather.wind_intensity = args.wind
    if args.fog is not None:
        weather.fog_density = args.fog
    if args.fogdist is not None:
        weather.fog_distance = args.fogdist
    if args.fogfalloff is not None:
        weather.fog_falloff = args.fogfalloff
    if args.wetness is not None:
        weather.wetness = args.wetness
    if args.scatteringintensity is not None:
        weather.scattering_intensity = args.scatteringintensity
    if args.miescatteringscale is not None:
        weather.mie_scattering_scale = args.miescatteringscale
    if args.rayleighscatteringscale is not None:
        weather.rayleigh_scattering_scale = args.rayleighscatteringscale


def apply_lights_to_cars(args, world):
    if args.cars is None:
        return

    light_mask = carla.VehicleLightState.NONE
    for option in args.cars:
        light_mask |= CAR_LIGHTS[option][0]

    # Get all cars in level
    all_vehicles = world.get_actors()
    for ve in all_vehicles:
        if "vehicle." in ve.type_id:
            ve.set_light_state(carla.VehicleLightState(light_mask))

def apply_lights_manager(args, light_manager):
    if args.lights is None:
        return

    light_group = 'None'
    if args.lightgroup is not None:
        light_group = args.lightgroup

    # filter by group
    lights = light_manager.get_all_lights(LIGHT_GROUP[light_group][0]) # light_group

    i = 0
    while (i < len(args.lights)):
        option = args.lights[i]

        if option == "on":
            light_manager.turn_on(lights)
        elif option == "off":
            light_manager.turn_off(lights)
        elif option == "intensity":
            light_manager.set_intensity(lights, int(args.lights[i + 1]))
            i += 1
        elif option == "color":
            r = int(args.lights[i + 1])
            g = int(args.lights[i + 2])
            b = int(args.lights[i + 3])
            light_manager.set_color(lights, carla.Color(r, g, b))
            i += 3

        i += 1
