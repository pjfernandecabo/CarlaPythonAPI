import glob
import os
import sys
try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass
import carla

import random
import time
import numpy as np
import cv2

from RL-Studio.carla_env.carlaenv import CarlaEnv
from RL-Studio.algorithms.qlearn import QLearnF1


def main():

    # Weather
    weather = carla.WeatherParameters(
        cloudiness=0.0,
        precipitation=0.0,
        sun_altitude_angle=2.5)
    # town    
    town = "Town07"
    # CarlaEnv
    environment = CarlaEnv(town, weather)

    # setting agent
    blueprint_library: carla.BlueprintLibrary = environment.get_blueprint_library()
    model = blueprint_library.filter("model3")[0]
    cam = blueprint_library.find("sensor.camera.rgb")
    colsensor = blueprint_library.find('sensor.other.collision')
    environment.spawn_vehicle(model, cam, colsensor)

    # Qlearn
    agent = QLearnF1(environment)
    time.sleep(5)

    '''aux = True
    while aux:
        aux = environment.show_image()
        action = carla.VehicleControl(throttle=0.6, steer=0)
        agent.step(0)
        pos = environment.calc_center()
        reward = agent.reward(action, pos)
        print(reward)
        # agent.new_state(pos)'''

    alpha = 0.8
    gamma = 0.9
    epsilon = 0.9999

    for i in range(1, 10000, 1):
        state = agent.reset()
        time.sleep(0.6)

        epochs, penalties, reward = 0, 0, 0
        done = False
        print(f"Episode: {i}, epsilon: {epsilon}")

        while not done:
            '''if not environment.show_image():
                environment.destroy_all_actors()
                exit(0)'''
            if random.uniform(0, 1) < epsilon:
                action = agent.get_action()
                epsilon *= 0.9998
            else:
                action = max(agent.Q_table[state], key=agent.Q_table[state].get)

            next_state, reward, done, info = agent.step(action)

            print(f"Estado: {state}\n acciones: recompensas {agent.Q_table[state]}\n accion seleccionada: {action}\n reward: {reward}\n Estado resultante: {next_state}")
            print()

            old_value = agent.Q_table[state][action]
            aux = agent.Q_table[next_state].values()
            next_max = max(aux)

            new_value = (1 - alpha) * old_value + alpha * (reward + gamma * next_max)
            agent.Q_table[state][action] = round(new_value, 5)

            state = next_state
            epochs += 1

        print("\n\n\n")

    environment.destroy_all_actors()


if __name__ == '__main__':
    main()