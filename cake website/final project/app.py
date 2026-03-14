import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import random


app = Flask(__name__)
app.secret_key = "cake_shop_secret_key_v1"
app.url_map.strict_slashes = False

# Baker credentials (simple auth)
BAKER_CREDENTIALS = {
    "baker": "baker",
    "Ghayathri.M ": "Ghayu@91423"
}



# ---------- Config ----------
DB_FOLDER = "db"
UPLOAD_FOLDER = os.path.join("static", "uploads")
ORDER_UPLOAD_FOLDER = os.path.join("static", "order_uploads")
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "gif"}

# Admin credentials
ADMIN_CREDENTIALS = {
    "demon": "demon",
    "Ghayathri.M ": "Ghayu@91423"
}
os.makedirs(DB_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ORDER_UPLOAD_FOLDER, exist_ok=True)


# ---------- JSON helpers ----------
def _path(fname): return os.path.join(DB_FOLDER, fname)


def load_json(fname):
    path = _path(fname)

    # If file does NOT exist, create an empty list file.
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump([], f)

    # Read and validate JSON
    try:
        with open(path, "r") as f:
            data = json.load(f)

        # If the file is corrupted, reset it safely.
        if not isinstance(data, list):
            raise ValueError("Invalid JSON structure")

        return data

    except Exception:
        # Auto-repair corrupted file
        with open(path, "w") as f:
            json.dump([], f)
        return []


def save_json(fname, data):
    path = _path(fname)

    # Prevent writing wrong data types
    if not isinstance(data, list):
        data = []

    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# create necessary files
for f in ("users.json", "products.json", "orders.json", "order_items.json", "reviews.json", "custom_cakes.json", "saved_designs.json"):
    if not os.path.exists(_path(f)):
        save_json(f, [])


# ---------- Helpers ----------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def next_id(list_of_dicts, key):
    """
    Returns the next safe ID by finding the highest existing ID.
    Prevents ID corruption if items are deleted or out of order.
    """
    if not list_of_dicts:
        return 1

    # Safely pick the highest ID
    try:
        highest = max(int(item.get(key, 0)) for item in list_of_dicts)
    except:
        highest = 0

    return highest + 1


def load_products(): return load_json("products.json")
def save_products(p): save_json("products.json", p)


# ---------- Cart session helpers ----------
def add_to_cart_session(pid, qty=1):
    cart = session.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + int(qty)
    session["cart"] = cart


def remove_from_cart_session(pid):
    cart = session.get("cart", {})
    cart.pop(str(pid), None)
    session["cart"] = cart


def cart_items_with_products():
    cart = session.get("cart", {}) or {}
    prods = load_products()
    # Load custom cakes for custom cake items
    custom_cakes = load_json("custom_cakes.json")
    items = []
    total = 0.0

    for pid_str, qty in cart.items():
        # Check if it's a custom cake (starts with "custom_")
        if pid_str.startswith("custom_"):
            # Find custom cake in database
            custom_cake = next((c for c in custom_cakes if c.get("custom_id") == pid_str), None)
            if custom_cake:
                items.append({
                    "product_id": pid_str,
                    "product_name": f"Custom Cake - {custom_cake.get('theme', {}).get('name', 'Custom Design')}",
                    "product_price": custom_cake.get("total_price", 0),
                    "quantity": qty,
                    "image_url": "/static/images/custom-cake-placeholder.jpg",
                    "is_custom": True,
                    "custom_id": pid_str,
                    "custom_details": custom_cake
                })
                total += custom_cake.get("total_price", 0) * qty
            continue

        # Regular product (numeric ID)
        try:
            pid = int(pid_str)
        except:
            continue

        prod = next((p for p in prods if p["product_id"] == pid), None)
        if prod:
            raw_price = str(prod.get("product_price", 0)).replace(",", "").strip()

            try:
                price = float(raw_price)
            except:
                price = 0.0

            items.append({
                "product_id": pid,
                "product_name": prod["product_name"],
                "product_price": price,
                "quantity": qty,
                "image_url": prod.get("image_url"),
                "is_custom": False
            })

            total += price * qty

    return items, total
# ========================= CUSTOM CAKE BUILDER =========================

