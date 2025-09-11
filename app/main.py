from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from app.dependencies import SECRET_KEY, ALGORITHM
from app.routes import proveedores, facturas
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException

app = FastAPI(
    title="Invoice API",
    version="1.0.0",
)

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Simulación de usuario. Reemplaza por consulta real a la base de datos.
    if form_data.username == "responsable" and form_data.password == "1234":
        token_data = {"sub": "2", "role": "responsable"}
        access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

app.include_router(proveedores.router, prefix="/proveedores", tags=["Proveedores"])
app.include_router(facturas.router, prefix="/facturas", tags=["Facturas"])

# Manejo global de errores
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )
