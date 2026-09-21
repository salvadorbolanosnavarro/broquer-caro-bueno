import hmac
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .core.config import configuracion
from .core.errores import ErrorProducto
from .modulos import cuentas, registro, oauth, archivos, trabajos, contactos, oportunidades, tareas, inmuebles, finanzas
app = FastAPI(title='Broquer API', version='0.2.0', docs_url=None, redoc_url=None)

@app.middleware('http')
async def seguridad(request: Request, call_next):
    cfg = configuracion()
    if request.url.path not in ('/salud', '/v1/estado'):
        if len(cfg.proxy_secret) < 32:
            return JSONResponse({'codigo':'conexion_pendiente','mensaje_usuario':'El servicio no está conectado.'},status_code=503)
        if not hmac.compare_digest(request.headers.get('x-broquer-proxy',''), cfg.proxy_secret):
            return JSONResponse({'codigo':'acceso_invalido','mensaje_usuario':'Abre Broquer para continuar.'},status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('origin') not in cfg.origenes_permitidos:
        return JSONResponse({'codigo':'origen_invalido','mensaje_usuario':'Vuelve a abrir Broquer e inténtalo otra vez.'},status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.exception_handler(ErrorProducto)
async def producto(request, exc):
    headers = {'Retry-After':'900'} if exc.estado == 429 else {}
    return JSONResponse({'codigo':exc.codigo,'mensaje_usuario':exc.mensaje},status_code=exc.estado,headers=headers)

@app.exception_handler(RequestValidationError)
async def validacion(request, exc):
    return JSONResponse({'codigo':'datos_invalidos','mensaje_usuario':'Revisa los campos del formulario.'},status_code=422)

@app.exception_handler(Exception)
async def fallo(request, exc):
    logging.getLogger('broquer').error('request_failed:%s',type(exc).__name__)
    return JSONResponse({'codigo':'servicio_no_disponible','mensaje_usuario':'No pudimos completar la solicitud. Intenta de nuevo.'},status_code=503)

@app.get('/salud')
def salud():
    return {'servicio':'broquer','estado':'activo'}

for modulo in [cuentas, registro, oauth, archivos, trabajos, contactos, oportunidades, tareas, inmuebles, finanzas]:
    app.include_router(modulo.router)