# Customization options database
CUSTOM_OPTIONS = {
    "layers": [
        {"id": 1, "name": "Single Layer", "price": 100.00, "description": "Basic single layer cake"},
        {"id": 2, "name": "Double Layer", "price": 180.00, "description": "Two layers with filling"},
        {"id": 3, "name": "Triple Layer", "price": 250.00, "description": "Three luxurious layers"},
        {"id": 4, "name": "Multi-tier (2 tiers)", "price": 350.00, "description": "Perfect for celebrations"},
        {"id": 5, "name": "Multi-tier (3+ tiers)", "price": 500.00, "description": "Wedding-style cake"}
    ],
    "fillings": [
        {"id": 1, "name": "Vanilla Buttercream", "price": 20.00, "colorable": True},
        {"id": 2, "name": "Chocolate Ganache", "price": 25.00, "colorable": False},
        {"id": 3, "name": "Raspberry Jam", "price": 15.00, "colorable": True},
        {"id": 4, "name": "Lemon Curd", "price": 18.00, "colorable": True},
        {"id": 5, "name": "Cream Cheese", "price": 22.00, "colorable": True},
        {"id": 6, "name": "Salted Caramel", "price": 25.00, "colorable": False},
        {"id": 7, "name": "Strawberry Mousse", "price": 28.00, "colorable": True},
        {"id": 8, "name": "Coffee Cream", "price": 20.00, "colorable": False}
    ],
    "frostings": [
        {"id": 1, "name": "Buttercream", "price": 30.00, "colorable": True, "description": "Smooth and creamy"},
        {"id": 2, "name": "Fondant", "price": 50.00, "colorable": True, "description": "Professional finish"},
        {"id": 3, "name": "Cream Cheese Frosting", "price": 35.00, "colorable": True, "description": "Tangy and sweet"},
        {"id": 4, "name": "Whipped Cream", "price": 25.00, "colorable": True, "description": "Light and airy"},
        {"id": 5, "name": "Chocolate Ganache", "price": 40.00, "colorable": False, "description": "Rich and glossy"},
        {"id": 6, "name": "Mirror Glaze", "price": 45.00, "colorable": True, "description": "Shiny and modern"}
    ],
    "shapes": [
        {"id": 1, "name": "Round", "price": 0.00, "sizes": ["6\"", "8\"", "10\"", "12\""]},
        {"id": 2, "name": "Square", "price": 20.00, "sizes": ["6\"", "8\"", "10\"", "12\""]},
        {"id": 3, "name": "Heart", "price": 30.00, "sizes": ["6\"", "8\"", "10\""]},
        {"id": 4, "name": "Rectangle (Sheet)", "price": 25.00, "sizes": ["9x13\"", "11x15\""]},
        {"id": 5, "name": "Hexagon", "price": 35.00, "sizes": ["6\"", "8\"", "10\""]},
        {"id": 6, "name": "Oval", "price": 25.00, "sizes": ["6\"", "8\"", "10\""]}
    ],
    "supports": [
        {"id": 1, "name": "Basic Support", "price": 10.00, "description": "For single layer cakes"},
        {"id": 2, "name": "Dowel Rods", "price": 25.00, "description": "For multi-layer cakes"},
        {"id": 3, "name": "Cake Pillars", "price": 40.00, "description": "For tiered cakes"},
        {"id": 4, "name": "Acrylic Separators", "price": 60.00, "description": "Modern transparent supports"},
        {"id": 5, "name": "No Support Needed", "price": 0.00, "description": "For small single layers"}
    ],
    "toppers": [
        {"id": 1, "name": "Number/Letter Topper", "price": 15.00, "colorable": True},
        {"id": 2, "name": "Fresh Flowers", "price": 25.00, "colorable": False},
        {"id": 3, "name": "Sugar Flowers", "price": 35.00, "colorable": True},
        {"id": 4, "name": "Edible Image", "price": 20.00, "colorable": False},
        {"id": 5, "name": "Chocolate Sculpture", "price": 30.00, "colorable": False},
        {"id": 6, "name": "Custom Figurine", "price": 45.00, "colorable": True},
        {"id": 7, "name": "Sparkler Candles", "price": 10.00, "colorable": False},
        {"id": 8, "name": "No Topper", "price": 0.00, "colorable": False}
    ],
    "piped_designs": [
        {"id": 1, "name": "Simple Border", "price": 10.00, "colorable": True},
        {"id": 2, "name": "Rope Border", "price": 15.00, "colorable": True},
        {"id": 3, "name": "Rosette Swirls", "price": 20.00, "colorable": True},
        {"id": 4, "name": "Lace Pattern", "price": 25.00, "colorable": True},
        {"id": 5, "name": "Floral Piping", "price": 30.00, "colorable": True},
        {"id": 6, "name": "Writing/Message", "price": 15.00, "colorable": True},
        {"id": 7, "name": "No Piping", "price": 0.00, "colorable": False}
    ],
    "embellishments": [
        {"id": 1, "name": "Sprinkles", "price": 5.00, "colorable": True, "type": "edible"},
        {"id": 2, "name": "Edible Pearls", "price": 12.00, "colorable": True, "type": "edible"},
        {"id": 3, "name": "Gold Leaf", "price": 20.00, "colorable": False, "type": "edible"},
        {"id": 4, "name": "Silver Leaf", "price": 20.00, "colorable": False, "type": "edible"},
        {"id": 5, "name": "Fresh Berries", "price": 15.00, "colorable": False, "type": "fresh_fruit"},
        {"id": 6, "name": "Chocolate Shavings", "price": 10.00, "colorable": False, "type": "edible"},
        {"id": 7, "name": "Coconut Flakes", "price": 8.00, "colorable": True, "type": "edible"},
        {"id": 8, "name": "Candy Pieces", "price": 10.00, "colorable": True, "type": "edible"},
        {"id": 9, "name": "No Embellishments", "price": 0.00, "colorable": False, "type": "none"}
    ],
    "themes": [
        {"id": 1, "name": "Birthday", "price": 20.00, "colorable": True},
        {"id": 2, "name": "Wedding", "price": 40.00, "colorable": True},
        {"id": 3, "name": "Baby Shower", "price": 25.00, "colorable": True},
        {"id": 4, "name": "Graduation", "price": 20.00, "colorable": True},
        {"id": 5, "name": "Anniversary", "price": 25.00, "colorable": True},
        {"id": 6, "name": "Holiday", "price": 30.00, "colorable": True},
        {"id": 7, "name": "Sports Theme", "price": 25.00, "colorable": True},
        {"id": 8, "name": "No Specific Theme", "price": 0.00, "colorable": False}
    ],
    "packaging": [
        {"id": 1, "name": "Standard Box", "price": 5.00, "colorable": False},
        {"id": 2, "name": "Premium Gift Box", "price": 15.00, "colorable": False},
        {"id": 3, "name": "Clear Acrylic Box", "price": 25.00, "colorable": False},
        {"id": 4, "name": "Cake Carrier", "price": 35.00, "colorable": False},
        {"id": 5, "name": "Eco-friendly Box", "price": 10.00, "colorable": False}
    ]
}

