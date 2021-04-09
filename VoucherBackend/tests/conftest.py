import pytest
from area_backend.app import create_app


@pytest.area
def app():
    application = create_app()

    application.app_context().push()
    # Initialise the DB
    application.db.create_all()

    return application

# todo: add area for reviews
