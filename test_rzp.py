import razorpay

client = razorpay.Client(auth=("rzp_test_TX2Aummpl8hEY7", "eXeX20iiM2aBkOq6KGiDQXIe"))

try:
    link = client.payment_link.create({
        "amount": 249900,
        "currency": "INR",
        "description": "Test Recovery Link",
        "customer": {
            "name": "Aarav Mehta",
            "email": "aarav@example.com"
        }
    })
    print("SUCCESS! Real URL:", link["short_url"])
except Exception as e:
    print("RAZORPAY ERROR:", e)