from flask import Flask, render_template, request, redirect, url_for, session
import requests
import pymysql

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

# Database Connection using pymysql
db = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="mobile comparison"
)
cursor = db.cursor()

# Create table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        phone VARCHAR(10) NOT NULL
    )
""")
db.commit()

#  User Authentication Routes
@app.route('/')
def home():
    return render_template('sign-in.html')

@app.route('/validate-signin', methods=['POST'])
def validate_signin():
    email = request.form.get('email')
    phone = request.form.get('phone')

    if not email or not phone or len(phone) != 10 or not phone.isdigit():
        return "Invalid email or phone number. <a href='/'>Go back</a>"

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute("INSERT INTO users (email, phone) VALUES (%s, %s)", (email, phone))
        db.commit()

    session['email'] = email
    session['phone'] = phone

    return redirect(url_for('index'))

@app.route('/index')
def index():
    if 'email' not in session or 'phone' not in session:
        return redirect(url_for('home'))
    return render_template('index.html')

#  Wishlist Routes (PLACE IT HERE)
@app.route('/wishlist', methods=['GET'])
def wishlist():
    if 'email' not in session:
        return redirect(url_for('signin_page'))

    cursor.execute("SELECT * FROM wishlist WHERE user_email = %s", (session['email'],))
    wishlist_items = cursor.fetchall()
    return render_template('wishlist.html', wishlist=wishlist_items)

@app.route('/add-to-wishlist', methods=['POST'])
def add_to_wishlist():
    if 'email' not in session:
        return redirect(url_for('signin_page'))

    product_title = request.form.get('product_title')
    product_photo = request.form.get('product_photo')
    product_price = request.form.get('product_price')
    product_url = request.form.get('product_url')
    source = request.form.get('source')

    cursor.execute("""
        INSERT INTO wishlist (user_email, product_title, product_photo, product_price, product_url, source)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (session['email'], product_title, product_photo, product_price, product_url, source))
    db.commit()

    return redirect(url_for('wishlist'))

@app.route('/remove-from-wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'email' not in session:
        return redirect(url_for('signin_page'))

    product_title = request.form.get('product_title')

    cursor.execute("DELETE FROM wishlist WHERE user_email = %s AND product_title = %s",
                   (session['email'], product_title))
    db.commit()

    return redirect(url_for('wishlist'))

#  Search Function (AFTER Wishlist Routes)
@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    if not query:
        return "No search query provided!", 400

    print(f"Searching for: {query}")  # Debugging

    amazon_products = fetch_amazon_products(query)
    aliexpress_products = fetch_aliexpress_products(query)

    if not amazon_products and not aliexpress_products:
        print("No products found from APIs!")  # Debugging

    all_products = amazon_products + aliexpress_products
    all_products = remove_duplicates(all_products)

    return render_template('result.html', products=all_products, query=query)

#  Helper Functions (LAST)
def fetch_amazon_products(query):
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": "5d58e9e70fmsh6a23c92ad4571c6p1c3895jsn9f1f8c12ce6d",
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    params = {"query": query, "country": "IN"}

    response = requests.get(url, headers=headers, params=params)
    print(response.status_code, response.text)  # Debugging API Response

    if response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("products", [])
    else:
        return []

def fetch_aliexpress_products(query):
    url = "https://aliexpress-datahub.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": "5d58e9e70fmsh6a23c92ad4571c6p1c3895jsn9f1f8c12ce6d",
        "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"
    }
    params = {"q": query, "page": "1"}

    response = requests.get(url, headers=headers, params=params)
    print(response.status_code, response.text)  # Debugging API Response

    if response.status_code == 200:
        data = response.json()
        products = []
        for item in data.get('products', []):
            products.append({
                "product_title": item.get('product_title', 'No Title'),
                "product_photo": item.get('product_main_image_url', 'https://via.placeholder.com/120'),
                "product_price": item.get('app_sale_price', 'Not Available'),
                "product_url": item.get('product_detail_url', '#'),
                "source": "AliExpress"
            })
        return products
    else:
        return []

def remove_duplicates(products):
    unique_products = {}

    for product in products:
        title = product.get('product_title', '').strip().lower()
        price_str = product.get('product_price', '')

        if price_str is None:  # Handle NoneType price
            price_str = "0"  # Default value for missing prices

        price_str = price_str.replace('₹', '').replace(',', '').strip()

        try:
            price = float(price_str)
        except ValueError:
            price = float('inf')  # Set to a very high value if price is not a valid number

        if title in unique_products:
            if price < unique_products[title]['price']:  # Keep the cheaper product
                unique_products[title] = {'product': product, 'price': price}
        else:
            unique_products[title] = {'product': product, 'price': price}

    return [entry['product'] for entry in unique_products.values()]


if __name__ == '__main__':
    app.run(debug=True)
