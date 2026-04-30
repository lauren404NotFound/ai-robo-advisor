"""
ui/styles.py
============
Theme constants, SVG icon helper, and global CSS injector.
Extracted from the monolithic app.py.
"""
from __future__ import annotations
import streamlit as st




# ══════════════════════════════════════════════════════════════════════════════
# THEME - "Cyber Lilac" (Inspired by modern fintech UI)
# ══════════════════════════════════════════════════════════════════════════════
ACCENT  = "#9B72F2"  # Vibrant Lilac
ACCENT2 = "#B18AFF"  # Soft Lavender
ACCENT3 = "#E6D5FF"  # White-ish Purple
CANVAS  = "#0B0B1A"  # Light background
PANEL   = "rgba(18, 18, 38, 0.72)"
BORDER  = "rgba(155, 114, 242, 0.22)"
TEXT    = "#F3F3F9"
MUTED   = "rgba(237, 237, 243, 0.55)"
GRID    = "rgba(155, 114, 242, 0.08)"
TMPL    = "plotly_dark"
POS     = "#4AE3A0"  # Spring Green
NEG     = "#FF6B6B"  # Vibrant Coral

PROFILE_COLORS = {
    "Ultra Conservative": "#60A5FA",
    "Conservative":        "#4AE3A0",
    "Moderate":            "#FBBF24",
    "Balanced Growth":     "#F97316",
    "Growth":              "#EF4444",
    "Aggressive Growth":   "#9B72F2",
}



GLOBAL_CURRENCIES = [
    "AED (د.إ)", "AFN (؋)", "ALL (L)", "AMD (֏)", "ANG (ƒ)", "AOA (Kz)", "ARS ($)", "AUD (A$)", "AWG (ƒ)", "AZN (₼)", "BAM (KM)", "BBD ($)", 
    "BDT (৳)", "BGN (лв)", "BHD (.د.ب)", "BIF (Fr)", "BMD ($)", "BND ($)", "BOB (Bs.)", "BRL (R$)", "BSD ($)", "BTN (Nu.)", "BWP (P)", "BYN (Br)", 
    "BZD ($)", "CAD (C$)", "CDF (Fr)", "CHF (Fr)", "CLP ($)", "CNY (¥)", "COP ($)", "CRC (₡)", "CUP ($)", "CVE ($)", "CZK (Kč)", "DJF (Fr)", 
    "DKK (kr)", "DOP ($)", "DZD (د.ج)", "EGP (£)", "ERN (Nfk)", "ETB (Br)", "EUR (€)", "FJD ($)", "FKP (£)", "GBP (£)", "GEL (₾)", "GHS (₵)", 
    "GIP (£)", "GMD (D)", "GNF (Fr)", "GTQ (Q)", "GYD ($)", "HKD ($)", "HNL (L)", "HRK (kn)", "HTG (G)", "HUF (Ft)", "IDR (Rp)", "ILS (₪)", 
    "INR (₹)", "IQD (ع.د)", "IRR (﷼)", "ISK (kr)", "JMD ($)", "JOD (د.ا)", "JPY (¥)", "KES (Sh)", "KGS (с)", "KHR (៛)", "KMF (Fr)", "KPW (₩)", 
    "KRW (₩)", "KWD (د.ك)", "KYD ($)", "KZT (₸)", "LAK (₭)", "LBP (ل.ل)", "LKR (Rs)", "LRD ($)", "LSL (L)", "LYD (ل.د)", "MAD (د.م.)", "MDL (L)", 
    "MGA (Ar)", "MKD (ден)", "MMK (Ks)", "MNT (₮)", "MOP (P)", "MRU (UM)", "MUR (₨)", "MVR (MVR)", "MWK (MK)", "MXN ($)", "MYR (RM)", "MZN (MT)", 
    "NAD ($)", "NGN (₦)", "NIO (C$)", "NOK (kr)", "NPR (₨)", "NZD ($)", "OMR (ر.ع.)", "PAB (B/.)", "PEN (S/.)", "PGK (K)", "PHP (₱)", "PKR (₨)", 
    "PLN (zł)", "PYG (₲)", "QAR (ر.ق)", "RON (lei)", "RSD (дин.)", "RUB (₽)", "RWF (Fr)", "SAR (ر.س)", "SBD ($)", "SCR (₨)", "SDG (ج.س.)", 
    "SEK (kr)", "SGD ($)", "SHP (£)", "SLL (Le)", "SOS (Sh)", "SRD ($)", "SSP (£)", "STN (Db)", "SYP (£)", "SZL (L)", "THB (฿)", "TJS (SM)", 
    "TMT (T)", "TND (د.ت)", "TOP (T$)", "TRY (₺)", "TTD ($)", "TWD (NT$)", "TZS (Sh)", "UAH (₴)", "UGX (Sh)", "USD ($)", "UYU ($)", "UZS (so'm)", 
    "VES (Bs.S)", "VND (₫)", "VUV (Vt)", "WST (T)", "XAF (Fr)", "XCD ($)", "XOF (Fr)", "XPF (Fr)", "YER (﷼)", "ZAR (R)", "ZMW (ZK)", "ZWL ($)"
]

