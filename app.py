from flask import Flask, render_template, request, redirect, url_for
import pyttsx3
import pymysql

app = Flask(__name__)

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ecommerce'
}

# Voice support function
def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# Helper function to get database connection
def get_db_connection():
    return pymysql.connect(**db_config)

# Routes
@app.route('/', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        choice = request.form.get('choice')
        if choice == '1':
            return redirect(url_for('login'))
        elif choice == '2':
            return redirect(url_for('signup'))
        else:
            speak_text("Invalid choice. Please choose 1 for Login or 2 for Signup.")
    speak_text("Welcome to the e-commerce website. Press 1 to login or 2 to sign up.")
    return render_template('welcome.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            speak_text("Login successful. Redirecting to home page.")
            return redirect(url_for('home'))
        else:
            speak_text("Invalid credentials. Please try again.")

    speak_text("Enter your username. Then press tab to enter your password.")
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            speak_text("Signup successful. You can now log in.")
            return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            speak_text("Username already exists or there was an issue with signup. Please try again.")
        finally:
            cursor.close()
            conn.close()

    speak_text("Enter a username to sign up. Then press tab to enter your password.")
    return render_template('signup.html')


@app.route('/home', methods=['GET', 'POST'])
def home():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    # Create a dictionary to map category numbers to IDs
    category_map = {str(index + 1): category['id'] for index, category in enumerate(categories)}

    # Construct voice feedback message
    category_names = ", ".join([f"{index + 1} for {category['name']}" for index, category in enumerate(categories)])
    full_message = f"Choose a category by entering the number: {category_names}. Enter 0 to logout."
    speak_text(full_message)

    if request.method == 'POST':
        category_id = request.form.get('category_id')

        if category_id == '0':
            # Redirect to the welcome page on logout
            speak_text("You have been logged out. Redirecting to the welcome page.")
            return redirect(url_for('welcome'))

        # Check if the category_id exists in the dictionary
        if category_id in category_map:
            return redirect(url_for('items', category_id=category_map[category_id]))
        else:
            speak_text("Invalid category. Please select a valid category number.")
            return render_template('home.html', categories=categories)

    return render_template('home.html', categories=categories)



@app.route('/items/<int:category_id>', methods=['GET', 'POST'])
def items(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM items WHERE category_id = %s", (category_id,))
    items = cursor.fetchall()
    cursor.close()
    conn.close()

    if not items:
        speak_text("No items found in this category.")
        return redirect(url_for('home'))

    # Create the voice output for items
    item_descriptions = [
        f"Item ID {item['id']}: {item['name']} costing {item['price']} dollars." for item in items
    ]
    item_descriptions.append("Enter 3 to go back to the home page.")
    speak_text("Here are the items available: " + " ".join(item_descriptions))

    if request.method == 'POST':
        item_id = request.form.get('item_id')
        if item_id == "3":
            return redirect(url_for('home'))
        if item_id and any(int(item_id) == item['id'] for item in items):
            return redirect(url_for('item_options', item_id=item_id))
        else:
            speak_text("Invalid choice. Please select a valid item ID.")

    return render_template('items.html', items=items, category_id=category_id)


@app.route('/item_options/<int:item_id>', methods=['GET', 'POST'])
def item_options(item_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()

    if not item:
        speak_text("The selected item does not exist. Returning to home.")
        return redirect(url_for('home'))

    speak_text(
        f"You selected {item['name']}. It costs {item['price']} dollars. "
        "Enter 1 to buy, 2 to add to cart, or 3 to go back."
    )

    if request.method == 'POST':
        choice = request.form.get('choice')
        if choice == '1':
            return redirect(url_for('checkout', item_id=item_id))
        elif choice == '2':
            return redirect(url_for('add_to_cart', item_id=item_id))
        elif choice == '3':
            return redirect(url_for('home'))
        else:
            speak_text("Invalid choice. Please select 1 to buy, 2 to add to cart, or 3 to go back.")

    return render_template('item_options.html', item=item)


@app.route('/checkout/<int:item_id>', methods=['GET'])
def checkout(item_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    conn.close()

    speak_text(f"Checking out {item['name']}.")
    return render_template('checkout.html', item=item)


@app.route('/add_to_cart/<int:item_id>', methods=['GET'])
def add_to_cart(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO cart (user_id, item_id, quantity) VALUES (%s, %s, %s)",
            (1, item_id, 1)  # Example: User ID 1, Item ID, Quantity 1
        )
        conn.commit()
        speak_text("Item added to cart.")
    except pymysql.MySQLError as e:
        speak_text("Failed to add the item to the cart.")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
