import requests
import json
import random
import time

base_url = "http://127.0.0.1:5000"

def test_captain_flow():
    print("--- Starting Captain Auth Flow Test ---")
    rand_id = random.randint(1000, 9999)
    email = f"capt_{rand_id}@urbanx.com"


    signup_data = {
        "name": f"Captain {rand_id}",
        "email": email,
        "password": "password123",
        "vehicle_type": "bike",
        "age": 30
    }

    print(f"1. Attempting Signup for {email}...")
    try:
        r = requests.post(f"{base_url}/captain/signup", json=signup_data)
        if r.status_code == 201:
             print("   [PASS] Signup Successful")
        else:
             print(f"   [FAIL] Signup Failed: {r.status_code} - {r.text}")
             return
    except Exception as e:
        print(f"   [FAIL] Exception during signup: {e}")
        return

    print("2. Attempting Login with CORRECT vehicle type...")
    login_correct = {
        "email": email,
        "password": "password123",
        "vehicle_type": "bike"
    }
    r = requests.post(f"{base_url}/captain/login", json=login_correct)
    if r.status_code == 200:
        data = r.json()
        print("   [PASS] Login Successful")

        cap = data.get('captain', {})
        if cap.get('age') == 30:
            print(f"   [PASS] Age is {cap.get('age')}")
        else:
            print(f"   [FAIL] Age mismatch: {cap.get('age')}")

        if cap.get('total_earnings') == 0.0:
             print(f"   [PASS] Earnings is {cap.get('total_earnings')}")
        else:
             print(f"   [FAIL] Earnings mismatch: {cap.get('total_earnings')}")
    else:
        print(f"   [FAIL] Login Failed: {r.status_code} - {r.text}")


    print("3. Attempting Login with WRONG vehicle type...")
    login_wrong = {
        "email": email,
        "password": "password123",
        "vehicle_type": "cab"
    }
    r = requests.post(f"{base_url}/captain/login", json=login_wrong)
    if r.status_code == 401:
        print("   [PASS] Login Rejected correctly")
    else:
        print(f"   [FAIL] Login should have failed but got: {r.status_code}")

    print("--- Test Complete ---")


    print("Testing done, conducting Unit testing")
    print("JUnit, Selenium.....\n\testing")

if __name__ == "__main__":
    test_captain_flow()

