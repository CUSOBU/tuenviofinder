#!/usr/bin/python3

import datetime
import json
import logging
import os
import urllib
from logging.handlers import RotatingFileHandler

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

DIRECTORY = os.path.dirname(os.path.realpath(__file__)) + '/'

logger = logging.getLogger('tuenviofinder')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fh = RotatingFileHandler(DIRECTORY + 'logs/sync.log', mode='a', maxBytes=5 * 1024 * 1024, backupCount=1, encoding=None, delay=0)
fh.setFormatter(formatter)
logger.addHandler(fh)

env_path = DIRECTORY + '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TOKEN")
URL = "https://api.telegram.org/bot" + TOKEN + "/"

USER = {

}

PROVINCIAS = {
    'pr': ['Pinar del Río', {'pinar': 'Pinar del Río'}],
    'ar': ['Artemisa', {'artemisa': 'Artemisa'}],
    'my': ['Mayabeque', {'mayabeque-tv': 'Mayabeque'}],
    'mt': ['Matanzas', {'matanzas': 'Matanzas'}],
    'cf': ['Cienfuegos', {'cienfuegos': 'Cienfuegos'}],
    'vc': ['Villa Clara', {'villaclara': 'Villa Clara'}],
    'ss': ['Sancti Spíritus', {'sancti': 'Sancti Spíritus'}],
    'ca': ['Ciego de Ávila', {'ciego': 'Ciego de Ávila'}],
    'cm': ['Camagüey', {'camaguey': 'Camagüey'}],
    'lt': ['Las Tunas', {'tunas': 'Las Tunas'}],
    'hg': ['Holguín', {'holguin': 'Holguín'}],
    'gr': ['Granma', {'granma': 'Granma'}],
    'st': ['Santiago de Cuba', {'santiago': 'Santiago de Cuba'}],
    'gt': ['Guantánamo', {'guantanamo': 'Guantánamo'}],
    'ij': ['La Isla', {'isla': 'La Isla'}],
    'lh': ['La Habana', {'carlos3': 'Carlos Tercero', '4caminos': 'Cuatro Caminos'}]
}

RESULTADOS = {

}

PRODUCTOS = {

}

# Tiempo en segundos que una palabra de búsqueda permanece válida
TTL = 300


def update(offset):
    # Llamar al metodo getUpdates del bot, utilizando un offset
    respuesta = requests.get(URL + "getUpdates" +
                             "?offset=" + str(offset) + "&timeout=" + str(100))

    # Decodificar la respuesta recibida a formato UTF8
    mensajes_js = respuesta.content.decode("utf8")

    # Convertir y retornar el string de JSON a un diccionario de Python
    return json.loads(mensajes_js)


def info_mensaje(mensaje):
    # Comprobar el tipo de mensaje
    if "text" in mensaje["message"]:
        tipo = "texto"
    elif "sticker" in mensaje["message"]:
        tipo = "sticker"
    elif "animation" in mensaje["message"]:
        tipo = "animacion"  # Nota: los GIF cuentan como animaciones
    elif "photo" in mensaje["message"]:
        tipo = "foto"
    else:
        # Para no hacer mas largo este ejemplo, el resto de tipos entran
        # en la categoria "otro"
        tipo = "otro"

    # Recoger la info del mensaje (remitente, id del chat e id del mensaje)
    persona = mensaje["message"]["from"]["first_name"]
    id_chat = mensaje["message"]["chat"]["id"]
    id_update = mensaje["update_id"]

    # Devolver toda la informacion
    return tipo, id_chat, persona, id_update


def leer_mensaje(mensaje):
    # Extraer el texto, nombre de la persona e id del último mensaje recibido
    texto = mensaje["message"]["text"]

    # Devolver las dos id, el nombre y el texto del mensaje
    return texto


