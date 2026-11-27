"""
Customer Onboarding Form - SY Comms / South Wales Telecoms
-----------------------------------------------------------
One branded form for both companies. The brand comes from the link:
    https://<your-app>.streamlit.app/                -> SY Comms
    https://<your-app>.streamlit.app/?brand=sw       -> South Wales Telecoms
Optional: &company=Acme%20Ltd pre-fills the business name.

On submit the answers are sent to the Zoho CRM function "onboarding_form_submit",
which raises a ticket in "SYC - Broadband and Provisioning" (and adds a note to the
customer's CRM account when the email matches a contact).

Streamlit secret needed (Settings -> Secrets):
    FUNCTION_URL = "https://www.zohoapis.eu/crm/v7/functions/onboarding_form_submit/actions/execute?auth_type=apikey&zapikey=..."
"""

import io
import json
import re

import pandas as pd
import requests
import streamlit as st

# --------------------------------------------------------------------------------------
# Brands
# --------------------------------------------------------------------------------------
BRANDS = {
    "sy": {
        "name": "SY Comms",
        "full": "SY Communications",
        "logo": "SY&middot;COMMS",
        "email": "support@sycomms.co.uk",
        "phone": "01743 667419",
    },
    "sw": {
        "name": "South Wales Telecoms",
        "full": "South Wales Telecoms",
        "logo": "SOUTH WALES<br>TELECOMS",
        "email": "support@southwalestelecoms.co.uk",
        "phone": "01792 004407",
    },
}

PURPLE = "#2d1a6e"
PURPLE_DARK = "#1c1633"
LILAC = "#f4f2fb"


def qp(name, default=""):
    try:
        v = st.query_params.get(name, default)
    except Exception:
        v = default
    if isinstance(v, list):
        v = v[0] if v else default
    return v or default


brand_key = "sw" if qp("brand", "sy").lower().startswith("sw") else "sy"
B = BRANDS[brand_key]

st.set_page_config(
    page_title=f"{B['name']} - Customer Onboarding",
    page_icon="📞",
    layout="centered",
)

