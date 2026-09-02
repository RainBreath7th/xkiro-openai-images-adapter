import httpx
import respx


@respx.mock
async def test_generation_forwards_xkiro_api_key(client):
    route = respx.post("https://api.xkiro.com/v1/images/generations").mock(
        return_value=httpx.Response(400, json={"error": {"message": "stop"}})
    )

    response = await client.post(
        "/v1/images/generations",
        headers={"Authorization": "Bearer client-key"},
        json={"prompt": "a cat"},
    )

    assert response.status_code == 400
    assert route.calls.last.request.headers["Authorization"] == "Bearer upstream-key"


    respx.post("https://api.xkiro.com/v1/images/generations").mock(return_value=httpx.Response(202, json={"id": "job-2"}))
    respx.get("https://api.xkiro.com/v1/images/generations/job-2").mock(return_value=httpx.Response(200, json={
        "status": "succeeded", "created": 321, "data": [{"url": "https://cdn.xkiro.com/a.png"}]
    }))
    respx.get("https://cdn.xkiro.com/a.png").mock(return_value=httpx.Response(200, content=b"png"))
    response = await client.post(
        "/v1/images/generations", headers={"Authorization": "Bearer client-key"},
        json={"prompt": "a cat", "response_format": "b64_json"},
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["b64_json"] == "cG5n"


@respx.mock
async def test_models_forward_xkiro_api_key(client):
    route = respx.get("https://api.xkiro.com/v1/models").mock(
        return_value=httpx.Response(200, json={"object": "list", "data": []})
    )

    response = await client.get("/v1/models", headers={"Authorization": "Bearer client-key"})

    assert response.status_code == 200
    assert route.calls.last.request.headers["Authorization"] == "Bearer upstream-key"


    payload = {"object": "list", "data": [{"id": "gpt-image", "modality": "image", "pricing": {"input": 0}}]}
    route = respx.get("https://api.xkiro.com/v1/models").mock(return_value=httpx.Response(200, json=payload))
    response = await client.get("/v1/models", headers={"Authorization": "Bearer client-key"})
    assert response.status_code == 200
    assert route.calls.last.request.headers["Authorization"] == "Bearer upstream-key"
    assert route.calls.last.request.url.params["modality"] == "image"
