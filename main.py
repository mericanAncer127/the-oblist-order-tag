import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timezone, timedelta

load_dotenv()

# Set up your Shopify credentials

API_KEY = os.getenv("API_KEY")
PASSWORD = os.getenv("PASSWORD")
SHOP_NAME = os.getenv("HOSTNAME")

# Initialize the Shopify session
base_url = f'https://{SHOP_NAME}/admin/api/2024-10/'

def get_all_unfulfilled_orders():
  last = 0
  orders = []
  headers = {'X-Shopify-Access-Token': PASSWORD, 'Content-Type': 'application/json'}

  while True:
    # Fetch unfulfilled orders with pagination using `since_id`
    url = f'{base_url}orders.json?fulfillment_status=unshipped&limit=250&since_id={last}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raises error if request fails
    data = response.json()
    
    # Get orders from this page
    sub_orders = data['orders']
    if not sub_orders:  # Break if there are no more orders
      break

    # Add orders from this page to the list
    orders.extend(sub_orders)
    
    # Update the last order ID to use for the next `since_id` query
    last = sub_orders[-1]['id']

    # If the number of orders fetched is less than 250, it's the last page
    if len(sub_orders) < 250:
      break

  return orders

# Execute the function to fetch all unfulfilled orders
try:
    all_unfulfilled_orders = get_all_unfulfilled_orders()
    print(f"Total unfulfilled orders fetched: {len(all_unfulfilled_orders)}")
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except requests.exceptions.RequestException as req_err:
    print(f"Request error occurred: {req_err}")

def handle_late_order(current_tags, order_id):
  new_tags='late-delivery'
  
  # Combine current tags with new tags (make sure to remove duplicates)
  all_tags = f"{current_tags}, {new_tags}".strip(", ")
  all_tags = ", ".join(set(all_tags.split(", ")))

  # URL for updating the order tags
  url = f"{base_url}orders/{order_id}.json"
  
  # Data to update the tags
  data = {
    "order": {
      "id": order_id,
      "tags": all_tags
    }
  }

  # Send the PUT request to update tags
  response = requests.put(url, json=data, auth=(API_KEY, PASSWORD))
  response.raise_for_status()  # Raise an error for bad responses
  if response.status_code == 200:
    print(f'***** Order #{order_id} is now late: Updated Tags to {all_tags} *****')
  else:
    print(f'***** Order #{order_id} is now late: But Failed Updateing Tags  *****')

# Function to get product by ID
def get_product_meta_fields_by_id(product_id):
  url = f"https://{SHOP_NAME}/admin/api/2024-10/products/{product_id}/metafields.json"
  headers = {'X-Shopify-Access-Token': PASSWORD, 'Content-Type': 'application/json'}
  response = requests.get(url, headers=headers)

  data = response.json()
  try:
    metafields = data['metafields']
    return metafields
  except Exception as e:
    print("Error fetching product:", e)
    return None

def get_current_time():
  # Get current UTC time
  utc_now = datetime.now(timezone.utc)
  # Create a timezone object for UTC+1
  utc_plus_one = timezone(timedelta(hours=1))
  # Convert UTC time to UTC+1
  utc_plus_one_time = utc_now.astimezone(utc_plus_one)
  
  return utc_plus_one_time

# first_order = all_unfulfilled_orders[0]
# for key in first_order:
#   print(f'{key}:{first_order[key]}')

for order in all_unfulfilled_orders:
  created_at_str = order['created_at']
  print('=' * 50)
  print("Order created at: ", created_at_str)
  order_tagged = False
  for item in order['line_items']:
    product_id = item['product_id']
    if not product_id:
      continue
    meta = get_product_meta_fields_by_id(product_id)
    # Example usage

    if meta:
      for field in meta:
        if field['key'] == 'maxdeltime':
          value = field['value']
          n_days = int(value)*7  # Replace with the number of weeks you want to add
          if not value:
            n_days = 3 
          print(f"maxDelveryTime: {n_days} days")
          # Parse the date string
          order_made_at = datetime.fromisoformat(created_at_str)
          # Add n weeks
          order_expected_at = order_made_at + timedelta(days=n_days)

          if order_expected_at < get_current_time():
            handle_late_order(order['tags'], order['id'])
            order_tagged = True
          # Print the new date
          print("Expected Date:", order_expected_at)
          print("Today:", get_current_time())
    else:
        print("Product not found.")
    if order_tagged:
      break
      