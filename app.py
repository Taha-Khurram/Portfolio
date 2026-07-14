from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mail import Mail, Message


# ------------------------------------------------
# Flask App Configuration
# ------------------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ------------------------------------------------
# Email Configuration (Mailtrap SMTP)
# ------------------------------------------------
app.config.update(
    MAIL_SERVER='sandbox.smtp.mailtrap.io',
    MAIL_PORT=2525,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='36feb2aa59b160',  # replace with your Mailtrap username
    MAIL_PASSWORD='3c62203f444240',  # replace with your Mailtrap password
    MAIL_DEFAULT_SENDER=('Portfolio Contact', 'm.tahaofficial007@gmail.com')
)

mail = Mail(app)


# ------------------------------------------------
# Frontend Routes
# ------------------------------------------------
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')


# ------------------------------------------------
# Portfolio Project Routes
# ------------------------------------------------
@app.route('/seo_helper_master')
def project1():
    return render_template('seo_helper_master.html')


@app.route('/time_center')
def project2():
    return render_template('time_center_ecommerce.html')


# ------------------------------------------------
# Contact Form Handler (POST)
# ------------------------------------------------
@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name')
    email = request.form.get('email')
    company = request.form.get('company', 'N/A')
    service = request.form.get('service')
    details = request.form.get('details')

    # Basic validation
    if not name or not email or not service or not details:
        flash("Please fill out all required fields before submitting.", "warning")
        return redirect(url_for('contact'))

    # Build email content
    msg_body = f"""
    📬 New message received from your portfolio site:

    Name: {name}
    Email: {email}
    Company: {company}
    Service: {service}

    Message:
    {details}
    """

    try:
        msg = Message(subject="New Portfolio Contact Message", recipients=['m.tahaofficial007@gmail.com'])
        msg.body = msg_body
        mail.send(msg)

        flash("Thank you for reaching out! Your message has been sent successfully.", "success")
        return redirect(url_for('contact'))

    except Exception as e:
        print("Error sending email:", e)
        flash("Something went wrong while sending your message. Please try again later.", "danger")
        return redirect(url_for('contact'))


# ------------------------------------------------
# Run Flask App
# ------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
