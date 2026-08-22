from app.clients.grid5000 import Grid5000Client


def test_grid5000_job_payload() -> None:
    payload = Grid5000Client.build_job_payload(
        site_id="grenoble",
        node_name="chartreuse3-1",
        duration_minutes=60,
    )

    assert payload["resources"] == (
        "host=1,walltime=01:00:00"
    )
    assert payload["properties"] == (
        "host='chartreuse3-1'"
    )

    assert payload["command"] == "sleep 3600"

    payload = Grid5000Client.build_job_payload(
        site_id="grenoble",
        node_name="chartreuse3-1",
        duration_minutes=60,
        queue="abaca",
    )

    assert payload["queue"] == "abaca"