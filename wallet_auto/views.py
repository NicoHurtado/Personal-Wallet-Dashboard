from django.shortcuts import render
from wallet_auto.auto import *
from django.http import HttpResponse
from datetime import datetime

def home(request):
    return render(request, "index.html")


def automation(request):
    context = {}

    if request.method == "POST":
        salidas, Recepcion, cuanto_entro, cuanto_salio, total_constante, fig_html, gastos_por_mes = dataframes()

        salidas['Fecha'] = pd.to_datetime(salidas['Fecha']).dt.strftime("%Y-%m-%d")
        Recepcion['Fecha'] = pd.to_datetime(Recepcion['Fecha']).dt.strftime("%Y-%m-%d")

        salidas = salidas.sort_values(by='Fecha', ascending=False)
        Recepcion = Recepcion.sort_values(by='Fecha', ascending=False)

        salidas_list = salidas.to_dict(orient='records')
        recepcion_list = Recepcion.to_dict(orient='records')
        gastos_por_mes_list = gastos_por_mes.to_dict(orient='records')

        context = {
            "salidas": salidas_list,
            "Recepcion": recepcion_list,
            "cuanto_entro": cuanto_entro,
            "cuanto_salio": cuanto_salio,
            "total_constante": total_constante,
            "fig": fig_html,
            "gastos_por_mes": gastos_por_mes_list
        }




    return render(request, "index.html", context=context)