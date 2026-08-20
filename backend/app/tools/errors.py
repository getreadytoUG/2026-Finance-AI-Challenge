class ToolExecutionError(Exception):
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"{tool_name}: {message}")
