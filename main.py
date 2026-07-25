import os
import time
from flask import Flask, request, session, render_template_string, jsonify, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- CONFIGURACIÓN ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------------------------------------------------------
# 📸 LOGO DEL BAR
LOGO_URL = "https://i.imgur.com/crEnZHt.png"
# ---------------------------------------------------------

# Configuración de Spotify
sp_oauth = SpotifyOAuth(
    client_id=os.environ.get('SPOTIFY_CLIENT_ID', ''),
    client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET', ''),
    redirect_uri=os.environ.get('SPOTIFY_REDIRECT_URI', ''),
    scope="user-modify-playback-state,user-read-playback-state,user-read-currently-playing",
    cache_path=".spotify_cache"
)

# ESTADO DEL BAR
BAR_ABIERTO = True

# MEMORIA DE CLIENTES
historial_usuarios = {}

# 🟢 NUEVO: COLA VIRTUAL (Para saber el turno exacto)
cola_virtual = [] 

# --- HTML DE LA APP (TU VERSIÓN FAVORITA) ---
HTML_CLIENTE = """
<!DOCTYPE html>
<html lang="es">
<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
   <title>Sánchez Sport Bar 🎵</title>
   <style>
       body { background-color: #000000; color: white; font-family: 'Helvetica Neue', sans-serif; text-align: center; padding: 20px; margin: 0; padding-bottom: 150px; }

       .logo-container { margin-top: 15px; margin-bottom: 5px; }
       .logo-img { width: 130px; height: auto; border-radius: 12px; border: 2px solid #222; }

       /* TÍTULOS */
       h1 { margin: 5px 0; line-height: 1.2; }
       .titulo-principal { color: #1DB954; font-size: 1.6em; text-transform: uppercase; font-weight: 900; display: block; }
       .titulo-secundario { color: white; font-size: 1.1em; font-weight: 300; display: block; margin-top: 5px; letter-spacing: 2px; text-transform: uppercase; }
       .subtitle { font-size: 0.95em; color: #b3b3b3; margin-top: 10px; margin-bottom: 25px; font-style: italic; }

       /* Buscador */
       .search-box { background: #1a1a1a; padding: 20px; border-radius: 20px; margin-bottom: 20px; border: 1px solid #333; }
       input { width: 90%; padding: 15px; border-radius: 30px; border: none; font-size: 16px; outline: none; margin-bottom: 15px; text-align: center; background: #333; color: white; }
       button.search-btn { background-color: #1DB954; color: black; border: none; padding: 12px 30px; border-radius: 30px; font-weight: bold; cursor: pointer; font-size: 1em; text-transform: uppercase; }

       /* Lista de canciones */
       .song-item { background: #181818; padding: 10px; margin: 10px 0; border-radius: 12px; display: flex; align-items: center; text-align: left; border: 1px solid #333; }
       .song-img { width: 50px; height: 50px; border-radius: 8px; margin-right: 15px; }
       .song-info { flex-grow: 1; }
       .song-title { font-weight: bold; display: block; font-size: 0.95em; color: white; }
       .song-artist { color: #b3b3b3; font-size: 0.8em; }
       .add-btn { background: white; color: black; font-size: 0.75em; padding: 8px 15px; border-radius: 20px; border: none; font-weight: bold; cursor: pointer; }

       /* Créditos y Footer */
       .credits { position: fixed; bottom: 0; left: 0; width: 100%; background: rgba(10, 10, 10, 0.98); padding: 15px; border-top: 2px solid #1DB954; font-size: 0.9em; z-index: 100; text-align: left; box-sizing: border-box; }
       .credit-info { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
       .credit-number { color: #1DB954; font-size: 1.4em; font-weight: bold; }

       .my-requests { font-size: 0.8em; color: #aaa; max-height: 80px; overflow-y: auto; border-top: 1px solid #333; padding-top: 5px; }
       .request-item { display: block; margin-top: 3px; }
       .request-check { color: #1DB954; margin-right: 5px; }

       /* PANTALLA CERRADO */
       .closed-screen { padding-top: 30px; }
       .closed-icon { font-size: 60px; margin-bottom: 10px; display: block; opacity: 0.7; }
       .mensaje-final { color: #ccc; font-size: 1.1em; line-height: 1.6; margin-top: 20px; font-weight: 300; }
       .mensaje-final strong { color: white; font-weight: 600; }
       .logo-cerrado { width: 100px; opacity: 0.6; filter: grayscale(80%); border-radius: 50%; margin-bottom: 20px; }
   </style>
</head>
<body>

   {% if not abierto %}
       <div class="closed-screen">
           <img src="{{ logo }}" class="logo-cerrado">

           <h1 style="color:#ff4444; font-size: 2.5em; text-transform: uppercase; margin-bottom: 0;">CERRADO</h1>
           <h2 style="color:white; font-weight:300; margin-top:5px; font-size:1.2em;">ROCKOLA DIGITAL</h2>

           <div class="mensaje-final">
               <p>¡Muchas gracias por tu visita!</p>
               <p>La Rockola ha cerrado sus puertas por hoy.</p>
               <br>
               <p><strong>Te esperamos pronto en<br>Sánchez Sport Bar<br>para seguir disfrutando.</strong></p>
           </div>
       </div>
   {% else %}

       <div class="logo-container">
           <img src="{{ logo }}" class="logo-img" alt="Logo Sánchez Sport Bar">
       </div>

       <h1>
           <span class="titulo-principal">Sánchez Sport Bar</span>
           <span class="titulo-secundario">Rockola Digital</span>
       </h1>
       <p class="subtitle">Pide, ¡tú pones la música!</p>

       <div class="search-box">
           <input type="text" id="busqueda" placeholder="Nombre de canción o artista...">
           <br>
           <button class="search-btn" onclick="buscar()">🔍 Buscar</button>
       </div>

       <div id="resultados"></div>

       <div class="credits">
           <div class="credit-info">
               <span>🎵 Créditos disponibles:</span>
               <span class="credit-number"><span id="creditos-cnt">...</span>/5</span>
           </div>

           <div class="my-requests">
               <strong>Tus pedidos recientes:</strong>
               <div id="lista-pedidos">
                   <span style="font-style:italic;">Aún no has pedido nada.</span>
               </div>
           </div>
       </div>

       <script>
           document.getElementById("busqueda").addEventListener("keypress", function(event) {
               if (event.key === "Enter") { buscar(); }
           });

           function buscar() {
               let q = document.getElementById('busqueda').value;
               if(!q) return;

               let btn = document.querySelector('.search-btn');
               let originalText = btn.innerText;
               btn.innerText = "⏳ ...";
               btn.disabled = true;
               document.getElementById('resultados').innerHTML = '';

               fetch('/api/buscar?q=' + q)
               .then(r => r.json())
               .then(data => {
                   btn.innerText = originalText;
                   btn.disabled = false;
                   let html = '';
                   
                   if (data.error) {
                       html = `<p style="color:#ff4444;">${data.error}</p>`;
                   } else if (!data.tracks || data.tracks.items.length === 0) {
                       html = '<p style="color:#777;">No encontramos nada 😢</p>';
                   } else {
                       data.tracks.items.forEach(track => {
                           let nombreSafe = track.name.replace(/'/g, "");
                           let img = track.album.images[2] ? track.album.images[2].url : '';
                           html += `
                           <div class="song-item">
                               <img src="${img}" class="song-img">
                               <div class="song-info">
                                   <span class="song-title">${track.name}</span>
                                   <span class="song-artist">${track.artists[0].name}</span>
                               </div>
                               <button class="add-btn" onclick="agregar('${track.uri}', '${nombreSafe}')">PEDIR</button>
                           </div>`;
                       });
                   }
                   document.getElementById('resultados').innerHTML = html;
               });
           }

           function agregar(uri, nombre) {
               if(!confirm("¿Pedir '" + nombre + "'?")) return;
               let nombreEncoded = encodeURIComponent(nombre);

               fetch('/api/agregar?uri=' + uri + '&nombre=' + nombreEncoded)
               .then(r => r.json())
               .then(data => {
                   alert(data.mensaje);
                   document.getElementById('busqueda').value = '';
                   document.getElementById('resultados').innerHTML = '';
                   actualizarEstado();
               });
           }

           function actualizarEstado() {
               fetch('/api/creditos').then(r => r.json()).then(d => {
                   document.getElementById('creditos-cnt').innerText = d.disponibles;
                   let listaHtml = '';
                   if(d.pedidos.length === 0) {
                       listaHtml = '<span style="font-style:italic; opacity:0.7;">Nada por aquí...</span>';
                   } else {
                       d.pedidos.forEach(p => {
                           listaHtml += `<span class="request-item"><span class="request-check">✔</span> ${p}</span>`;
                       });
                   }
                   document.getElementById('lista-pedidos').innerHTML = listaHtml;
               });
           }

           actualizarEstado();
           setInterval(actualizarEstado, 60000);
       </script>
   {% endif %}

   <script>
       let estadoActual = {{ 'true' if abierto else 'false' }};
       setInterval(() => {
           fetch('/api/status')
           .then(r => r.json())
           .then(data => {
               if (data.abierto !== estadoActual) {
                   location.reload();
               }
           })
           .catch(err => console.log("..."));
       }, 5000);
   </script>

</body>
</html>
"""

