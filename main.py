import json
import uuid
import time
import random
import datetime
import boto3
from faker import Faker

fake = Faker()

kinesis_client = boto3.client(
    'kinesis',
    region_name='us-east-1'
)

STREAM_NAME = 'ecommerce-events'

PRODUCTS = [
    {"id": str(uuid.uuid4()), "name": "Wireless Earbuds", "price": 49.99},
    {"id": str(uuid.uuid4()), "name": "Smart Watch", "price": 199.99},
    {"id": str(uuid.uuid4()), "name": "Bluetooth Speaker", "price": 79.99},
    {"id": str(uuid.uuid4()), "name": "Laptop", "price": 899.99},
    {"id": str(uuid.uuid4()), "name": "Smartphone", "price": 699.99},
    {"id": str(uuid.uuid4()), "name": "Tablet", "price": 349.99},
    {"id": str(uuid.uuid4()), "name": "Headphones", "price": 149.99},
    {"id": str(uuid.uuid4()), "name": "Camera", "price": 499.99},
    {"id": str(uuid.uuid4()), "name": "Gaming Console", "price": 399.99},
    {"id": str(uuid.uuid4()), "name": "External Hard Drive", "price": 89.99}
]

EVENT_TYPES = {
    "page_view": 0.6,    # 60% of events
    "add_to_cart": 0.25, # 25% of events
    "purchase": 0.15     # 15% of events
}

def generate_event():
    """Generate a random e-commerce event"""

    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    product = random.choice(PRODUCTS)
    
    event_type = random.choices(
        list(EVENT_TYPES.keys()),
        weights=list(EVENT_TYPES.values())
    )[0]
    
    quantity = 1
    if event_type in ["add_to_cart", "purchase"]:
        quantity = random.randint(1, 3)
    
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "product_id": product["id"],
        "timestamp": datetime.datetime.now().timestamp(),
        "session_id": session_id,
        "price": product["price"],
        "quantity": quantity,
        "user_agent": fake.user_agent(),
        "page_url": f"https://example.com/products/{product['id']}",
        "ip_address": fake.ipv4()
    }
    
    return event

def put_event_to_kinesis(event):
    """Send event to Kinesis Data Stream"""
    response = kinesis_client.put_record(
        StreamName=STREAM_NAME,
        Data=json.dumps(event),
        PartitionKey=event['user_id']
    )
    return response

def simulate_events(count=100, delay=0.2):
    """Simulate multiple e-commerce events"""
    for i in range(count):
        event = generate_event()
        response = put_event_to_kinesis(event)
        print(f"Event {i+1}/{count} sent to Kinesis. Sequence number: {response['SequenceNumber']}")
        print(f"Event data: {json.dumps(event, indent=2)}")
        time.sleep(delay)  # Add delay between events

if __name__ == "__main__":
    print(f"Starting to send {100} events to Kinesis stream '{STREAM_NAME}'...")
    simulate_events(count=100)
    print("Done sending events.")