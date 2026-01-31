"""
Repository para Propuestas de Ahorro.
CRUD y consultas para la tabla propuestas_ahorro.
"""
import uuid
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.models.propuesta import PropuestaAhorro


class PropuestasRepo:
    """Repository para operaciones de Propuestas de Ahorro."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CRUD BÁSICO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def create(self, **kwargs) -> PropuestaAhorro:
        """Crear una nueva propuesta."""
        propuesta = PropuestaAhorro(**kwargs)
        self.db.add(propuesta)
        self.db.flush()
        return propuesta
    
    def create_batch(self, propuestas_data: list[dict]) -> list[PropuestaAhorro]:
        """Crear múltiples propuestas de una vez."""
        propuestas = [PropuestaAhorro(**data) for data in propuestas_data]
        self.db.add_all(propuestas)
        self.db.flush()
        return propuestas
    
    def save(self, propuesta: PropuestaAhorro) -> PropuestaAhorro:
        """Guardar cambios en una propuesta existente."""
        self.db.add(propuesta)
        self.db.flush()
        return propuesta
    
    def get_by_id(self, propuesta_id: uuid.UUID) -> PropuestaAhorro | None:
        """Obtener propuesta por ID."""
        return self.db.execute(
            select(PropuestaAhorro).where(PropuestaAhorro.id == propuesta_id)
        ).scalar_one_or_none()
    
    def delete(self, propuesta: PropuestaAhorro) -> None:
        """Eliminar una propuesta."""
        self.db.delete(propuesta)
        self.db.flush()
    
    def delete_by_analisis(self, analisis_id: uuid.UUID) -> int:
        """Eliminar todas las propuestas de un análisis. Retorna cantidad eliminada."""
        propuestas = self.list_by_analisis(analisis_id)
        count = len(propuestas)
        for p in propuestas:
            self.db.delete(p)
        self.db.flush()
        return count
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CONSULTAS POR ANÁLISIS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def list_by_analisis(
        self, 
        analisis_id: uuid.UUID
    ) -> Sequence[PropuestaAhorro]:
        """Listar todas las propuestas de un análisis, ordenadas por opción."""
        return self.db.execute(
            select(PropuestaAhorro)
            .where(PropuestaAhorro.analisis_id == analisis_id)
            .order_by(PropuestaAhorro.numero_opcion)
        ).scalars().all()
    
    def get_by_analisis_and_opcion(
        self,
        analisis_id: uuid.UUID,
        numero_opcion: int
    ) -> PropuestaAhorro | None:
        """Obtener propuesta específica por análisis y número de opción."""
        return self.db.execute(
            select(PropuestaAhorro).where(
                and_(
                    PropuestaAhorro.analisis_id == analisis_id,
                    PropuestaAhorro.numero_opcion == numero_opcion
                )
            )
        ).scalar_one_or_none()
    
    def count_by_analisis(self, analisis_id: uuid.UUID) -> int:
        """Contar propuestas de un análisis."""
        result = self.db.execute(
            select(func.count(PropuestaAhorro.id))
            .where(PropuestaAhorro.analisis_id == analisis_id)
        ).scalar()
        return result or 0
    
    def has_propuestas(self, analisis_id: uuid.UUID) -> bool:
        """Verificar si un análisis tiene propuestas generadas."""
        return self.count_by_analisis(analisis_id) > 0
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SELECCIÓN DE OPCIÓN
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_selected(self, analisis_id: uuid.UUID) -> PropuestaAhorro | None:
        """Obtener la opción seleccionada de un análisis."""
        return self.db.execute(
            select(PropuestaAhorro).where(
                and_(
                    PropuestaAhorro.analisis_id == analisis_id,
                    PropuestaAhorro.es_opcion_seleccionada == True
                )
            )
        ).scalar_one_or_none()
    
    def select_opcion(
        self,
        analisis_id: uuid.UUID,
        numero_opcion: int
    ) -> PropuestaAhorro | None:
        """
        Marcar una opción como seleccionada.
        Desmarca cualquier otra opción previamente seleccionada.
        """
        # Desmarcar todas las opciones del análisis
        propuestas = self.list_by_analisis(analisis_id)
        for p in propuestas:
            p.es_opcion_seleccionada = False
        
        # Marcar la opción indicada
        propuesta = self.get_by_analisis_and_opcion(analisis_id, numero_opcion)
        if propuesta:
            propuesta.es_opcion_seleccionada = True
            self.db.flush()
        
        return propuesta
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ACTUALIZACIONES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def update_calculo(
        self,
        propuesta: PropuestaAhorro,
        resultado: dict
    ) -> PropuestaAhorro:
        """Actualizar propuesta con resultados del motor de cálculo."""
        # Tiempo
        propuesta.cuotas_nuevas = resultado.get("cuotas_nuevas")
        propuesta.tiempo_restante_anios = resultado.get("tiempo_restante_anios")
        propuesta.tiempo_restante_meses = resultado.get("tiempo_restante_meses")
        propuesta.cuotas_reducidas = resultado.get("cuotas_reducidas")
        propuesta.tiempo_ahorrado_anios = resultado.get("tiempo_ahorrado_anios")
        propuesta.tiempo_ahorrado_meses = resultado.get("tiempo_ahorrado_meses")
        
        # Dinero
        propuesta.nuevo_valor_cuota = resultado.get("nuevo_valor_cuota")
        propuesta.total_por_pagar_aprox = resultado.get("total_por_pagar_aprox")
        propuesta.valor_ahorrado_intereses = resultado.get("valor_ahorrado_intereses")
        propuesta.veces_pagado = resultado.get("veces_pagado")
        
        # Honorarios
        propuesta.honorarios_calculados = resultado.get("honorarios_calculados")
        propuesta.honorarios_con_iva = resultado.get("honorarios_con_iva")
        propuesta.ingreso_minimo_requerido = resultado.get("ingreso_minimo_requerido")
        
        self.db.flush()
        return propuesta
    
    def update_origen(
        self,
        propuesta_id: uuid.UUID,
        origen: str
    ) -> PropuestaAhorro | None:
        """Cambiar el origen de una propuesta (USER -> ADMIN)."""
        propuesta = self.get_by_id(propuesta_id)
        if propuesta:
            propuesta.origen = origen
            self.db.flush()
        return propuesta
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ESTADÍSTICAS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_max_ahorro(self, analisis_id: uuid.UUID) -> Decimal | None:
        """Obtener el máximo ahorro entre las opciones de un análisis."""
        result = self.db.execute(
            select(func.max(PropuestaAhorro.valor_ahorrado_intereses))
            .where(PropuestaAhorro.analisis_id == analisis_id)
        ).scalar()
        return result
    
    def get_total_honorarios_potenciales(self, analisis_id: uuid.UUID) -> Decimal | None:
        """Obtener el total de honorarios potenciales (de la opción más alta)."""
        result = self.db.execute(
            select(func.max(PropuestaAhorro.honorarios_con_iva))
            .where(PropuestaAhorro.analisis_id == analisis_id)
        ).scalar()
        return result


def get_propuestas_repo(db: Session) -> PropuestasRepo:
    """Factory function para obtener el repositorio."""
    return PropuestasRepo(db)
