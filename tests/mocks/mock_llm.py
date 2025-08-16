# tests/mocks/mock_llm.py

class MockLLM:
    """
    A mock LLM class for testing purposes.
    This class mimics the behavior of a LangChain LLM object,
    specifically the .invoke() method, but returns a hardcoded response.
    """
    def __init__(self, *args, **kwargs):
        """
        Accepts any arguments to match the signature of real LLM clients
        but does not use them.
        """
        pass

    def invoke(self, prompt: str, *args, **kwargs) -> str:
        """
        Mimics the LLM's invoke method.

        Args:
            prompt (str): The input prompt for the LLM.

        Returns:
            str: A hardcoded, generic response for testing.
        """
        # In a more advanced mock, you could have logic here to return
        # different responses based on the prompt content.
        # For now, a simple, consistent response is sufficient.
        return "This is a mock LLM response to the prompt."

    def __call__(self, prompt: str, *args, **kwargs) -> str:
        """
        Some LangChain components might use the __call__ method as an alias for invoke.
        """
        return self.invoke(prompt, *args, **kwargs)
