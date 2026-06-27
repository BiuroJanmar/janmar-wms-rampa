import streamlit as st
import random
from datetime import datetime
from io import BytesIO
from streamlit_drawable_canvas import st_canvas

# Importy do generowania PDF i rejestracji zewnętrznych czcionek TTF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Konfiguracja ekranu pod tablet na magazynie
st.set_page_config(page_title="Janmar WMS - Rampa", page_icon="📦", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stWidgetLabel"] p { font-size: 20px !important; font-weight: 600 !important; }
    .stButton>button { width: 100% !important; height: 70px !important; font-size: 22px !important; font-weight: bold !important; border-radius: 12px !important; margin-bottom: 10px !important; }
    div[data-testid="stNumberInput"] input { font-size: 24px !important; height: 55px !important; font-weight: bold !important; }
    div[data-testid="stTextInput"] input { font-size: 22px !important; height: 55px !important; }
    .status-box { padding: 20px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 24px; color: white; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("🏭 JANMAR WMS - PANEL PRZYJĘCIA v1.4")
st.subheader("Wersja z pełnym kodowaniem polskich znaków TTF")
st.write("---")

# Bazy danych w pamięci podręcznej (Session State)
if "baza_dostawcow" not in st.session_state:
    st.session_state["baza_dostawcow"] = {
        "JAN-11199": {"nazwa": "MARCIN PRZEWORSKI", "tel": "601234567"},
        "JAN-10023": {"nazwa": "AGRO-HURT JANUSZ", "tel": "601234567"},
        "JAN-10452": {"nazwa": "POL-FRUT SP. Z O.O.", "tel": "509876543"}
    }
if "lista_towarow" not in st.session_state:
    st.session_state["lista_towarow"] = ["ARBUZ LUZ", "ZIEMNIAK WCZESNY LUZ", "ZIEMNIAK LUZ", "KAPUSTA PEKIŃSKA LUZ", "KAPUSTA WŁOSKA LUZ"]
if "palety_tir" not in st.session_state:
    st.session_state["palety_tir"] = []
if "lista_magazynierow" not in st.session_state:
    st.session_state["lista_magazynierow"] = ["Zbigniew Tkaczyk", "Jan Kowalski", "Mariusz Nowak", "Piotr Zieliński"]

# GENERATOR DOKUMENTU PDF PZ
def generuj_pdf_pz(nr_pz, data, dostawca_id, dostawca_dane, towar, opakowanie_str, paleta_str, przywiezione_op, pobrane_op, przywiezione_pal, pobrane_pal, netto, status, uwagi, osoba_prow, podpis_img):
    
    # REJESTRACJA CZCIONKI Z PEŁNYM WSPARCIEM POLSKICH ZNAKÓW (TrueType)
    try:
        pdfmetrics.registerFont(TTFont('PolishFont', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('PolishFont-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        f_regular = 'PolishFont'
        f_bold = 'PolishFont-Bold'
    except:
        # Awaryjny font, gdyby system miał inną ścieżkę (standard w ReportLab)
        f_regular = 'Helvetica'
        f_bold = 'Helvetica-Bold'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottom=30)
    story = []
    styles = getSampleStyleSheet()
    
    # Style oparte na zarejestrowanej polskiej czcionce TTF
    title_style = ParagraphStyle('TitleStyle', fontName=f_bold, fontSize=18, leading=22, textColor=colors.HexColor('#1F497D'), alignment=1)
    sub_style = ParagraphStyle('SubStyle', fontName=f_regular, fontSize=10, leading=14)
    header_table_style = ParagraphStyle('HeaderTableStyle', fontName=f_bold, fontSize=9, leading=11, textColor=colors.white, alignment=1)
    cell_table_style = ParagraphStyle('CellTableStyle', fontName=f_regular, fontSize=9, leading=11, alignment=0)
    cell_table_center = ParagraphStyle('CellTableCenter', fontName=f_regular, fontSize=9, leading=11, alignment=1)
    
    story.append(Paragraph(f"DOKUMENT PZ - PRZYJĘCIE ZEWNĘTRZNE nr: {nr_pz}", title_style))
    story.append(Spacer(1, 15))
    
    status_kolor = '#2ecc71' if status == 'ZIELONY' else ('#f39c12' if status == 'POMARAŃCZOWY' else '#e74c3c')
    
    dane_ogolne = [
        [Paragraph(f"<b>Nabywca / Magazyn:</b><br/>GPW JANMAR SP. Z O.O.<br/>ul. Gołaśka 3/58, Kraków", sub_style),
         Paragraph(f"<b>Dostawca:</b><br/>{dostawca_dane['nazwa']}<br/>ID: {dostawca_id}<br/>Tel: {dostawca_dane.get('tel', '-')}", sub_style)],
        [Paragraph(f"<b>Data dostawy:</b> {data}<br/><b>Sporządził:</b> {osoba_prow}", sub_style),
         Paragraph(f"<font color='{status_kolor}'><b>STATUS JAKOŚCI: {status}</b></font><br/>Uwagi: {uwagi}", sub_style)]
    ]
    t_ogolne = Table(dane_ogolne, colWidths=[270, 270])
    t_ogolne.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F5F8')), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F497D')), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D9D9D9')), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    story.append(t_ogolne)
    story.append(Spacer(1, 20))
    
    tabela_towarowa = [
        [Paragraph("Parametr rozliczeniowy", header_table_style), Paragraph("Dostarczono (Wjazd)", header_table_style), Paragraph("Pobrano (Wyjazd)", header_table_style), Paragraph("Saldo Końcowe", header_table_style)],
        [Paragraph(f"Towar: {towar}", cell_table_style), Paragraph(f"{netto} kg/szt.", cell_table_center), Paragraph("-", cell_table_center), Paragraph(f"{netto} kg/szt.", cell_table_center)],
        [Paragraph(f"Opakowania ({opakowanie_str})", cell_table_style), Paragraph(f"{przywiezione_op} szt.", cell_table_center), Paragraph(f"{pobrane_op} szt.", cell_table_center), Paragraph(f"{przywiezione_op - pobrane_op} szt.", cell_table_center)],
        [Paragraph(f"Palety ({paleta_str})", cell_table_style), Paragraph(f"{przywiezione_pal} szt.", cell_table_center), Paragraph(f"{pobrane_pal} szt.", cell_table_center), Paragraph(f"{przywiezione_pal - pobrane_pal} szt.", cell_table_center)]
    ]
    t_towarowa = Table(tabela_towarowa, colWidths=[250, 100, 95, 95])
    t_towarowa.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F497D')), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#1F497D')), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D9D9D9')), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    story.append(t_towarowa)
    story.append(Spacer(1, 40))
    
    podpis_kierowcy_io = BytesIO()
    podpis_img.save(podpis_kierowcy_io, format='PNG')
    podpis_kierowcy_io.seek(0)
    img_reportlab = Image(podpis_kierowcy_io, width=120, height=50)
    
    tabela_podpisow = [
        [Paragraph(f"<b>Podpis Magazyniera Janmar:</b><br/><br/>............................................<br/>{osoba_prow}", sub_style),
         Paragraph("<b>Podpisano na tablecie przez Dostawcę:</b>", sub_style), img_reportlab]
    ]
    t_podpisy = Table(tabela_podpisow, colWidths=[240, 180, 120])
    t_podpisy.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'BOTTOM')]))
    story.append(t_podpisy)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# KROK 1: DOSTAWCA