# Color options
COLOR_OPTIONS = [
    {"name": "White", "hex": "#FFFFFF"},
    {"name": "Ivory", "hex": "#FFFFF0"},
    {"name": "Pink", "hex": "#FFC0CB"},
    {"name": "Red", "hex": "#FF0000"},
    {"name": "Orange", "hex": "#FFA500"},
    {"name": "Yellow", "hex": "#FFFF00"},
    {"name": "Green", "hex": "#008000"},
    {"name": "Blue", "hex": "#0000FF"},
    {"name": "Purple", "hex": "#800080"},
    {"name": "Brown", "hex": "#A52A2A"},
    {"name": "Black", "hex": "#000000"},
    {"name": "Gold", "hex": "#FFD700"},
    {"name": "Silver", "hex": "#C0C0C0"},
    {"name": "Teal", "hex": "#008080"},
    {"name": "Lavender", "hex": "#E6E6FA"},
    {"name": "Coral", "hex": "#FF7F50"},
    {"name": "Mint", "hex": "#98FF98"},
    {"name": "Custom Color", "hex": "#FF69B4"}  # Placeholder for custom
]


DECORATION_OPTIONS = [
    {"id": 1, "name": "Rainbow Sprinkles", "price": 20},
    {"id": 2, "name": "Chocolate Chips", "price": 30},
    {"id": 3, "name": "White Choco Chips", "price": 35},
    {"id": 4, "name": "Fondant Figures", "price": 80},
    {"id": 5, "name": "Sugar Pearls", "price": 25},
    {"id": 6, "name": "Gold Dust", "price": 50},
    {"id": 7, "name": "Crushed Nuts", "price": 30},
    {"id": 8, "name": "Extra Cream Piping", "price": 40},
    {"id": 9, "name": "Edible Glitter", "price": 45}
]


@app.route("/custom_cake/add_to_cart", methods=["POST"])
def add_custom_cake_to_cart():
    if "user_id" not in session:
        flash("Please login to add custom cake to cart", "warning")
        return redirect(url_for("login"))

    # ---------- Read selections ----------
    def pick(opt, key):
        return next((x for x in CUSTOM_OPTIONS[key] if x["id"] == opt), None)

    layer = pick(int(request.form.get("layer", 1)), "layers")
    filling = pick(int(request.form.get("filling", 1)), "fillings")
    frosting = pick(int(request.form.get("frosting", 1)), "frostings")
    shape = pick(int(request.form.get("shape", 1)), "shapes")
    support = pick(int(request.form.get("support", 1)), "supports")
    topper = pick(int(request.form.get("topper", 1)), "toppers")
    piping = pick(int(request.form.get("piping", 1)), "piped_designs")
    embellishment = pick(int(request.form.get("embellishment", 1)), "embellishments")
    theme = pick(int(request.form.get("theme", 1)), "themes")
    packaging = pick(int(request.form.get("packaging", 1)), "packaging")

    size = request.form.get("size", "8\"")
    message = request.form.get("message", "")

    # ---------- Price calculation ----------
    total_price = sum(
        x["price"] for x in [
            layer, filling, frosting, shape,
            support, topper, piping,
            embellishment, theme, packaging
        ] if x
    )

    custom_id = f"custom_{int(datetime.utcnow().timestamp())}"

    custom_cake = {
        "custom_id": custom_id,
        "user_id": session["user_id"],
        "layer": layer,
        "filling": filling,
        "frosting": frosting,
        "shape": shape,
        "size": size,
        "support": support,
        "topper": topper,
        "piping": piping,
        "embellishment": embellishment,
        "theme": theme,
        "packaging": packaging,
        "message": message,
        "total_price": total_price,
        "timestamp": datetime.utcnow().isoformat()
    }

    # ---------- Save custom cake ----------
    custom_cakes = load_json("custom_cakes.json")
    custom_cakes.append(custom_cake)
    save_json("custom_cakes.json", custom_cakes)

    # ---------- Add to cart ----------
    add_to_cart_session(custom_id, qty=1)

    flash("Custom cake added to cart successfully!", "success")
    return redirect(url_for("cart"))


def create_custom_cake_description(customization):
    """Generate a descriptive text for the custom cake"""
    desc = f"Custom {customization['layer']['name']} Cake\n"
    desc += f"Shape: {customization['shape']['name']} ({customization['size']})\n"
    desc += f"Filling: {customization['filling']['name']}\n"
    desc += f"Frosting: {customization['frosting']['name']}\n"
    desc += f"Theme: {customization['theme']['name']}\n"
    if customization['message']:
        desc += f"Message: {customization['message']}\n"
    desc += f"Total: ₹{customization['total_price']:.2f}"
    return desc

