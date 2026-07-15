"""Rol hiyerarsisi: scope_city_for / scope_district_for / require_write_access (bkz. CLAUDE.md v2.9)."""

import pytest
from fastapi import HTTPException

from app.core.auth import require_write_access, scope_city_for, scope_district_for
from app.modules.auth.models import USER_ROLES


def test_user_roles_include_hierarchy():
    assert set(USER_ROLES) == {"admin", "city_operator", "ilce_amiri", "merkez"}


def test_scope_city_for_city_operator_and_ilce_amiri():
    assert scope_city_for({"role": "city_operator", "city": "Amasya"}) == "amasya"
    assert scope_city_for({"role": "ilce_amiri", "city": "amasya", "district": "Merzifon"}) == "amasya"


def test_scope_city_for_admin_and_merkez_unrestricted():
    assert scope_city_for({"role": "admin", "city": None}) is None
    assert scope_city_for({"role": "merkez", "city": None}) is None
    assert scope_city_for(None) is None


def test_scope_district_for_only_ilce_amiri():
    assert scope_district_for({"role": "ilce_amiri", "city": "amasya", "district": "Merzifon"}) == "Merzifon"
    assert scope_district_for({"role": "city_operator", "city": "amasya"}) is None
    assert scope_district_for({"role": "admin"}) is None
    assert scope_district_for(None) is None


async def test_require_write_access_allows_ilce_amiri():
    user = {"role": "ilce_amiri", "city": "amasya", "district": "Merzifon"}
    result = await require_write_access(x_admin_key=None, user=user)
    assert result == user


async def test_require_write_access_rejects_merkez_without_admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "test-key")
    user = {"role": "merkez", "city": None}
    with pytest.raises(HTTPException) as exc_info:
        await require_write_access(x_admin_key=None, user=user)
    assert exc_info.value.status_code == 401
