"""Shared IA gateway. No public IA endpoint until product modules pass their own gates."""
from decimal import Decimal, ROUND_HALF_UP
from time import monotonic, sleep
import json
import httpx
from pydantic import BaseModel, ValidationError
from .config import configuracion
from .cuotas import reservar_cuota
from .base import transaccion
from .errores import ErrorProducto

def calcular_costo(entrada, salida, precios):
    costo=(Decimal(entrada)*Decimal(precios['entrada_millon_usd'])+Decimal(salida)*Decimal(precios['salida_millon_usd']))/Decimal(1000000)
    return costo.quantize(Decimal('.00000001'),rounding=ROUND_HALF_UP)

def generar(ctx, modulo, prompt, esquema: type[BaseModel] | None = None):
    cfg = configuracion()
    if not cfg.anthropic_api_key:
        raise ErrorProducto(503,'ia_no_conectada','La inteligencia artificial no está conectada.')
    with transaccion(ctx.usuario_id) as db:
        precios=db.execute("SELECT entrada_millon_usd,salida_millon_usd FROM broquer.precios_ia WHERE proveedor='anthropic' AND modelo=%s AND activo",(cfg.ia_modelo_default,)).fetchone()
    if not precios:
        raise ErrorProducto(503,'ia_sin_tarifa','La inteligencia artificial todavía no está disponible.')
    reservar_cuota(ctx,modulo,'generar')
    if esquema:
        prompt += '\nResponde únicamente con JSON conforme a este esquema: ' + json.dumps(esquema.model_json_schema(),ensure_ascii=False)
    mensajes=[{'role':'user','content':prompt}]
    salida_invalida=False
    for intento in range(1,4):
        inicio=monotonic();datos={};exito=False;codigo=None;reintentar=False
        try:
            with httpx.Client(timeout=45,follow_redirects=False) as cliente:
                r=cliente.post('https://api.anthropic.com/v1/messages',headers={'x-api-key':cfg.anthropic_api_key,'anthropic-version':'2023-06-01'},json={'model':cfg.ia_modelo_default,'max_tokens':1024,'messages':mensajes})
                if r.status_code==429 or r.status_code>=500:
                    codigo='proveedor_temporal';reintentar=True
                elif not r.is_success:
                    codigo='proveedor_rechazo'
                else:
                    datos=r.json()
                    if esquema:
                        texto=''.join(b.get('text','') for b in datos.get('content',[]) if b.get('type')=='text')
                        try:
                            valor=esquema.model_validate_json(texto)
                        except (ValidationError,ValueError):
                            codigo='salida_invalida'
                            if not salida_invalida:
                                mensajes.append({'role':'assistant','content':texto})
                                mensajes.append({'role':'user','content':'Devuelve únicamente JSON válido conforme al esquema solicitado.'})
                                reintentar=True;salida_invalida=True
                        else:
                            exito=True;return valor
                    else:
                        exito=True;return datos
        except httpx.RequestError:
            # Network timeouts may already have incurred provider charges; do not retry blindly.
            codigo='conexion_proveedor'
        except (ValueError,KeyError):
            codigo='respuesta_invalida'
        finally:
            uso=datos.get('usage',{})
            entrada=uso.get('input_tokens',0);salida=uso.get('output_tokens',0)
            costo=calcular_costo(entrada,salida,precios) if uso else None
            with transaccion(ctx.usuario_id) as db:
                db.execute('''INSERT INTO broquer.uso_ia(org_id,creado_por,modulo,proveedor,modelo,tokens_entrada,tokens_salida,exito,costo_usd,latencia_ms,error_codigo,intento)
                    VALUES(%s,%s,%s,'anthropic',%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (ctx.org_id,ctx.usuario_id,modulo,cfg.ia_modelo_default,entrada,salida,exito,costo,int((monotonic()-inicio)*1000),codigo,intento))
        if not reintentar or intento==3:
            raise ErrorProducto(503,'ia_no_disponible','No pudimos completar la solicitud de IA. Intenta más tarde.')
        sleep(min(4,2**(intento-1)))
