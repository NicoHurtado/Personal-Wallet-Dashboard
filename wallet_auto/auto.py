import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objs as go
import os

patron_recepcion_transferencia = re.compile(
    r"informa recepcion transferencia de ([\w\s]+) por \$([\d,]+) en la cuenta \*(\d+)\. (\d{2}/\d{2}/\d{4}) (\d{2}:\d{2})"
)

patron_realizacion_transferencia_QR = re.compile(
    r"Realizaste una transferencia con QR por \$(\d{1,3}(?:,\d{3})*\.\d{2}), desde cta (\d+) a cta (\d+)\. (\d{4}/\d{2}/\d{2}) (\d{2}:\d{2})"
)

patron_informe_transferencia = re.compile(
    r"informa Transferencia por \$(\d{1,3}(?:,\d{3})*) desde cta \*(\d+) a cta (\d+)\. (\d{2}/\d{2}/\d{4}) (\d{2}:\d{2})"
)

patron_compra = re.compile(
    r"informa Compra por \$(\d{1,3}(?:\.\d{3})*,\d{2}) en ([\w\s\-]+) (\d{2}:\d{2})\. (\d{2}/\d{2}/\d{4}) T\.Deb \*(\d+)"
)

patron_pago_TC = re.compile(
    r"Pagaste \$(\d{1,3}(?:,\d{3})*\.\d{2}) a (.+?) desde tu producto \*(\d+) el (\d{2}/\d{2}/\d{4}) (\d{2}:\d{2})"
)

patron_retiro = re.compile(
    r"le informa Retiro por \$(\d{1,3}(?:\.\d{3})*,\d{2}) en ([\w\d]+)\. Hora (\d{2}:\d{2}) (\d{2}/\d{2}/\d{4}) T\.Deb \*(\d+)"
)

patron_pago_nomina = re.compile(
    r"Pago de Nomina de [A-Z]+ [A-Z]+ por \$([\d,]+\.\d+) en su Cuenta Ahorros\. (\d{2}:\d{2}) (\d{2}/\d{2}/\d{4})"
)


username = ""
password = ""


imap_server = "imap.gmail.com"
mail = imaplib.IMAP4_SSL(imap_server)
mail.login(username, password)
mail.select("inbox")
status, messages = mail.search(None, "ALL")
#status, messages = mail.search(None, "X-GM-LABELS", '"Updates"')


email_ids = messages[0].split()


def take_info():
    with open("emails.txt", "w", encoding="utf-8") as f:
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    from_ = msg.get("From")
                    
                    if "alertasynotificaciones@notificacionesbancolombia.com" in from_:
                        email_body = ""
                    

                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))

                                try:
                                    body = part.get_payload(decode=True)
                                    charset = part.get_content_charset()  
                                    if charset:
                                        body = body.decode(charset)
                                    else:
                                        body = body.decode("utf-8") 
                                except Exception as e:
                                    print(f"Error decoding part: {e}")
                                    continue

                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    email_body += f"{body}\n"
                                elif content_type == "text/html":
                                    soup = BeautifulSoup(body, "html.parser")
                                    email_body += f"{soup.get_text()}\n"
                        else:
                            content_type = msg.get_content_type()
                            try:
                                body = msg.get_payload(decode=True)
                                charset = msg.get_content_charset()  
                                if charset:
                                    body = body.decode(charset)
                                else:
                                    body = body.decode("utf-8")  
                            except Exception as e:
                                print(f"Error decoding message: {e}")
                                continue

                            if content_type == "text/plain":
                                email_body = body
                            elif content_type == "text/html":
                                soup = BeautifulSoup(body, "html.parser")
                                email_body = soup.get_text()

                        f.write(f"{email_body}\n")
    mail.close()
    mail.logout()
    
def buscar(patron):
    with open('emails.txt', 'r', encoding='utf-8') as file:
        contenido = file.read()

    matches = patron.findall(contenido)
    #Entrada
    if patron == patron_recepcion_transferencia:
        df = pd.DataFrame(matches, columns=['Nombre', 'Monto', 'Cuenta', 'Fecha', 'Hora'])
        df['Monto'] = df['Monto'].str.replace(',', '', regex=False).astype(int)

    #Salida
    elif patron == patron_realizacion_transferencia_QR:
        df = pd.DataFrame(matches, columns=['Monto', 'Cuenta_Origen', 'Cuenta_Destino', 'Fecha', 'Hora'])
        df['Monto'] = df['Monto'].str.replace(',', '').astype(float)
        df['Monto'] = df['Monto'].astype(int)
        df['Categoria'] = 'Transferencia QR'

    #Salida
    elif patron == patron_informe_transferencia:
        df = pd.DataFrame(matches, columns=['Monto', 'Cuenta_Origen', 'Cuenta_Destino', 'Fecha', 'Hora'])
        df['Monto'] = df['Monto'].str.replace(',', '', regex=False).astype(int)
        df['Categoria'] = 'Transferencia'

    #Salida
    elif patron == patron_compra:
        df = pd.DataFrame(matches, columns=['Monto', 'Comercio', 'Hora', 'Fecha', 'Tarjeta'])
        df['Monto'] = df['Monto'].str.replace('.', '').str.replace(',', '.').astype(float)
        df['Monto'] = df['Monto'].astype(int).astype(str).astype(int)
        df['Categoria'] = 'Compra'
        
    #Salida
    elif patron == patron_pago_TC:
        df = pd.DataFrame(matches, columns=['Monto', 'Destinatario', 'Producto', 'Fecha', 'Hora'])
        df['Monto'] = df['Monto'].str.replace(',', '').astype(float)
        df['Monto'] = df['Monto'].astype(int)
        df['Categoria'] = 'Pago TC'

    #Salida
    elif patron == patron_retiro:
        df = pd.DataFrame(matches, columns=['Monto', 'Lugar', 'Hora', 'Fecha', 'Tarjeta'])
        df['Monto'] = df['Monto'].str.replace('.', '').str.replace(',', '.').astype(float)
        df['Monto'] = df['Monto'].astype(int).astype(str).astype(int)
        df['Categoria'] = 'Retiro Cajero'

    return df