st.header("1. Dane Dostawy i Kontrahenta")
automatyczna_data = datetime.today().strftime('%Y-%m-%d %H:%M')
st.info(f"📅 Data i godzina przyjęcia (Auto): **{automatyczna_data}**")

opcje_dostawcow = {k: f"{v['nazwa']} ({k})" for k, v in st.session_state["baza_dostawcow"].items()}
wybrany_id = st.selectbox("Wybierz dostawcę z bazy:", options=list(opcje_dostawcow.keys()), format_func=lambda x: opcje_dostawcow[x])

nowy_dostawca_chk = st.checkbox("➕ [ RĘCZNE DODAWANIE NOWEGO DOSTAWCY ]")
if nowy_dostawca_chk:
    nowa_nazwa = st.text_input("Nazwa nowego dostawcy:")
    nowy_tel = st.text_input("Numer telefonu komórkowego (9 cyfr):", max_chars=9)
    if st.button("💾 ZAPISZ DOSTAWCĘ W BAZIE"):
        if nowa_nazwa and len(nowy_tel) == 9 and nowy_tel.isdigit():
            wylosowane_id = f"JAN-{random.randint(11000, 99999)}"
            st.session_state["baza_dostawcow"][wylosowane_id] = {"nazwa": nowa_nazwa.upper(), "tel": nowy_tel}
            st.success("✅ Dodano dostawcę. Wybierz go z listy powyżej.")
            st.rerun()

st.write("---")

# KROK 2: ASORTYMENT
st.header("2. Asortyment i Opakowania")
wybrany_towar = st.selectbox("Wybierz rodzaj towaru:", options=st.session_state["lista_towarow"])

nowy_towar_chk = st.checkbox("➕ [ RĘCZNE DODAWANIE NOWEGO ASORTYMENTU ]")
if nowy_towar_chk:
    dodaj_towar_nazwa = st.text_input("Wpisz nową nazwę towaru:")
    if st.button("💾 ZAPISZ NOWY ASORTYMENT"):
        if dodaj_towar_nazwa:
            st.session_state["lista_towarow"].append(dodaj_towar_nazwa.upper())
            st.success("✅ Dodano towar do listy.")
            st.rerun()

