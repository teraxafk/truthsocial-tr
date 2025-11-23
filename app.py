import streamlit as st
from duckduckgo_search import DDGS
from groq import Groq
import time
from datetime import datetime
import random
import re

# ==============================================================================
try:
    SABIT_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    SABIT_API_KEY = ""
# ==============================================================================

# ---------------------------------------------------------
# 1. SAYFA AYARLARI (İsim Güncellendi)
# ---------------------------------------------------------
st.set_page_config(page_title="TruthSocial", page_icon="⚖️", layout="wide")

# ---------------------------------------------------------
# 2. HAFIZA VE VERİTABANI
# ---------------------------------------------------------
if 'giris_yapti' not in st.session_state: st.session_state['giris_yapti'] = False
if 'aktif_kullanici' not in st.session_state: st.session_state['aktif_kullanici'] = None
if 'premium_uye' not in st.session_state: st.session_state['premium_uye'] = False

# Kullanıcılar
if 'kullanici_db' not in st.session_state:
    st.session_state['kullanici_db'] = {
        "admin@test.com": {"sifre": "1234", "ad": "Yönetici", "premium": True, "puan": 9.9},
        "uye@test.com":   {"sifre": "1234", "ad": "Ahmet", "premium": False, "puan": 7.5} 
    }

# Forum Verileri (Puanlar Eklendi)
if 'forum_konulari' not in st.session_state:
    st.session_state['forum_konulari'] = [
        {
            "id": 1,
            "baslik": "Formula 1 Las Vegas GP Kaosu!",
            "ozet": "Yarışta beklenmedik diskalifiyeler ve kazalar gündem oldu...",
            "icerik": "Las Vegas GP'sinde yaşanan olaylar şampiyonayı karıştırdı. Norris ve Piastri'nin durumları hakkında FIA'dan son dakika açıklaması geldi.",
            "yazar": "SporEditörü",
            "yazar_puan": 9.8,
            "yorumlar": [{"user": "F1_Fan", "puan": 8.4, "msg": "İnanılmaz bir yarıştı!"}]
        },
        {
            "id": 2,
            "baslik": "Ekonomide Faiz Kararı Beklentisi",
            "ozet": "Merkez bankasının yarınki toplantısından beklentiler...",
            "icerik": "Piyasalar yarınki faiz kararına kilitlendi. Uzmanlar pas geçilmesini beklerken, döviz kurundaki hareketlilik endişe yaratıyor.",
            "yazar": "EkoAnaliz",
            "yazar_puan": 9.2,
            "yorumlar": []
        }
    ]

