import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_admin_map_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/health")).json()["status"] == "ok"
        admin = await client.get("/admin")
        assert admin.status_code == 200
        assert "Admin" in admin.text
        map_page = await client.get("/map")
        assert map_page.status_code == 200
        assert "TRIA C4I" in map_page.text
        assert "Canlı Devriyeler" in map_page.text
        assert "c4i.js" in map_page.text
        assert "Olay Tipi" in map_page.text
        assert "Sunum Demo" not in map_page.text  # demo/test verisi sistemi kaldirildi
        assert "markercluster" in map_page.text.lower()
        assert "leaflet-heat" in map_page.text.lower()
        assert "timeSlider" not in map_page.text
        assert "leaflet-draw" not in map_page.text.lower()
        root = await client.get("/", follow_redirects=False)
        assert root.status_code in (301, 302, 307, 308)
        assert "/admin" in root.headers.get("location", "")