rodzaj_opakowania = st.radio("Rodzaj opakowania towaru:", ["OPAKOWANIE JEDNORAZOWE", "OPAKOWANIE WYMIENNE"])
szczegoly_opakowania = "Luz/Brak"
if rodzaj_opakowania == "OPAKOWANIE WYMIENNE":
    szczegoly_opakowania = st.selectbox("Wybierz typ opakowania wymiennego:", options=["KARTON JANMAR", "ŁUSZCZKA JANMAR", "SKRZYNIA JANMAR", "WŁASNOŚĆ DOSTAWCY", "OPAKOWANIE IFCO", "OPAKOWANIE EPS"])

rodzaj_palety = st.selectbox("Towar przyjechał na palecie:", ["PALETA EURO", "PALETA JEDNORAZOWA", "LUZEM (BEZ PALET)"])
st.write("---")

# KROK 3: WAGI I SALDA
st.header("3. Rejestracja Ilości i Wag")
tryb_przyjecia = st.radio("Wybierz gabaryt dostawy:", ["SZYBKIE PRZYJĘCIE (Mała dostawa / Busy)", "ROZŁADUNEK TIR (Ważenie paletowe)"])

waga_netto_laczna = 0.0
ilosc_opakowan_laczna = 0
ilosc_palet_dostarczonych = 0

if tryb_przyjecia == "SZYBKIE PRZYJĘCIE (Mała dostawa / Busy)":
    ilosc_szt_kg_laczna = st.number_input("Łączna ilość towaru (kg / szt):", min_value=0.0, value=0.0)
    ilosc_opakowan_laczna = st.number_input("Ilość przywiezionych skrzynek:", min_value=0, value=0)
    ilosc_palet_dostarczonych = st.number_input("Ilość przywiezionych palet:", min_value=0, value=0)
    waga_netto_laczna = ilosc_szt_kg_laczna
else:
    col1, col2, col3 = st.columns(3)
    with col1: waga_brutto_p = st.number_input("Waga BRUTTO palety (kg):", min_value=0.0, value=0.0)
    with col2: ilosc_op_p = st.number_input("Ilość skrzynek na palecie (szt):", min_value=0, value=0)
    with col3: waga_jednego_op = st.number_input("Waga skrzynki (tara - kg):", min_value=0.0, value=0.5, step=0.1)
    
    tara_palety_sztywna = 25.0 if rodzaj_palety == "PALETA EURO" else 15.0
    if rodzaj_palety == "LUZEM (BEZ PALET)": tara_palety_sztywna = 0.0
    tara_laczna_palety = tara_palety_sztywna + (ilosc_op_p * waga_jednego_op)
    netto_palety_wyliczone = max(0.0, waga_brutto_p - tara_laczna_palety)
    
    st.warning(f"🧮 Wyliczone NETTO dla tej palety: **{netto_palety_wyliczone} kg**")
    if st.button("➕ ZATWIERDŹ I ZWAŻ NASTĘPNĄ PALETĘ"):
        if waga_brutto_p > 0 and ilosc_op_p > 0:
            st.session_state["palety_tir"].append({"paleta_nr": len(st.session_state["palety_tir"]) + 1, "opakowania": ilosc_op_p, "netto": netto_palety_wyliczone})
            st.rerun()
            
    if st.session_state["palety_tir"]:
        waga_netto_laczna = sum(p['netto'] for p in st.session_state["palety_tir"])
        ilosc_opakowan_laczna = sum(p['opakowania'] for p in st.session_state["palety_tir"])
        ilosc_palet_dostarczonych = len(st.session_state["palety_tir"])
        st.markdown(f"**RAZEM Z TIR-A:** Palet: `{ilosc_palet_dostarczonych}` | Skrzynek: `{ilosc_opakowan_laczna}` | NETTO: `{waga_netto_laczna} kg`")
        if st.button("🗑️ RESETUJ PALETY"):
            st.session_state["palety_tir"] = []
            st.rerun()

st.markdown("### 🔄 Saldo Wydawki (Co dostawca zabiera ze sobą)")
ilosc_opakowan_pobranych = 0
ilosc_palet_pobranych = 0
col_op, col_pal = st.columns(2)
with col_op:
    nie_op = st.checkbox("✅ NIE POBIERA OPAKOWAŃ POWROTNYCH", value=True)
    if not nie_op: ilosc_opakowan_pobranych = st.number_input("Ilość ODRZUCONYCH/POBRANYCH skrzynek:", min_value=0, value=0)
with col_pal:
    nie_pal = st.checkbox("✅ NIE POBIERA PALET POWROTNYCH", value=True)
    if not nie_pal: ilosc_palet_pobranych = st.number_input("Ilość ZWROCONYCH/POBRANYCH palet:", min_value=0, value=0)

