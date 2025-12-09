
from flask import Flask, render_template, request, redirect, url_for, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
import sqlite3
import random
import string
from datetime import datetime, timedelta
import razorpay

app = Flask(__name__)

# Razorpay API credentials (test keys - use these only for development/testing)
RAZORPAY_KEY_ID = "rzp_test_Z4xTjUwapFvU2k"
RAZORPAY_KEY_SECRET = "bj1omL5zyDKVK51yurdMqsM6"

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Initialize SQLite database and insert initial records if empty
def init_db():
    with sqlite3.connect('parking.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS parking_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot INTEGER,
                        vehicle_number TEXT,
                        contact_number TEXT,
                        entry_time TEXT,
                        exit_time TEXT,
                        duration TEXT,
                        total_charge TEXT
                    )''')
        c.execute("SELECT COUNT(*) FROM parking_records")
        count = c.fetchone()[0]
        if count == 0:
            initial_records = [
                (1, "VP-07-NA-6003", "+910276421070", "00:00:13", "00:00:45", "27 seconds", "₹3.19"),
                (1, "CK-73-AX-3074", "+919518611573", "00:08:21", "00:08:39", "13 seconds", "₹1.53"),
                (1, "XE-77-TN-3313", "+917583594753", "00:01:04", "00:02:12", "63 seconds", "₹7.43"),
                (2, "JI-77-QW-7806", "+910907682382", "00:00:59", "00:01:18", "15 seconds", "₹1.77"),
                (2, "IS-53-CL-2100", "+914464040351", "00:07:09", "00:07:27", "14 seconds", "₹1.65"),
            ]
            c.executemany("INSERT INTO parking_records (slot, vehicle_number, contact_number, entry_time, exit_time, duration, total_charge) VALUES (?, ?, ?, ?, ?, ?, ?)", initial_records)
        conn.commit()

# Generate a random parking record
def generate_random_record():
    slot = random.randint(1, 5)
    state_code = ''.join(random.choices(string.ascii_uppercase, k=2))
    region_code = str(random.randint(10, 99))
    series = ''.join(random.choices(string.ascii_uppercase, k=2))
    number = str(random.randint(1000, 9999))
    vehicle_number = f"{state_code}-{region_code}-{series}-{number}"
    contact_number = f"+91{random.randint(6000000000, 9999999999)}"
    base_time = datetime.now()
    entry_delta = random.randint(0, 480)  # minutes ago
    entry_time = base_time - timedelta(minutes=entry_delta)
    duration_seconds = random.randint(10, 120)
    exit_time = entry_time + timedelta(seconds=duration_seconds)
    entry_time_str = entry_time.strftime("%H:%M:%S")
    exit_time_str = exit_time.strftime("%H:%M:%S")
    duration_str = f"{duration_seconds} seconds"
    total_charge = round(duration_seconds * 0.118, 2)
    total_charge_str = f"₹{total_charge}"
    return (slot, vehicle_number, contact_number, entry_time_str, exit_time_str, duration_str, total_charge_str)

@app.route('/')
def home():
    vehicle_data = {
        "parking_slot": 1,
        "vehicle_number": "AB-1234",
        "contact_number": "+91 9876543210",
        "entry_time": "12:00 PM",
        "exit_time": "01:00 PM",
        "duration": "1 hour",
        "total_charge": "₹50.00"
    }
    return render_template('home.html', vehicle=vehicle_data)

@app.route('/sign_in')
def sign_in():
    return render_template('sign_in.html')

@app.route('/sign_up')
def sign_up():
    return render_template('sign_up.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/upi_payment')
def upi_payment():
    return render_template('upi_payment.html')

@app.route('/credit_card_payment')
def credit_card_payment():
    return render_template('credit_card_payment.html')

@app.route('/debit_card_payment')
def debit_card_payment():
    return render_template('debit_card_payment.html')

@app.route('/razorpay_payment')
def razorpay_payment():
    with sqlite3.connect('parking.db') as conn:
        c = conn.cursor()
        c.execute("SELECT total_charge FROM parking_records ORDER BY id DESC LIMIT 1")
        result = c.fetchone()
        if result is None:
            return jsonify({'status': 'error', 'message': 'No parking records found'}), 404
        total_charge_str = result[0]
    total_charge = float(total_charge_str.replace('₹', ''))
    amount_in_paise = int(total_charge * 100)
    order_data = {
        'amount': amount_in_paise,
        'currency': 'INR',
        'payment_capture': '1'
    }
    try:
        order = razorpay_client.order.create(data=order_data)
    except razorpay.errors.BadRequestError as e:
        print(f"Razorpay order creation failed: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Order creation failed: {str(e)}'}), 400
    return render_template('razorpay_payment.html', 
                           order_id=order['id'], 
                           amount=amount_in_paise, 
                           key_id=RAZORPAY_KEY_ID)

@app.route('/razorpay_success', methods=['POST'])
def razorpay_success():
    payment_id = request.form.get('razorpay_payment_id')
    order_id = request.form.get('razorpay_order_id')
    signature = request.form.get('razorpay_signature')
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
        return redirect(url_for('payment_success'))
    except razorpay.errors.SignatureVerificationError as e:
        print(f"Razorpay verification failed: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Payment verification failed'}), 400

@app.route('/payment_success')
def payment_success():
    return render_template('payment_success.html')

@app.route('/process_debit_card_payment', methods=['POST'])
def process_debit_card_payment():
    card_number = request.form['card_number']
    cardholder_name = request.form['cardholder_name']
    expiry_date = request.form['expiry_date']
    cvv = request.form['cvv']
    # Note: Card details are not logged for security reasons
    # Process payment securely via a payment gateway (e.g., Razorpay) in production
    return redirect(url_for('payment_success'))

@app.route('/send-receipt-email', methods=['POST'])
def send_receipt_email():
    try:
        # Log incoming request
        data = request.json
        print(f"Received JSON: {data}")
        pdf_base64 = data.get('pdfBase64')
        if not pdf_base64:
            print("No PDF data provided")
            return jsonify({'status': 'error', 'message': 'No PDF data provided'}), 400

        # Decode Base64 PDF
        try:
            pdf_data = base64.b64decode(pdf_base64, validate=True)
        except base64.binascii.Error as e:
            print(f"Base64 decoding error: {str(e)}")
            return jsonify({'status': 'error', 'message': f'Invalid Base64 data: {str(e)}'}), 400

        # Email configuration
        sender_email = "yaseenbepari2002@gmail.com"
        sender_password = "xngucuzcxabjgiqi"  # Replace with a valid app password
        recipient_email = "abrarsudarji339@gmail.com"  # Update as needed

        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "Your Parking Receipt from Park & Power"
        body = "Thank you for your payment. Please find your receipt attached.\n\nThanks,\nPark & Power Team"
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="Parking_Receipt.pdf"')
        msg.attach(part)

        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Enable debug output
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print("Email sent successfully")
        return jsonify({'status': 'success', 'message': 'Email sent successfully'})

    except smtplib.SMTPAuthenticationError as e:
        print(f"Authentication error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Authentication failed: {str(e)}'}), 401
    except smtplib.SMTPException as e:
        print(f"SMTP error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'SMTP error: {str(e)}'}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Unexpected error: {str(e)}'}), 500

@app.route('/parking_history')
def parking_history():
    init_db()
    with sqlite3.connect('parking.db') as conn:
        c = conn.cursor()
        new_record = generate_random_record()
        c.execute("INSERT INTO parking_records (slot, vehicle_number, contact_number, entry_time, exit_time, duration, total_charge) VALUES (?, ?, ?, ?, ?, ?, ?)", new_record)
        conn.commit()
        c.execute("SELECT slot, vehicle_number, contact_number, entry_time, exit_time, duration, total_charge FROM parking_records")
        records = [{"slot": row[0], "vehicle_number": row[1], "contact_number": row[2], "entry_time": row[3], "exit_time": row[4], "duration": row[5], "total_charge": row[6]} for row in c.fetchall()]
    return render_template('parking_history.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)
