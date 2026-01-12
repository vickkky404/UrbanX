import requests
import json

base_url = "http://127.0.0.1:5000"

def test_captain_flow():
    print("Testing Captain Flow...")

    # 1. Signup
    signup_data = {
        "name": "Test Captain",
        "email": "captain_test_vehicle@urbanx.com",
        "password": "password123",
        "vehicle_type": "bike",
        "age": 30
    }

    # Try signup (might already exist, so we handle that)
    try:
        r = requests.post(f"{base_url}/captain/signup", json=signup_data)
        print(f"Signup Status: {r.status_code}, Response: {r.json()}")
    except Exception as e:
        print(f"Signup failed to connect: {e}")
        return

    # 2. Login with CORRECT vehicle
    login_correct = {
        "email": "captain_test_vehicle@urbanx.com",
        "password": "password123",
        "vehicle_type": "bike"
    }
    r = requests.post(f"{base_url}/captain/login", json=login_correct)
    print(f"Login (Correct Vehicle) Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Login Success. Response Data: {data}")
        if 'captain' in data:
            cap = data['captain']
            if cap.get('age') == 30:
                print("PASS: Age is correctly returned.")
            else:
                print(f"FAIL: Age mismatch. Got {cap.get('age')}")

            if cap.get('total_earnings') == 0.0:
                 print("PASS: Earnings initialized correctly.")
            else:
                 print(f"FAIL: Earnings mismatch. Got {cap.get('total_earnings')}")
    else:
        print(f"FAIL: Correct login failed. {r.text}")

    # 3. Login with WRONG vehicle
    login_wrong = {
        "email": "captain_test_vehicle@urbanx.com",
        "password": "password123",
        "vehicle_type": "car" # Mismatch
    }
    r = requests.post(f"{base_url}/captain/login", json=login_wrong)
    print(f"Login (Wrong Vehicle) Status: {r.status_code}")
    if r.status_code == 401:
        print(f"PASS: Wrong vehicle rejected. Message: {r.json().get('message')}")
    else:
        print(f"FAIL: Wrong vehicle NOT rejected. Status: {r.status_code}")

if __name__ == "__main__":
    test_captain_flow()

