from pydantic import BaseModel, Field
from typing import Optional

class SeccionIn(BaseModel):
    nombre:      str
    rama:        Optional[str] = None
    color:       Optional[str] = "#2d6a4f"
    capacidad:   int           = Field(default=30, ge=1, le=500)
    lider:       Optional[str] = None
    descripcion: Optional[str] = None

class MiembroIn(BaseModel):
    numero_scout:        Optional[str] = None
    nombre:              str
    apellido:            str
    tipo:                str  # 'beneficiario' o 'scouter'
    fecha_nacimiento:    Optional[str] = None
    cargo:               Optional[str] = None
    seccion_id:          Optional[str] = None
    fecha_ingreso:       Optional[str] = None
    telefono:            Optional[str] = None
    email:               Optional[str] = None
    direccion:           Optional[str] = None
    nombre_tutor:        Optional[str] = None
    telefono_emergencia: Optional[str] = None
    grupo_sanguineo:     Optional[str] = None
    alergias:            Optional[str] = None
    activo:              bool = True
    notas:               Optional[str] = None

class ActividadIn(BaseModel):
    titulo:      str
    fecha:       str  # Formato YYYY-MM-DD
    hora:        Optional[str] = None
    descripcion: Optional[str] = None
    lugar:       Optional[str] = None
    seccion:     str  # Ejemplo: 'Manada', 'Tropa', 'Todo el Grupo'
    color:       Optional[str] = None

class AsistenciaIn(BaseModel):
    miembro_id: str
    actividad:  str
    fecha:      str  # Formato YYYY-MM-DD
    presente:   bool = True
    notas:      Optional[str] = None

class AsistenciaLote(BaseModel):
    actividad: str
    fecha:     str
    registros: list[dict]  # Soporta la estructura interna [{miembro_id, presente, notas}]

class UsuarioIn(BaseModel):
    nombre_completo: str
    rol:             str  # 'dev', 'master', 'jefe_seccion', etc.
    tipo:            str  # 'scouter' o 'tutor'
    seccion_id:      Optional[str] = None
    miembro_id:      Optional[str] = None

class ActualizarRolIn(BaseModel):
    rol:        str
    seccion_id: Optional[str] = None

class LoginIn(BaseModel):
    email:    str
    password: str

class CambiarPasswordIn(BaseModel):
    password_actual: str
    password_nueva:  str

class EquipoIn(BaseModel):
    miembro_id:       str
    articulo:         str
    estado:           str           = "Bueno"
    fecha_asignacion: Optional[str] = None
    notes:            Optional[str] = None

class UniformeIn(BaseModel):
    miembro_id: str
    pieza:      str
    tiene:      bool          = False
    talla:      Optional[str] = None
    estado:     str           = "Pendiente"
    notas:      Optional[str] = None

class RegistroAnualIn(BaseModel):
    miembro_id:    str
    anio:          int
    estado:        str            = "Pendiente"
    fecha_pago:    Optional[str]  = None
    monto:         Optional[float] = None
    observaciones: Optional[str]  = None

class TransferenciaIn(BaseModel):
    miembro_id:         str
    seccion_destino_id: str
    motivo:             Optional[str] = None
    realizado_por:      Optional[str] = None
    notas:              Optional[str] = None