import os
import hmac
import base64
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


def _data_uri(path: Path, mime: str) -> str:
    raw = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{raw}"


def credentials():
    try:
        username = st.secrets["auth"]["username"]
        password = st.secrets["auth"]["password"]
    except Exception:
        username = os.getenv("AMA_USERNAME", "admin")
        password = os.getenv("AMA_PASSWORD", "demo-Aviation-2026")
    return str(username), str(password)


def require_login():
    if st.session_state.get("authenticated", False):
        return True

    lang_col, theme_col, _ = st.columns([1.1, 1.2, 3.7])
    with lang_col:
        lang_choice = st.selectbox(
            "LANGUAGE / LANGUE",
            ["Français", "English", "العربية", "Español"],
            index={"fr": 0, "en": 1, "ar": 2, "es": 3}.get(st.session_state.get("ama_language", "fr"), 0),
            key="login_language_choice"
        )
        lang_code = {"Français": "fr", "English": "en", "العربية": "ar", "Español": "es"}[lang_choice]
        if lang_code != st.session_state.get("ama_language", "fr"):
            st.session_state.ama_language = lang_code
            st.rerun()
    lang = st.session_state.get("ama_language", "fr")
    copy = {
      "fr": {"kicker":"AIRCRAFT MAINTENANCE · ENGINEERING INTELLIGENCE","headline":"Au-delà du<br/><span>hangar.</span>",
             "intro":"Une lecture technique de la performance flotte, de la fiabilité et des opérations de maintenance.",
             "mission":"MISSION CONTROL / DONNÉES DE MAINTENANCE","manifesto":"Chaque intervention<br/>raconte une histoire.",
             "manifesto_p":"Explore les ordres de travail, détecte les tendances et transforme les données de maintenance en décisions mieux documentées.",
             "access":"ACCÈS À L’ESPACE ANALYTIQUE","login":"Connexion sécurisée","login_p":"Identifie-toi pour accéder au centre d'analyse.",
             "username":"Nom d’utilisateur","password":"Mot de passe","enter":"Entrer dans le cockpit  →",
             "bad":"Identifiants incorrects. Vérifie le nom d’utilisateur et le mot de passe.",
             "security":"◈ SESSION PROTÉGÉE · ACCÈS DE DÉMONSTRATION",
             "demo":"Accès de démonstration local. Configure des identifiants forts via st.secrets ou les variables AMA_USERNAME / AMA_PASSWORD avant tout déploiement.",
             "theme":"Thème"},
      "en": {"kicker":"AIRCRAFT MAINTENANCE · ENGINEERING INTELLIGENCE","headline":"Beyond the<br/><span>hangar floor.</span>",
             "intro":"A technical view of fleet performance, reliability and maintenance operations.",
             "mission":"MISSION CONTROL / MAINTENANCE DATA","manifesto":"Every intervention<br/>tells a story.",
             "manifesto_p":"Explore work orders, identify trends and turn maintenance data into better-informed decisions.",
             "access":"ANALYTICS WORKSPACE ACCESS","login":"Secure sign in","login_p":"Sign in to access the analytics center.",
             "username":"Username","password":"Password","enter":"Enter the cockpit  →",
             "bad":"Incorrect credentials. Check your username and password.",
             "security":"◈ PROTECTED SESSION · DEMO ACCESS",
             "demo":"Local demo access. Configure strong credentials through st.secrets or AMA_USERNAME / AMA_PASSWORD before deployment.",
             "theme":"Theme"},
      "ar": {"kicker":"صيانة الطائرات · الذكاء الهندسي","headline":"ما وراء<br/><span>الحظيرة.</span>",
             "intro":"رؤية تقنية لأداء الأسطول والموثوقية وعمليات الصيانة.",
             "mission":"مركز التحكم / بيانات الصيانة","manifesto":"كل عملية صيانة<br/>تحكي قصة.",
             "manifesto_p":"استكشف أوامر العمل، واكتشف الاتجاهات، وحوّل بيانات الصيانة إلى قرارات مدروسة.",
             "access":"الدخول إلى مساحة التحليلات","login":"تسجيل دخول آمن","login_p":"سجّل الدخول للوصول إلى مركز التحليل.",
             "username":"اسم المستخدم","password":"كلمة المرور","enter":"الدخول إلى قمرة القيادة ←",
             "bad":"بيانات الدخول غير صحيحة. تحقق من اسم المستخدم وكلمة المرور.",
             "security":"◈ جلسة محمية · وصول تجريبي",
             "demo":"وصول تجريبي محلي. اضبط بيانات اعتماد قوية عبر st.secrets أو متغيرات AMA_USERNAME / AMA_PASSWORD قبل النشر.",
             "theme":"المظهر"},
      "es": {"kicker":"MANTENIMIENTO DE AERONAVES · INTELIGENCIA TÉCNICA","headline":"Más allá del<br/><span>hangar.</span>",
             "intro":"Una visión técnica del rendimiento de la flota, la fiabilidad y las operaciones de mantenimiento.",
             "mission":"CENTRO DE CONTROL / DATOS DE MANTENIMIENTO","manifesto":"Cada intervención<br/>cuenta una historia.",
             "manifesto_p":"Explora las órdenes de trabajo, identifica tendencias y convierte los datos de mantenimiento en decisiones mejor fundamentadas.",
             "access":"ACCESO AL ESPACIO ANALÍTICO","login":"Acceso seguro","login_p":"Identifícate para acceder al centro de análisis.",
             "username":"Usuario","password":"Contraseña","enter":"Entrar al cockpit  →",
             "bad":"Credenciales incorrectas. Comprueba el usuario y la contraseña.",
             "security":"◈ SESIÓN PROTEGIDA · ACCESO DE DEMOSTRACIÓN",
             "demo":"Acceso de demostración local. Configura credenciales seguras mediante st.secrets o AMA_USERNAME / AMA_PASSWORD antes del despliegue.",
             "theme":"Tema"}
    }[lang]
    if lang == "ar":
        st.markdown("<style>.main .block-container{direction:rtl;text-align:right}.login-manifesto,.login-panel-top{text-align:right}</style>", unsafe_allow_html=True)
    theme_col, _ = st.columns([1.2, 4.8])
    with theme_col:
        choice = st.selectbox(
            copy["theme"], (["Dark cockpit", "Light hangar"] if lang == "en" else (["Dark cockpit", "Hangar clair"] if lang == "fr" else ["Cockpit oscuro", "Hangar claro"])),
            index=0 if st.session_state.get("ama_theme", "dark") == "dark" else 1,
            key="login_theme_choice", label_visibility="collapsed"
        )
        selected_theme = "dark" if choice in ("Dark cockpit", "Cockpit oscuro") else "light"
        if selected_theme != st.session_state.get("ama_theme", "dark"):
            st.session_state.ama_theme = selected_theme
            st.rerun()


    logo = _data_uri(ROOT / "assets" / "ama_logo.svg", "image/svg+xml")
    login_photo = _data_uri(ROOT / "assets" / "hangar_hero.jpg", "image/jpeg")
    st.markdown(f"""
    <section class="login-hero" style="background-image:linear-gradient(110deg,rgba(5,16,31,.93) 0%,rgba(5,16,31,.78) 58%,rgba(5,16,31,.60) 100%),url('{login_photo}')">
      <div class="login-hero-content">
        <img class="login-logo" src="{logo}" alt="AERONEX logo" />
        <div class="login-kicker">{copy["kicker"]}</div>
        <h1>{copy["headline"]}</h1>
        <p>{copy["intro"]}</p>
        <div class="login-tags"><span>FLEET MONITORING</span><span>ATA ANALYTICS</span><span>RELIABILITY</span></div>
      </div>
      <div class="login-hero-index">AERONEX / 01 — MAINTENANCE INTELLIGENCE</div>
    </section>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.markdown(f"""
        <div class="login-manifesto">
          <div class="manifesto-line"></div>
          <div class="eyebrow">{copy["mission"]}</div>
          <h2>{copy["manifesto"]}</h2>
          <p>{copy["manifesto_p"]}</p>
          <div class="login-stat-strip">
            <div><strong>AERONEX</strong><small>PLATFORM</small></div>
            <div><strong>ATA</strong><small>ANALYTICS</small></div>
            <div><strong>LIVE</strong><small>CSV-DRIVEN</small></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown("<div class='login-panel-top'><span class='status-pulse'></span> ACCÈS À L’ESPACE ANALYTIQUE</div>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            st.markdown(f"### {copy['login']}")
            st.caption(copy["login_p"])
            username = st.text_input(copy["username"], placeholder="Ex. admin")
            password = st.text_input(copy["password"], type="password", placeholder="••••••••••")
            submitted = st.form_submit_button(copy["enter"], use_container_width=True)
        if submitted:
            valid_user, valid_password = credentials()
            if hmac.compare_digest(username, valid_user) and hmac.compare_digest(password, valid_password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error(copy["bad"])
        st.markdown(f"<div class='login-security'>{copy['security']}</div>", unsafe_allow_html=True)
        st.caption(copy["demo"])
    st.markdown("<div class='login-footer'>AERONEX — AIRCRAFT MAINTENANCE INTELLIGENCE <span>·</span> DESIGNED FOR AVIATION DATA</div>", unsafe_allow_html=True)
    return False
