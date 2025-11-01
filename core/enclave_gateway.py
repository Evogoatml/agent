from core.llm_interface import LLMInterface
from core.diagnostics import Diagnostics
from core.memory import Memory

class EnclaveGateway:
    def __init__(self):
        self.llm = LLMInterface()
        self.log = Diagnostics()
        self.memory = Memory()

    def process_request(self, prompt):
        self.log.record("request_received", {"prompt": prompt})
        response = self.llm.query(prompt)
        self.memory.add("last_response", response)
        self.log.record("response_generated", {"response": response[:200]})
        return response
