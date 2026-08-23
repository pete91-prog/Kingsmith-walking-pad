import asyncio

from kingsmith_walkingpad.wifi import probe_host


async def test_probe_closed_host() -> None:
    result = await probe_host("127.0.0.1", ports=(1,), timeout=0.2)
    assert result.host == "127.0.0.1"
    assert result.open_ports == []
    assert "cloud-bound" in result.notes


async def test_probe_open_port() -> None:
    server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await probe_host("127.0.0.1", ports=(port,), timeout=0.5)
        assert result.open_ports == [port]
    finally:
        server.close()
        await server.wait_closed()
