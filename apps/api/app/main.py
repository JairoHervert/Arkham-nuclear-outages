# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from app.core.config import settings

# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     description="API para el challenge de Arkham de monitoreo de apagones nucleares."
# )

# # Configuración de CORS para que React (puerto 3000 o 5173) pueda conectarse
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], # En producción pondrías la URL de Azure
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/")
# async def root():
#     return {
#         "message": f"Bienvenido a {settings.PROJECT_NAME}",
#         "status": "online"
#     }

# # Aquí es donde importaremos las rutas (routes_data, routes_refresh) más adelante