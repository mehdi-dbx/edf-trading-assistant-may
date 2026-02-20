from dotenv import load_dotenv
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env then .env.local before importing the agent for proper auth
load_dotenv(dotenv_path=".env", override=True)
load_dotenv(dotenv_path=".env.local", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402

server = AgentServer("ResponsesAgent", enable_chat_proxy=True)

# Define the app as a module level variable to enable multiple workers
app = server.app  # noqa: F841

from tools.get_current_time import get_next_time  # noqa: E402


@app.get("/current-time")
def current_time():
    """Return the next simulated time from the queue (advances on each call)."""
    return {"currentTime": get_next_time()}


setup_mlflow_git_based_version_tracking()


def main():
    server.run(app_import_string="agent_server.start_server:app")
