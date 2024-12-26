import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'  # kill warning about tensorflow
import tensorflow as tf
import numpy as np
import sys

from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras import losses
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import plot_model
from tensorflow.keras.models import load_model


class TrainModel:
    def __init__(self, num_layers, width, batch_size, learning_rate, input_dim, output_dim):
        self._input_dim = input_dim
        self._output_dim = output_dim
        self._batch_size = batch_size
        self._learning_rate = learning_rate
        self._model1 = self._build_model(num_layers, width)
        self._model2 = self._build_model(num_layers, width)


    def _build_model(self, num_layers, width):
        """
        Build and compile a fully connected deep neural network
        """
        inputs = keras.Input(shape=(self._input_dim,))
        x = layers.Dense(width, activation='relu')(inputs)  # Input actions 
        for _ in range(num_layers):
            x = layers.Dense(width, activation='relu')(x)
        outputs = layers.Dense(self._output_dim, activation='linear')(x)   # Output states

        model = keras.Model(inputs=inputs, outputs=outputs, name='my_model')
        model.compile(loss=losses.MeanSquaredError(), optimizer=Adam(learning_rate=self._learning_rate))   # Set loss and optimizer 
        return model
    

    def predict_one(self, state, agent_id):
        """
        Predict the action values from a single state for the corresponding agent
        """
        state = np.reshape(state, [1, self._input_dim])

        if agent_id == 1:
          action = self._model1.predict(state)
        elif agent_id == 2:
          action = self._model2.predict(state)

        return  action


    def predict_batch(self, states1, states2):
        """
        Predict the action values from a batch of states for both agents
        """
        return self._model1.predict(states1), self._model2.predict(states2)


    def train_batch(self, states1, q1_sa, states2, q2_sa):
        """
        Train the nn using the updated q-values for both agents
        """
        self._model1.fit(states1, q1_sa, epochs=1, verbose=0)
        self._model2.fit(states2, q2_sa, epochs=1, verbose=0)


    def save_model(self, path):
        """
        Save the current models in the folder as .keras file
        """
        self._model1.save(os.path.join(path, 'trained_model1.keras'))
        self._model2.save(os.path.join(path, 'trained_model2.keras'))       

    @property
    def input_dim(self):
        return self._input_dim


    @property
    def output_dim(self):
        return self._output_dim


    @property
    def batch_size(self):
        return self._batch_size


class TestModel:
    def __init__(self, input_dim, model_path):
        self._input_dim = input_dim
        self._model1, self._model2  = self._load_my_model(model_path)


    def _load_my_model(self, model_folder_path):
        """
        Load the models stored in the folder specified by the model number and agent, if it exists
        """
        model_file1_path = os.path.join(model_folder_path, 'trained_model1.keras')
        model_file2_path = os.path.join(model_folder_path, 'trained_model2.keras')
        
        if os.path.isfile(model_file1_path):
            loaded_model1 = load_model(model_file1_path)
            if os.path.isfile(model_file2_path):
               loaded_model2 = load_model(model_file2_path)
               return loaded_model1,loaded_model2
        else:
            sys.exit("Model number not found")



    def predict_one(self, state, agent_id):
        """
        Predict the action values from a single state for the corresponding agent
        """
        state = np.reshape(state, [1, self._input_dim])
        if agent_id == 1:
          action = self._model1.predict(state)
        elif agent_id == 2:
          action = self._model2.predict(state)

        return action

    @property
    def input_dim(self):
        return self._input_dim