def enviar_mensaje(idchat, texto):
    logger.debug("Sending message {chat} >> {text}".format(chat=idchat, text=texto))
    # Llamar el metodo sendMessage del bot, passando el texto y la id del chat
    requests.get(URL + "sendMessage?text=" + texto + "&chat_id=" + str(idchat) + "&parse_mode=html")


def update_soup(url, mensaje, ahora, tienda):
    respuesta = requests.get(url)
    data = respuesta.content.decode("utf8")
    soup = BeautifulSoup(data, 'html.parser')
    if mensaje not in RESULTADOS:
        RESULTADOS[mensaje] = dict()
    RESULTADOS[mensaje][tienda] = {'tiempo': ahora, 'soup': soup}
    return soup


def obtener_soup(mensaje, nombre, idchat):
    # Arreglo con una tupla para cada tienda con sus valores
    result = []
    if idchat in USER:
        # Seleccionar provincia que tiene el usuario en sus ajustes
        prov = USER[idchat]['prov']

        # Se hace el procesamiento para cada tienda en cada provincia
        for tienda in PROVINCIAS[prov][1]:
            url_base = "https://www.tuenvio.cu/" + tienda
            url = url_base + "/Search.aspx?keywords=%22" + mensaje + "%22&depPid=0"
            respuesta, data, soup = "", "", ""
            ahora = datetime.datetime.now()

            # Si el resultado no se encuentra cacheado buscar y guardar
            if mensaje not in RESULTADOS or tienda not in RESULTADOS[mensaje]:
                debug_print("Buscando: \"" + mensaje + "\" para " + nombre)
                soup = update_soup(url, mensaje, ahora, tienda)
            # Si el resultado está cacheado
            elif tienda in RESULTADOS[mensaje]:
                delta = ahora - RESULTADOS[mensaje][tienda]['tiempo']
                # Si aún es válido se retorna lo que hay en cache
                if delta.total_seconds() <= TTL:
                    debug_print("\"" + mensaje + "\"" + " aún en cache, no se realiza la búsqueda.")
                    soup = RESULTADOS[mensaje][tienda]["soup"]
                # Si no es válido se actualiza la cache
                else:
                    debug_print("Actualizando : \"" + mensaje + "\" para " + nombre)
                    soup = update_soup(url, mensaje, ahora, tienda)
            result.append((soup, url_base, tienda))
    return result


def procesar_comando(mensaje, idchat):
    texto_respuesta, salida = '', ''
    if mensaje.startswith("/start"):
        texto_respuesta = "Búsqueda de productos en tuenvio.cu. Envíe una o varias palabras y se le responderá la disponibilidad. También puede probar la /ayuda. Suerte!"
        salida = "ha iniciado chat con el bot."
    elif mensaje.startswith("/ayuda"):
        texto_respuesta = "Envíe una palabra para buscar. O puede seleccionar una provincia:\n\n"
        for prov in PROVINCIAS:
            texto_respuesta += "/" + prov + ": " + PROVINCIAS[prov][0] + "\n"
        salida = "ha solicitado la ayuda."
    else:
        comando = mensaje.split('/')[1]
        # Vemos si comando es una provincia
        if comando in PROVINCIAS:
            USER[idchat] = {'prov': comando}
            texto_respuesta = "Ha seleccionado la provincia: " + PROVINCIAS[comando][0] + "."
            salida = "ha cambiado la provincia de búsqueda a " + PROVINCIAS[comando][0] + "."
        # Si no entonces comando es un identificador de producto
        elif comando in PRODUCTOS:
            prov = USER[idchat]['prov']
            producto = PRODUCTOS[comando][prov]['producto']
            texto_respuesta = "Consultando: " + producto + "\n\nClick para ver en: " + PRODUCTOS[comando][prov]['link']
            salida = "ha consultado el link del producto " + producto + "."
        else:
            texto_respuesta = "Ha seleccionado incorrectamente el comando de provincia. Por favor, utilice la /ayuda."
            salida = "ha utilizado incorrectamente la ayuda."
    return texto_respuesta, salida


