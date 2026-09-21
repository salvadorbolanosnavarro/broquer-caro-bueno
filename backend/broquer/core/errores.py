class ErrorProducto(Exception):
    def __init__(self, estado:int,codigo:str,mensaje:str):
        self.estado=estado; self.codigo=codigo; self.mensaje=mensaje
