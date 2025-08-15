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

def test_me_items(test_db, client):
    # Create user
    response = client.post(
        "/users/",
        json={"email": "spiderman@example.com", "password": "webslinger"},
    )
    assert response.status_code == 200, response.text
    user = response.json()
    user_id = user["id"]
    api_token = user["api_token"]

    # Create items for this user
    item_payloads = [
        {"title": "Save MJ", "description": "Rescue Mary Jane from danger."},
        {"title": "Fight crime", "description": "Patrol the city at night."},
    ]
    for payload in item_payloads:
        response = client.post(
            f"/users/{user_id}/items/",
            json=payload,
            headers={"X-API-TOKEN": api_token},
        )
        assert response.status_code == 200, response.text

    # Create another user and item to ensure isolation
    response = client.post(
        "/users/",
        json={"email": "venom@example.com", "password": "symbiote"},
    )
    other_user = response.json()
    other_token = other_user["api_token"]
    response = client.post(
        f"/users/{other_user['id']}/items/",
        json={"title": "Eat brains", "description": "Venom's favorite activity."},
        headers={"X-API-TOKEN": other_token},
    )
    assert response.status_code == 200, response.text

    # Authenticated request to /me/items
    response = client.get("/me/items", headers={"X-API-TOKEN": api_token})
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 2
    titles = {item["title"] for item in items}
    assert titles == {"Save MJ", "Fight crime"}

    # Unauthenticated request should fail
    response = client.get("/me/items")
    assert response.status_code == 401

def test_delete_user_and_transfer_items(test_db, client):
    # Create two users
    response = client.post(
        "/users/",
        json={"email": "user1@example.com", "password": "pw1"},
    )
    user1 = response.json()
    user1_id = user1["id"]
    token1 = user1["api_token"]

    response = client.post(
        "/users/",
        json={"email": "user2@example.com", "password": "pw2"},
    )
    user2 = response.json()
    user2_id = user2["id"]
    token2 = user2["api_token"]

    # Ensure user1 has the smallest id
    if user2_id < user1_id:
        user1, user2 = user2, user1
        user1_id, user2_id = user2_id, user1_id
        token1, token2 = token2, token1

    # Create items for user2
    item_payloads = [
        {"title": "Task A", "description": "A desc"},
        {"title": "Task B", "description": "B desc"},
    ]
    for payload in item_payloads:
        response = client.post(
            f"/users/{user2_id}/items/",
            json=payload,
            headers={"X-API-TOKEN": token2},
        )
        assert response.status_code == 200, response.text

    # Delete user2 (should transfer items to user1)
    response = client.delete(f"/users/{user2_id}", headers={"X-API-TOKEN": token1})
    assert response.status_code == 200, response.text
    deleted_user = response.json()
    assert deleted_user["id"] == user2_id
    assert deleted_user["is_active"] is False

    # Check that user2's items now belong to user1
    response = client.get("/me/items", headers={"X-API-TOKEN": token1})
    assert response.status_code == 200, response.text
    items = response.json()
    titles = {item["title"] for item in items}
    assert titles.issuperset({"Task A", "Task B"})

    # Deleting a non-existent user returns 404
    response = client.delete("/users/99999", headers={"X-API-TOKEN": token1})
    assert response.status_code == 404

    # Deleting without authentication returns 401
    response = client.delete(f"/users/{user1_id}")
    assert response.status_code == 401
