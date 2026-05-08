// PepsiCo Taller Management - JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirmación para acciones importantes
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Actualizar hora actual cada minuto
    function updateCurrentTime() {
        const now = new Date();
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleString('es-CL');
        }
    }
    
    updateCurrentTime();
    setInterval(updateCurrentTime, 60000);
});

// Función para cambiar estado de OT
function cambiarEstadoOT(otId, nuevoEstado) {
    if (confirm(`¿Estás seguro de que quieres cambiar el estado a "${nuevoEstado}"?`)) {
        fetch(`/api/ordenes-trabajo/${otId}/estado`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ estado: nuevoEstado })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al cambiar el estado');
        });
    }
}

// Sistema de notificaciones en tiempo real
function actualizarContadorNotificaciones() {
    fetch('/notificaciones/contador')
        .then(response => response.json())
        .then(data => {
            const counter = document.getElementById('notificacion-counter');
            if (data.count > 0) {
                counter.textContent = data.count > 99 ? '99+' : data.count;
                counter.style.display = 'block';
            } else {
                counter.style.display = 'none';
            }
        })
        .catch(error => console.error('Error al cargar contador:', error));
}

function cargarNotificacionesRecientes() {
    fetch('/notificaciones')
        .then(response => response.text())
        .then(html => {
            // Usar DOMParser para extraer las notificaciones del HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const notificacionesItems = doc.querySelectorAll('.list-group-item');
            
            const notificacionesList = document.getElementById('notificaciones-list');
            
            if (notificacionesItems.length > 0) {
                let htmlContent = '';
                // Tomar solo las primeras 5 notificaciones
                Array.from(notificacionesItems).slice(0, 5).forEach(item => {
                    htmlContent += item.outerHTML;
                });
                notificacionesList.innerHTML = htmlContent;
            } else {
                notificacionesList.innerHTML = 
                    '<div class="text-center p-3 text-muted">No hay notificaciones</div>';
            }
        })
        .catch(error => {
            console.error('Error al cargar notificaciones:', error);
            document.getElementById('notificaciones-list').innerHTML = 
                '<div class="text-center p-3 text-danger">Error al cargar notificaciones</div>';
        });
}

// Actualizar cada 30 segundos
document.addEventListener('DOMContentLoaded', function() {
    // Cargar inicialmente
    actualizarContadorNotificaciones();
    cargarNotificacionesRecientes();
    
    // Actualizar periódicamente
    setInterval(actualizarContadorNotificaciones, 30000); // 30 segundos
    setInterval(cargarNotificacionesRecientes, 30000);
    
    // Actualizar cuando se hace clic en el dropdown
    document.getElementById('notificacionesDropdown').addEventListener('click', function() {
        cargarNotificacionesRecientes();
    });
});

// Función para marcar notificación como leída
function marcarComoLeida(notificacionId) {
    fetch(`/notificaciones/${notificacionId}/marcar-leida`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            actualizarContadorNotificaciones();
        }
    })
    .catch(error => console.error('Error:', error));
}

// En static/js/app.js - versión mejorada
function marcarComoLeida(notificacionId) {
    fetch(`/notificaciones/${notificacionId}/marcar-leida`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Actualizar contador global
            actualizarContadorNotificaciones();
            
            // Recargar notificaciones en dropdown
            cargarNotificacionesRecientes();
            
            // Si hay información adicional, usarla
            if (data.notificaciones_restantes !== undefined) {
                console.log(`Notificaciones restantes: ${data.notificaciones_restantes}`);
            }
            
            console.log('✅ Notificación marcada como leída correctamente');
        } else {
            console.error('Error:', data.error);
            alert('Error: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error de red:', error);
        alert('Error de conexión');
    });
}

// En static/js/app.js - AGREGAR ESTO
function initMobileSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const body = document.body;

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('mobile-open');
            body.classList.toggle('sidebar-open');
            
            // Toggle icono hamburguesa/cruz
            const icon = this.querySelector('.navbar-toggler-icon');
            if (sidebar.classList.contains('mobile-open')) {
                icon.classList.remove('navbar-toggler-icon');
                icon.innerHTML = '✕'; // Icono de cruz
            } else {
                icon.classList.add('navbar-toggler-icon');
                icon.innerHTML = ''; // Volver al icono por defecto
            }
        });

        // Cerrar sidebar al hacer clic en un link (en móviles)
        if (window.innerWidth < 768) {
            const sidebarLinks = sidebar.querySelectorAll('.nav-link');
            sidebarLinks.forEach(link => {
                link.addEventListener('click', () => {
                    sidebar.classList.remove('mobile-open');
                    body.classList.remove('sidebar-open');
                    // Restaurar icono hamburguesa
                    const icon = sidebarToggle.querySelector('.navbar-toggler-icon');
                    icon.classList.add('navbar-toggler-icon');
                    icon.innerHTML = '';
                });
            });
        }
    }
}

// Inicializar cuando cargue la página
document.addEventListener('DOMContentLoaded', function() {
    initMobileSidebar();
    
    // Re-inicializar cuando cambie el tamaño de la ventana
    window.addEventListener('resize', function() {
        const sidebar = document.querySelector('.sidebar');
        const body = document.body;
        
        if (window.innerWidth >= 768) {
            sidebar.classList.remove('mobile-open');
            body.classList.remove('sidebar-open');
        }
    });
});