@app.route("/custom_cake/save_design", methods=["POST"])
def save_custom_design():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first"})

    if "custom_cake" not in session:
        return jsonify({"success": False, "message": "No design to save"})

    custom_cake = session["custom_cake"]
    design_name = request.form.get("design_name", "My Custom Design")

    # Load saved designs
    saved_designs = load_json("saved_designs.json")

    new_design = {
        "design_id": next_id(saved_designs, "design_id"),
        "user_id": session["user_id"],
        "design_name": design_name,
        "customization": custom_cake,
        "saved_date": datetime.utcnow().isoformat()
    }

    saved_designs.append(new_design)
    save_json("saved_designs.json", saved_designs)

    return jsonify({"success": True, "message": "Design saved successfully!"})

@app.route("/custom_cake/my_designs")
def my_custom_designs():
    saved_designs = load_json("saved_designs.json")

    # Get designs for logged-in user, or empty list if not logged in
    my_designs = []
    if "user_id" in session:
        my_designs = [d for d in saved_designs if d["user_id"] == session["user_id"]]

    return render_template("my_custom_designs.html", designs=my_designs)

@app.route("/custom_cake/load_design/<int:design_id>")
def load_custom_design(design_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    saved_designs = load_json("saved_designs.json")
    design = next((d for d in saved_designs if d["design_id"] == design_id and d["user_id"] == session["user_id"]), None)

    if design:
        session["custom_cake"] = design["customization"]
        flash("Design loaded successfully!", "success")
        return redirect(url_for("custom_cake_preview"))

    flash("Design not found", "warning")
    return redirect(url_for("my_custom_designs"))

# ---------- Routes ----------
from random import sample, shuffle

@app.route("/")
def index():
    products = load_products()

    # ARTISANAL: all products with category == "artisanal"
    artisanal = [p for p in products if p.get("category") == "artisanal"]

    # BEST SELLING: prefer explicit flag, else fallback to top "sales" number, else random 6
    best = [p for p in products if p.get("best_selling")]
    if not best:
        # try sort by integer 'sales' if present
        with_sales = [p for p in products if isinstance(p.get("sales"), (int, float))]
        if with_sales:
            best = sorted(with_sales, key=lambda x: x.get("sales", 0), reverse=True)[:6]
        else:
            # fallback: random sample up to 6
            if len(products) <= 6:
                best = products.copy()
            else:
                best = sample(products, 6)

    # BAKERY: category == "bakery"
    bakery = [p for p in products if p.get("category") == "bakery"]

    # Provide a logo path from your uploaded files (developer requested using uploaded path)
    # Replace this path if you prefer to use /static/logo.png
    uploaded_logo_path = "/static/logo.png"

    # Shuffle carousel artisanal items so homepage changes slightly on refresh
    shuffle(artisanal)

    return render_template(
        "index.html",
        products=products,
        artisanal=artisanal,
        best_selling=best,
        bakery_items=bakery,
        logo_url=uploaded_logo_path
    )

# ========================= USER AUTH =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        users = load_json("users.json")
        username = request.form.get("username").strip()
        password = request.form.get("password")
        email = request.form.get("email")
        address = request.form.get("address", "")
        phone = request.form.get("phone", "")

        # Validate phone number (only 10 digits)
        if phone and (len(phone) != 10 or not phone.isdigit()):
            flash("Phone number must be exactly 10 digits", "warning")
            return redirect(url_for("register"))

        if any(u["username"] == username for u in users):
            flash("Username already exists", "warning")
            return redirect(url_for("register"))

        new_user = {
            "user_id": next_id(users, "user_id"),
            "username": username,
            "password": password,
            "email": email,
            "address": address,
            "phone": phone
        }
        users.append(new_user)
        save_json("users.json", users)
        flash("Registered successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        users = load_json("users.json")
        username = request.form.get("username")
        password = request.form.get("password")

        user = next((u for u in users if u["username"] ==
                    username and u["password"] == password), None)

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            flash("Logged in successfully!", "success")
            return redirect(url_for("shop"))

        flash("Invalid username or password", "warning")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("shop"))


# ========================= SHOP =========================
@app.route("/shop")
def shop():
    query = request.args.get("q", "").strip().lower()
    products = load_products()

    if query:
        products = [
            p for p in products
            if query in p["product_name"].lower()
            or query in p.get("description", "").lower()
        ]

    return render_template("shop.html", products=products, query=query)


@app.route("/product/<int:product_id>")
def product_details(product_id):
    products = load_products()
    p = next((x for x in products if x["product_id"] == product_id), None)
    if not p:
        flash("Product not found", "warning")
        return redirect(url_for("shop"))

    # Load reviews and filter for this product
    all_reviews = load_json("reviews.json")
    reviews_for = [r for r in all_reviews if r.get("product_id") == product_id]
    # show newest first
    reviews_for = sorted(reviews_for, key=lambda x: x.get("timestamp", ""), reverse=True)

    # Similar cakes (random selection excluding current)
    other_products = [prod for prod in products if prod["product_id"] != product_id]
    similar = random.sample(other_products, min(len(other_products), 6)) if other_products else []

    return render_template("product_details.html",
                           product=p,
                           reviews=reviews_for,
                           similar=similar)



# ========================= ADMIN AUTH =========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if ADMIN_CREDENTIALS.get(u) == p:
            session["admin"] = u
            session["admin_logged"] = True
            flash("Admin logged in", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid credentials", "warning")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged", None)
    flash("Admin logged out", "success")
    return redirect(url_for("shop"))


# ========================= ADMIN DASHBOARD =========================
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    # Load all DB JSON files
    orders = load_json("orders.json")
    order_items = load_json("order_items.json")
    users = load_json("users.json")

    detailed_orders = []

    for o in orders:

        # get all items inside this order
        items = [item for item in order_items if item["order_id"] == o["order_id"]]

        # find the user
        user = next((u for u in users if u["user_id"] == o["user_id"]), None)

        detailed_orders.append({
            "order_id": o["order_id"],
            "user_id": o["user_id"],
            "username": user["username"] if user else "Unknown",
            "email": user["email"] if user else "",
            "phone": user["phone"] if user else "",
            "address": user["address"] if user else "",
            "order_status": o.get("order_status", "Pending"),
            "payment_mode": o.get("payment_mode", "Not Selected"),
            "delivery_date": o.get("delivery_date", "Not Set"),
            "delivery_slot": o.get("delivery_slot", "Not Set"),
            "notes": o.get("notes", ""),
            "photo": o.get("photo", None),
            "items": items
        })

    # Calculate admin stats
    stats = {
        "pending": sum(1 for o in detailed_orders if o["order_status"] == "Pending"),
        "baking": sum(1 for o in detailed_orders if o["order_status"] == "Baking"),
        "out": sum(1 for o in detailed_orders if o["order_status"] == "Out for Delivery"),
        "delivered": sum(1 for o in detailed_orders if o["order_status"] == "Delivered"),
        "total": len(detailed_orders)
    }

    return render_template(
        "admin_dashboard.html",
        orders=detailed_orders,
        stats=stats
    )


# ========================= ADMIN PRODUCT MANAGEMENT =========================

# List all products
@app.route("/admin/products")
def admin_products():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    products = load_products()

    # Sort so newest product appears first
    products = sorted(products, key=lambda x: x.get("product_id", 0), reverse=True)

    return render_template("admin_products.html", products=products)


# Delete product
@app.route("/admin/product/delete/<int:pid>", methods=["POST"])
def admin_delete_product(pid):
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    products = load_products()
    updated = [p for p in products if p["product_id"] != pid]
    save_products(updated)

    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin_products"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login to view your profile", "error")
        return redirect(url_for("login"))

    users = load_json("users.json")
    user = None

    for u in users:
        try:
            if int(u.get("user_id")) == int(user_id):
                user = u
                break
        except Exception:
            if u.get("user_id") == user_id:
                user = u
                break

    if not user:
        flash("User not found — please login again", "error")
        session.clear()
        return redirect(url_for("login"))

    # Render standalone profile template (not extending base.html)
    return render_template("profile.html", user=user)


