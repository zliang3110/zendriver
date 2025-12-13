"""
Example: Using a proxy with authentication in zendriver

This example demonstrates how to use an HTTP proxy with authentication.
For proxies that require username/password authentication, we use the
CDP Fetch API to handle the auth challenge.

Proxy URL format: http://username:password@host:port
"""

import asyncio
from urllib.parse import urlparse

try:
    import zendriver as zd
    from zendriver import cdp
except (ModuleNotFoundError, ImportError):
    import os
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import zendriver as zd
    from zendriver import cdp


# Parse proxy URL to extract components
PROXY_URL = "http://brd-customer-hl_b566ad26-zone-isp_proxy6:o61gdbb5nenf@brd.superproxy.io:33335"


def parse_proxy_url(proxy_url: str) -> dict:
    """
    Parse a proxy URL into its components.

    Args:
        proxy_url: Proxy URL in format http://username:password@host:port

    Returns:
        Dictionary with host, port, username, password
    """
    parsed = urlparse(proxy_url)
    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "username": parsed.username,
        "password": parsed.password,
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
    }


async def main() -> None:
    # Parse the proxy URL
    proxy = parse_proxy_url(PROXY_URL)
    print(f"Using proxy server: {proxy['server']}")

    # Start browser with proxy server argument
    # Note: --proxy-server only sets the proxy host:port, authentication is handled separately
    browser = await zd.start(
        browser_args=[
            f"--proxy-server={proxy['server']}",
        ]
    )

    tab = browser.main_tab

    # Set up handler for proxy authentication challenges
    async def handle_auth_required(event: cdp.fetch.AuthRequired) -> None:
        """Handle proxy authentication challenge (HTTP 407)"""
        print(f"Auth required for: {event.request.url}")
        print(f"Auth challenge from: {event.auth_challenge.origin}")

        # Respond with credentials
        auth_response = cdp.fetch.AuthChallengeResponse(
            response="ProvideCredentials",
            username=proxy["username"],
            password=proxy["password"],
        )
        await tab.send(cdp.fetch.continue_with_auth(event.request_id, auth_response))

    # Set up handler for paused requests (continue them normally)
    async def handle_request_paused(event: cdp.fetch.RequestPaused) -> None:
        """Continue paused requests that are not auth challenges"""
        # RequestPaused is fired for intercepted requests
        # We need to continue them, auth challenges are handled by AuthRequired
        try:
            await tab.send(cdp.fetch.continue_request(request_id=event.request_id))
        except Exception as e:
            print(f"Error continuing request: {e}")

    # Register event handlers BEFORE enabling fetch
    tab.add_handler(cdp.fetch.AuthRequired, handle_auth_required)
    tab.add_handler(cdp.fetch.RequestPaused, handle_request_paused)

    # Enable Fetch domain to handle proxy authentication
    # handleAuthRequests=True enables authRequired events for 401/407 responses
    await tab.send(cdp.fetch.enable(handle_auth_requests=True))

    # Navigate to a page to test the proxy
    # Using httpbin to verify our IP and headers
    print("\nNavigating to test page...")
    await tab.get("https://httpbin.org/ip")

    # Wait for page to load
    await tab.sleep(3)

    # Get and print the page content (shows the IP from proxy)
    body = await tab.select("body")
    if body:
        content = await body.get_html()
        print(f"\nResponse from httpbin.org/ip:\n{content}")

    # Test another page
    print("\nNavigating to example.com...")
    await tab.get("https://example.com")
    await tab.sleep(2)

    title = await tab.select("h1")
    if title:
        print(f"Page title: {await title.text}")

    print("\nProxy test completed successfully!")

    # Keep browser open for inspection (optional)
    # await tab.sleep(30)

    await browser.stop()


async def simple_proxy_example() -> None:
    """
    Simple example for proxies that don't require authentication.
    Just use the --proxy-server browser argument.
    """
    # For a proxy without authentication, simply use:
    browser = await zd.start(
        browser_args=[
            "--proxy-server=http://proxy-host:proxy-port",
        ]
    )

    tab = browser.main_tab
    await tab.get("https://example.com")
    await tab.sleep(2)

    await browser.stop()


async def socks5_proxy_example() -> None:
    """
    Example using SOCKS5 proxy.
    """
    browser = await zd.start(
        browser_args=[
            "--proxy-server=socks5://socks-proxy-host:1080",
        ]
    )

    tab = browser.main_tab
    await tab.get("https://example.com")
    await tab.sleep(2)

    await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
