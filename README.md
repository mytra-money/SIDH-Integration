# SIDH Integration
Frappe app for SIDH SSO and Progress API integration.

## SSO Redirection Flow

### Standard Flow (Free Courses)
1. Learner clicks **Enroll** on SIDH course page
2. SIDH redirects learner to the SSO URL provided by Training Partner
3. Learner details are sent as an **AES-128-CBC encrypted token**
4. TP system decrypts token using CRYPTOKEY and CRYPTOIV
5. Learner session is created and learner is enrolled in the course

### Paid Course Flow — Payment Directly to Training Partner
When a course is **Paid** and payment is collected by the Training Partner directly:

1. During course creation on SIDH, fee type is selected as **Paid**
2. The **"Payment made to whom"** option is auto-selected by SIDH
3. SIDH redirects learner to TP SSO URL with encrypted token
4. TP system must handle **payment verification first**
5. After successful payment, TP creates learner session and enrolls in course


## SSO URL Configuration
The SSO URL is auto-set in SIDH Settings doctype: `{site_url}/api/method/sidh_integration.sidh_sso.handle_sidh_sso`