GLOBAL_COUNTRIES = [
    "+1 (USA/Canada)", "+7 (Russia/Kazakhstan)", "+20 (Egypt)", "+27 (South Africa)", "+30 (Greece)", "+31 (Netherlands)", "+32 (Belgium)", 
    "+33 (France)", "+34 (Spain)", "+36 (Hungary)", "+39 (Italy)", "+40 (Romania)", "+41 (Switzerland)", "+43 (Austria)", "+44 (UK)", 
    "+45 (Denmark)", "+46 (Sweden)", "+47 (Norway)", "+48 (Poland)", "+49 (Germany)", "+51 (Peru)", "+52 (Mexico)", "+53 (Cuba)", "+54 (Argentina)", 
    "+55 (Brazil)", "+56 (Chile)", "+57 (Colombia)", "+58 (Venezuela)", "+60 (Malaysia)", "+61 (Australia)", "+62 (Indonesia)", "+63 (Philippines)", 
    "+64 (New Zealand)", "+65 (Singapore)", "+66 (Thailand)", "+81 (Japan)", "+82 (South Korea)", "+84 (Vietnam)", "+86 (China)", "+90 (Turkey)", 
    "+91 (India)", "+92 (Pakistan)", "+93 (Afghanistan)", "+94 (Sri Lanka)", "+95 (Myanmar)", "+98 (Iran)", "+212 (Morocco)", "+213 (Algeria)", 
    "+216 (Tunisia)", "+218 (Libya)", "+220 (Gambia)", "+221 (Senegal)", "+222 (Mauritania)", "+223 (Mali)", "+224 (Guinea)", "+225 (Ivory Coast)", 
    "+226 (Burkina Faso)", "+227 (Niger)", "+228 (Togo)", "+229 (Benin)", "+230 (Mauritius)", "+231 (Liberia)", "+232 (Sierra Leone)", "+233 (Ghana)", 
    "+234 (Nigeria)", "+235 (Chad)", "+236 (CAR)", "+237 (Cameroon)", "+238 (Cape Verde)", "+239 (STP)", "+240 (Equatorial Guinea)", "+241 (Gabon)", 
    "+242 (Congo)", "+243 (DRC)", "+244 (Angola)", "+245 (Guinea-Bissau)", "+246 (Diego Garcia)", "+247 (Ascension)", "+248 (Seychelles)", "+249 (Sudan)", 
    "+250 (Rwanda)", "+251 (Ethiopia)", "+252 (Somalia)", "+253 (Djibouti)", "+254 (Kenya)", "+255 (Tanzania)", "+256 (Uganda)", "+257 (Burundi)", 
    "+258 (Mozambique)", "+260 (Zambia)", "+261 (Madagascar)", "+262 (Reunion/Mayotte)", "+263 (Zimbabwe)", "+264 (Namibia)", "+265 (Malawi)", 
    "+266 (Lesotho)", "+267 (Botswana)", "+268 (Eswatini)", "+269 (Comoros)", "+290 (St Helena)", "+291 (Eritrea)", "+297 (Aruba)", "+298 (Faroe Islands)", 
    "+299 (Greenland)", "+350 (Gibraltar)", "+351 (Portugal)", "+352 (Luxembourg)", "+353 (Ireland)", "+354 (Iceland)", "+355 (Albania)", "+356 (Malta)", 
    "+357 (Cyprus)", "+358 (Finland)", "+359 (Bulgaria)", "+370 (Lithuania)", "+371 (Latvia)", "+372 (Estonia)", "+373 (Moldova)", "+374 (Armenia)", 
    "+375 (Belarus)", "+376 (Andorra)", "+377 (Monaco)", "+378 (San Marino)", "+380 (Ukraine)", "+381 (Serbia)", "+382 (Montenegro)", "+383 (Kosovo)", 
    "+385 (Croatia)", "+386 (Slovenia)", "+387 (Bosnia)", "+389 (North Macedonia)", "+420 (Czech Republic)", "+421 (Slovakia)", "+423 (Liechtenstein)", 
    "+500 (Falkland Islands)", "+501 (Belize)", "+502 (Guatemala)", "+503 (El Salvador)", "+504 (Honduras)", "+505 (Nicaragua)", "+506 (Costa Rica)", 
    "+507 (Panama)", "+508 (St Pierre & Miquelon)", "+509 (Haiti)", "+590 (Guadeloupe)", "+591 (Bolivia)", "+592 (Guyana)", "+593 (Ecuador)", 
    "+594 (French Guiana)", "+595 (Paraguay)", "+596 (Martinique)", "+597 (Suriname)", "+598 (Uruguay)", "+599 (Curacao/Bonaire)", "+670 (East Timor)", 
    "+672 (Antarctica/Norfolk)", "+673 (Brunei)", "+674 (Nauru)", "+675 (Papua New Guinea)", "+676 (Tonga)", "+677 (Solomon Islands)", "+678 (Vanuatu)", 
    "+679 (Fiji)", "+680 (Palau)", "+681 (Wallis & Futuna)", "+682 (Cook Islands)", "+683 (Niue)", "+685 (Samoa)", "+686 (Kiribati)", "+687 (New Caledonia)", 
    "+688 (Tuvalu)", "+689 (French Polynesia)", "+690 (Tokelau)", "+691 (Micronesia)", "+692 (Marshall Islands)", "+850 (North Korea)", "+852 (Hong Kong)", 
    "+853 (Macau)", "+855 (Cambodia)", "+856 (Laos)", "+880 (Bangladesh)", "+886 (Taiwan)", "+960 (Maldives)", "+961 (Lebanon)", "+962 (Jordan)", 
    "+963 (Syria)", "+964 (Iraq)", "+965 (Kuwait)", "+966 (Saudi Arabia)", "+967 (Yemen)", "+968 (Oman)", "+970 (Palestine)", "+971 (UAE)", "+972 (Israel)", 
    "+973 (Bahrain)", "+974 (Qatar)", "+975 (Bhutan)", "+976 (Mongolia)", "+977 (Nepal)", "+992 (Tajikistan)", "+993 (Turkmenistan)", "+994 (Azerbaijan)", 
    "+995 (Georgia)", "+996 (Kyrgyzstan)", "+998 (Uzbekistan)"
]