# Add edit_profile route to fix the error
@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login to edit your profile", "error")
        return redirect(url_for("login"))

    users = load_json("users.json")
    user = None

    for u in users:
        try:
            if int(u.get("user_id")) == int(user_id):
                user = u
                break
        except Exception:
            if u.get("user_id") == user_id:
                user = u
                break

    if not user:
        flash("User not found", "error")
        return redirect(url_for("profile"))

    if request.method == "POST":
        # Get form data
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()

        # Validate phone number
        if phone and (len(phone) != 10 or not phone.isdigit()):
            flash("Phone number must be exactly 10 digits", "warning")
            return redirect(url_for("edit_profile"))

        # Update user data
        for u in users:
            if u.get("user_id") == user.get("user_id"):
                u["email"] = email
                u["address"] = address
                u["phone"] = phone
                break

        save_json("users.json", users)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=user)


# Edit product
@app.route("/admin/product/edit/<int:pid>", methods=["GET", "POST"])
def admin_edit_product(pid):
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    products = load_products()
    product = next((p for p in products if p["product_id"] == pid), None)

    if not product:
        flash("Product not found", "warning")
        return redirect(url_for("admin_products"))

    if request.method == "POST":
        product["product_name"] = request.form.get("product_name")
        product["product_price"] = request.form.get("product_price")
        product["description"] = request.form.get("description")

        file = request.files.get("file")
        if file and file.filename and allowed_file(file.filename):
            fn = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, fn))
            product["image_url"] = f"/static/uploads/{fn}"

        save_products(products)
        flash("Product updated successfully!", "success")
        return redirect(url_for("admin_products"))

    return render_template("edit_product.html", product=product)


# Preview product
@app.route("/admin/product/<int:pid>")
def admin_product_preview(pid):
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    products = load_products()
    p = next((x for x in products if x["product_id"] == pid), None)

    if not p:
        flash("Product not found", "warning")
        return redirect(url_for("admin_products"))

    return render_template("admin_product_preview.html", product=p)


