import importlib
import sys
import types


def test_resolve_camoufox_geoip_disables_invalid_mmdb(monkeypatch, tmp_path):
    mmdb_file = tmp_path / "GeoLite2-City.mmdb"
    mmdb_file.write_bytes(b"not a maxmind database")

    camoufox_module = types.ModuleType("camoufox")
    locale_module = types.ModuleType("camoufox.locale")
    locale_module.MMDB_FILE = mmdb_file

    class InvalidDatabaseError(Exception):
        pass

    def open_database(_path):
        raise InvalidDatabaseError("invalid database")

    maxminddb_module = types.ModuleType("maxminddb")
    maxminddb_module.open_database = open_database
    maxminddb_module.errors = types.SimpleNamespace(
        InvalidDatabaseError=InvalidDatabaseError
    )

    monkeypatch.setitem(sys.modules, "camoufox", camoufox_module)
    monkeypatch.setitem(sys.modules, "camoufox.locale", locale_module)
    monkeypatch.setitem(sys.modules, "maxminddb", maxminddb_module)
    monkeypatch.delenv("CTF_CAMOUFOX_GEOIP", raising=False)
    sys.modules.pop("shared.camoufox_runtime", None)

    camoufox_runtime = importlib.import_module("shared.camoufox_runtime")

    assert camoufox_runtime.resolve_camoufox_geoip() is False
