"""DMD STUDIO — capa de control, edición y visualización sobre los motores.

La web NO contiene lógica musical: los motores Python existentes
(dark_director, jazz_engine, forge, scripts/produce.py) siguen siendo la
única fuente de verdad. Este paquete expone una API local (FastAPI) que
orquesta el pipeline real y almacena proyectos/generaciones en disco.
"""

__version__ = "1.0.0"
