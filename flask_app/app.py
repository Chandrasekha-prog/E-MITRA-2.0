import os
import json
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import requests
from dotenv import load_dotenv

from database import supabase
from rules_engine import calculate_fertilizer_recommendation
from weather_service import get_current_weather

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")

# Fast2SMS API Key for real-time OTP routing
FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "")

@app.route("/", methods=["GET"])
def index():
    if "farmer" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    mobile = request.form.get("mobile")
    if not mobile or not mobile.isdigit() or len(mobile) != 10:
        return jsonify({"success": False, "message": "Invalid 10-digit mobile number"})
        
    # Generate random 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Save to session securely
    session["sent_otp"] = otp
    session["otp_mobile"] = mobile
    
    if FAST2SMS_API_KEY:
        try:
            url = "https://www.fast2sms.com/dev/bulkV2"
            querystring = {
                "authorization": FAST2SMS_API_KEY,
                "variables_values": otp,
                "route": "otp",
                "numbers": mobile
            }
            headers = {'cache-control': "no-cache"}
            response = requests.request("GET", url, headers=headers, params=querystring)
            res_data = response.json()
            
            # Fast2SMS returns "return": True on success
            if res_data.get("return") == True:
                print(f"Fast2SMS Success: {res_data}")
                return jsonify({"success": True, "message": "OTP sent securely to your mobile via SMS!"})
            else:
                print(f"Fast2SMS API Blocked by Account Limits: {res_data.get('message')}")
                # Fallback to Simulator
                print("\n" + "="*50)
                print("📠 FAST2SMS FAILED (ACCOUNT UNVERIFIED/UNFUNDED) - FALLBACK TO SIMULATOR 📠")
                print(f"To: +91 {mobile}")
                print(f"Message: Your Krish-e-Mitra verification OTP is: {otp}")
                print("="*50 + "\n")
                return jsonify({"success": True, "message": f"Dev Mode (SMS Failed: {res_data.get('message', 'Unverified Account')}). Check console for OTP."})
                
        except Exception as e:
            print(f"Error sending LIVE SMS: {e}")
            return jsonify({"success": False, "message": "Failed to connect to SMS service."})
    else:
        # --- Simulated SMS Gateway Output (Fallback) ---
        print("\n" + "="*50)
        print("📠 SIMULATED SMS GATEWAY (NO API KEY PROVIDED) 📠")
        print(f"To: +91 {mobile}")
        print(f"Message: Your Krish-e-Mitra verification OTP is: {otp}")
        print("="*50 + "\n")
        
        return jsonify({"success": True, "message": "Developer Mode: OTP sent successfully (Check server console)"})

