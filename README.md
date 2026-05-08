<h1 align="center">🚚 Sistema de Gestión de Taller - PepsiCo</h1>

<p align="center">
  <img src="shields.io" alt="Flask">
  <img src="shields.io" alt="PostgreSQL">
  <img src="shields.io" alt="Frontend">
  <img src="shields.io" alt="Render">
</p>

## 📋 Problemática y Solución

En PepsiCo, el proceso de reparación y mantenimiento de la flota de camiones se gestionaba de manera **100% manual utilizando papel y lápiz**. Esta práctica generaba falta de trazabilidad, errores en la captura de datos y lentitud en la toma de decisiones.

Este proyecto nace para **automatizar y simplificar el flujo de trabajo**, digitalizando desde el ingreso del vehículo hasta su entrega final, asegurando mejores prácticas operativas y centralizando la información en una plataforma web robusta.

---

## 🚀 Características Principales

La arquitectura del sistema está diseñada para cubrir todas las aristas del mantenimiento de flota:

*   **Dashboard:** Visualización de métricas clave para la toma de decisiones.
*   **Agenda:** Control de citas y disponibilidad del taller.
*   **Gestión de Vehículos:** Catálogo detallado de la flota y su historial.
*   **Órdenes de Trabajo:** Creación, seguimiento y cierre de reparaciones.
*   **Control de Inventario:** Gestión de repuestos y relación con proveedores.
*   **Reportes:** Generación de informes automáticos de rendimiento y costos.
*   **Gestión de Usuarios:** Control de acceso basado en roles (RBAC).

---

## 👥 Perfiles y Roles (RBAC)

Para garantizar la seguridad y eficiencia, la plataforma ofrece vistas personalizadas según el cargo del usuario:


| Rol | Descripción y Funciones |
| :--- | :--- |
| **Administrador** | Control total del sistema y configuración de usuarios. |
| **Jefe de Taller** | Supervisión técnica y asignación de prioridades. |
| **Mecánico de Flota** | Registro de avances y uso de repuestos en reparaciones. |
| **Recepcionista** | Ingreso inicial y diagnóstico básico del vehículo. |
| **Guardia de Acceso** | Control de entradas y salidas físicas del recinto. |
| **Chofer** | Reporte de fallas y consulta de estado de su vehículo asignado. |

> 💡 *El sistema también incluye otros roles específicos como Coordinador de Zona y Supervisor de Flotas.*

---

## 🛠️ Estados de Reparación

El sistema implementa un flujo de estados dinámico para cada vehículo. Los 4 más relevantes dentro del proyecto son:

*   🟢 **En Reparación:** Trabajo activo en taller.
*   🔴 **Cancelado:** Orden anulada por motivos administrativos.
*   🔵 **Finalizado:** Reparación terminada, pendiente de retiro.
*   ✅ **Validado:** Control de calidad aprobado.

---

## 💻 Stack Tecnológico

*   **Frontend:** HTML5, CSS3 (Bootstrap / Material Design), JavaScript.
*   **Backend:** Python (Flask).
*   **Base de Datos:** PostgreSQL (Producción) / SQLite (Desarrollo).
*   **Autenticación:** Flask-Login.
*   **Despliegue:** Render / Gunicorn.

---

## ⚙️ Instalación Local

Sigue estos pasos para ejecutar el proyecto en tu entorno local:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/JoeyBecerra/proyecto-titulo-pepsico.git
   cd proyecto-titulo-pepsico
   ```

2. **Crear y activar el entorno virtual:**
   * **Linux/macOS:**
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```
   * **Windows:**
     ```cmd
     python -m venv venv
     venv\(\Scripts\activate\)
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```

---
<p align="center">
  <sub>Desarrollado por <b>José Ignacio</b> - Proyecto de Título</sub>
</p>
