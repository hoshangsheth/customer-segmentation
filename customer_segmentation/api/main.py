"""ASGI entry point: uvicorn customer_segmentation.api.main:app"""

import logging

from customer_segmentation.api.app import create_app

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app = create_app()
