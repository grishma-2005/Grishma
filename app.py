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

@app.route('/')
def home():
    return render_template('sign-in.html')

@app.route('/validate-signin', methods=['POST'])
def validate_signin():
    email = request.form.get('email')
    phone = request.form.get('phone')

    if not email or not phone or len(phone) != 10 or not phone.isdigit():
        return "Invalid email or phone number. <a href='/'>Go back</a>"

    session['email'] = email
    session['phone'] = phone

    # Store user data in the database
    cursor.execute("INSERT INTO users (email, phone) VALUES (%s, %s)", (email, phone))
    db.commit()

    return redirect(url_for('captcha'))

@app.route('/captcha')
def captcha():
    if 'email' not in session or 'phone' not in session:
        return redirect(url_for('home'))  
    return render_template('captcha.html')

@app.route('/store-captcha-code', methods=['POST'])
def store_captcha_code():
    captcha_code = request.form.get('captcha_code')
    session['captcha_code'] = captcha_code
    return '', 204  

@app.route('/validate-captcha', methods=['POST'])
def validate_captcha():
    user_captcha = request.form.get('captchaInput')
    generated_captcha = session.get('captcha_code')

    if user_captcha and generated_captcha and user_captcha.upper() == generated_captcha.upper():
        return redirect(url_for('index'))
    else:
        return "Captcha did not match. <a href='/captcha'>Try Again</a>"

@app.route('/index')
def index():
    if 'email' not in session or 'phone' not in session:
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')

    if not query:
        return "No search query provided!", 400

    color_filter = extract_color_from_query(query)

    amazon_products = fetch_amazon_products(query)
    aliexpress_products = fetch_aliexpress_products(query)

    all_products = amazon_products + aliexpress_products

    all_products = remove_duplicates(all_products)

    if color_filter:
        all_products = [product for product in all_products if color_filter in product.get('product_title', '').lower()]

    return render_template('result.html', products=all_products, query=query)

def extract_color_from_query(query):
    colors = ['red', 'blue', 'green', 'black', 'white', 'yellow', 'gold', 'silver', 'purple', 'pink']
    for color in colors:
        if color in query.lower():
            return color
    return None

def fetch_amazon_products(query):
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": "2c179a882amsh5e2b1e455d1f66bp143ee7jsn590ca4a957d4",
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    params = {"query": query, "country": "IN"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        products = data.get("data", {}).get("products", [])
        for product in products:
            product['source'] = 'Amazon'
        return products
    else:
        return []

def fetch_aliexpress_products(query):
    url = "https://aliexpress-datahub.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": "5b59bdb511mshc1f870121bdf79cp193064jsn118bb1ad689a",
        "X-RapidAPI-Host": "aliexpress-datahub.p.rapidapi.com"
    }
    params = {"q": query, "page": "1"}

    response = requests.get(url, headers=headers, params=params)
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
        price_str = product.get('product_price', '').replace('₹', '').replace(',', '').strip()

        try:
            price = float(price_str)
        except ValueError:
            price = float('inf')

        if title in unique_products:
            if price < unique_products[title]['price']:
                unique_products[title] = {'product': product, 'price': price}
        else:
            unique_products[title] = {'product': product, 'price': price}

    return [entry['product'] for entry in unique_products.values()]

if __name__ == '__main__':
    app.run(debug=True)
