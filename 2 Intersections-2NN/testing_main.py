from __future__ import absolute_import
from __future__ import print_function

import os
from shutil import copyfile

from testing_simulation import Simulation
from generator import TrafficGenerator
from model import TestModel
from visualization import Visualization
from utils import import_test_configuration, set_sumo, set_test_path


if __name__ == "__main__":

    # initialise parameters and classes
    config = import_test_configuration(config_file='testing_settings.ini')
    sumo_cmd = set_sumo(config['gui'], config['sumocfg_file_name'], config['max_steps'])
    model_path, plot_path = set_test_path(config['models_path_name'], config['model_to_test'])

    Model = TestModel(
        input_dim=config['num_states'],
        model_path=model_path
    )

    TrafficGen = TrafficGenerator(
        Model,
        config['max_steps'], 
        config['n_cars_generated']
    )

    Visualization = Visualization(
        plot_path, 
        dpi=96
    )
        
    Simulation = Simulation(
        Model,
        TrafficGen,
        sumo_cmd,
        config['max_steps'],
        config['green_duration'],
        config['yellow_duration'],
        config['num_states'],
        config['num_actions'],
        config['reward']
    )

    print('\n----- Test episode')
    simulation_time = Simulation.run(config['episode_seed'])  # run the simulation
    print('Simulation time:', simulation_time, 's')

    print("----- Testing info saved at:", plot_path)

    copyfile(src='testing_settings.ini', dst=os.path.join(plot_path, 'testing_settings.ini'))

    # save desired data
    Visualization.save_data_and_plot(0,data=Simulation.reward1_episode, filename='reward1', xlabel='Action step', ylabel='Reward 1')
    Visualization.save_data_and_plot(0,data=Simulation.queue1_length_episode, filename='queue1', xlabel='Step', ylabel='Queue length 1 (vehicles)')
    Visualization.save_data_and_plot(0,data=Simulation.reward2_episode, filename='reward2', xlabel='Action step', ylabel='Reward 2')
    Visualization.save_data_and_plot(0,data=Simulation.queue2_length_episode, filename='queue2', xlabel='Step', ylabel='Queue length 2 (vehicles)')
    Visualization.save_data_and_plot(0,data=Simulation.queue_total_length_episode, filename='total_queue', xlabel='Step', ylabel=' Total Queue length (vehicles)')
    Visualization.save_data_and_plot(1,data=Simulation._TrafficGen._distribution_store, filename='distribution', xlabel='Step', ylabel='Num cars (vehicles)')
    Visualization.save_data_and_plot(1,data=Simulation.store_action1, filename='action1', xlabel='Episode', ylabel='Action 1')
    Visualization.save_data_and_plot(1,data=Simulation.store_action2, filename='action2', xlabel='Episode', ylabel='Action 2')



