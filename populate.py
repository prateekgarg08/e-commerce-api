import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from uuid import uuid4
import bcrypt
from faker import Faker

# Initialize Faker for generating realistic data
fake = Faker()

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['ecommerce']

# Clear existing data
db.users.delete_many({})
db.merchants.delete_many({})
db.categories.delete_many({})
db.products.delete_many({})
db.orders.delete_many({})

# Helper function to generate a random past date
def random_past_date(days=365):
    return datetime.utcnow() - timedelta(days=random.randint(1, days))

# Create admin user
admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
admin_user = {
    "_id": str(uuid4()),
    "email": "admin@example.com",
    "hashed_password": admin_password,
    "full_name": "Admin User",
    "role": "admin",
    "is_active": True,
    "created_at": random_past_date(100),
    "updated_at": datetime.utcnow()
}
db.users.insert_one(admin_user)
print(f"Created admin user: {admin_user['email']}")

# Create merchant users and their merchant profiles
merchant_users = []
merchants = []

for i in range(2):
    # Create merchant user
    merchant_password = bcrypt.hashpw(f"merchant{i+1}".encode('utf-8'), bcrypt.gensalt())
    merchant_user = {
        "_id": str(uuid4()),
        "email": f"merchant{i+1}@example.com",
        "hashed_password": merchant_password,
        "full_name": fake.name(),
        "role": "merchant",
        "is_active": True,
        "created_at": random_past_date(100),
        "updated_at": datetime.utcnow()
    }
    db.users.insert_one(merchant_user)
    merchant_users.append(merchant_user)
    
    # Create merchant profile
    merchant = {
        "_id": str(uuid4()),
        "user_id": merchant_user["_id"],
        "business_name": fake.company(),
        "business_description": fake.catch_phrase(),
        "contact_email": merchant_user["email"],
        "contact_phone": fake.phone_number(),
        "is_verified": bool(random.getrandbits(1)),
        "created_at": merchant_user["created_at"],
        "updated_at": merchant_user["updated_at"]
    }
    db.merchants.insert_one(merchant)
    merchants.append(merchant)
    print(f"Created merchant: {merchant['business_name']}")

# Create regular users
regular_users = []
for i in range(5):
    user_password = bcrypt.hashpw(f"user{i+1}".encode('utf-8'), bcrypt.gensalt())
    user = {
        "_id": str(uuid4()),
        "email": f"user{i+1}@example.com",
        "hashed_password": user_password,
        "full_name": fake.name(),
        "role": "user",
        "is_active": True,
        "created_at": random_past_date(100),
        "updated_at": datetime.utcnow()
    }
    db.users.insert_one(user)
    regular_users.append(user)
    print(f"Created user: {user['email']}")

# Create categories
categories = []
category_names = [
    "Electronics", 
    "Clothing", 
    "Home & Garden", 
    "Books & Media", 
    "Sports & Outdoors"
]

for i, name in enumerate(category_names):
    category = {
        "_id": str(uuid4()),
        "name": name,
        "description": fake.sentence(),
        "parent_id": None,
        "is_active": True,
        "created_at": random_past_date(100),
        "updated_at": datetime.utcnow()
    }
    db.categories.insert_one(category)
    categories.append(category)
    print(f"Created category: {category['name']}")

# Create products (10 per category)
products = []
for category in categories:
    # Generate products for this category
    for i in range(10):
        # Choose a random merchant
        merchant = random.choice(merchants)
        
        # Product details
        product_name = fake.bs()
        price = round(random.uniform(10.0, 1000.0), 2)
        product = {
            "_id": str(uuid4()),
            "name": product_name,
            "description": fake.paragraph(),
            "price": price,
            "merchant_id": merchant["_id"],
            "category_id": category["_id"],
            "stock_quantity": random.randint(0, 100),
            "images": [fake.image_url() for _ in range(random.randint(1, 3))],
            "is_active": bool(random.getrandbits(1)),
            "created_at": random_past_date(50),
            "updated_at": datetime.utcnow()
        }
        db.products.insert_one(product)
        products.append(product)
        print(f"Created product: {product['name']} (Category: {category['name']}, Merchant: {merchant['business_name']})")

# Create some orders
for i in range(20):
    # Choose a random user
    user = random.choice(regular_users)
    
    # Generate 1-5 random order items
    num_items = random.randint(1, 5)
    order_items = []
    total_amount = 0
    
    # Select random products for this order
    for _ in range(num_items):
        product = random.choice(products)
        quantity = random.randint(1, 3)
        item_price = product["price"]
        
        order_item = {
            "product_id": product["_id"],
            "quantity": quantity,
            "price": item_price
        }
        
        order_items.append(order_item)
        total_amount += item_price * quantity
    
    # Create the order
    statuses = ["pending", "paid", "shipped", "delivered", "cancelled"]
    weights = [0.2, 0.3, 0.2, 0.2, 0.1]  # Weighted probabilities
    status = random.choices(statuses, weights=weights, k=1)[0]
    
    order = {
        "_id": str(uuid4()),
        "user_id": user["_id"],
        "items": order_items,
        "total_amount": round(total_amount, 2),
        "status": status,
        "shipping_address": fake.address(),
        "contact_phone": fake.phone_number(),
        "created_at": random_past_date(30),
        "updated_at": datetime.utcnow()
    }
    
    db.orders.insert_one(order)
    print(f"Created order #{i+1}: ${order['total_amount']} ({status})")

print("\nDatabase population complete!")
print(f"Created {db.users.count_documents({})} users")
print(f"Created {db.merchants.count_documents({})} merchants")
print(f"Created {db.categories.count_documents({})} categories")
print(f"Created {db.products.count_documents({})} products")
print(f"Created {db.orders.count_documents({})} orders")