# ---------------------------------------------------------
# 3. TASARIM (CSS - Yeni Blur Efektleri)
# ---------------------------------------------------------
st.markdown("""
    <style>
    .main-title { color: #2c3e50; text-align: center; font-size: 3rem; font-weight: 800; letter-spacing: -1px; }
    
    /* GÜVEN SKORU KUTUSU */
    .trust-score-box {
        font-size: 1.5rem; font-weight: bold; color: white; 
        background-color: #28a745; padding: 10px; border-radius: 10px; 
        text-align: center; margin-bottom: 10px;
    }
    
    /* FORUM BLUR EFEKTLERİ (İÇERİK) */
    .blur-container { position: relative; }
    .blurred-text { color: transparent; text-shadow: 0 0 8px rgba(0,0,0,0.5); user-select: none; }
    .login-overlay {
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background-color: rgba(255, 255, 255, 0.95); padding: 10px 20px;
        border-radius: 20px; border: 2px solid #FF4B4B; font-weight: bold; color: #FF4B4B;
        text-align: center; cursor: pointer; width: 80%;
    }
    
    /* PUAN BLURLAMA (Premium Olmayanlar İçin) */
    .score-blur {
        color: transparent; text-shadow: 0 0 5px #000; cursor: help;
        background-color: #eee; padding: 2px 5px; border-radius: 5px;
    }
    .score-visible {
        color: #28a745; font-weight: bold; font-size: 0.9rem; 
        border: 1px solid #28a745; padding: 2px 6px; border-radius: 5px;
    }
    
    .forum-card { background-color: #fff; padding: 15px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------
def internette_ara(sorgu):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(sorgu, region='tr-tr', timelimit='d', max_results=3))
    except:
        return []

def teyit_et(iddia, veriler, api_key, ton):
    client = Groq(api_key=api_key)
    
    # TON AYARLARI (Persona)
    if ton == "Eğlenceli":
        rol = "Sen çok neşeli, esprili ve emoji kullanan birisin."
    elif ton == "Samimi":
        rol = "Sen kullanıcının en yakın arkadaşı gibisin, 'kanka', 'hocam' gibi hitaplar kullan."
    elif ton == "Ağzı Bozuk (Argo)":
        rol = "Sen sokak ağzıyla konuşan, lafını esirgemeyen, kaba, argo kullanan ve atarlı giderli birisin. Asla resmi konuşma. 'Lan', 'Oğlum', 'Saçmalama' gibi kelimeler kullanabilirsin."
    else:
        rol = "Sen çok ciddi, kurumsal ve sadece gerçeklere odaklanan bir spikersin."

    prompt = f"""
    KARAKTERİN: {rol}
    
    GÖREVİN: Aşağıdaki iddiayı ve arama sonuçlarını incele.
    
    KURALLAR:
    1. Cevabının EN BAŞINA mutlaka güvenirlik oranını şu formatta yaz: "GÜVEN ORANI: %XX" (XX yerine 0-100 arası sayı).
    2. Sonra kendi karakterine uygun şekilde yorumunu yap.
    3. Kaynaklara sadık kal.
    
    İDDİA: {iddia}
    ARAMA SONUÇLARI: {veriler}
    """
    
    res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
    return res.choices[0].message.content

# ---------------------------------------------------------
# 5. YAN MENÜ (GİRİŞ)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    
    if st.session_state['giris_yapti']:
        st.success(f"👤 {st.session_state['aktif_kullanici']}")
        if st.session_state['premium_uye']:
            st.warning("💎 Premium Hesap")
        else:
            st.info("Standart Hesap")
            if st.button("💎 Premium Al (Simüle)"):
                st.session_state['premium_uye'] = True
                st.rerun()

        if len(SABIT_API_KEY) > 20: api_key = SABIT_API_KEY
        else: api_key = st.text_input("API Key", type="password")
            
        if st.button("Çıkış Yap"):
            st.session_state['giris_yapti'] = False
            st.rerun()
    else:
        st.info("Tam erişim için giriş yapın.")
        tab_giris, tab_kayit = st.tabs(["Giriş", "Kayıt"])
        with tab_giris:
            email = st.text_input("E-Posta", key="login_mail")
            sifre = st.text_input("Şifre", type="password", key="login_pass")
            if st.button("Giriş Yap"):
                user = st.session_state['kullanici_db'].get(email)
                if user and user['sifre'] == sifre:
                    st.session_state['giris_yapti'] = True
                    st.session_state['aktif_kullanici'] = user['ad']
                    st.session_state['premium_uye'] = user['premium']
                    st.rerun()
                else: st.error("Hatalı!")

        with tab_kayit:
            ad = st.text_input("İsim", key="reg_name")
            mail = st.text_input("Mail", key="reg_mail")
            pas = st.text_input("Şifre", key="reg_pass")
            if st.button("Kayıt Ol"):
                st.session_state['kullanici_db'][mail] = {"sifre": pas, "ad": ad, "premium": False, "puan": 5.0}
                st.success("Kayıt olundu!")

# ---------------------------------------------------------
# 6. ANA EKRAN
# ---------------------------------------------------------

st.markdown('<div class="main-title">TruthSocial</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🕵️‍♂️ Gerçek Dedektifi", "🗣️ Forum"])

# --- TAB 1: HABER DOĞRULAMA (TON SEÇİMİ EKLENDİ) ---
with tab1:
    st.subheader("Haber Doğrulama")
    
    # Layout: Haber girişi + Buton + Ton Seçimi yan yana
    col_input, col_opts = st.columns([3, 1])
    
    with col_input:
        sorgu = st.text_area("Haber/İddia:", height=120, placeholder="Örn: Las Vegas GP iptal mi oldu?")
    
    with col_opts:
        st.write("🗣️ **Konuşma Şekli**")
        secenekler = ["Ciddi", "Eğlenceli", "Samimi", "Ağzı Bozuk (Argo)"]
        
        # Premium Kontrolü: Eğer Premium DEĞİLSE, seçim yapsa bile uyaracağız.
        secilen_ton = st.selectbox("Tarz Seç:", secenekler, index=0)
        
        # Kilit Görseli (Eğer premium değilse)
        if not st.session_state['premium_uye']:
            st.caption("🔒 Diğer modlar kilitli")

    if st.button("Gerçeği Bul", type="primary", use_container_width=True):
        # API Key Belirle
        kullanilacak_key = SABIT_API_KEY if len(SABIT_API_KEY) > 20 else None
        if not kullanilacak_key and st.session_state['giris_yapti']: kullanilacak_key = api_key
             
        if not kullanilacak_key or "BURAYA" in kullanilacak_key:
            st.error("API Anahtarı eksik!")
        else:
            # TON KONTROLÜ (PREMIUM TUZAĞI)
            final_ton = "Ciddi" # Varsayılan
            if secilen_ton != "Ciddi" and not st.session_state['premium_uye']:
                st.toast("⛔ Eğlenceli modlar sadece PREMIUM üyeler içindir! Ciddi moda dönüldü.", icon="🔒")
                final_ton = "Ciddi"
            else:
                final_ton = secilen_ton

            with st.spinner(f"Aranıyor... Mod: {final_ton}"):
                res = internette_ara(sorgu)
                if not res:
                    st.warning("Veri bulunamadı.")
                else:
                    raw_cevap = teyit_et(sorgu, res, kullanilacak_key, final_ton)
                    
                    # Güven Skorunu Ayıklama (Regex)
                    match = re.search(r"GÜVEN ORANI: %(\d+)", raw_cevap)
                    skor = match.group(1) if match else "?"
                    temiz_cevap = re.sub(r"GÜVEN ORANI: %\d+", "", raw_cevap).strip()
                    
                    # Skoru Göster
                    if skor != "?":
                        st.markdown(f'<div class="trust-score-box">Güvenirlik: %{skor}</div>', unsafe_allow_html=True)
                    
                    st.success("Analiz Sonucu:")
                    st.write(temiz_cevap)

# --- TAB 2: FORUM (PUAN VE BLUR SİSTEMİ) ---
with tab2:
    st.subheader("Gündem")
    
    for konu in st.session_state['forum_konulari']:
        with st.expander(f"📢 {konu['baslik']}"):
            
            # YAZAR PUANI GÖSTERİMİ
            if st.session_state['premium_uye']:
                puan_html = f"<span class='score-visible'>{konu['yazar_puan']}/10</span>"
            else:
                puan_html = "<span class='score-blur' title='Puanı görmek için Premium ol'>XX.X</span>"
            
            st.markdown(f"<small>Yazar: {konu['yazar']} {puan_html}</small>", unsafe_allow_html=True)
            
            # GİRİŞ YAPANLAR
            if st.session_state['giris_yapti']:
                st.write(konu['icerik']) 
                st.markdown("---")
                
                # YORUMLAR
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

            # MİSAFİRLER
            else:
                st.write(konu['ozet']) 
                st.markdown(f"""
                    <div class="blur-container">
                        <div class="blurred-text">Gizli içerik. Giriş yapın. Lorem ipsum dolor sit amet.</div>
                        <div class="login-overlay">🔒 GİRİŞ YAPIN</div>
                    </div>
                """, unsafe_allow_html=True)