# --- FUNCIONES DE SOPORTE ---
def obtener_token():
    """Obtiene el token de forma segura. Si fue revocado, borra la caché."""
    try:
        token_info = sp_oauth.get_cached_token()
        return token_info
    except Exception as e:
        if os.path.exists(".spotify_cache"):
            os.remove(".spotify_cache")
        return None

# --- RUTAS ---

@app.route('/')
def home():
    if 'uid' not in session:
        session['uid'] = os.urandom(8).hex()
    return render_template_string(HTML_CLIENTE, abierto=BAR_ABIERTO, logo=LOGO_URL)

# 🟢 NUEVAS RUTAS DE RE-AUTENTICACIÓN
@app.route('/login')
def login():
    """El administrador (tú) entra aquí para conectar su Spotify a la rockola."""
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Spotify te redirige aquí después de iniciar sesión con éxito."""
    code = request.args.get('code')
    if code:
        sp_oauth.get_access_token(code)
        return "<h2 style='color:green; text-align:center; padding:50px;'>✅ Autenticación exitosa. El token ha sido renovado. <br><a href='/'>Volver a la Rockola</a></h2>"
    return "<h2 style='color:red; text-align:center;'>❌ Error en la autenticación.</h2>"

@app.route('/api/status')
def status():
    return jsonify({'abierto': BAR_ABIERTO})

@app.route('/api/buscar')
def buscar():
    if not BAR_ABIERTO: 
        return jsonify({'tracks': {'items': []}})
    
    token_info = obtener_token()
    if not token_info: 
        return jsonify({'error': '⚠️ La rockola perdió conexión con Spotify. El administrador debe entrar a /login para repararlo.'})
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    q = request.args.get('q')
    
    try:
        return jsonify(sp.search(q, limit=5, type='track'))
    except Exception as e:
        return jsonify({'tracks': {'items': []}})

@app.route('/api/agregar')
def agregar():
    if not BAR_ABIERTO: 
        return jsonify({'mensaje': 'El bar está cerrado.'})

    user_id = session.get('uid')
    uri = request.args.get('uri')
    nombre_cancion = request.args.get('nombre', 'Canción desconocida')

    ahora = time.time()

    # --- LIMPIEZA DE COLA VIRTUAL ---
    global cola_virtual
    cola_virtual = [t for t in cola_virtual if ahora - t < 3600]

    # --- LIMPIEZA HISTORIAL USUARIO ---
    historial = historial_usuarios.get(user_id, [])
    historial = [h for h in historial if ahora - h['t'] < 1800]

    # 1. VERIFICAR LÍMITE (Max 5)
    if len(historial) >= 5:
        return jsonify({'mensaje': '❌ Límite alcanzado.\nEspera a que se recarguen tus créditos.'})

    # 2. VERIFICAR REPETICIÓN
    for h in historial:
        if h['uri'] == uri:
            return jsonify({'mensaje': f'❌ Ya pediste "{nombre_cancion}" hace poco.'})

    token_info = obtener_token()
    if not token_info: 
        return jsonify({'mensaje': '⚠️ Error: La rockola está desconectada. Avisa en barra para que la re-conecten (/login).'})
    
    sp = spotipy.Spotify(auth=token_info['access_token'])

    try:
        sp.add_to_queue(uri)

        # --- CALCULO DE TURNO ---
        cola_virtual.append(ahora)
        personas_antes = len(cola_virtual) - 1

        turno_mensaje = ""
        if personas_antes == 0:
            turno_mensaje = "\n(¡Es la siguiente!)"
        else:
            turno_mensaje = f"\n(Hay {personas_antes} pedidos delante de ti)"

        historial.append({'t': ahora, 'uri': uri, 'nombre': nombre_cancion})
        historial_usuarios[user_id] = historial

        return jsonify({'mensaje': f'✅ ¡Listo! Agregada.{turno_mensaje}'})

    except Exception as e:
        return jsonify({'mensaje': '⚠️ Error: No se pudo agregar a la cola.'})

@app.route('/api/creditos')
def creditos():
    user_id = session.get('uid')
    ahora = time.time()
    historial = historial_usuarios.get(user_id, [])
    historial = [h for h in historial if ahora - h['t'] < 1800]
    nombres_pedidos = [h['nombre'] for h in historial]
    return jsonify({'disponibles': 5 - len(historial), 'pedidos': nombres_pedidos})

@app.route('/admin/<accion>')
def admin(accion):
    global BAR_ABIERTO
    estilo = "font-family: sans-serif; text-align: center; padding-top: 50px; background:#111; color:white;"
    if accion == 'on':
        BAR_ABIERTO = True
        return f"<div style='{estilo}'><h1 style='color:green; font-size:3em;'>🟢 ENCENDIDA</h1><p>Sistema Operativo.</p></div>"
    elif accion == 'off':
        BAR_ABIERTO = False
        return f"<div style='{estilo}'><h1 style='color:red; font-size:3em;'>🔴 APAGADA</h1><p>Sistema Bloqueado.</p></div>"
    return "Comando no reconocido"

# ==========================================
# CÓDIGO DE SUPERVIVENCIA (CORREGIDO)
# ==========================================
if __name__ == '__main__':
    # Render asigna un puerto en la variable de entorno PORT
    # Si no la encuentra (como en tu PC local), usará el 10000 por defecto
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