# --------------------------------------------------------------------------------------
# Styling (matches the welcome-pack emails)
# --------------------------------------------------------------------------------------
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp, input, textarea, button {{ font-family: 'Inter', Arial, sans-serif !important; }}
.stApp {{ background: #eeecf4; }}
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer, [data-testid="stToolbar"] {{ visibility: hidden; }}
.block-container {{ max-width: 780px; padding-top: 1.5rem; padding-bottom: 4rem; }}

.ob-logo {{ width: 104px; height: 104px; border-radius: 52px; background: {PURPLE}; color: #fff;
  display: flex; align-items: center; justify-content: center; text-align: center;
  font-weight: 800; font-size: 14px; line-height: 17px; letter-spacing: .5px; margin: 0 auto 18px; }}
.ob-hero {{ background: {PURPLE}; color: #fff; border-radius: 14px; padding: 26px 30px; margin-bottom: 18px; }}
.ob-hero .eyebrow {{ font-size: 12px; letter-spacing: 2.5px; color: #c9bff2; font-weight: 700; text-transform: uppercase; }}
.ob-hero h1 {{ color: #fff; font-size: 28px; line-height: 1.25; margin: 6px 0 10px; font-weight: 800; padding: 0; }}
.ob-hero p {{ color: #e6e1fb; margin: 0; font-size: 15px; line-height: 1.55; }}

.ob-steps {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 22px; }}
.ob-steps span {{ background: #fff; border: 1px solid #ddd8ee; color: {PURPLE}; border-radius: 999px;
  padding: 5px 12px; font-size: 12.5px; font-weight: 600; }}

.ob-sec {{ display: flex; align-items: center; gap: 12px; margin: 6px 0 2px; }}
.ob-num {{ width: 32px; height: 32px; border-radius: 16px; background: {PURPLE}; color: #fff; font-weight: 800;
  display: flex; align-items: center; justify-content: center; font-size: 15px; flex: none; }}
.ob-sec h3 {{ margin: 0; padding: 0; color: {PURPLE}; font-size: 20px; font-weight: 800; }}
.ob-sub {{ color: #5d5875; font-size: 14px; margin: 2px 0 10px 44px; }}

div[class*="st-key-obcard"] {{ padding: 18px 20px 20px !important; }}
div[class*="st-key-obcard"], div[data-testid="stVerticalBlockBorderWrapper"] {{ background: #fff; border-radius: 14px !important;
  border: 1px solid #e3dff0 !important; box-shadow: 0 2px 10px rgba(45,26,110,.05); }}

.ob-note {{ background: {LILAC}; border-left: 4px solid {PURPLE}; border-radius: 8px; padding: 14px 18px;
  color: #2b2840; font-size: 14px; line-height: 1.55; margin: 8px 0 18px; }}
.ob-note b {{ color: {PURPLE}; }}
.ob-ai {{ background: linear-gradient(135deg, {PURPLE}, #5b3fc4); color: #fff; border-radius: 12px; padding: 16px 18px;
  font-size: 14px; line-height: 1.55; margin-bottom: 10px; }}
.ob-ai b {{ color: #fff; }}

.stButton > button, .stFormSubmitButton > button, div[data-testid="stFormSubmitButton"] button {{
  background: {PURPLE} !important; color: #fff !important; border: 0 !important; border-radius: 10px !important;
  padding: .7rem 1.6rem !important; font-weight: 700 !important; font-size: 16px !important; width: 100%; }}
.stButton > button:hover {{ background: #3d2896 !important; }}

.ob-foot {{ background: {PURPLE_DARK}; color: #fff; border-radius: 12px; padding: 18px 22px; margin-top: 26px;
  font-size: 13px; line-height: 1.6; }}
.ob-foot b {{ font-size: 15px; }}
.ob-foot a {{ color: #c9bff2; text-decoration: none; }}
.ob-done {{ background: #fff; border: 1px solid #e3dff0; border-radius: 14px; padding: 30px; text-align: center; }}
.ob-done h2 {{ color: {PURPLE}; margin: 6px 0 8px; }}
[data-testid="InputInstructions"] {{ display: none !important; }}
label, .stRadio label p, .stCheckbox label p {{ font-weight: 600 !important; color: #2b2840 !important; }}
</style>
""",
    unsafe_allow_html=True,
)


def section(num, title, sub=""):
    st.markdown(
        f'<div class="ob-sec"><div class="ob-num">{num}</div><h3>{title}</h3></div>'
        + (f'<div class="ob-sub">{sub}</div>' if sub else ""),
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        f"""<div class="ob-foot"><b>{B['full']}</b><br>
        Questions? Email <a href="mailto:{B['email']}">{B['email']}</a> or call <b style="font-size:13px">{B['phone']}</b></div>""",
        unsafe_allow_html=True,
    )


def header():
    st.markdown(f'<div class="ob-logo">{B["logo"]}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="ob-hero">
  <div class="eyebrow">Welcome to {B['name']}</div>
  <h1>Let's set up your new phone system</h1>
  <p>This form gives our engineers everything they need to build your system before install day:
  your team, your opening hours, your greetings and voicemail. It takes about 10 minutes, and you can leave
  anything you're unsure of blank &mdash; we'll go through it with you.</p>
</div>
<div class="ob-steps"><span>1 &middot; About you</span><span>2 &middot; IT &amp; network</span><span>3 &middot; Your calls</span>
<span>4 &middot; Your team</span><span>5 &middot; Phonebook</span><span>6 &middot; Anything else</span></div>""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------------
# Phonebook upload parsing
# --------------------------------------------------------------------------------------
PB_COLS = ["First name", "Surname", "Phone number"]


def parse_phonebook(upload):
    """Read a CSV/XLS(X) phonebook into the 3 standard columns."""
    if upload is None:
        return pd.DataFrame(columns=PB_COLS)
    name = upload.name.lower()
    data = upload.getvalue()
    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(data), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(data), dtype=str, encoding_errors="ignore")
    except Exception:
        return None
    df = df.dropna(how="all").fillna("")
    if df.shape[1] < 3:
        return None
    df = df.iloc[:, :3]
    df.columns = PB_COLS
    # drop a header row if the file had one that looked like data
    df = df[~df["First name"].str.strip().str.lower().isin(["first name", "firstname", "first"])]
    df["Phone number"] = df["Phone number"].astype(str).str.replace(r"\s+", "", regex=True)
    return df.reset_index(drop=True)


def rows_from_df(df, cols):
    out = []
    if df is None:
        return out
    for _, r in df.iterrows():
        vals = ["" if pd.isna(r.get(c)) else str(r.get(c)).strip() for c in cols]
        if any(v not in ("", "False", "None", "nan") for v in vals):
            out.append(vals)
    return out


# --------------------------------------------------------------------------------------
# Thank-you screen
# --------------------------------------------------------------------------------------
if st.session_state.get("done"):
    header_done = st.markdown(f'<div class="ob-logo">{B["logo"]}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="ob-done"><div style="font-size:44px">✅</div>
        <h2>Thank you &mdash; we've got everything</h2>
        <p style="color:#4a4560;font-size:15px;line-height:1.6;margin:0">
        Your answers have gone straight to our onboarding team, who'll use them to build your system.
        We'll be in touch if we need anything else.<br><br>
        Reference: <b>{st.session_state.get('ref','')}</b></p></div>""",
        unsafe_allow_html=True,
    )
    footer()
    st.stop()

# --------------------------------------------------------------------------------------
# The form
# --------------------------------------------------------------------------------------
header()

# 1. About you --------------------------------------------------------------------------
with st.container(border=True, key="obcard1"):
    section(1, "About you", "So we know who we're setting up and where.")
    c1, c2 = st.columns(2)
    company = c1.text_input("Business name *", value=qp("company"), key="company")
    contact_name = c2.text_input("Site contact name *")
    c3, c4 = st.columns(2)
    phone = c3.text_input("Best phone / mobile")
    email = c4.text_input("Email address *")
    address = st.text_area("Install and/or delivery address", height=90)

# 2. IT & network ----------------------------------------------------------------------
with st.container(border=True, key="obcard2"):
    section(2, "Your IT & network", "Helps us make sure your phones work smoothly on your network.")
    c1, c2 = st.columns(2)
    it_contact = c1.text_input("IT team / contact (if you have one)")
    crm = c2.text_input("CRM or database you use", placeholder="e.g. Zoho, Salesforce, an industry system")
    vpn = st.radio(
        "Do you have a VPN, firewall or network security policies in place?",
        ["No", "Yes", "Not sure"],
        horizontal=True,
    )
    vpn_details = ""
    if vpn == "Yes":
        vpn_details = st.text_area(
            "Tell us about your security setup",
            placeholder="Firewall make/model, VPN, any rules we need to know about...",
            height=90,
        )
    wifi_choice = st.radio(
        "Your Wi-Fi (for new broadband)",
        ["Keep my current Wi-Fi name & password", "I'd like to change it"],
        help="We can keep what you have already for new broadband, so your devices reconnect automatically.",
    )
    c1, c2 = st.columns(2)
    wifi_label = "Current" if wifi_choice.startswith("Keep") else "New"
    wifi_name = c1.text_input(f"{wifi_label} Wi-Fi name (SSID)")
    wifi_pass = c2.text_input(f"{wifi_label} Wi-Fi password")

# 3. Your calls ------------------------------------------------------------------------
def suggest(key, text):
    """Pre-fill a message with a suggestion, and keep it up to date (e.g. when the
    business name changes) until the customer edits it themselves."""
    prev = st.session_state.get(key + "__s")
    cur = st.session_state.get(key)
    if cur is None or cur == prev or not str(cur).strip():
        st.session_state[key] = text
    st.session_state[key + "__s"] = text


biz = (company or "").strip() or "[your business name]"
REC = "Please be advised, all calls are recorded for training and quality purposes."

with st.container(border=True, key="obcard3"):
    section(3, "Your calls", "How your phones answer, and when. We've suggested messages using your business name – edit them however you like.")
    hours = st.text_area(
        "Your business opening hours",
        placeholder="e.g. Monday to Friday 9.00am - 5.00pm, Saturday 9.00am - 12pm",
        height=80,
        key="hours",
    )
    hours_txt = " ".join((hours or "").split()) or "[your opening hours]"

    call_flow = st.selectbox(
        "When someone calls, what should happen?",
        [
            "Welcome message, then ring a group of people",
            "IVR menu – callers press 1, 2, 3 to reach the right team",
        ],
    )
    is_ivr = call_flow.startswith("IVR")
    ring_group = ""
    ivr_rows = []
    if not is_ivr:
        ring_group = st.text_input(
            "Who should the call ring?",
            value="All phones",
            help="e.g. All phones, or Reception + Sarah + Tom",
        )
        suggest(
            "welcome",
            f"Hello and thank you for calling {biz}. {REC} "
            "Please stay on the line and we will be with you in just a moment.",
        )
    else:
        st.caption("Add each option callers can choose, and who it should ring.")
        if "ivr_df" not in st.session_state:
            st.session_state.ivr_df = pd.DataFrame(
                {"Press": ["1", "2", "3"], "Option (what callers hear)": ["", "", ""], "Rings who?": ["", "", ""]}
            )
        ivr_df = st.data_editor(
            st.session_state.ivr_df,
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            column_config={
                "Press": st.column_config.TextColumn(width="small"),
                "Option (what callers hear)": st.column_config.TextColumn(
                    width="medium", help="e.g. Sales, Accounts, Technical support"),
                "Rings who?": st.column_config.TextColumn(width="medium", help="e.g. Sarah + Tom, or All phones"),
            },
            key="ivr_editor",
        )
        ivr_rows = rows_from_df(ivr_df, ["Press", "Option (what callers hear)", "Rings who?"])
        opts = [r for r in ivr_rows if r[1]]
        if opts:
            menu = " ".join(f"For {r[1]}, please press {r[0] or '?'}." for r in opts)
        else:
            menu = "For sales, please press 1. For accounts, please press 2. For anything else, please press 3."
        suggest(
            "welcome",
            f"Hello and thank you for calling {biz}. {REC} "
            f"Please listen carefully to the following options. {menu}",
        )

    welcome = st.text_area(
        "IVR menu message callers will hear" if is_ivr else "Welcome message callers will hear",
        height=110,
        key="welcome",
    )
    ring = st.select_slider(
        "How long should phones ring before going to voicemail?",
        options=[10, 15, 20, 25, 30, 40, 50, 60],
        value=20,
        format_func=lambda s: f"{s} seconds",
    )

    suggest(
        "day_vm",
        f"Hello and thank you for calling {biz}. We are sorry that we have been unable to answer your call "
        "at the moment. Please call us again in just a moment, or stay on the line to leave a message for us, "
        "and we will be back in touch with you as soon as we are available.",
    )
    day_vm = st.text_area(
        "Daytime voicemail (busy / no answer)",
        height=110,
        key="day_vm",
    )

    ooh = st.radio(
        "Do you need an out-of-hours (night) voicemail message?", ["Yes", "No"], horizontal=True
    )
    night_vm = ""
    if ooh == "Yes":
        suggest(
            "night_vm",
            f"Thank you for calling {biz}. Our offices are currently closed. Our normal opening hours are "
            f"{hours_txt}. Please call us again when we reopen, or stay on the line to leave a voice message "
            "for us, and we will be back in touch with you when we reopen.",
        )
        night_vm = st.text_area(
            "Out-of-hours (night) voicemail",
            height=120,
            key="night_vm",
        )
    outage = st.text_input(
        "Emergency divert number",
        help="In the unlikely event of a major service outage, we'll divert your calls here.",
        placeholder="A mobile or landline we can divert to in an emergency",
    )

# 4. Your team -------------------------------------------------------------------------
with st.container(border=True, key="obcard4"):
    section(
        4,
        "Your team",
        "Add each person / extension. We'll email mobile-app logins to the address you give.",
    )
    if "ext_df" not in st.session_state:
        st.session_state.ext_df = pd.DataFrame(
            {"Extension name": [""] * 3, "Email (for mobile app)": [""] * 3, "Voicemail to email": [False] * 3}
        )
    ext_df = st.data_editor(
        st.session_state.ext_df,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "Extension name": st.column_config.TextColumn(width="medium", help="e.g. Reception, Sarah, Warehouse"),
            "Email (for mobile app)": st.column_config.TextColumn(width="medium"),
            "Voicemail to email": st.column_config.CheckboxColumn(width="small"),
        },
        key="ext_editor",
    )
    vm_email = st.text_input(
        "Shared voicemail-to-email address (optional)",
        placeholder="e.g. office@yourbusiness.co.uk",
    )
    c1, c2 = st.columns(2)
    vm_pin = c1.text_input("4-digit voicemail PIN", max_chars=4, placeholder="e.g. 2580")
    app_pw = c2.text_input("Mobile app password", placeholder="e.g. Abcd1234!!", help="Letters and numbers")

# 5. Phonebook -------------------------------------------------------------------------
with st.container(border=True, key="obcard5"):
    section(5, "Phonebook", "Contacts you'd like loaded onto the system (optional).")
    want_pb = st.radio("Do you have a phonebook you'd like adding?", ["No", "Yes"], horizontal=True)
    pb_rows = []
    pb_upload_name = ""
    if want_pb == "Yes":
        up = st.file_uploader(
            "Upload a CSV or Excel file", type=["csv", "xlsx", "xls"],
            help="3 columns: FIRST NAME, SURNAME, PHONE NUMBER (no spaces)",
        )
        st.caption("3 columns: **First name, Surname, Phone number**. Or just type them into the table below.")
        parsed = parse_phonebook(up) if up else pd.DataFrame(columns=PB_COLS)
        if up and parsed is None:
            st.warning("We couldn't read that file - please check it has 3 columns, or type the contacts below.")
            parsed = pd.DataFrame(columns=PB_COLS)
        if up:
            pb_upload_name = up.name
            st.success(f"Loaded {len(parsed)} contacts from {up.name} - check them below.")
        if parsed.empty:
            parsed = pd.DataFrame({c: [""] * 3 for c in PB_COLS})
        pb_df = st.data_editor(
            parsed, num_rows="dynamic", width="stretch", hide_index=True,
            key=f"pb_editor_{pb_upload_name}",
        )
        pb_rows = rows_from_df(pb_df, PB_COLS)

# 6. Anything else ---------------------------------------------------------------------
with st.container(border=True, key="obcard6"):
    section(6, "Anything else", "Extra features and requests.")
    other = st.text_area(
        "Any other requests for your new phone system?",
        placeholder="e.g. IVR menu (press 1 for sales, 2 for accounts), ring/hunt groups, overflows, diverts...",
        height=100,
    )
    st.markdown(
        """<div class="ob-ai"><b>Did you know? We can build you a custom AI call-answering service.</b><br>
        80% of callers won't leave a message. With our AI call agent you'll never miss a call, you'll be notified
        even if a caller hangs up, and we'll include a chat &amp; call widget for your website.</div>""",
        unsafe_allow_html=True,
    )
    ai = st.radio(
        "Interested in AI call answering?",
        ["No thanks", "Yes - please call me back to discuss"],
        horizontal=True,
        label_visibility="collapsed",
    )

st.markdown(
    f"""<div class="ob-note"><b>Important:</b> please submit this form as soon as you can so we can build your
    system. If we don't receive it in time, or information is missing, your install or go-live date may be delayed.
    Not sure about something? Leave it blank, or contact our onboarding team on
    <b>{B['email']}</b> / <b>{B['phone']}</b>.</div>""",
    unsafe_allow_html=True,
)

submit = st.button("Submit my onboarding form →", type="primary")

# --------------------------------------------------------------------------------------
# Submit
# --------------------------------------------------------------------------------------
if submit:
    errors = []
    if not company.strip():
        errors.append("Business name")
    if not contact_name.strip():
        errors.append("Site contact name")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
        errors.append("a valid email address")
    if vm_pin.strip() and not re.fullmatch(r"\d{4}", vm_pin.strip()):
        errors.append("a 4-digit voicemail PIN (numbers only)")
    if errors:
        st.error("Please add " + ", ".join(errors) + ".")
        st.stop()

    ext_rows = []
    for row in rows_from_df(ext_df, ["Extension name", "Email (for mobile app)", "Voicemail to email"]):
        name, em, vm = row
        if name or em:
            ext_rows.append([name, em, "Yes" if vm == "True" else "No"])

    payload = {
        "brand": B["name"],
        "company": company.strip(),
        "contact_name": contact_name.strip(),
        "email": email.strip(),
        "sections": [
            {"title": "About you", "rows": [
                {"q": "Business name", "a": company},
                {"q": "Site contact name", "a": contact_name},
                {"q": "Best phone / mobile", "a": phone},
                {"q": "Email", "a": email},
                {"q": "Install / delivery address", "a": address},
            ]},
            {"title": "IT & network", "rows": [
                {"q": "IT team / contact", "a": it_contact},
                {"q": "CRM / database", "a": crm},
                {"q": "VPN / firewall / security policies", "a": vpn},
                {"q": "Security setup details", "a": vpn_details},
                {"q": "Wi-Fi", "a": wifi_choice},
                {"q": f"{wifi_label} Wi-Fi name (SSID)", "a": wifi_name},
                {"q": f"{wifi_label} Wi-Fi password", "a": wifi_pass},
            ]},
            {"title": "Calls", "rows": [
                {"q": "Opening hours", "a": hours},
                {"q": "Call flow", "a": call_flow},
                {"q": "Ring group (who answers)", "a": ring_group if not is_ivr else "See IVR options table"},
                {"q": "IVR menu message" if is_ivr else "Welcome message", "a": welcome},
                {"q": "Daytime voicemail (busy / no answer)", "a": day_vm},
                {"q": "Out-of-hours voicemail needed", "a": ooh},
                {"q": "Out-of-hours (night) voicemail", "a": night_vm},
                {"q": "Ring time before voicemail", "a": f"{ring} seconds"},
                {"q": "Emergency divert number", "a": outage},
            ]},
            {"title": "Team, voicemail & apps", "rows": [
                {"q": "Shared voicemail-to-email address", "a": vm_email},
                {"q": "Voicemail PIN", "a": vm_pin},
                {"q": "Mobile app password", "a": app_pw},
            ]},
            {"title": "Anything else", "rows": [
                {"q": "Other requests", "a": other},
                {"q": "AI call answering", "a": ai},
                {"q": "Phonebook wanted", "a": want_pb + (f" (uploaded {pb_upload_name})" if pb_upload_name else "")},
            ]},
        ],
        "tables": ([
            {"title": "IVR options", "headers": ["Press", "Option", "Rings who?"], "rows": ivr_rows},
        ] if is_ivr else []) + [
            {"title": "Extensions", "headers": ["Extension name", "Email (mobile app)", "Voicemail to email"],
             "rows": ext_rows},
            {"title": "Phonebook", "headers": PB_COLS, "rows": pb_rows},
        ],
    }

    url = st.secrets.get("FUNCTION_URL", "")
    if not url:
        st.error("This form isn't connected yet (FUNCTION_URL secret missing). "
                 f"Please email your details to {B['email']}.")
        st.stop()

    with st.spinner("Sending your answers to our onboarding team..."):
        try:
            r = requests.post(url, json=payload, timeout=60)
            out = r.json()
            result = str((out.get("details") or {}).get("output", ""))
        except Exception as e:  # network / JSON errors
            result = f"ERROR: {e}"

    if result.startswith("OK"):
        ref = result.split("|")[0].replace("OK", "").strip()
        st.session_state.done = True
        st.session_state.ref = ref
        st.rerun()
    else:
        st.error(
            "Sorry - something went wrong sending your form. Please try again, or email "
            f"{B['email']} / call {B['phone']}."
        )
        with st.expander("Technical details"):
            st.code(result[:1500])

footer()