# ══════════════════════════════════════════════════════════════════════════════
# ICONS (Lucide-style Outline)
# ══════════════════════════════════════════════════════════════════════════════
def get_svg(name, size=18, color="currentColor"):
    icons = {
        "home": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "dashboard": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>',
        "news": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6Z"/></svg>',
        "market": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
        "search": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
        "more": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>',
        "brain": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54Z"/></svg>',
        "zap": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m13 2-2 10h3l-2 10 7-12h-3l2-8Z"/></svg>',
        "shield": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/></svg>',
        "layers": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.1 6.27a2 2 0 0 0 0 3.66l9.07 4.09a2 2 0 0 0 1.66 0l9.07-4.09a2 2 0 0 0 0-3.66Z"/><path d="m2.1 14.07 9.07 4.09a2 2 0 0 0 1.66 0l9.07-4.09"/><path d="m2.1 19.07 9.07 4.09a2 2 0 0 0 1.66 0l9.07-4.09"/></svg>',
        "chart": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 16v-4"/><path d="M11 16V8"/><path d="M15 16v-6"/></svg>',
        "risk": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20"/><path d="m4.93 4.93 14.14 14.14"/><path d="M2 12h20"/><path d="m4.93 19.07 14.14-14.14"/></svg>',
        "user": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
        "portfolio": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><rect x="7" y="10" width="4" height="7" rx="1"/><rect x="13" y="5" width="4" height="12" rx="1"/></svg>',
        "settings": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.72l-.22-.39a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>',
        "logout": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1-2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
        "shield-check": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></svg>',
        "bell": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
        "list": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>',
        "cart": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.56-7.43h-13.88"/></svg>',
        "info": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        "puzzle": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19.4 14.9C18.4 14 18 12.8 18 11.6c0-1.1-.9-2-2-2h-2c-1.1 0-2-.9-2-2V5.6c0-1.2-.4-2.4-1.4-3.3-1.8-1.5-4.5-1.5-6.3 0-1 1-1.4 2.1-1.4 3.3V7.6c0 1.1-.9 2-2 2H1c-1.1 0-2 .9-2 2v2c0 1.1.4 2.2 1.4 3s2.4 1.4 3.6 1.4c1.1 0 2 .9 2 2v1c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2v-1c0-1.2.4-2.4 1.4-3.3s2.1-1.4 3.3-1.4h.7c1.1 0 2-.9 2-2v-2"></path></svg>',
        "warning": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "refresh": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><polyline points="21 3 21 8 16 8"/></svg>',
        "clipboard": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></svg>',
        "lightbulb": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-3.36 3-5.74a7 7 0 0 0-7-7Z"/></svg>',
        "globe": f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>'
    }
    return icons.get(name, "")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Robo-Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)



