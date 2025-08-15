# For asyncio on Windows
import sys
if sys.platform.startswith("win"):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def test_create_user(test_db, client):
    response = client.post(
        "/users/",
        json={"email": "deadpool@example.com", "password": "chimichangas4life"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "deadpool@example.com"
    assert "id" in data
    assert "api_token" in data
    user_id = data["id"]
    api_token = data["api_token"]

    # Authenticated request
    response = client.get(f"/users/{user_id}", headers={"X-API-TOKEN": api_token})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "deadpool@example.com"
    assert data["id"] == user_id

    # Unauthenticated request should fail
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 401
