import razorpay

client = razorpay.Client(auth=("rzp_test_TX2Aummpl8hEY7", "eXeX20iiM2aBkOq6KGiDQXIe"))

print("Fetching active test payment links...")
try:
    links = client.payment_link.all({"count": 30})
    items = links.get("payment_links", [])
    print(f"Found {len(items)} test links. Cancelling to free up sandbox limit...")
    
    for item in items:
        link_id = item.get("id")
        status = item.get("status")
        if status in ["created", "partially_paid"]:
            try:
                client.payment_link.cancel(link_id)
                print(f"Cancelled: {link_id}")
            except Exception as ex:
                print(f"Skipped {link_id}: {ex}")

    print("\n✅ Sandbox quota successfully cleared! You can now create new links.")
except Exception as e:
    print("Error:", e)