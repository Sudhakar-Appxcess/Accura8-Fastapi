# ** Base Modules
from fastapi import FastAPI
from fastapi.testclient import TestClient
# ** App Modules
from app.db import Base, engine
from app.app_middleware import register_middleware
from app.app_controller import register_controller
from app.app_models import setup_models
from app.app_service import register_logger
from app.helpers.scheduler import register_scheduler
from fastapi.middleware.cors import CORSMiddleware
# ** External Modules
from dotenv import load_dotenv


# Load Environment variables
load_dotenv()



# Register the Models
setup_models()

# Initialize the database
Base.metadata.create_all(bind=engine)

# Initialize the APP
app = FastAPI()

app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8081",
            "http://127.0.0.1:8081",
            "http://127.0.0.1:5500",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,         
        allow_methods=["*"],             
        allow_headers=["*"],             
        expose_headers=["*"]  # This is crucial
        # max_age=3600                    
    )

# Base Component Registers
register_middleware(app)
register_logger()
register_controller(app)
register_scheduler(app)

# Unittest Client
testClient = TestClient(app)
