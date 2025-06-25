from abc import ABC, abstractmethod

class BaseProceso(ABC):
    def __init__(self, proceso):
        self.proceso = proceso

    @abstractmethod
    def procesar(self):
        pass