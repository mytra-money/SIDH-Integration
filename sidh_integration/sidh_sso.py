import frappe
import base64
import json
import time
from Crypto.Cipher import AES

def unpad(byte_array):
    last_byte = byte_array[-1]
    return byte_array[0:-last_byte]


def decrypt_token(token, crypto_key, crypto_iv):
    try:
        byte_array = base64.b64decode(token)
        key        = base64.b64decode(crypto_key)
        iv         = base64.b64decode(crypto_iv)
        cipher     = AES.new(key, AES.MODE_CBC, iv)
        decrypted  = unpad(cipher.decrypt(byte_array)).decode("UTF-8")
        return json.loads(decrypted)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SIDH SSO Decryption Failed")
        frappe.throw("Decryption failed")


def validate_token_expiry(data):
    token_time = data.get("time_stamp")
    if not token_time:
        frappe.throw("Invalid token: missing timestamp")

    current_time = int(time.time() * 1000)
    if current_time - token_time > 30000:
        frappe.throw("Token expired")


def validate_payload(data):
    required_fields = ["candidate_id", "candidate_name", "course_id"]
    for field in required_fields:
        if not data.get(field):
            frappe.throw(f"Invalid token: missing field '{field}'")

    course_id = data.get("course_id")
    if not frappe.db.exists("LMS Course", course_id):
        frappe.throw(f"Course '{course_id}' does not exist")

    email = data.get("candidate_email")
    if email and "@" not in email:
        frappe.throw("Invalid token: malformed email address")


def get_or_create_user(data):
    candidate_id   = data.get("candidate_id")
    candidate_name = data.get("candidate_name", "").strip()
    last_name      = data.get("last_name", "").strip()
    email = (
        data.get("candidate_email")
        or f"{candidate_id}@sidh.in"
    )

    if frappe.db.exists("User", email):
        return email

    try:
        user = frappe.get_doc({
            "doctype"    : "User",
            "email"      : email,
            "first_name" : candidate_name,
            "last_name"  : last_name,
            "enabled"    : 1,
            "user_type"  : "Website User"
        })
        user.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SIDH SSO User Creation Failed")
        frappe.throw("User creation failed")

    return email


def enroll_user_in_course(email, course_id):
    """Enroll the user in the given course if not already enrolled."""
    if frappe.db.exists("LMS Enrollment", {
        "course" : course_id,
        "member" : email
    }):
        return

    try:
        enrollment = frappe.get_doc({
            "doctype"     : "LMS Enrollment",
            "course"      : course_id,
            "member"      : email,
            "member_type" : "Student"
        })
        enrollment.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "SIDH SSO Enrollment Failed")
        frappe.throw("Enrollment failed")


@frappe.whitelist(allow_guest=True)
def handle_sidh_sso():
    settings   = frappe.get_single("SIDH Settings")
    crypto_key = settings.get_password(fieldname="crypto_key", raise_exception=False)
    crypto_iv  = settings.get_password(fieldname="crypto_iv", raise_exception=False)

    token = frappe.request.args.get("token")
    if not token:
        frappe.throw("No token provided")

    data = decrypt_token(token, crypto_key, crypto_iv)

    validate_token_expiry(data)
    validate_payload(data)

    email     = get_or_create_user(data)
    course_id = data.get("course_id")

    frappe.local.login_manager.login_as(email)

    enroll_user_in_course(email, course_id)

    frappe.local.response["type"]     = "redirect"
    frappe.local.response["location"] = f"/lms/courses/{course_id}"