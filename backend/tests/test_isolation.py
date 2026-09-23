from .conftest import login_and_get_token


def test_cross_tenant_project_access_blocked(client, seeded):
    """Agency 2's admin cannot read Agency 1's project, even by guessing the
    real ID directly."""
    token2 = login_and_get_token(client, "admin2@test.com")
    resp = client.get(f"/projects/{seeded['p1']}/dashboard", headers={"Authorization": f"Bearer {token2}"})
    assert resp.status_code == 404  # not 403 -- see note in projects.py on why


def test_cross_tenant_task_creation_blocked(client, seeded):
    """Agency 2's admin cannot create a task inside Agency 1's project."""
    token2 = login_and_get_token(client, "admin2@test.com")
    resp = client.post(
        f"/projects/{seeded['p1']}/tasks",
        json={"title": "Sneaky task", "visibility": "internal"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404


def test_own_tenant_access_works(client, seeded):
    token1 = login_and_get_token(client, "admin1@test.com")
    resp = client.get(f"/projects/{seeded['p1']}/tasks", headers={"Authorization": f"Bearer {token1}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2  # both internal + client-visible task, staff sees everything


def test_client_never_sees_internal_tasks(client, seeded):
    """The core 'internal content leaking to clients' rule, exercised
    through the actual list endpoint a client's UI would call."""
    token_client = login_and_get_token(client, "client1@test.com")
    resp = client.get(f"/projects/{seeded['p1']}/tasks", headers={"Authorization": f"Bearer {token_client}"})
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "Client-visible task A1" in titles
    assert "Internal task A1" not in titles


def test_client_cannot_fetch_internal_task_by_direct_id(client, seeded):
    """Even knowing the exact task ID of an internal task, a client gets 404
    -- proves the filter is enforced on the single-item route too, not just
    the list view."""
    token_client = login_and_get_token(client, "client1@test.com")
    resp = client.get(
        f"/projects/{seeded['p1']}/tasks/{seeded['t1_internal']}",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert resp.status_code == 404


def test_client_cannot_create_or_update_task(client, seeded):
    token_client = login_and_get_token(client, "client1@test.com")
    create = client.post(
        f"/projects/{seeded['p1']}/tasks", json={"title": "x"},
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert create.status_code == 403

    update = client.patch(
        f"/projects/{seeded['p1']}/tasks/{seeded['t1_visible']}", json={"status": "done"},
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert update.status_code == 403


def test_client_comment_forced_client_visible(client, seeded):
    """Even if a client's request body tries to sneak visibility=internal,
    the server overrides it."""
    token_client = login_and_get_token(client, "client1@test.com")
    resp = client.post(
        f"/projects/{seeded['p1']}/tasks/{seeded['t1_visible']}/comments",
        json={"body": "trying to be sneaky", "visibility": "internal"},
        headers={"Authorization": f"Bearer {token_client}"},
    )
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "client_visible"


def test_client_cannot_see_internal_comments(client, seeded):
    token1 = login_and_get_token(client, "admin1@test.com")
    client.post(
        f"/projects/{seeded['p1']}/tasks/{seeded['t1_visible']}/comments",
        json={"body": "internal only note", "visibility": "internal"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    token_client = login_and_get_token(client, "client1@test.com")
    resp = client.get(
        f"/projects/{seeded['p1']}/tasks/{seeded['t1_visible']}/comments",
        headers={"Authorization": f"Bearer {token_client}"},
    )
    bodies = [c["body"] for c in resp.json()]
    assert "internal only note" not in bodies


def test_client_dashboard_excludes_internal_tasks_and_hours(client, seeded):
    token1 = login_and_get_token(client, "admin1@test.com")
    client.post(
        f"/projects/{seeded['p1']}/tasks/{seeded['t1_visible']}/time-entries",
        json={"duration_minutes": 60, "entry_date": "2026-01-01"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    token_client = login_and_get_token(client, "client1@test.com")
    dash = client.get(f"/projects/{seeded['p1']}/dashboard", headers={"Authorization": f"Bearer {token_client}"}).json()
    assert dash["total_hours"] == 0.0  # clients never see hours logged
    assert sum(dash["task_counts_by_status"].values()) == 1  # only the 1 client-visible task


def test_invite_resend_does_not_duplicate(client, seeded):
    token1 = login_and_get_token(client, "admin1@test.com")
    r1 = client.post("/invites", json={"email": "new@client.com", "role": "client_user", "client_id": seeded["c1"]},
                      headers={"Authorization": f"Bearer {token1}"})
    r2 = client.post("/invites", json={"email": "new@client.com", "role": "client_user", "client_id": seeded["c1"]},
                      headers={"Authorization": f"Bearer {token1}"})
    assert r1.json()["id"] == r2.json()["id"]  # same invite row reused, not duplicated

    all_invites = client.get("/invites", headers={"Authorization": f"Bearer {token1}"}).json()
    matching = [i for i in all_invites if i["email"] == "new@client.com"]
    assert len(matching) == 1


def test_accept_invite_twice_is_idempotent(client, seeded):
    token1 = login_and_get_token(client, "admin1@test.com")
    invite = client.post("/invites", json={"email": "double@client.com", "role": "client_user", "client_id": seeded["c1"]},
                          headers={"Authorization": f"Bearer {token1}"}).json()

    accept1 = client.post("/auth/accept-invite", json={"token": invite["token"], "name": "Double", "password": "pw"})
    accept2 = client.post("/auth/accept-invite", json={"token": invite["token"], "name": "Double", "password": "pw"})
    assert accept1.status_code == 200
    assert accept2.status_code == 200  # doesn't error, and doesn't create a second account

    # confirm exactly one membership exists for this user in this agency
    from .conftest import TestingSessionLocal
    from app.models import User, Membership
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "double@client.com").first()
    count = db.query(Membership).filter(Membership.user_id == user.id, Membership.agency_id == seeded["a1"]).count()
    db.close()
    assert count == 1


def test_removing_project_member_unassigns_their_tasks(client, seeded):
    token1 = login_and_get_token(client, "admin1@test.com")
    # add admin1 as a project member so we can assign+remove cleanly in this test
    client.post(f"/projects/{seeded['p1']}/members/{seeded['admin1']}", headers={"Authorization": f"Bearer {token1}"})
    client.patch(f"/projects/{seeded['p1']}/tasks/{seeded['t1_internal']}",
                 json={"assignee_user_id": seeded["admin1"]}, headers={"Authorization": f"Bearer {token1}"})

    client.delete(f"/projects/{seeded['p1']}/members/{seeded['admin1']}", headers={"Authorization": f"Bearer {token1}"})

    task = client.get(f"/projects/{seeded['p1']}/tasks/{seeded['t1_internal']}",
                       headers={"Authorization": f"Bearer {token1}"}).json()
    assert task["assignee_user_id"] is None


def test_same_email_different_role_in_different_agency(client, seeded):
    """The 'one person, two agencies' identity model: client1@test.com is a
    client_user in Agency 1. We give the SAME email a membership in Agency 2
    with a DIFFERENT role and confirm login surfaces both, scoped correctly."""
    from .conftest import TestingSessionLocal
    from app.models import Membership, Role
    db = TestingSessionLocal()
    db.add(Membership(user_id=seeded["client_user1"], agency_id=seeded["a2"], role="agency_member"))
    db.commit()
    db.close()

    login = client.post("/auth/login", json={"email": "client1@test.com", "password": "pw"}).json()
    roles_by_agency = {m["agency_id"]: m["role"] for m in login["memberships"]}
    assert roles_by_agency[seeded["a1"]] == "client_user"
    assert roles_by_agency[seeded["a2"]] == "agency_member"
