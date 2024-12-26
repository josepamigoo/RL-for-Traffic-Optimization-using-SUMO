import random

class Memory:  # saves and manages data from simulations
    def __init__(self, size_max, size_min):
        self._samples1 = []
        self._samples2= []
        self._size_max = size_max
        self._size_min = size_min


    def add_sample(self, sample, agent_id):
      if agent_id == 1:
         self._samples1.append(sample) 
         if self._size_now(agent_id) > self._size_max:
            self._samples1.pop(0)        
      elif agent_id == 2:
         self._samples2.append(sample)
         if self._size_now(agent_id) > self._size_max:
            self._samples2.pop(0)  
         
        # if the length is greater than the size of memory, remove the oldest element

    def get_samples(self, n, agent_id):

        if agent_id == 1:
         if self._size_now(agent_id) < self._size_min:
            return []

         if n > self._size_now(agent_id):
            return random.sample(self._samples1, self._size_now(agent_id))  # get all the samples
         else:
            return random.sample(self._samples1, n)  # get "batch size" number of samples
         
        if agent_id == 2:
         if self._size_now(agent_id) < self._size_min:
            return []

         if n > self._size_now(agent_id):
            return random.sample(self._samples2, self._size_now(agent_id))  # get all the samples
         else:
            return random.sample(self._samples2, n)  # get "batch size" number of samples

    def _size_now(self,agent_id):
        if agent_id == 1:
         l= len(self._samples1)
        if agent_id == 2:
         l= len(self._samples2)

        return l