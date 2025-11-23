import streamlit as st
from duckduckgo_search import DDGS
from groq import Groq
import time
from datetime import datetime
import random
import re

# ==============================================================================
# 🔒 GÜVENLİK: API ANAHTARI
# ==============================================================================
try:
    SABIT_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    SABIT_API_KEY = "" 

# ---------------------------------------------------------
# 1. SAYFA AYARLARI (Menüyü Zorla Açıyoruz)
# ---------------------------------------------------------
st.set_page_config(
    page_title="TruthSocial", 
    page_icon="🦅", 
    layout="wide",
    initial_sidebar_state="expanded" # BU ÇOK ÖNEMLİ: Menü açık başlasın
)

# ---------------------------------------------------------
# 🛑 TASARIM DÜZELTME (Menü Düğmesi Geri Geldi)
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* SAĞ ÜSTTEKİ BUTONLARI GİZLE (Github, Deploy, Manage App) */
    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    
    /* EN ÜSTTEKİ RENKLİ ÇİZGİYİ GİZLE */
    [data-testid="stDecoration"] {
        visibility: hidden;
        display: none;
    }

    /* FOOTER GİZLE */
    footer {
        visibility: hidden;
        display: none;
    }

    /* NOT: .stAppHeader'ı gizlemiyoruz, çünkü menü düğmesi orada yaşıyor! */
    
    .main-title { color: #2c3e50; text-align: center; font-size: 3rem; font-weight: 800; letter-spacing: -1px; }
    
    /* DİĞER STİLLER */
    .trust-score-box { font-size: 1.5rem; font-weight: bold; color: white; background-color: #28a745; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .source-card { background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 5px solid #0078D4; }
    .source-link { text-decoration: none; color: #0078D4; font-weight: bold; }
    .blur-container { position: relative; }
    .blurred-text { color: transparent; text-shadow: 0 0 8px rgba(0,0,0,0.5); user-select: none; }
    .login-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: rgba(255, 255, 255, 0.95); padding: 10px 20px; border-radius: 20px; border: 2px solid #FF4B4B; font-weight: bold; color: #FF4B4B; text-align: center; cursor: pointer; width: 80%; }
    .score-label { color: #28a745; font-weight: bold; font-size: 0.85rem; margin-right: 5px; }
    .score-blur { color: transparent; text-shadow: 0 0 5px #999; cursor: not-allowed; background-color: #eee; padding: 2px 5px; border-radius: 5px; user-select: none; }
    .score-visible { color: #fff; background-color: #28a745; font-weight: bold; font-size: 0.8rem; padding: 2px 8px; border-radius: 10px; }
    .forum-card { background-color: #fff; padding: 15px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. HAFIZA VE VERİTABANI
# ---------------------------------------------------------
if 'giris_yapti' not in st.session_state: st.session_state['giris_yapti'] = False
if 'aktif_kullanici' not in st.session_state: st.session_state['aktif_kullanici'] = None
if 'premium_uye' not in st.session_state: st.session_state['premium_uye'] = False

if 'kullanici_db' not in st.session_state:
    st.session_state['kullanici_db'] = {
        "admin@test.com": {"sifre": "1234", "ad": "Yönetici", "premium": True, "puan": 9.9},
        "uye@test.com":   {"sifre": "1234", "ad": "Ahmet", "premium": False, "puan": 7.5}
    }

if 'forum_konulari' not in st.session_state:
    st.session_state['forum_konulari'] = [
        {
            "id": 1,
            "baslik": "Mars'ta bulunan kemiklerin sırrı çözüldü mü?",
            "ozet": "NASA'nın son yayınladığı fotoğraflarda görülen kemik benzeri yapılar...",
            "icerik": "NASA'nın son yayınladığı fotoğraflarda görülen kemik benzeri yapılar aslında sadece rüzgar erozyonu ile oluşmuş kayalardır.",
            "yazar": "Mehmet Y.", "yazar_puan": 8.7,
            "yorumlar": [{"user": "Ali", "puan": 6.5, "msg": "Ben inanmıyorum!"}]
        },
        {
            "id": 2,
            "baslik": "Doların seyri ne olacak? Yapay zeka analizi.",
            "ozet": "Ekonomik veriler ve küresel piyasalar incelendiğinde...",
            "icerik": "Ekonomik veriler ve küresel piyasalar incelendiğinde önümüzdeki ay için dalgalı bir seyir bekleniyor. Özellikle FED kararları bu süreçte belirleyici olacak.",
            "yazar": "EkoAnaliz", "yazar_puan": 9.5,
            "yorumlar": []
        }
    ]

# ---------------------------------------------------------
# 3. FONKSİYONLAR
# ---------------------------------------------------------
def internette_ara(sorgu):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(sorgu, region='tr-tr', max_results=5))
        return results
    except Exception as e:
        return []

def teyit_et(iddia, veriler, api_key, ton):
    client = Groq(api_key=api_key)

    if "Eğlenceli" in ton: rol = "Sen neşeli, esprili ve emoji kullanan birisin."
    elif "Samimi" in ton: rol = "Sen kullanıcının kankasısın."
    elif "Ağzı Bozuk" in ton: rol = "Sen çok kaba, sokak ağzıyla konuşan, 'lan', 'oğlum' diyen, atarlı birisin. Asla kibar olma."
    else: rol = "Sen ciddi ve profesyonel bir haber spikesisin."

    prompt = f"""
    KARAKTERİN: {rol}
    GÖREVİN: İddiayı, Arama Sonuçlarına göre analiz et.
    KURALLAR:
    1. Arama sonuçlarında konuyla alakasız (oyun, reklam) şeyler varsa YOK SAY.
    2. Cevabın en başına mutlaka "GÜVEN ORANI: %XX" yaz (0-100 arası).
    
    İDDİA: {iddia}
    ARAMA SONUÇLARI: {veriler}
    """
    
    try:
        res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
        return res.choices[0].message.content
    except:
        return "GÜVEN ORANI: %0\n\nBir hata oluştu. API anahtarı 'Secrets' kısmına eklenmemiş olabilir."

# ---------------------------------------------------------
# 4. YAN MENÜ
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    if st.session_state['giris_yapti']:
        st.success(f"👤 {st.session_state['aktif_kullanici']}")
        if st.session_state['premium_uye']: st.warning("💎 Premium Hesap")
        else:
            st.info("Standart Hesap")
            if st.button("💎 Premium Al (Simüle)"): st.session_state['premium_uye'] = True; st.rerun()
        
        if len(SABIT_API_KEY) > 20: api_key = SABIT_API_KEY
        else: api_key = st.text_input("API Key (Manuel)", type="password")
        
        if st.button("Çıkış Yap"): st.session_state['giris_yapti'] = False; st.rerun()
    else:
        st.info("Tam erişim için giriş yapın.")
        tab_giris, tab_kayit = st.tabs(["Giriş", "Kayıt"])
        with tab_giris:
            email = st.text_input("E-Posta", key="l_mail")
            sifre = st.text_input("Şifre", type="password", key="l_pass")
            if st.button("Giriş Yap"):
                user = st.session_state['kullanici_db'].get(email)
                if user and user['sifre'] == sifre:
                    st.session_state['giris_yapti'] = True; st.session_state['aktif_kullanici'] = user['ad']; st.session_state['premium_uye'] = user['premium']; st.rerun()
                else: st.error("Hatalı!")
        with tab_kayit:
            ad = st.text_input("İsim", key="r_name")
            mail = st.text_input("Mail", key="r_mail")
            pas = st.text_input("Şifre", key="r_pass")
            if st.button("Kayıt Ol"): st.session_state['kullanici_db'][mail] = {"sifre": pas, "ad": ad, "premium": False, "puan": 5.0}; st.success("Kayıt olundu!")

# ---------------------------------------------------------
# 5. ANA EKRAN
# ---------------------------------------------------------
st.markdown('<div class="main-title">TruthSocial</div>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["🕵️‍♂️ Haber Doğrulama", "🗣️ Gerçekler Forumu"])

# --- TAB 1: HABER DOĞRULAMA ---
with tab1:
    st.subheader("Hızlı Doğrulama")
    col_input, col_opts = st.columns([3, 1])
    with col_input:
        sorgu = st.text_area("Haber/İddia:", height=120, placeholder="Örn: Son F1 yarışında kim kazandı?")
    with col_opts:
        st.write("🗣️ **Konuşma Şekli**")
        if st.session_state['premium_uye']:
            secenekler = ["Ciddi", "Eğlenceli", "Samimi", "Ağzı Bozuk (Argo)"]
        else:
            secenekler = ["Ciddi", "🔒 Eğlenceli (Premium)", "🔒 Samimi (Premium)", "🔒 Ağzı Bozuk (Premium)"]
        secilen_ton_raw = st.selectbox("Tarz Seç:", secenekler, index=0)

    if st.button("Gerçeği Bul", type="primary", use_container_width=True):
        kullanilacak_key = SABIT_API_KEY if len(SABIT_API_KEY) > 20 else None
        if not kullanilacak_key and st.session_state['giris_yapti']: kullanilacak_key = api_key
             
        if not kullanilacak_key or "BURAYA" in kullanilacak_key:
            st.error("API Anahtarı bulunamadı! 'Secrets' ayarlarını kontrol et.")
        else:
            if "🔒" in secilen_ton_raw:
                st.toast("⛔ Bu mod sadece PREMIUM üyeler içindir! Ciddi mod kullanılıyor.", icon="🔒")
                final_ton = "Ciddi"
            else:
                final_ton = secilen_ton_raw

            with st.spinner(f"Son dakika haberleri taranıyor..."):
                res = internette_ara(sorgu)
                if not res:
                    st.warning("⚠️ Bu konuda henüz haber ajanslarına düşen bir bilgi yok.")
                    raw_cevap = teyit_et(sorgu, "Güncel haber bulunamadı.", kullanilacak_key, final_ton)
                else:
                    raw_cevap = teyit_et(sorgu, res, kullanilacak_key, final_ton)
                
                match = re.search(r"GÜVEN ORANI: %(\d+)", raw_cevap)
                skor = match.group(1) if match else "?"
                temiz_cevap = re.sub(r"GÜVEN ORANI: %\d+", "", raw_cevap).strip()
                
                if skor != "?":
                    color = "#28a745" if int(skor) > 70 else "#dc3545"
                    st.markdown(f'<div class="trust-score-box" style="background-color:{color}">Güvenirlik: %{skor}</div>', unsafe_allow_html=True)
                
                st.success("Analiz Sonucu:")
                st.write(temiz_cevap)
                
                with st.expander("🔗 Bulunan Kaynaklar (Tıkla ve Git)"):
                    if res:
                        for item in res:
                            baslik = item.get('title', 'Kaynak Bağlantısı')
                            link = item.get('url', item.get('href', '#'))
                            kaynak_tarih = item.get('date', '')
                            st.markdown(f"""
                            <div class="source-card">
                                <a href="{link}" target="_blank" class="source-link">{baslik}</a><br>
                                <small>{kaynak_tarih}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.write("Kaynak bulunamadı.")

# --- TAB 2: GERÇEKLER FORUMU ---
with tab2:
    st.subheader("Gündem")
    for konu in st.session_state['forum_konulari']:
        with st.expander(f"📢 {konu['baslik']}"):
            if st.session_state['premium_uye']:
                puan_html = f"<span class='score-label'>Güvenirlik Puanı:</span> <span class='score-visible'>{konu['yazar_puan']}/10</span>"
            else:
                puan_html = "<span class='score-label'>Güvenirlik Puanı:</span> <span class='score-blur' title='Puanı görmek için Premium ol'>XX.X</span>"
            st.markdown(f"<small>Yazar: {konu['yazar']} | {puan_html}</small>", unsafe_allow_html=True)
            
            if st.session_state['giris_yapti']:
                st.write(konu['icerik'])
                st.markdown("---")
                for yorum in konu['yorumlar']:
                    if st.session_state['premium_uye']:
                        y_puan = f"<span class='score-visible'>{yorum.get('puan', 5.0)}/10</span>"
                    else:
                        y_puan = "<span class='score-blur' title='Premium Gerekli'>XX.X</span>"
                    st.markdown(f"**{yorum['user']}** {y_puan}: {yorum['msg']}", unsafe_allow_html=True)
                yeni = st.text_input("Yorum:", key=f"t_{konu['id']}")
                if st.button("Gönder", key=f"b_{konu['id']}"):
                    konu['yorumlar'].append({"user": st.session_state['aktif_kullanici'], "msg": yeni, "puan": 5.0})
                    st.success("Gönderildi")
                    time.sleep(0.5); st.rerun()
            else:
                st.write(konu['ozet'])
                st.markdown(f"""
                    <div class="blur-container">
                        <div class="blurred-text">Gizli içerik. Giriş yapın. Lorem ipsum dolor sit amet.</div>
                        <div class="login-overlay">🔒 GİRİŞ YAPIN</div>
                    </div>
                """, unsafe_allow_html=True)
