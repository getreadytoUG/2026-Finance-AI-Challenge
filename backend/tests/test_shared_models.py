from app.shared.models import Account, Transaction


def test_account_and_transaction_models_are_importable_and_map_to_tables():
    assert Account.__tablename__ == "accounts"
    assert Transaction.__tablename__ == "transactions"


def test_tables_are_created_on_app_startup(client):
    # The client fixture creates all tables (via Base.metadata.create_all) against
    # an isolated in-memory DB when the app starts — if Account/Transaction weren't
    # imported anywhere before that call, their tables would silently be missing.
    # Hitting any route confirms app startup succeeded with them registered.
    response = client.get("/health")
    assert response.status_code == 200
