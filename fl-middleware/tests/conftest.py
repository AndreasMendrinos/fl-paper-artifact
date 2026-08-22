import os


# Tests must never depend on live external provider APIs.
# These variables are set before the test modules import the FastAPI app.
os.environ["IOTLAB_MODE"] = "mock"
os.environ["CHAMELEON_MODE"] = "mock"
os.environ["GRID5000_MODE"] = "mock"

os.environ["IOTLAB_ENABLED"] = "true"
os.environ["CHAMELEON_ENABLED"] = "true"
os.environ["GRID5000_ENABLED"] = "true"

os.environ["CHAMELEON_SITES"] = "auto"
os.environ["CHAMELEON_SITE_CLASSES"] = "baremetal"
os.environ["CHAMELEON_CLUSTER"] = "chameleon"