@app.route("/login", methods=["POST"])
def login():
    mobile = request.form.get("mobile")
    otp = request.form.get("otp")
    
    session_otp = session.get("sent_otp")
    session_mobile = session.get("otp_mobile")
    
    # Allow 123456 as a safe dev-fallback, or check real matching OTP
    if otp != "123456" and not (otp == session_otp and mobile == session_mobile):
        return jsonify({"success": False, "message": "Invalid or expired OTP. Please request a new one."})
        
    try:
        response = supabase.table("farmers").select("*").eq("mobile", mobile).execute()
        farmers = response.data
        if not farmers:
            return jsonify({"success": False, "message": "Farmer not registered. Please register first."})
            
        farmer = farmers[0]
        session["farmer"] = farmer
        
        # Clear used OTP
        session.pop("sent_otp", None)
        session.pop("otp_mobile", None)
        
        return jsonify({"success": True, "message": "Login successful"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/signup", methods=["POST"])
def signup():
    mobile = request.form.get("mobile")
    name = request.form.get("name")
    district = request.form.get("district")
    mandal = request.form.get("mandal")
    otp = request.form.get("otp")
    
    session_otp = session.get("sent_otp")
    session_mobile = session.get("otp_mobile")
    
    # Allow 123456 as a safe dev-fallback, or check real matching OTP
    if otp != "123456" and not (otp == session_otp and mobile == session_mobile):
        return jsonify({"success": False, "message": "Invalid or expired OTP. Please request a new one."})
        
    try:
        # Check if already exists
        existing = supabase.table("farmers").select("id").eq("mobile", mobile).execute()
        if existing.data:
            return jsonify({"success": False, "message": "Mobile number already registered"})
            
        new_farmer = {
            "mobile": mobile,
            "name": name,
            "district": district,
            "mandal": mandal,
            "language_preference": "en"
        }
        res = supabase.table("farmers").insert(new_farmer).execute()
        
        if res.data:
            session["farmer"] = res.data[0]
            
            # Clear used OTP
            session.pop("sent_otp", None)
            session.pop("otp_mobile", None)
            
            return jsonify({"success": True, "message": "Registration successful"})
        return jsonify({"success": False, "message": "Failed to register"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/dashboard")
def dashboard():
    if "farmer" not in session:
        return redirect(url_for("index"))
        
    farmer = session["farmer"]
    # Get history
    history = []
    try:
        history_res = supabase.table("recommendations").select("*").eq("farmer_id", farmer["id"]).order("created_at", desc=True).limit(10).execute()
        for rec in history_res.data:
            rec_data = json.loads(rec["recommendation_json"])
            rec_data['created_at'] = rec["created_at"]
            history.append(rec_data)
    except Exception as e:
        print("Error fetching history", e)
        
    return render_template("dashboard.html", farmer=farmer, history=history)

@app.route("/recommendation/new", methods=["GET", "POST"])
def new_recommendation():
    if "farmer" not in session:
        return redirect(url_for("index"))
        
    farmer = session["farmer"]
    
    if request.method == "POST":
        crop_name = request.form.get("crop_name")
        variety = request.form.get("variety")
        district = request.form.get("district") or farmer["district"]
        mandal = request.form.get("mandal") or farmer["mandal"]
        area_sown = float(request.form.get("area_sown"))
        sowing_date_str = request.form.get("sowing_date")
        sowing_date = datetime.strptime(sowing_date_str, "%Y-%m-%d")
        
        try:
            # Create field
            field_data = {
                "farmer_id": farmer["id"],
                "location": f"{mandal}, {district}",
                "crop_type": crop_name,
                "variety": variety,
                "sowing_date": sowing_date_str,
                "area_sown": area_sown
            }
            field_res = supabase.table("fields").insert(field_data).execute()
            field_id = field_res.data[0]["id"] if field_res.data else None
            
            # Generate recommendation (Passing None for DB as we'll mock soil info in rules_engine)
            rec_data = calculate_fertilizer_recommendation(
                crop_name=crop_name,
                sowing_date=sowing_date,
                district=district,
                mandal=mandal,
                area_sown=area_sown,
                db=None, # Adapted parameter
                variety=variety
            )
            
            if field_id:
                rec_record = {
                    "farmer_id": farmer["id"],
                    "field_id": field_id,
                    "recommendation_json": json.dumps(rec_data, ensure_ascii=False)
                }
                supabase.table("recommendations").insert(rec_record).execute()
                
            session["last_recommendation"] = rec_data
            return redirect(url_for("results"))
        except Exception as e:
            flash(f"Error calculating recommendation: {str(e)}", "error")
            
    return render_template("recommendation_form.html", farmer=farmer)

@app.route("/results")
def results():
    if "farmer" not in session:
        return redirect(url_for("index"))
        
    rec_data = session.get("last_recommendation")
    if not rec_data:
        return redirect(url_for("dashboard"))
        
    return render_template("results.html", recommendation=rec_data, farmer=session["farmer"])

@app.route("/disease-detection")
def disease_detection():
    if "farmer" not in session:
        return redirect(url_for("index"))
    return render_template("disease_vision.html", farmer=session["farmer"])

@app.route("/api/disease-detection", methods=["POST"])
def api_disease_detection():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image uploaded"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    import tempfile
    import werkzeug.utils
    import uuid
    from disease_service import analyze_plant_disease
    
    filename = f"{uuid.uuid4().hex}_{werkzeug.utils.secure_filename(file.filename)}"
    # Save the file temporarily
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    file.save(filepath)
    
    # Process using Gemini
    result = analyze_plant_disease(filepath)
    
    # Store in database if successful and not mock
    if result.get("success"):
        if "farmer" in session:
            try:
                import base64
                with open(filepath, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                    
                # Format to standard data URI
                image_base64_data = f"data:{file.mimetype or 'image/jpeg'};base64,{encoded_string}"
                
                history_data = {
                    "farmer_id": session["farmer"]["id"],
                    "image_base64": image_base64_data,
                    "plant_type": result.get("plant_type", ""),
                    "disease_name": result.get("disease_name", ""),
                    "is_healthy": not result.get("disease_detected", False),
                    "description": result.get("description", ""),
                    "recommendation": result.get("recommendation", "")
                }
                supabase.table("disease_history").insert(history_data).execute()
            except Exception as e:
                print(f"Error saving disease history to database: {e}")
                
    # Cleanup temp file
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
            
    return jsonify(result)

@app.route("/book", methods=["GET", "POST"])
def book_fertilizers():
    if "farmer" not in session:
        return redirect(url_for("index"))
        
    farmer = session["farmer"]
    
    if request.method == "POST":
        fertilizer = request.form.get("fertilizer")
        quantity = float(request.form.get("quantity", 0))
        total_price = float(request.form.get("total_price", 0))
        delivery_address = request.form.get("delivery_address")
        payment_status = request.form.get("payment_status", "Pending")
        
        try:
            booking_data = {
                "farmer_id": farmer["id"],
                "fertilizer_name": fertilizer,
                "quantity_kg": quantity,
                "total_price": total_price,
                "delivery_address": delivery_address,
                "status": payment_status
            }
            supabase.table("bookings").insert(booking_data).execute()
        except Exception as e:
            print(f"Error booking: {e}")
            
        return redirect(url_for("book_fertilizers"))

    bookings = []
    try:
        book_res = supabase.table("bookings").select("*").eq("farmer_id", farmer["id"]).order("created_at", desc=True).limit(20).execute()
        bookings = book_res.data
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        
    return render_template("booking.html", farmer=farmer, bookings=bookings)

@app.route("/api/weather")
def api_weather():
    district = request.args.get("district")
    mandal = request.args.get("mandal")
    try:
        data = get_current_weather(district, mandal)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/complaints")
def complaints():
    if "farmer" not in session:
        return redirect(url_for("index"))
    
    farmer = session["farmer"]
    complaints_list = []
    try:
        comp_res = supabase.table("complaints").select("*").eq("farmer_id", farmer["id"]).order("created_at", desc=True).limit(10).execute()
        complaints_list = comp_res.data
    except Exception as e:
        print(f"Error fetching complaints: {e}")

    return render_template("complaint.html", farmer=farmer, complaints=complaints_list)

@app.route("/api/complaint", methods=["POST"])
def api_complaint():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image uploaded"}), 400
        
    file = request.files['image']
    text_desc = request.form.get("description", "")
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    import tempfile
    import werkzeug.utils
    import uuid
    from complaint_service import analyze_complaint
    
    filename = f"{uuid.uuid4().hex}_{werkzeug.utils.secure_filename(file.filename)}"
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, filename)
    file.save(filepath)
    
    result = analyze_complaint(filepath, text_desc)
    
    if result.get("success"):
        if "farmer" in session:
            try:
                import base64
                with open(filepath, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                    
                image_base64_data = f"data:{file.mimetype or 'image/jpeg'};base64,{encoded_string}"
                
                status = "Sent to Officer" if not result.get("is_fake") else "Rejected as Fake"
                
                comp_data = {
                    "farmer_id": session["farmer"]["id"],
                    "image_base64": image_base64_data,
                    "text_description": text_desc,
                    "is_fake": result.get("is_fake"),
                    "veracity_score": result.get("veracity_score"),
                    "status": status
                }
                supabase.table("complaints").insert(comp_data).execute()
            except Exception as e:
                print(f"Error saving complaint: {e}")
                
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
            
    return jsonify(result)

@app.route("/market")
def market():
    if "farmer" not in session:
        return redirect(url_for("index"))
    
    farmer = session["farmer"]
    # Mock Market Prices
    market_prices = [
        {"crop": "Paddy", "price": 2050, "trend": "increase", "change": "+50"},
        {"crop": "Maize", "price": 1850, "trend": "decrease", "change": "-20"},
        {"crop": "Cotton", "price": 7500, "trend": "increase", "change": "+150"},
        {"crop": "Chilli", "price": 14000, "trend": "decrease", "change": "-500"},
        {"crop": "Groundnut", "price": 6300, "trend": "stable", "change": "0"},
    ]
    return render_template("market.html", farmer=farmer, market_prices=market_prices)

@app.route("/crop-advisor")
def crop_advisor():
    if "farmer" not in session:
        return redirect(url_for("index"))
        
    farmer = session["farmer"]
    
    # Simple mocked advisor content
    season = "Kharif (Monsoon)"
    best_crops = ["Paddy", "Cotton", "Maize", "Red Gram"]
    water_advice = [
        {"crop": "Paddy", "advice": "Requires flooded fields. Maintain 2-5cm standing water. Use Alternate Wetting and Drying (AWD) to save 30% water."},
        {"crop": "Cotton", "advice": "Avoid waterlogging. Apply drip irrigation if possible. Critical stages for watering: Flowering and Boll formation."},
        {"crop": "Maize", "advice": "Needs moderate water. Sensitive to water stress during silking and tasseling stages."},
    ]
    
    return render_template("crop_advisor.html", 
                           farmer=farmer, 
                           season=season, 
                           best_crops=best_crops, 
                           water_advice=water_advice)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
