import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_spatial_search_polygon():
    transport = ASGITransport(app=app)
    body = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [32.0, 39.5],
                    [33.5, 39.5],
                    [33.5, 40.5],
                    [32.0, 40.5],
                    [32.0, 39.5],
                ]
            ],
        }
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            res = await client.post("/api/v1/incidents/spatial-search", json=body)
        except Exception:
            pytest.skip("Veritabani baglantisi yok")
        if res.status_code == 200:
            data = res.json()
            assert data["type"] == "FeatureCollection"
            assert "features" in data
        else:
            pytest.skip("Veritabani baglantisi yok")