# ========================= ADMIN ADD PRODUCT =========================
@app.route("/admin/add_product", methods=["GET", "POST"])
def admin_add_product():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        products = load_products()

        name = request.form.get("product_name")
        price = request.form.get("product_price")
        desc = request.form.get("description")

        # ===================== MAIN IMAGE =====================
        main_file = request.files.get("file")
        if not main_file or main_file.filename == "":
            flash("Please upload a main product image", "warning")
            return redirect(request.url)

        if not allowed_file(main_file.filename):
            flash("Invalid image type for main image", "warning")
            return redirect(request.url)

        main_fn = secure_filename(main_file.filename)
        main_path = os.path.join(UPLOAD_FOLDER, main_fn)
        main_file.save(main_path)
        main_url = f"/static/uploads/{main_fn}"

        # ===================== EXTRA IMAGES =====================
        extra_images = request.files.getlist("extra_images")
        extra_image_urls = []

        for img in extra_images:
            if img and img.filename != "" and allowed_file(img.filename):
                fn = secure_filename(img.filename)
                img.save(os.path.join(UPLOAD_FOLDER, fn))
                extra_image_urls.append(f"/static/uploads/{fn}")

        # ===================== SAVE PRODUCT =====================
        new_id = next_id(products, "product_id")

        product = {
            "product_id": new_id,
            "product_name": name,
            "product_price": price,
            "description": desc,
            "image_url": main_url,
            "extra_images": extra_image_urls,
            "category": "artisanal"  # Default category for shop cakes
        }

        # ⭐ Put new product at the TOP
        products.insert(0, product)

        save_products(products)

        flash("Product added successfully!", "success")
        return redirect(url_for("admin_products"))

    return render_template("add_product.html")


# ========================= CART =========================
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    add_to_cart_session(product_id, qty=1)
    flash("Added to cart", "success")
    return redirect(request.referrer or url_for("shop"))


@app.route("/cart")
def cart():
    items, total = cart_items_with_products()
    return render_template("cart.html", items=items, total=total)


@app.route("/remove_from_cart/<product_id>", methods=["POST"])
def remove_from_cart(product_id):
    remove_from_cart_session(product_id)
    flash("Removed from cart", "success")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        flash("Please login to checkout", "warning")
        return redirect(url_for("login"))

    # Load cart items
    items, cart_total = cart_items_with_products()

    if not items:
        flash("Your cart is empty", "warning")
        return redirect(url_for("shop"))

    # Decorations from session
    decorations = session.get("decorations", {"items": [], "total_price": 0})
    decoration_items = decorations.get("items", [])
    decoration_total = decorations.get("total_price", 0)

    # ✅ FINAL TOTAL
    total = cart_total + decoration_total

    if request.method == "POST":
        orders = load_json("orders.json")
        order_items_db = load_json("order_items.json")
        users = load_json("users.json")

        user = next(
            (u for u in users if u["user_id"] == session["user_id"]),
            None
        )

        address = request.form.get("address", "")
        phone = request.form.get("phone", "")
        delivery_date = request.form.get("delivery_date")
        delivery_time = request.form.get("delivery_time")
        payment_mode = request.form.get("payment_mode")
        customer_message = request.form.get("customer_message", "")

        # Phone validation
        if phone and (len(phone) != 10 or not phone.isdigit()):
            flash("Phone number must be exactly 10 digits", "warning")
            return redirect(url_for("checkout"))

        # Optional reference photo
        photo_file = request.files.get("order_photo")
        photo_url = ""
        if photo_file and photo_file.filename and allowed_file(photo_file.filename):
            fn = secure_filename(photo_file.filename)
            path = os.path.join(ORDER_UPLOAD_FOLDER, fn)
            photo_file.save(path)
            photo_url = f"/static/order_uploads/{fn}"

        new_order_id = next_id(orders, "order_id")

        order = {
            "order_id": new_order_id,
            "user_id": session["user_id"],
            "items": items,
            "decorations": decoration_items,
            "cart_total": cart_total,
            "decoration_price": decoration_total,
            "total_amount": total,   # ✅ MATCHES TEMPLATE
            "customer_message": customer_message,
            "delivery_date": delivery_date,
            "delivery_time": delivery_time,
            "payment_mode": payment_mode,
            "address": address,
            "phone": phone,
            "photo_url": photo_url,
            "timestamp": datetime.utcnow().isoformat(),
            "order_status": "Pending"
        }

        orders.append(order)
        save_json("orders.json", orders)

        # Save flat order items
        for it in items:
            order_items_db.append({
                "order_id": new_order_id,
                "product_id": it["product_id"],
                "product_name": it["product_name"],
                "quantity": it["quantity"],
                "price": it["product_price"]
            })

        save_json("order_items.json", order_items_db)

        # Clear cart
        session["cart"] = {}
        session.pop("decorations", None)

        flash("Order placed successfully!", "success")
        return redirect(url_for("orders"))

    # GET request
    users = load_json("users.json")
    user = next(
        (u for u in users if u["user_id"] == session["user_id"]),
        None
    )

    return render_template(
        "checkout.html",
        items=items,
        decorations=decoration_items,
        total=total,   # ✅ REQUIRED BY TEMPLATE
        user=user
    )


