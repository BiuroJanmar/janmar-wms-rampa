import streamlit as st
import random
import qrcode
import requests
import json
from datetime import datetime
from io import BytesIO
from streamlit_drawable_canvas import st_canvas
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Importy do generowania PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# KONFIGURACJA POŁĄCZENIA FIREBASE
FIREBASE_BASE_URL = "https://janmar-kalkulator-default-rtdb.europe-west1.firebasedatabase.app"
FIREBASE_URL = f"{FIREBASE_BASE_URL}/janmar_wms_rampa.json"
FIREBASE_KONTRAHENCI_URL = f"{FIREBASE_BASE_URL}/janmar_wms_kontrahenci.json"
FIREBASE_PRACOWNICY_URL = f"{FIREBASE_BASE_URL}/janmar_wms_pracownicy.json"
FIREBASE_ASORTYMENT_URL = f"{FIREBASE_BASE_URL}/janmar_wms_asortyment.json"

st.set_page_config(page_title="Janmar WMS - Rampa", page_icon="📦", layout="centered")

# AUTORYZACJA GOOGLE DRIVE
def pobierz_google_drive_service():
    info = dict(st.secrets["gcp_service_account"])
    # Naprawa znaków nowej linii w kluczu prywatnym
    info["private_key"] = info["private_key"].replace("\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(info)
    scoped_credentials = credentials.with_scopes(['https://www.googleapis.com/auth/drive'])
    return build('drive', 'v3', credentials=scoped_credentials)

def przeslij_pdf_na_google_drive(file_bytes, file_name):
    try:
        service = pobierz_google_drive_service()
        
        # Szukanie folderu JANMAR_WMS_PZ_RAPORTY
        folder_id = None
        q = "mimeType='application/vnd.google-apps.folder' and name='JANMAR_WMS_PZ_RAPORTY' and trashed=false"
        results = service.files().list(q=q, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if items:
            folder_id = items[0]['id']
        else:
            file_metadata = {'name': 'JANMAR_WMS_PZ_RAPORTY', 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
        # Przesyłanie pliku do folderu
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(BytesIO(file_bytes), mime_type='application/pdf', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        # Uprawnienia widoczności dla każdego, kto ma link
        service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"❌ Błąd zapisu na Dysku Google: {e}")
        return None

if "autoryzowany" not in st.session_state:
    st.session_state["autoryzowany"] = False

if not st.session_state["autoryzowany"]:
    st.title("🏭 JANMAR WMS - PANEL RAMPOWY")
    st.write("---")
    haslo_input = st.text_input("Hasło dostępu:", type="password")
    if st.button("🔓 ZALOGUJ DO SYSTEMU"):
        if haslo_input == "Janmar2026":
            st.session_state["autoryzowany"] = True
            st.rerun()
        else:
            st.error("❌ Błędne hasło!")
    st.stop()

st.markdown("""
    <style>
    html, body, [data-testid="stWidgetLabel"] p { font-size: 20px !important; font-weight: 600 !important; }
    .stButton>button { width: 100% !important; height: 70px !important; font-size: 22px !important; font-weight: bold !important; border-radius: 12px !important; margin-bottom: 10px !important; }
    div[data-testid="stNumberInput"] input { font-size: 24px !important; height: 55px !important; font-weight: bold !important; }
    div[data-testid="stTextInput"] input { font-size: 22px !important; height: 55px !important; }
    .status-box { padding: 20px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 24px; color: white; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 JANMAR WMS - PANEL PRZYJĘCIA v2.4 ☁️")
st.write("---")

def pobierz_slownik_firebase(url, domyslny_slownik):
    try:
        res = requests.get(url)
        if res.status_code == 200 and res.json():
            return res.json()
        else:
            requests.put(url, data=json.dumps(domyslny_slownik))
            return domyslny_slownik
    except:
        return domyslny_slownik

DOMYSLNI_DOSTAWCY = {
    "JAN-11199": {"nazwa": "MARCIN PRZEWORSKI", "tel": "601234567"},
    "JAN-10023": {"nazwa": "AGRO-HURT JANUSZ", "tel": "601234567"}
}
DOMYSLNI_PRACOWNICY = {"M-01": "Zbigniew Tkaczyk", "M-02": "Jan Kowalski"}
DOMYSLNY_ASORTYMENT = {"A-01": "ARBUZ LUZ", "A-02": "ZIEMNIAK LUZ"}

baza_dostawcow = pobierz_slownik_firebase(FIREBASE_KONTRAHENCI_URL, DOMYSLNI_DOSTAWCY)
baza_pracownikow = pobierz_slownik_firebase(FIREBASE_PRACOWNICY_URL, DOMYSLNI_PRACOWNICY)
baza_asortymentu = pobierz_slownik_firebase(FIREBASE_ASORTYMENT_URL, DOMYSLNY_ASORTYMENT)

if "palety_tir" not in st.session_state:
    st.session_state["palety_tir"] = []

def generuj_pdf_pz(nr_pz, data, dostawca_id, dostawca_dane, towar, opakowanie_str, paleta_str, przywiezione_op, pobrane_op, przywiezione_pal, pobrane_pal, netto, status, uwagi, osoba_prow, podpis_img, qr_img_bytes):
    try:
        pdfmetrics.registerFont(TTFont('PolishFont', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('PolishFont-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        f_regular = 'PolishFont'
        f_bold = 'PolishFont-Bold'
    except:
        f_regular = 'Helvetica'
        f_bold = 'Helvetica-Bold'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottom=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', fontName=f_bold, fontSize=18, leading=22, textColor=colors.HexColor('#1F497D'), alignment=1)
    sub_style = ParagraphStyle('SubStyle', fontName=f_regular, fontSize=10, leading=14)
    header_table_style = ParagraphStyle('HeaderTableStyle', fontName=f_bold, fontSize=9, leading=11, textColor=colors.white, alignment=1)
    cell_table_style = ParagraphStyle('CellTableStyle', fontName=f_regular, fontSize=9, leading=11, alignment=0)
    cell_table_center = ParagraphStyle('CellTableCenter', fontName=f_regular, fontSize=9, leading=11, alignment=1)
    
    story.append(Paragraph(f"DOKUMENT PZ - PRZYJĘCIE ZEWNĘTRZNE nr: {nr_pz}", title_style))
    story.append(Spacer(1, 15))
    
    status_kolor = '#2ecc71' if status == 'ZIELONY' else ('#f39c12' if status == 'POMARAŃCZOWY' else '#e74c3c')
    
    dane_ogolne = [
        [Paragraph(f"<b>Nabywca:</b> GPW JANMAR SP. Z O.O.", sub_style),
         Paragraph(f"<b>Dostawca:</b> {dostawca_dane['nazwa']} ({dostawca_id})", sub_style)],
        [Paragraph(f"<b>Data dostawy:</b> {data}<br/><b>Magazynier:</b> {osoba_prow}", sub_style),
         Paragraph(f"<font color='{status_kolor}'><b>STATUS JAKOŚCI: {status}</b></font><br/>Uwagi: {uwagi}", sub_style)]
    ]
    t_ogolne = Table(dane_ogolne, colWidths=[270, 270])
    t_ogolne.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F5F8')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F497D')), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D9D9D9')), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    story.append(t_ogolne)
    story.append(Spacer(1, 20))
    
    tabela_towarowa = [
        [Paragraph("Parametr rozliczeniowy", header_table_style), Paragraph("Dostarczono", header_table_style), Paragraph("Pobrano", header_table_style), Paragraph("Saldo", header_table_style)],
        [Paragraph(f"Towar: {towar}", cell_table_style), Paragraph(f"{netto} kg.", cell_table_center), Paragraph("-", cell_table_center), Paragraph(f"{netto} kg.", cell_table_center)],
        [Paragraph(f"Opakowania ({opakowanie_str})", cell_table_style), Paragraph(f"{przywiezione_op} szt.", cell_table_center), Paragraph(f"{pobrane_op} szt.", cell_table_center), Paragraph(f"{przywiezione_op - pobrane_op} szt.", cell_table_center)],
        [Paragraph(f"Palety ({paleta_str})", cell_table_style), Paragraph(f"{przywiezione_pal} szt.", cell_table_center), Paragraph(f"{pobrane_pal} szt.", cell_table_center), Paragraph(f"{przywiezione_pal - pobrane_pal} szt.", cell_table_center)]
    ]
    t_towarowa = Table(tabela_towarowa, colWidths=[250, 100, 95, 95])
    t_towarowa.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F497D')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F497D')), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D9D9D9'))]))
    story.append(t_towarowa)
    story.append(Spacer(1, 30))
    
    podpis_kierowcy_io = BytesIO()
    podpis_img.save(podpis_kierowcy_io, format='PNG')
    podpis_kierowcy_io.seek(0)
    img_podpis = Image(podpis_kierowcy_io, width=120, height=50)
    img_qr = Image(qr_img_bytes, width=70, height=70)
    
    tabela_podpisow = [
        [Paragraph(f"<b>Podpis Magazyniera:</b><br/>{osoba_prow}", sub_style),
         Paragraph("<b>Podpis Dostawcy:</b>", sub_style), img_podpis,
         Paragraph("<b>KOD QR BIURA:</b>", sub_style), img_qr]
    ]
    t_podpisy = Table(tabela_podpisow, colWidths=[170, 90, 110, 100, 70])
    t_podpisy.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    story.append(t_podpisy)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Sekcja formularza (Uproszczona na potrzeby integracji)
automatyczna_data = datetime.today().strftime('%Y-%m-%d %H:%M')
opcje_dostawcow = {k: f"{v['nazwa']} ({k})" for k, v in baza_dostawcow.items()}
wybrany_id = st.selectbox("Wybierz dostawcę:", options=list(opcje_dostawcow.keys()), format_func=lambda x: opcje_dostawcow[x])

opcje_asortymentu = list(baza_asortymentu.values())
wybrany_towar = st.selectbox("Wybierz towar:", options=opcje_asortymentu)

rodzaj_opakowania = st.radio("Opakowanie:", ["OPAKOWANIE JEDNORAZOWE", "OPAKOWANIE WYMIENNE"])
szczegoly_opakowania = "Luz"
rodzaj_palety = st.selectbox("Paleta:", ["PALETA EURO", "PALETA JEDNORAZOWA"])

waga_netto_laczna = st.number_input("Waga Netto (kg):", min_value=0.0, value=100.0)
ilosc_opakowan_laczna = st.number_input("Ilość opakowań (szt):", min_value=0, value=10)
ilosc_palet_dostarczonych = st.number_input("Ilość palet (szt):", min_value=0, value=1)

ilosc_opakowan_pobranych = 0
ilosc_palet_pobranych = 0

st.write("---")
st.session_state["status_jakosci"] = st.radio("Jakość:", ["ZIELONY", "POMARAŃCZOWY", "CZERWONY"])
komentarz_jakosc = "Zgodny z normami."

canvas_result = st_canvas(fill_color="white", stroke_width=3, stroke_color="#1F497D", background_color="#FFFFFF", height=150, width=400, drawing_mode="freedraw", key="canvas")
wybrany_magazynier = st.selectbox("Magazynier:", options=opcje_magazynierów)

if st.button("🔒 ZATWIERDŹ PRZYJĘCIE"):
    if canvas_result.image_data is not None:
        from PIL import Image as PILImage
        import numpy as np
        img_array = np.array(canvas_result.image_data)
        podpis_pil = PILImage.fromarray(img_array.astype('uint8'), 'RGBA')
        
        id_losowe = str(random.randint(10000, 99999))
        rok_biezacy = datetime.today().strftime('%Y')
        losowy_nr_pz = f"PZ_{id_losowe}_{rok_biezacy}"
        dane_d_koncowe = baza_dostawcow[wybrany_id]
        
        link_dla_handlowca = f"https://janmar-wms-biuro-jgtio5bge3ogkstnnlpa9j.streamlit.app/?p={losowy_nr_pz}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(link_dla_handlowca)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        qr_io = BytesIO()
        qr_img.save(qr_io, format='PNG')
        qr_io.seek(0)
        
        pdf_bytes = generuj_pdf_pz(
            losowy_nr_pz.replace("_","/"), automatyczna_data, wybrany_id, dane_d_koncowe, wybrany_towar,
            f"{rodzaj_opakowania} - {szczegoly_opakowania}", rodzaj_palety,
            ilosc_opakowan_laczna, ilosc_opakowan_pobranych, ilosc_palet_dostarczonych, ilosc_palet_pobranych,
            waga_netto_laczna, st.session_state["status_jakosci"], komentarz_jakosc, wybrany_magazynier, podpis_pil, qr_io
        )
        
        nazwa_pliku_pdf = f"PZ_{id_losowe}_{rok_biezacy}.pdf"
        drive_link = przeslij_pdf_na_google_drive(pdf_bytes, nazwa_pliku_pdf)
        
        if drive_link:
            payload = {
                "nr_pz": losowy_nr_pz.replace("_", "/"),
                "data": automatyczna_data,
                "dostawca_id": wybrany_id,
                "dostawca_nazwa": dane_d_koncowe['nazwa'],
                "towar": wybrany_towar,
                "netto": float(waga_netto_laczna),
                "opakowania_przywiezione": int(ilosc_opakowan_laczna),
                "opakowania_pobrane": int(ilosc_opakowan_pobranych),
                "palety_przywiezione": int(ilosc_palet_dostarczonych),
                "palety_pobrane": int(ilosc_palet_pobranych),
                "palety_typ": rodzaj_palety,
                "status_jakosci": st.session_state["status_jakosci"],
                "uwagi": komentarz_jakosc,
                "magazynier": wybrany_magazynier,
                "link_drive": drive_link
            }
            requests.put(f"{FIREBASE_URL.replace('.json', '')}/{losowy_nr_pz}.json", data=json.dumps(payload))
            st.success("☁️ Raport PZ zapisany na Google Drive i w bazie Firebase!")
            st.image(qr_io, width=200)
