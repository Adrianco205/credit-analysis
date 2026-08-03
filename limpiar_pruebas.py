import sys
import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import Usuario

def limpiar_usuarios_prueba():
    db = SessionLocal()
    try:
        # IDs de prueba según las capturas de pantalla
        identificaciones_prueba = [
            "3333333",      # pruebaHosma
            "2020202020",   # Osnaider Jose Perez Torres
            "300000000",    # luisprueba
            "2010202020",   # hosman
            "399999999",    # eloyPrueba
            "20202020"      # osnaider
        ]
        
        print(f"Buscando usuarios de prueba con identificaciones: {identificaciones_prueba}")
        usuarios = db.query(Usuario).filter(Usuario.identificacion.in_(identificaciones_prueba)).all()
        
        if not usuarios:
            print("No se encontraron usuarios de prueba para eliminar.")
            return

        for u in usuarios:
            print(f"Eliminando usuario: {u.nombres} {u.primer_apellido} (ID: {u.identificacion})")
            # Al eliminar el usuario, se eliminarán en cascada sus documentos y los análisis hipotecarios vinculados.
            db.delete(u)
            
        db.commit()
        print("¡Todos los usuarios de prueba y sus análisis han sido eliminados correctamente!")
        
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    limpiar_usuarios_prueba()