# ========================= USER ORDERS =========================
@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    all_orders = load_json("orders.json")
    my_orders = [o for o in all_orders if o["user_id"]
                 == session["user_id"]]

    return render_template("orders.html", orders=my_orders)


@app.route("/order/<int:order_id>")
def order_detail(order_id):

    orders = load_json("orders.json")
    order_items_db = load_json("order_items.json")
    products = load_products()
    users = load_json("users.json")

    # Find the order
    order = next((o for o in orders if o["order_id"] == order_id), None)
    if not order:
        flash("Order not found", "warning")
        return redirect(url_for("orders"))

    # Check permissions
    if session.get("user_id") != order.get("user_id") and not session.get("admin_logged"):
        flash("Not authorized", "danger")
        return redirect(url_for("shop"))

    # Get user
    user = next((u for u in users if u["user_id"] == order["user_id"]), None)

    # Build AMAZON-STYLE order items list
    order_items = []
    for it in order_items_db:
        if it["order_id"] == order_id:

            product = next(
                (p for p in products if p["product_id"] == it["product_id"]),
                None
            )

            if not product:
                continue

            order_items.append({
                "product_name": it["product_name"],
                "quantity": it["quantity"],
                "price": product["product_price"],
                "image": product["image_url"]   # 🔥 product image
            })

    return render_template(
        "order_detail.html",
        order=order,
        items=order_items,
        user=user
    )

