import asyncio
from web_server import get_stats

class MockRequest:
    headers = {"X-User-Id": "1651746145"}

async def main():
    try:
        req = MockRequest()
        res = await get_stats(req)
        print("Success:", res.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