st.write("---")

# KROK 4: JAKOŚĆ
st.header("4. Ocena Jakościowa Towaru")
if "status_jakosci" not in st.session_state: st.session_state["status_jakosci"] = "NIEWYBRANY"
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🟢 TOWAR OK"): st.session_state["status_jakosci"] = "ZIELONY"
with c2:
    if st.button("🟠 WARUNKOWY"): st.session_state["status_jakosci"] = "POMARAŃCZOWY"
with c3:
    if st.button("🔴 ZWROT"): st.session_state["status_jakosci"] = "CZERWONY"

komentarz_jakosc = "Zgodny z normami."
if st.session_state["status_jakosci"] == "ZIELONY":
    st.markdown('<div class="status-box" style="background-color: #2ecc71;">🟢 JAKOŚĆ OK - TOWAR PRZYJĘTY</div>', unsafe_allow_html=True)
elif st.session_state["status_jakosci"] == "POMARAŃCZOWY":
    st.markdown('<div class="status-box" style="background-color: #f39c12;">🟠 PRZYJĘCIE WARUNKOWE</div>', unsafe_allow_html=True)
    komentarz_jakosc = st.selectbox("Powód:", ["TOWAR PRZYJĘTY WARUNKOWO DO ROZLICZENIA PO SPRZEDAŻY PRZEZ KUPCA", "UBYTEK WAGI POWYŻEJ TOLERANCJI", "WIDOCZNE USZKODZENIA MECHANICZNE / TRANSPORTOWE", "ODKŁOSY/OZNAKI PSUCIA – WYMAGA PRZEBRANIA NA MAGAZYNIE"])
elif st.session_state["status_jakosci"] == "CZERWONY":
    st.markdown('<div class="status-box" style="background-color: #e74c3c;">🔴 TOWAR ODRZUCONY - ZWROT</div>', unsafe_allow_html=True)
    komentarz_jakosc = st.text_input("Uzasadnienie (wymagane):")
st.write("---")

# KROK 5: PODPIS
st.header("5. Podpis Dostawcy i Autoryzacja")
st.markdown("✍️ ... Podpisz się palcem w ramce:")
canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#1F497D", background_color="#FFFFFF", height=150, width=400, drawing_mode="freedraw", key="canvas")

wybrany_magazynier = st.selectbox("Przyjmujący magazynier:", options=st.session_state["lista_magazynierow"] + ["➕ DODAJ NOWEGO MAGAZYNIERA DO LISTY"])

if wybrany_magazynier == "➕ DODAJ NOWEGO MAGAZYNIERA DO LISTY":
    nowy_m_imie = st.text_input("Wpisz Imię i Nazwisko nowego pracownika:")
    if st.button("💾 ZAPISZ MAGAZYNIERA"):
        if nowy_m_imie:
            st.session_state["lista_magazynierow"].append(nowy_m_imie.strip())
            st.success("✅ Dodano. Wybierz pracownika z listy powyżej.")
            st.rerun()

if st.button("🔒 ZATWIERDŹ PRZYJĘCIE I GENERUJ PDF"):
    if st.session_state["status_jakosci"] == "NIEWYBRANY":
        st.error("❌ Wybierz status jakości!")
    elif wybrany_magazynier == "➕ DODAJ NOWEGO MAGAZYNIERA DO LISTY":
        st.error("❌ Wybierz konkretnego pracownika!")
    elif canvas_result.image_data is None:
        st.error("❌ Brak podpisów kierowcy!")
    else:
        from PIL import Image as PILImage
        import numpy as np
        img_array = np.array(canvas_result.image_data)
        podpis_pil = PILImage.fromarray(img_array.astype('uint8'), 'RGBA')
        
        dane_d_koncowe = st.session_state["baza_dostawcow"][wybrany_id]
        losowy_nr_pz = f"PZ/{random.randint(10000,99999)}/{datetime.today().strftime('%Y')}"
        
        pdf_data = generuj_pdf_pz(
            losowy_nr_pz, automatyczna_data, wybrany_id, dane_d_koncowe, wybrany_towar,
            f"{rodzaj_opakowania} - {szczegoly_opakowania}", rodzaj_palety,
            ilosc_opakowan_laczna, ilosc_opakowan_pobranych, ilosc_palet_dostarczonych, ilosc_palet_pobranych,
            waga_netto_laczna, st.session_state["status_jakosci"], komentarz_jakosc, wybrany_magazynier, podpis_pil
        )
        
        st.success(f"🎉 DOSTAWA ZATWIERDZONA! Numer PZ: {losowy_nr_pz}")
        st.download_button(label="📥 POBIERZ RAPORT PZ (PDF Z PODPISEM)", data=pdf_data, file_name=f"PZ_{losowy_nr_pz.replace('/','_')}.pdf", mime="application/pdf")