@app.route("/admin/order/<int:order_id>")
def admin_view_order(order_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    orders = load_json("orders.json")

    order = next((o for o in orders if o["order_id"] == order_id), None)

    if not order:
        flash("Order not found", "warning")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_order_view.html", order=order)

@app.route("/baker/login", methods=["GET", "POST"])
def baker_login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if BAKER_CREDENTIALS.get(u) == p:
            session["baker"] = u
            session["baker_logged"] = True
            flash("Baker logged in", "success")
            return redirect(url_for("baker_dashboard"))

        flash("Invalid credentials", "warning")

    return render_template("baker_login.html")

@app.route("/baker/logout")
def baker_logout():
    session.pop("baker_logged", None)
    flash("Baker logged out", "success")
    return redirect(url_for("baker_login"))


@app.route("/baker")
def baker_dashboard():
    if not session.get("baker_logged"):
        return redirect(url_for("baker_login"))

    orders = load_json("orders.json")

    baking_orders = [o for o in orders if o.get("order_status") in ["Pending", "Baking"]]

    return render_template("baker_dashboard.html", orders=baking_orders)

@app.route("/baker/order/<int:order_id>")
def baker_view_order(order_id):
    if not session.get("baker_logged"):
        return redirect(url_for("baker_login"))

    orders = load_json("orders.json")
    order = next((o for o in orders if o["order_id"] == order_id), None)

    if not order:
        flash("Order not found", "warning")
        return redirect(url_for("baker_dashboard"))

    return render_template("baker_order_view.html", order=order)

@app.route("/baker/order/update/<int:order_id>", methods=["POST"])
def baker_update_status(order_id):
    if not session.get("baker_logged"):
        return redirect(url_for("baker_login"))

    new_status = request.form.get("status")
    note = request.form.get("baker_note", "")

    orders = load_json("orders.json")
    updated = False

    for o in orders:
        if o["order_id"] == order_id:
            o["order_status"] = new_status

            if note:
                o["baker_note"] = note

            if "status_history" not in o:
                o["status_history"] = []

            o["status_history"].append({
                "status": new_status,
                "timestamp": datetime.utcnow().isoformat()
            })

            updated = True
            break

    if updated:
        save_json("orders.json", orders)
        flash("Order status updated!", "success")
    else:
        flash("Order not found!", "warning")

    return redirect(url_for("baker_view_order", order_id=order_id))

@app.route("/product/<int:product_id>/review", methods=["POST"])
def submit_review(product_id):
    # Basic validation
    name = request.form.get("name", "Anonymous").strip()
    try:
        rating = int(request.form.get("rating", 5))
        rating = max(1, min(5, rating))
    except:
        rating = 5
    comment = request.form.get("comment", "").strip()

    reviews = load_json("reviews.json")

    new_review = {
        "review_id": next_id(reviews, "review_id"),
        "product_id": product_id,
        "name": name,
        "rating": rating,
        "comment": comment,
        "timestamp": datetime.utcnow().isoformat()
    }

    reviews.append(new_review)
    save_json("reviews.json", reviews)

    flash("Thank you — your review was saved!", "success")
    return redirect(url_for("product_details", product_id=product_id))

@app.route("/admin/add_item", methods=["GET", "POST"])
def admin_add_item():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    # Redirect to the appropriate add page or show an error
    flash("Please use specific add pages: Add Product, Add Themed Cake, or Add Bakery Item", "info")
    return redirect(url_for("admin_products"))

@app.route("/admin/add_themed_product", methods=["GET", "POST"])
def admin_add_themed_product():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        products = load_products()

        name = request.form.get("product_name")
        price = request.form.get("product_price")
        desc = request.form.get("description")

        # ===================== MAIN IMAGE =====================
        main_file = request.files.get("file")
        if not main_file or main_file.filename == "":
            flash("Please upload a main image", "warning")
            return redirect(request.url)

        main_fn = secure_filename(main_file.filename)
        main_file.save(os.path.join(UPLOAD_FOLDER, main_fn))
        main_url = f"/static/uploads/{main_fn}"

        # ===================== EXTRA IMAGES =====================
        extra_images = request.files.getlist("extra_images")
        extra_urls = []

        for img in extra_images:
            if img and img.filename:
                fn = secure_filename(img.filename)
                img.save(os.path.join(UPLOAD_FOLDER, fn))
                extra_urls.append(f"/static/uploads/{fn}")

        # ===================== SAVE PRODUCT =====================
        new_id = next_id(products, "product_id")

        product = {
            "product_id": new_id,
            "product_name": name,
            "product_price": price,
            "description": desc,
            "image_url": main_url,
            "extra_images": extra_urls,
            "category": "themed"
        }

        products.insert(0, product)
        save_products(products)

        flash("Themed cake added successfully!", "success")
        return redirect(url_for("admin_products"))

    return render_template("add_themed_product.html")


@app.route("/themed")
def themed_cakes():
    query = request.args.get("q", "").strip().lower()
    products = load_products()
    themed = [p for p in products if p.get("category") == "themed"]

    if query:
        themed = [
            p for p in themed
            if query in p["product_name"].lower()
            or query in p.get("description", "").lower()
        ]

    return render_template("themed.html", products=themed, query=query)

@app.route("/admin/add_bakery", methods=["GET", "POST"])
def admin_add_bakery():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        products = load_products()

        name = request.form.get("product_name")
        price = request.form.get("product_price")
        desc = request.form.get("description")

        # ============= MAIN IMAGE =============
        main_file = request.files.get("file")
        if not main_file:
            flash("Please upload a main image!", "warning")
            return redirect(request.url)

        main_fn = secure_filename(main_file.filename)
        main_file.save(os.path.join(UPLOAD_FOLDER, main_fn))
        main_url = f"/static/uploads/{main_fn}"

        # ============= EXTRA IMAGES ============
        extra_files = request.files.getlist("extra_images")
        extra_urls = []
        for f in extra_files:
            if f and f.filename:
                fn = secure_filename(f.filename)
                f.save(os.path.join(UPLOAD_FOLDER, fn))
                extra_urls.append(f"/static/uploads/{fn}")

        # ============= SAVE PRODUCT ============
        new_id = next_id(products, "product_id")

        product = {
            "product_id": new_id,
            "product_name": name,
            "product_price": price,
            "description": desc,
            "image_url": main_url,
            "extra_images": extra_urls,
            "category": "bakery"
        }

        products.insert(0, product)
        save_products(products)

        flash("Bakery item added successfully!", "success")
        return redirect(url_for("admin_products"))

    return render_template("add_bakery.html")


@app.route("/bakery")
def bakery_items():
    products = load_products()
    bakery = [p for p in products if p.get("category") == "bakery"]
    return render_template("bakery.html", products=bakery)

@app.route("/about")
def about():
    return render_template("about.html")
@app.route("/custom_cake/continue/<string:custom_id>")
def continue_custom_cake(custom_id):
    if "user_id" not in session:
        flash("Please login to continue your custom cake", "warning")
        return redirect(url_for("login"))

    custom_cakes = load_json("custom_cakes.json")

    cake = next(
        (c for c in custom_cakes
         if c.get("custom_id") == custom_id
         and c.get("user_id") == session["user_id"]),
        None
    )

    if not cake:
        flash("Custom cake not found", "warning")
        return redirect(url_for("custom_cake_builder"))

    session["custom_cake"] = cake
    flash("Custom cake loaded successfully", "success")
    return redirect(url_for("custom_cake_preview"))


def get_session_decorations():
    return session.get("decorations", {"items": [], "total_price": 0})


@app.route("/cake_decorations", methods=["GET", "POST"])
def cake_decorations():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        selected_ids = request.form.getlist("decorations")
        decorations = []
        total = 0

        for did in selected_ids:
            deco = next((d for d in DECORATION_OPTIONS if str(d["id"]) == did), None)
            if deco:
                decorations.append(deco)
                total += deco["price"]

        session["decorations"] = {
            "items": decorations,
            "total_price": total
        }

        return redirect(url_for("checkout"))

    return render_template(
        "cake_decorations.html",
        decorations=DECORATION_OPTIONS
    )

@app.route("/custom_cake")
def custom_cake_builder():
    if "user_id" not in session:
        flash("Please login to build a custom cake", "warning")
        return redirect(url_for("login"))

    return render_template(
        "custom_cake_builder.html",
        options=CUSTOM_OPTIONS,
        layers=CUSTOM_OPTIONS["layers"],   # ✅ ADD THIS
        colors=COLOR_OPTIONS
    )

@app.route("/custom_cake/preview")
def custom_cake_preview():
    if "user_id" not in session:
        flash("Please login to continue", "warning")
        return redirect(url_for("login"))

    # MUST be named 'customization' because template expects it
    customization = session.get("custom_cake")

    if not customization:
        flash("No custom cake to preview", "warning")
        return redirect(url_for("custom_cake_builder"))

    return render_template(
        "custom_cake_preview.html",
        customization=customization,
        description=create_custom_cake_description(customization)
    )


# ========================= RUN APP =========================
if __name__ == "__main__":
    app.run(port=5500)