def parse_fecha(fecha):
    for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
        try:
            return pd.to_datetime(fecha, format=fmt)
        except ValueError:
            continue
    return pd.NaT

def dataframes():
    
    take_info()
    realizacion_trans_qr = buscar(patron_realizacion_transferencia_QR)
    trans = buscar(patron_informe_transferencia)
    compra = buscar(patron_compra)
    pago_TC = buscar(patron_pago_TC)
    retiro = buscar(patron_retiro)

    salidas = pd.concat([realizacion_trans_qr, trans, compra, pago_TC, retiro], ignore_index=True)
    salidas = salidas[['Monto', 'Fecha', 'Hora', 'Categoria', 'Comercio', 'Lugar']]
    salidas['Categoria'] = salidas.apply(lambda row: f"Retiro Cajero {row['Lugar']}" if pd.notna(row['Lugar']) else (row['Comercio'] if pd.notna(row['Comercio']) else row['Categoria']), axis=1)
    salidas = salidas[['Monto', 'Fecha', 'Hora', 'Categoria']]

    print('-----------------Salidas--------------')
    print(salidas)
    print('---------------------------------------------------------')

    Recepcion = buscar(patron_recepcion_transferencia)
    Recepcion = Recepcion[['Monto', 'Fecha', 'Hora']]

    print('-----------------Entradas--------------')
    print(Recepcion)
    print('---------------------------------------------------------')

    cuanto_entro = Recepcion['Monto'].sum()

    cuanto_salio = salidas['Monto'].sum()
    print(f"Cuanto salio: {cuanto_salio}")
    print(f"Cuanto entro: {cuanto_entro}")

    total = Recepcion['Monto'].sum() - salidas['Monto'].sum()
    a_sumar = 2344491-20058
    total_constante = total + a_sumar

    print(f"Total: {total_constante}")

    salidas['Fecha'] = salidas['Fecha'].apply(parse_fecha)
    Recepcion['Fecha'] = Recepcion['Fecha'].apply(parse_fecha)
    entradas_agrupadas = Recepcion.groupby('Fecha')['Monto'].sum().reset_index()

    salidas['Fecha'] = salidas['Fecha'].apply(parse_fecha)
    salidas['AñoMes'] = salidas['Fecha'].dt.to_period('M')
    gastos_por_mes_salida = salidas.groupby('AñoMes')['Monto'].sum().reset_index()

    print(gastos_por_mes_salida)
    

    

    entradas_salidas = pd.concat([entradas_agrupadas.assign(Tipo='Entrada'), salidas.assign(Tipo='Salida')])

    entradas_salidas = entradas_salidas.sort_values(by='Fecha')
    color_entrada = 'green'
    color_salida = 'red'
    trace_entrada = go.Scatter(
        x=entradas_salidas[entradas_salidas['Tipo'] == 'Entrada']['Fecha'],
        y=entradas_salidas[entradas_salidas['Tipo'] == 'Entrada']['Monto'],
        mode='lines+markers',
        name='Entrada',
        line=dict(color=color_entrada),
        marker=dict(color=color_entrada),  
        hovertext=entradas_salidas[entradas_salidas['Tipo'] == 'Entrada']['Monto'].astype(str) + '<br>' + entradas_salidas[entradas_salidas['Tipo'] == 'Entrada']['Fecha'].dt.strftime('%b %d') + '<br>Entrada',
        hoverinfo='text'
    )

    trace_salida = go.Scatter(
        x=entradas_salidas[entradas_salidas['Tipo'] == 'Salida']['Fecha'],
        y=entradas_salidas[entradas_salidas['Tipo'] == 'Salida']['Monto'],
        mode='lines+markers', 
        name='Salida',
        line=dict(color=color_salida),  
        marker=dict(color=color_salida),  
        hovertext=entradas_salidas[entradas_salidas['Tipo'] == 'Salida']['Monto'].astype(str) + '<br>' + entradas_salidas[entradas_salidas['Tipo'] == 'Salida']['Fecha'].dt.strftime('%b %d') + '<br>Salida',
        hoverinfo='text'
    )
    layout = go.Layout(
    title='Grafica:',
    xaxis=dict(title='Fecha'),
    yaxis=dict(title='Monto'),
    hovermode='closest',
    paper_bgcolor='rgba(0,0,0,0)',  
    plot_bgcolor='rgba(0,0,0,0)'    
    )
    fig = go.Figure(data=[trace_entrada, trace_salida], layout=layout)
    fig_html = fig.to_html(full_html=False)

    return salidas, Recepcion, cuanto_entro, cuanto_salio, total_constante, fig_html, gastos_por_mes_salida

def parse_fecha_mes(fecha_str):
    for fmt in ('%Y/%m/%d', '%d/%m/%Y'):
        try:
            return pd.to_datetime(fecha_str, format=fmt)
        except ValueError:
            continue
    raise ValueError(f"Fecha {fecha_str} no coincide con los formatos esperados")
