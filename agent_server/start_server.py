from dotenv import load_dotenv
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env then .env.local before importing the agent for proper auth
load_dotenv(dotenv_path=".env.local", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402

server = AgentServer("ResponsesAgent", enable_chat_proxy=True)

# Define the app as a module level variable to enable multiple workers
app = server.app  # noqa: F841

from fastapi import Request

from tools.get_current_time import get_next_time  # noqa: E402


@app.get("/current-time")
def current_time(request: Request):
    """Return simulated time. advance=true moves forward; backward=true moves back; else peeks."""
    advance = request.query_params.get("advance", "false").lower() == "true"
    backward = request.query_params.get("backward", "false").lower() == "true"
    if backward:
        t = get_next_time(advance=False, backward=True)
    else:
        t = get_next_time(advance)
    print(f"[current-time] advance={advance} backward={backward} -> {t}", flush=True)
    return {"currentTime": t}


@app.get("/current-time/backward")
def current_time_backward():
    """Step simulated time backward and return new time (avoids query-param forwarding issues)."""
    t = get_next_time(advance=False, backward=True)
    print(f"[current-time/backward] -> {t}", flush=True)
    return {"currentTime": t}


setup_mlflow_git_based_version_tracking()


def main():
    server.run(app_import_string="agent_server.start_server:app")