st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {{
  font-family: 'Inter', system-ui, sans-serif !important;
}}
.stApp {{
  background:
    radial-gradient(1000px 700px at 0% 0%, rgba(155, 114, 242, 0.15) 0%, transparent 60%),
    radial-gradient(800px 600px at 100% 20%, rgba(177, 138, 255, 0.08) 0%, transparent 70%),
    radial-gradient(1200px 800px at 50% 100%, rgba(138, 43, 226, 0.06) 0%, transparent 60%),
    linear-gradient(135deg, #070B1A 0%, #0F172A 100%);
  color: {TEXT};
}}
.block-container {{
  padding-top: 0 !important;
  padding-bottom: 4rem !important;
  max-width: 1400px; padding-top: 4rem !important;
}}
header[data-testid="stHeader"], div[data-testid="stToolbar"],
.stDeployButton, #MainMenu {{ display:none !important; visibility:hidden; }}

/* ══ TOP NAV ══ */
.nav-bar {{
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  display: flex; align-items: center;
  padding: 0 40px; height: 68px;
  background: rgba(11, 11, 26, 0.9);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid rgba(155, 114, 242, 0.15);
  pointer-events: none;
}}

.nav-link {{
  color: {MUTED}; font-size: 14px; font-weight: 500;
  transition: all 0.25s; text-decoration: none;
  padding: 8px 16px; border-radius: 12px;
  display: flex; align-items: center; gap: 8px;
  white-space: nowrap;
}}
.nav-link-wrap.active .nav-link:hover {{ color: #ffffff; background: rgba(255,255,255,0.05); }}
.nav-link-wrap.active .nav-link {{ color: #3BA4FF; font-weight: 700; border-bottom: 2px solid #3BA4FF; border-bottom-left-radius: 0; border-bottom-right-radius: 0; }}

.nav-link {{
  color: {ACCENT}; background: transparent; font-weight: 700;
}}
.nav-right {{
  display: flex; align-items: center; justify-content: flex-end; gap: 12px;
}}
#nav-trigger-marker {{ position: fixed; top: 0; left: 0; height: 0; width: 0; z-index: 1001; }}

/* The Streamlit block containing the buttons */
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) {{
    position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important;
    height: 68px !important; z-index: 1005 !important;
    display: grid !important; gap: 0 !important;
    grid-template-columns: 240px repeat(5, 110px) 1fr 360px !important;
    padding: 0 40px !important; align-items: center !important;
    background: transparent !important; pointer-events: auto !important;
}}
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) button {{
    background: transparent !important; border: none !important; color: transparent !important;
    height: 68px !important; width: 100% !important; margin: 0 !important;
    box-shadow: none !important;
}}
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) button:hover {{
    background: rgba(255,255,255,0.03) !important;
}}
div[data-testid="stHorizontalBlock"]:has(#nav-trigger-marker) div[data-testid="column"] {{
    width: 100% !important; flex: none !important; padding: 0 !important;
}}
.nav-account {{
  display: flex; align-items: center; gap: 8px;
  padding: 5px 12px; border-radius: 20px;
  border: 1px solid {BORDER}; background: rgba(138,43,226,0.08);
  font-size: 13px; color: {ACCENT3}; font-weight: 600;
}}
.nav-avatar {{
  width: 26px; height: 26px; border-radius: 50%;
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800; color: #ffffff;
}}
.nav-btn {{
  padding: 6px 16px; border-radius: 8px; font-size: 13px;
  font-weight: 600; cursor: pointer; transition: all 0.18s;
  border: none;
}}
.nav-btn-outline {{
  background: transparent; color: {ACCENT2};
  border: 1px solid rgba(138,43,226,0.4);
}}
.nav-btn-outline:hover {{ background: rgba(138,43,226,0.12); }}
.nav-btn-primary {{
  background: {ACCENT}; color: #ffffff;
}}
.nav-btn-primary:hover {{ background: #7020cc; box-shadow: 0 4px 16px rgba(138,43,226,0.4); }}
.nav-btn-danger {{
  background: transparent; color: {NEG};
  border: 1px solid rgba(255,107,107,0.3);
}}
.nav-btn-danger:hover {{ background: rgba(255,107,107,0.08); }}

/* ══ INPUT TEXT COLOURS (make number/text inputs readable on dark theme) ══ */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea {{
  color: #ffffff !important;
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(109,94,252,0.3) !important;
  border-radius: 10px !important;
}}
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextInput"] input:focus {{
  border-color: #9B72F2 !important;
  box-shadow: 0 0 0 2px rgba(155,114,242,0.18) !important;
}}





/* ══ AUTH MODAL OVERLAY (Controlled within render_auth_modal) ══ */
.modal-title {{
  font-size: 28px; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 6px; text-align: center;
  background: linear-gradient(90deg, #ffffff 0%, #a78bfa 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.modal-sub {{
  font-size: 14px; color: #8BA6D3; text-align: center; margin-bottom: 28px;
}}
.modal-divider {{ display: flex; align-items: center; gap: 12px; margin: 18px 0; }}
.modal-divider-line {{ flex: 1; height: 1px; background: rgba(109,94,252,0.25); }}
.modal-divider-text {{ font-size: 11px; color: #6D5EFC; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 700; }}
.social-btn {{
  display: flex; align-items: center; justify-content: center; gap: 10px;
  width: 100%; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px;
  font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.06); color: #ffffff !important;
  text-decoration: none !important;
}}
.social-btn:hover {{ background: rgba(255,255,255,0.12); border-color: rgba(109,94,252,0.5); transform: translateY(-1px); color: #ffffff !important; }}

/* Force the Streamlit Google button to match the LinkedIn button */
button[key="google_oauth_btn"] {{
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    height: 43px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    margin-bottom: 10px !important;
    width: 100% !important;
    transition: all 0.2s !important;
}}
button[key="google_oauth_btn"]:hover {{
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(109,94,252,0.5) !important;
    transform: translateY(-1px) !important;
}}
.auth-tab-row {{
  display: flex; gap: 6px; margin-bottom: 24px;
  background: rgba(0,0,0,0.3); border-radius: 10px; padding: 4px;
  border: 1px solid rgba(109,94,252,0.2);
}}
.auth-tab {{
  flex: 1; padding: 8px; border-radius: 8px; text-align: center;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #8BA6D3;
}}
.auth-tab.active {{ background: #6D5EFC; color: #ffffff; box-shadow: 0 4px 12px rgba(109,94,252,0.35); }}

/* Native Streamlit Inputs Override within Modal */
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="base-input"] {{
  background-color: rgba(255,255,255,0.06) !important;
  border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  transition: all 0.25s ease !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) div[data-baseweb="base-input"]:focus-within {{
  border-color: #6D5EFC !important;
  box-shadow: 0 0 0 2px rgba(109,94,252,0.3), 0 0 20px rgba(109,94,252,0.15) !important;
  background-color: rgba(109,94,252,0.08) !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) input {{ color: #ffffff !important; font-size: 15px !important; }}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) label p {{ color: #a0b4d0 !important; font-size: 13px !important; font-weight: 500 !important; }}

/* FIX: Ensure all Streamlit labels in dark mode are visible */
[data-testid="stWidgetLabel"] p, [data-testid="stCheckbox"] label p {{
    color: #ffffff !important;
    font-weight: 500 !important;
    opacity: 0.95 !important;
}}
/* Specifically target number input labels which tend to be dark */
.stNumberInput label p {{
    color: #ffffff !important;
    font-size: 14px !important;
    margin-bottom: 4px !important;
}}




/* Streamlit button overrides inside modal */
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="primary"] {{
  background: linear-gradient(135deg, #6D5EFC, #3BA4FF) !important;
  border: none !important;
  border-radius: 12px !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  box-shadow: 0 8px 24px rgba(109,94,252,0.4) !important;
  transition: all 0.2s !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="primary"]:hover {{
  transform: translateY(-2px) !important;
  box-shadow: 0 12px 32px rgba(109,94,252,0.5) !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="secondary"] {{
  background: rgba(255,255,255,0.05) !important;
  border: 1px solid rgba(255,255,255,0.15) !important;
  border-radius: 12px !important;
  color: #a0b4d0 !important;
}}
div[data-testid="stVerticalBlock"]:has(#auth-modal-marker) button[kind="secondary"]:hover {{
  background: rgba(255,255,255,0.1) !important;
  border-color: rgba(109,94,252,0.4) !important;
  color: #ffffff !important;
}}
.auth-switch {{
  text-align: center; font-size: 13px; color: {MUTED}; margin-top: 18px;
}}
.auth-switch span {{ color: {ACCENT2}; cursor: pointer; font-weight: 600; }}
.auth-error {{
  background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.3);
  border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;
  font-size: 13px; color: {NEG};
}}

/* ══ PAGE HERO ══ */
.page-hero {{
  padding: 52px 0 36px 0; text-align: center;
}}
.page-hero-title {{
  font-size: 42px; font-weight: 900; letter-spacing: -0.04em;
  background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT2} 60%, {ACCENT} 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 14px;
}}
.page-hero-sub {{
  font-size: 16px; color: {MUTED}; max-width: 560px; margin: 0 auto; line-height: 1.65;
}}

/* ══ HOME FEATURE GRID ══ */
.feat-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 18px; margin: 40px 0;
}}
.feat-card {{
  border: 1px solid {BORDER}; background: {PANEL}; border-radius: 18px;
  padding: 28px 24px; transition: all 0.22s; cursor: pointer;
  backdrop-filter: blur(16px);
}}
.feat-card:hover {{
  border-color: rgba(191,148,255,0.4);
  box-shadow: 0 16px 48px rgba(138,43,226,0.2);
  transform: translateY(-3px);
}}
.feat-icon {{ font-size: 32px; margin-bottom: 14px; }}
.feat-title {{ font-size: 16px; font-weight: 700; color: #ffffff; margin-bottom: 8px; }}
.feat-desc  {{ font-size: 13px; color: {MUTED}; line-height: 1.6; }}

/* ══ CARDS / PANELS ══ */
.card {{
  border: 1px solid {BORDER}; background: {PANEL};
  border-radius: 28px; padding: 28px; margin-bottom: 24px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.4);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(14px);
}}
.card:hover {{
  border-color: rgba(155, 114, 242, 0.4);
  box-shadow: 0 20px 60px rgba(155, 114, 242, 0.15);
  transform: translateY(-4px);
}}
.panel-title {{
  font-weight: 800; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.15em;
  color: {ACCENT2}; margin-bottom: 20px;
  border-left: 4px solid {ACCENT}; padding-left: 12px;
}}

/* ══ KPI GRID ══ */
.kpi-grid {{
  display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin: 14px 0;
}}
.kpi {{
  border: 1px solid {BORDER}; background: rgba(10,10,22,0.6);
  border-radius: 14px; padding: 14px 12px; transition: all 0.2s;
}}
.kpi:hover {{
  transform: translateY(-3px);
  border-color: rgba(191,148,255,0.5);
  box-shadow: 0 16px 40px rgba(138,43,226,0.18);
}}
.kpi-label {{ color:{MUTED}; font-size:9px; font-weight:800; text-transform:uppercase; letter-spacing:0.10em; margin-bottom:7px; }}
.kpi-value {{ font-family:'JetBrains Mono',monospace; font-size:19px; font-weight:800; color:#ffffff; }}
.kpi-hint  {{ color:rgba(230,213,255,0.35); font-size:9px; margin-top:7px; line-height:1.4; }}

/* ══ SURVEY ══ */
.survey-wrap {{
  max-width: 700px; margin: 0 auto; padding: 20px 0;
}}
.q-number {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  color: {ACCENT2}; margin-bottom: 6px; letter-spacing: 0.08em; text-transform: uppercase;
}}
.q-text {{
  font-size: 22px; font-weight: 700; color: #ffffff;
  margin-bottom: 6px; line-height: 1.35;
}}
.q-desc {{
  font-size: 13px; color: {MUTED}; margin-bottom: 20px; line-height: 1.6;
}}
.progress-bar-wrap {{
  background: rgba(138,43,226,0.12); border-radius: 99px;
  height: 4px; margin-bottom: 24px; overflow: hidden;
}}
.progress-bar-fill {{
  background: linear-gradient(90deg, {ACCENT}, {ACCENT2});
  height: 4px; border-radius: 99px; transition: width 0.4s ease;
}}

/* ══ PROFILE HERO ══ */
.profile-hero {{
  border: 1px solid {BORDER};
  background: linear-gradient(135deg, rgba(155, 114, 242, 0.22), rgba(11, 11, 26, 0.95));
  border-radius: 32px; padding: 40px; margin-bottom: 28px;
  box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 40px rgba(155, 114, 242, 0.15);
  position: relative; overflow: hidden;
}}
.profile-hero::after {{
    content: ""; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle, rgba(155, 114, 242, 0.05) 0%, transparent 70%);
    pointer-events: none;
}}
.profile-name {{ font-size: 32px; font-weight: 950; color: #ffffff; letter-spacing: -0.04em; margin-bottom: 12px; }}
.profile-desc {{ font-size: 14px; color: {MUTED}; line-height: 1.7; max-width: 820px; }}
.tag-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }}
.tag {{
  background: rgba(155, 114, 242, 0.15); border: 1px solid rgba(155, 114, 242, 0.3);
  border-radius: 99px; padding: 6px 18px; font-size: 12px;
  color: {ACCENT2}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
}}

/* ══ AI EXPLAIN SECTION ══ */
.ai-explain-box {{
  background: linear-gradient(135deg, rgba(138,43,226,0.10), rgba(10,10,30,0.85));
  border: 1px solid rgba(138,43,226,0.30);
  border-radius: 18px; padding: 28px 30px; margin-bottom: 16px;
}}
.ai-explain-header {{
  display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
}}
.ai-explain-icon {{
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2});
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}}
.ai-explain-title {{
  font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;
}}
.ai-explain-sub {{
  font-size: 12px; color: {MUTED};
}}
.ai-explain-para {{
  font-size: 14px; color: rgba(237,237,243,0.85);
  line-height: 1.75; margin-bottom: 14px;
  padding: 14px 18px; border-radius: 12px;
  background: rgba(255,255,255,0.03); border-left: 3px solid {ACCENT};
}}
.ai-explain-para:last-child {{ margin-bottom: 0; }}
.ai-explain-para b {{ color: {ACCENT2}; }}

/* ══ INSIGHTS ══ */
.insight-pos, .insight-neg {{
  border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; font-size: 14px;
}}
.insight-pos {{ background: rgba(74,227,160,0.08); border-left: 3px solid {POS}; }}
.insight-neg {{ background: rgba(255,107,107,0.08); border-left: 3px solid {NEG}; }}

/* ══ ETF TABLE ══ */
.etf-row {{
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid {BORDER}; font-size: 14px;
}}
.etf-name   {{ color: {ACCENT2}; font-weight: 600; }}
.etf-ticker {{ font-family: 'JetBrains Mono', monospace; color: {POS}; font-size: 12px; }}

/* ══ NEWS / MARKET PLACEHOLDERS ══ */
.coming-soon {{
  text-align: center; padding: 80px 20px;
}}
.coming-soon-icon {{ font-size: 56px; margin-bottom: 20px; }}
.coming-soon-title {{
  font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 10px;
}}
.coming-soon-sub {{ font-size: 15px; color: {MUTED}; }}
.market-card {{
  border: 1px solid {BORDER}; background: {PANEL}; border-radius: 14px;
  padding: 18px 20px; transition: all 0.2s;
}}
.market-card:hover {{ border-color: rgba(191,148,255,0.4); transform: translateY(-2px); }}
.market-ticker {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 700; color: {ACCENT2}; }}
.market-name   {{ font-size: 11px; color: {MUTED}; margin-top: 2px; }}
.market-price  {{ font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 800; color: #ffffff; margin-top: 8px; }}
.market-change-pos {{ font-size: 12px; color: {POS}; font-weight: 600; }}
.market-change-neg {{ font-size: 12px; color: {NEG}; font-weight: 600; }}

/* plotly modebar */
.js-plotly-plot .plotly .modebar {{ opacity: 0.15; }}
.js-plotly-plot:hover .plotly .modebar {{ opacity: 0.90; }}

/* radio styled like DeepIQ */
div[role='radiogroup'] > label {{
  border: 1px solid {BORDER}; border-radius: 12px; padding: 10px 18px;
  margin-bottom: 8px; cursor: pointer; transition: all 0.2s;
  background: rgba(255,255,255,0.02);
  color: #ffffff !important;
}}
div[role='radiogroup'] > label p {{
  color: #ffffff !important;
}}
div[role='radiogroup'] > label:hover {{
  border-color: rgba(191,148,255,0.5);
  background: rgba(138,43,226,0.08);
  color: #ffffff !important;
}}
div[role='radiogroup'] > label[data-checked="true"] {{
  border-color: rgba(191,148,255,0.7);
  background: rgba(138,43,226,0.15);
  color: #ffffff !important;
}}

/* primary button lilac */
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, {ACCENT}, {ACCENT2}) !important; border: none !important;
  border-radius: 14px !important; font-weight: 800 !important;
  font-size: 16px !important; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
  color: #ffffff !important; padding: 0.6rem 2rem !important;
  box-shadow: 0 10px 30px rgba(155, 114, 242, 0.3) !important;
}}
.stButton > button[kind="primary"]:hover {{
  transform: translateY(-3px) scale(1.02) !important;
  box-shadow: 0 15px 45px rgba(155, 114, 242, 0.5) !important;
}}
.stButton > button {{ 
  border-radius: 14px !important; font-weight: 600 !important; 
  background: rgba(155, 114, 242, 0.05) !important;
  border: 1px solid rgba(155, 114, 242, 0.2) !important;
  color: {TEXT} !important;
}}
.stButton > button:hover {{ border-color: {ACCENT} !important; background: rgba(155, 114, 242, 0.1) !important; }}

/* Custom Text Inputs */
div[data-baseweb="input"] {{
  background-color: rgba(20, 20, 35, 0.8) !important;
  border: 1px solid rgba(155,114,242,0.4) !important;
  border-radius: 8px !important;
}}
div[data-baseweb="input"] input {{
  color: #B18AFF !important;
  font-weight: 600 !important;
  -webkit-text-fill-color: #B18AFF !important;
}}
div[data-baseweb="input"]:focus-within {{
  border-color: #B18AFF !important;
  box-shadow: 0 0 0 1px #B18AFF !important;
}}
/* ══ RICH TOOLTIP POPOVER CARDS ══ */
.rich-tooltip {{
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}}
.rich-tooltip .tt-icon {{
  font-size: 13px;
  opacity: 0.6;
  transition: opacity 0.2s;
}}
.rich-tooltip:hover .tt-icon {{ opacity: 1; }}
.tooltip-text {{
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  position: absolute;
  bottom: calc(100% + 10px);
  left: 0;
  width: 300px;
  z-index: 9999;
  background: rgba(15, 15, 35, 0.97);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(109, 94, 252, 0.35);
  border-radius: 14px;
  padding: 14px 16px;
  font-size: 13px;
  font-weight: 400;
  color: #C8D6F0;
  line-height: 1.65;
  box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(109,94,252,0.1);
  transform: translateY(6px);
  transition: opacity 0.2s ease, transform 0.2s ease, visibility 0s linear 0.2s;
  white-space: normal;
  text-align: left;
}}
.tooltip-text::before {{
  content: "";
  position: absolute;
  bottom: -7px; left: 18px;
  width: 12px; height: 12px;
  background: rgba(15,15,35,0.97);
  border-right: 1px solid rgba(109,94,252,0.35);
  border-bottom: 1px solid rgba(109,94,252,0.35);
  transform: rotate(45deg);
}}
.tooltip-text .tt-header {{
  font-size: 11px; font-weight: 700; color: #6D5EFC;
  text-transform: uppercase; letter-spacing: .06em;
  margin-bottom: 6px;
  display: flex; align-items: center; gap: 5px;
}}
.rich-tooltip.tt-open .tooltip-text {{
  visibility: visible;
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  transition: opacity 0.2s ease, transform 0.2s ease;
}}

/* ══ EXPANDER (purple-glass) ══ */
details[data-testid="stExpander"] > summary {{
  background: rgba(109,94,252,0.08) !important;
  border: 1px solid rgba(109,94,252,0.3) !important;
  border-radius: 12px !important;
  padding: 12px 18px !important;
  color: #9B72F2 !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.02em !important;
}}
details[data-testid="stExpander"] > summary:hover {{
  background: rgba(109,94,252,0.15) !important;
  border-color: rgba(109,94,252,0.5) !important;
}}
details[data-testid="stExpander"][open] > summary {{
  border-radius: 12px 12px 0 0 !important;
  border-bottom-color: rgba(109,94,252,0.15) !important;
}}
details[data-testid="stExpander"] > div {{
  border: 1px solid rgba(109,94,252,0.3) !important;
  border-top: none !important;
  border-radius: 0 0 12px 12px !important;
  background: rgba(109,94,252,0.04) !important;
}}
</style>
<script>
(function(){{
  document.addEventListener('click', function(e){{
    var trigger = e.target.closest('.rich-tooltip');
    document.querySelectorAll('.rich-tooltip.tt-open').forEach(function(el){{
      if (el !== trigger) el.classList.remove('tt-open');
    }});
    if (trigger) trigger.classList.toggle('tt-open');
  }});
}})();
</script>
""", unsafe_allow_html=True)


def inject_global_css():
    """Call once at the top of app.py to apply the global theme."""
    pass  # CSS is already injected above at module import time via st.markdown