def debug_print(message):
    print(message)
    logger.debug(message)


# Variable para almacenar la ID del ultimo mensaje procesado
ultima_id = 0

while (True):
    try:
        mensajes_diccionario = update(ultima_id)
        for i in mensajes_diccionario["result"]:

            # Guardar la informacion del mensaje
            try:
                tipo, idchat, nombre, id_update = info_mensaje(i)
            except:
                tipo, idchat, nombre, id_update = "delete", "744256293", "Disnel 56", 1

            answer = False
            # Generar una respuesta dependiendo del tipo de mensaje
            if tipo == "texto":
                mensaje = leer_mensaje(i)
                texto_respuesta = ""
                answer = False
                if mensaje.startswith("/"):
                    texto_respuesta, salida = procesar_comando(mensaje, idchat)
                    debug_print(nombre + " " + salida)
                else:
                    try:
                        for soup, url_base, tienda in obtener_soup(mensaje, nombre, idchat):
                            prov = USER[idchat]['prov']
                            nombre_tienda = PROVINCIAS[prov][1][tienda]
                            l = soup.select('div.thumbSetting')
                            texto_respuesta += "[Resultados en: " + nombre_tienda + "]\n\n"
                            for child in l:
                                answer = True
                                producto = child.select('div.thumbTitle a')[0].contents[0]
                                phref = child.select('div.thumbTitle a')[0]['href']
                                pid = phref.split('&')[0].split('=')[1]
                                plink = url_base + "/" + phref
                                if pid not in PRODUCTOS:
                                    PRODUCTOS[pid] = dict()
                                    PRODUCTOS[pid][prov] = {'producto': producto, 'link': plink}
                                else:
                                    if prov not in PRODUCTOS[pid]:
                                        PRODUCTOS[pid][prov] = {'producto': producto, 'link': plink}
                                precio = child.select('div.thumbPrice span')[0].contents[0]
                                texto_respuesta += producto + " --> " + precio + urllib.parse.quote(" <a href=\"" + plink + "\">[ver más]</a>") + "\n"
                            texto_respuesta += "\n"
                    except Exception as inst:
                        texto_respuesta = "Ocurrió la siguiente excepción: " + str(inst)
            else:
                texto_respuesta = "Solo se admiten textos."

            # Si la ID del mensaje es mayor que el ultimo, se guarda la ID + 1
            if id_update > (ultima_id - 1):
                ultima_id = id_update + 1

            # Enviar la respuesta
            respuestas_posibles = ["Búsqueda", "Ha seleccionado", "Consultando", "Envíe"]
            hay_resp_posible = False
            for rp in respuestas_posibles:
                if texto_respuesta.startswith(rp):
                    hay_resp_posible = True
                    break

            if texto_respuesta:
                if texto_respuesta.startswith("Ocurrió"):
                    enviar_mensaje("744256293", texto_respuesta)
                    debug_print("error")
                elif hay_resp_posible:
                    enviar_mensaje(idchat, texto_respuesta)
                    debug_print("Busqueda o seleccion de provincia o consulta de producto")
                else:
                    if answer:
                        texto_respuesta = "🎉🎉🎉¡¡¡Encontrado!!! 🎉🎉🎉\n\n" + texto_respuesta
                        enviar_mensaje(idchat, texto_respuesta)
                        debug_print(texto_respuesta)
                    else:
                        enviar_mensaje(idchat, "No hay productos que contengan la palabra buscada ... 😭")
                        debug_print("no hubo respuesta")
                        debug_print(texto_respuesta)
            else:
                enviar_mensaje(idchat, "No hay productos que contengan la palabra buscada ... 😭")
                debug_print("mensaje vacio")

        # Vaciar el diccionario
        mensajes_diccionario = []
    except Exception as ex:
        logger.error("Unhandled error >> {error}".format(error=ex))
