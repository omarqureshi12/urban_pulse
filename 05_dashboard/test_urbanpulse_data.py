"""Read-only smoke tests for the packaged UrbanPulse dashboard data layer."""

from urbanpulse_data import (
    add_primary_metric_flags,
    available_options,
    connect,
    load_contracts,
    load_filtered,
    load_provenance,
    load_quality_flags,
)


def main() -> None:
    con = connect()
    options = available_options(con)
    assert len(options["cities"]) == 7
    assert "Unknown" in options["zones"]
    assert options["hours"] == [0, 4, 8, 12, 16, 20]

    frame = load_filtered(
        con,
        cities=options["cities"],
        zones=options["zones"],
        start_date=options["min_date"],
        end_date=options["max_date"],
        hours=options["hours"],
    )
    assert len(frame) == 1600
    flags = load_quality_flags(con)
    enriched = add_primary_metric_flags(frame, flags)
    assert int(enriched["speed_primary_valid"].sum()) == 1551
    assert int(enriched["temperature_primary_valid"].sum()) > 0

    contracts = load_contracts(con)
    assert "parking" in set(contracts["contract_key"])
    assert "power_outage" in set(contracts["contract_key"])
    run, diagnostics = load_provenance(con)
    assert not run.empty
    assert not diagnostics.empty
    assert int(diagnostics["flagged"].sum()) == 0
    con.close()
    print("urbanpulse_data_smoke_test=passed")


if __name__ == "__main__":
    main()
