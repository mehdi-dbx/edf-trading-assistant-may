import os
import sys

# --- BEGIN: TEMPORARY LOCAL TESTING ONLY - REMOVE FOR DATABRICKS ---
# On macOS, WeasyPrint (PDF report tool) needs Homebrew Pango/Cairo; not needed on Databricks.
if sys.platform == "darwin":
    brew_lib = "/opt/homebrew/lib"
    if os.path.isdir(brew_lib):
        existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        os.environ["DYLD_LIBRARY_PATH"] = f"{brew_lib}{':' + existing if existing else ''}"
# --- END: TEMPORARY LOCAL TESTING ONLY - REMOVE FOR DATABRICKS ---

from dotenv import load_dotenv
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env then .env.local before importing the agent for proper auth
load_dotenv(dotenv_path=".env", override=True)
load_dotenv(dotenv_path=".env.local", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402

agent_server = AgentServer("ResponsesAgent", enable_chat_proxy=True)

# Define the app as a module level variable to enable multiple workers
app = agent_server.app  # noqa: F841
setup_mlflow_git_based_version_tracking()


def main():
    agent_server.run(app_import_string="agent_server.start_server:app")
