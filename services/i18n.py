"""
Translations for LampAdvisor — ES (default) and EN.
Access via the Jinja2 global T('key') injected by middleware.
"""
from contextvars import ContextVar

_lang: ContextVar[str] = ContextVar("lang", default="es")


def set_lang(lang: str) -> None:
    _lang.set(lang if lang in TRANSLATIONS else "es")


def get_lang() -> str:
    return _lang.get()


def T(key: str, **fmt) -> str:
    """Return translated string, falling back to ES then to the key itself."""
    lang = _lang.get()
    text = TRANSLATIONS.get(lang, TRANSLATIONS["es"]).get(key) \
           or TRANSLATIONS["es"].get(key, key)
    return text.format(**fmt) if fmt else text


TRANSLATIONS: dict[str, dict[str, str]] = {
    # ──────────────────────────────────────────────────────────────────────
    "es": {
        # Navigation
        "nav_section_projects":  "Proyectos",
        "nav_new_project":       "Nuevo Proyecto",
        "nav_all_projects":      "Todos los Proyectos",
        "nav_section_catalog":   "Catálogo",
        "nav_lamp_database":     "Base de Lámparas",
        "nav_import_catalog":    "Importar Catálogo",
        "nav_add_lamp":          "Añadir Lámpara",
        "nav_section_tools":     "Herramientas",
        "nav_ai_chat":           "Chat IA",
        "nav_dashboard":         "Tablero",
        "nav_settings":          "Ajustes",
        "nav_section_admin":     "Admin",
        "nav_manage_users":      "Gestionar Usuarios",
        "nav_ai_subtitle":       "Propuestas de Iluminación IA",

        # Floating chat panel
        "chat_title":            "LampAdvisor IA",
        "chat_subtitle":         "Pregunta sobre tu catálogo",
        "chat_try":              "Prueba preguntar:",
        "chat_suggest_1":        "Iluminación residencial de lujo",
        "chat_suggest_2":        "Colgantes regulables",
        "chat_suggest_3":        "Cálculo de lámparas",
        "chat_suggest_4":        "Resumen del catálogo",
        "chat_placeholder":      "Pregunta sobre lámparas, proyectos…",

        # API status (JS labels injected)
        "api_connected":         "Conectado",
        "api_no_key":            "Sin clave API",
        "api_invalid_key":       "Clave API inválida",
        "api_no_permission":     "Error de permisos API",
        "api_network_error":     "Error de red",
        "api_error":             "Error de API",
        "api_checking":          "Verificando…",

        # Common buttons
        "btn_save":              "Guardar",
        "btn_saving":            "Guardando…",
        "btn_cancel":            "Cancelar",
        "btn_delete":            "Eliminar",
        "btn_edit":              "Editar",
        "btn_view":              "Ver",
        "btn_rename":            "Renombrar",
        "btn_back":              "Atrás",
        "btn_new_project":       "Nuevo Proyecto",

        # Status labels
        "status_pending":        "pendiente",
        "status_analyzed":       "analizado",
        "status_proposed":       "propuesto",

        # Property levels
        "level_basic":           "Básico",
        "level_mid":             "Medio",
        "level_premium":         "Premium",
        "level_luxury":          "Lujo",

        # Dashboard (index.html)
        "dash_title":            "Tablero",
        "dash_subtitle":         "Resumen de tu sistema de propuestas de iluminación.",
        "dash_lamps":            "Lámparas en catálogo",
        "dash_projects":         "Proyectos analizados",
        "dash_proposals":        "Propuestas generadas",
        "dash_new_project":      "Nuevo Proyecto",
        "dash_new_project_sub":  "Sube PDF / DWG — obtén propuestas IA",
        "dash_import_catalog":   "Importar Catálogo de Lámparas",
        "dash_import_sub_empty": "Sin lámparas aún — IA mapeará tu catálogo automáticamente",
        "dash_update_catalog":   "Actualizar Catálogo",
        "dash_update_sub":       "Importar más lámparas — IA maneja cualquier formato",
        "dash_getting_started":  "Cómo empezar",
        "dash_step1":            "Descarga la <a href='/lamps/template' class='underline font-medium'>plantilla CSV</a> para ver el formato de columnas",
        "dash_step2":            "Rellena tu catálogo de lámparas — o usa cualquier Excel/PDF existente",
        "dash_step3":            "<a href='/lamps/import' class='underline font-medium'>Impórtalo</a> — IA mapeará las columnas automáticamente",
        "dash_step4":            "<a href='/projects/new' class='underline font-medium'>Crea un proyecto</a> — sube un plano PDF o DWG",
        "dash_step5":            "Obtén 1–3 propuestas de lámparas personalizadas con justificación IA",
        "dash_recent_projects":  "Proyectos Recientes",
        "dash_view_all":         "Ver todos →",

        # Projects list (projects.html)
        "projects_title":        "Proyectos",
        "col_project":           "Proyecto",
        "col_client":            "Cliente",
        "col_type":              "Tipo",
        "col_level":             "Nivel",
        "col_area":              "Área",
        "col_status":            "Estado",
        "col_date":              "Fecha",
        "projects_empty":        "Aún no hay proyectos",
        "btn_create_first":      "Crear primer proyecto",
        "confirm_delete_project":"¿Eliminar este proyecto y todas sus propuestas? Esta acción no se puede deshacer.",

        # Agent — upload
        "agent_title":           "Nuevo Proyecto",
        "agent_desc":            "Sube tus planos y Alex — tu especialista de iluminación IA — los analizará, discutirá los requisitos y creará una propuesta desde tu catálogo.",
        "agent_drop_title":      "Arrastra tus planos aquí",
        "agent_drop_sub":        "PDF, DWG o DXF · hasta 3 archivos · máx. 50 MB cada uno",
        "agent_files_selected":  "archivo(s) seleccionado(s)",
        "agent_analyze_btn":     "Analizar Archivo",
        "agent_analyze_n_btn":   "Analizar {n} Archivos",

        # Agent — analyzing
        "agent_analyzing_title": "Analizando tu proyecto…",
        "agent_analyzing_sub":   "Claude está leyendo los planos",

        # Agent — chat
        "agent_specialist":      "Alex · Especialista en Iluminación IA",
        "agent_generate_brief":  "Generar Especificación →",
        "agent_chat_ph":         "ej. La cocina es de 25m², añadir terraza con iluminación IP65…",

        # Agent — brief
        "agent_brief_title":     "Especificación de Iluminación",
        "agent_brief_generating":"Generando especificación…",
        "agent_brief_compiling": "Compilando la especificación completa de iluminación",
        "agent_fixture_groups":  "grupos de luminarias",
        "agent_fixtures_total":  "luminarias en total",
        "btn_edit_brief":        "← Editar",
        "agent_find_products":   "Buscar Productos en Catálogo →",

        # Agent — proposal
        "agent_proposal_title":  "Propuesta de Iluminación",
        "agent_line_items":      "línea(s)",
        "agent_searching":       "Buscando en catálogo…",
        "agent_matching":        "Buscando los mejores productos para tus requisitos",
        "btn_to_brief":          "← Especificación",
        "agent_required":        "Requerido",
        "agent_closest":         ", el más cercano es",
        "agent_fixtures_across": "luminarias en",
        "agent_groups":          "grupos",
        "agent_est_total":       "Total Estimado",
        "agent_no_catalog":      "No se encontraron productos en el catálogo.",
        "agent_import_first":    "Importa un catálogo primero y vuelve para generar una propuesta.",
        "agent_import_btn":      "Importar Catálogo",

        # Agent — save
        "agent_save_title":      "Guardar este proyecto",
        "agent_save_desc":       "Los proyectos guardados aparecen en tu panel con la propuesta completa",
        "agent_name_label":      "Nombre del proyecto",
        "agent_name_ph":         "ej. Villa Rossi — Residencia Principal",
        "agent_client_label":    "Nombre del cliente",
        "agent_client_ph":       "ej. Marco Rossi",
        "agent_save_btn":        "Guardar Proyecto y Ver Propuesta Completa →",

        # Alert messages (rendered into JS)
        "alert_upload_failed":   "Error al subir",
        "alert_no_content":      "No se pudo leer contenido. Verifica que el archivo tenga texto.",
        "alert_analysis_failed": "Análisis fallido",
        "alert_conn_lost":       "Conexión perdida durante el análisis.",
        "alert_chat_failed":     "Algo salió mal",
        "alert_brief_failed":    "Error al generar la especificación",
        "alert_proposal_failed": "Error al buscar en el catálogo",
        "alert_save_failed":     "Error al guardar el proyecto",

        # Lamps catalog (lamps.html)
        "lamps_title":           "Catálogo de Lámparas",
        "lamps_import_btn":      "Importar",
        "lamps_add_btn":         "Añadir Lámpara",
        "lamps_reload_seed":     "Recargar Base",
        "lamps_clear_all":       "Borrar Todo",
        "lamps_empty":           "El catálogo está vacío",
        "lamps_import_cta":      "Importar catálogo",
        "lamps_col_brand":       "Marca / Modelo",
        "lamps_col_category":    "Categoría",
        "lamps_col_specs":       "Especificaciones",
        "lamps_col_price":       "Precio",
        "lamps_col_actions":     "",

        # Import (lamp_import.html)
        "import_title":          "Importar Catálogo",
        "import_drop":           "Arrastra tu archivo Excel o CSV aquí",
        "import_formats":        "XLSX o CSV",
        "import_btn":            "Importar Catálogo",
        "import_importing":      "Importando…",

        # Settings
        "settings_title":        "Configuración de IA",
        "settings_save_btn":     "Guardar Ajustes",

        # Auth — login
        "login_heading":         "Iniciar sesión en tu cuenta",
        "login_email":           "Correo electrónico",
        "login_password":        "Contraseña",
        "login_btn":             "Iniciar Sesión",
        "login_no_account":      "¿No tienes cuenta?",
        "login_request_access":  "Solicitar acceso",

        # Auth — register
        "register_heading":      "Crear cuenta",
        "register_name":         "Nombre completo",
        "register_email":        "Correo electrónico",
        "register_password":     "Contraseña",
        "register_btn":          "Crear cuenta",
        "register_have_account": "¿Ya tienes cuenta?",
        "register_login_link":   "Iniciar sesión",

        # Pending
        "pending_title":         "Cuenta pendiente de aprobación",
        "pending_msg":           "Tu cuenta está siendo revisada por un administrador. Te avisaremos cuando sea aprobada.",
        "pending_logout":        "Cerrar sesión",

        # Language names
        "lang_es": "Español",
        "lang_en": "English",
    },

    # ──────────────────────────────────────────────────────────────────────
    "en": {
        # Navigation
        "nav_section_projects":  "Projects",
        "nav_new_project":       "New Project",
        "nav_all_projects":      "All Projects",
        "nav_section_catalog":   "Catalog",
        "nav_lamp_database":     "Lamp Database",
        "nav_import_catalog":    "Import Catalog",
        "nav_add_lamp":          "Add Lamp",
        "nav_section_tools":     "Tools",
        "nav_ai_chat":           "AI Chat",
        "nav_dashboard":         "Dashboard",
        "nav_settings":          "Settings",
        "nav_section_admin":     "Admin",
        "nav_manage_users":      "Manage Users",
        "nav_ai_subtitle":       "AI Lighting Proposals",

        # Floating chat panel
        "chat_title":            "LampAdvisor AI",
        "chat_subtitle":         "Ask anything about your catalog",
        "chat_try":              "Try asking:",
        "chat_suggest_1":        "Luxury residential",
        "chat_suggest_2":        "Dimmable pendants",
        "chat_suggest_3":        "Lamp count calc",
        "chat_suggest_4":        "Catalog summary",
        "chat_placeholder":      "Ask about lamps, projects, specs…",

        # API status
        "api_connected":         "Connected",
        "api_no_key":            "No API Key",
        "api_invalid_key":       "Invalid API Key",
        "api_no_permission":     "API Permission Error",
        "api_network_error":     "Network Error",
        "api_error":             "API Error",
        "api_checking":          "Checking…",

        # Common buttons
        "btn_save":              "Save",
        "btn_saving":            "Saving…",
        "btn_cancel":            "Cancel",
        "btn_delete":            "Delete",
        "btn_edit":              "Edit",
        "btn_view":              "View",
        "btn_rename":            "Rename",
        "btn_back":              "Back",
        "btn_new_project":       "New Project",

        # Status labels
        "status_pending":        "pending",
        "status_analyzed":       "analyzed",
        "status_proposed":       "proposed",

        # Property levels
        "level_basic":           "Basic",
        "level_mid":             "Mid",
        "level_premium":         "Premium",
        "level_luxury":          "Luxury",

        # Dashboard
        "dash_title":            "Dashboard",
        "dash_subtitle":         "Overview of your lighting proposal system.",
        "dash_lamps":            "Lamps in catalog",
        "dash_projects":         "Projects analyzed",
        "dash_proposals":        "Proposals generated",
        "dash_new_project":      "New Project",
        "dash_new_project_sub":  "Upload PDF / DWG — get AI proposals",
        "dash_import_catalog":   "Import Lamp Catalog",
        "dash_import_sub_empty": "No lamps yet — AI will map your catalog automatically",
        "dash_update_catalog":   "Update Catalog",
        "dash_update_sub":       "Import more lamps — AI handles any format",
        "dash_getting_started":  "Getting Started",
        "dash_step1":            "Download the <a href='/lamps/template' class='underline font-medium'>CSV template</a> to see the column format",
        "dash_step2":            "Fill in your lamp catalog — or use any existing Excel/PDF catalog",
        "dash_step3":            "<a href='/lamps/import' class='underline font-medium'>Import it</a> — AI will automatically map columns to the right fields",
        "dash_step4":            "<a href='/projects/new' class='underline font-medium'>Create a project</a> — upload a PDF or DWG floor plan",
        "dash_step5":            "Get 1–3 tailored lamp proposals with AI justification",
        "dash_recent_projects":  "Recent Projects",
        "dash_view_all":         "View all →",

        # Projects list
        "projects_title":        "Projects",
        "col_project":           "Project",
        "col_client":            "Client",
        "col_type":              "Type",
        "col_level":             "Level",
        "col_area":              "Area",
        "col_status":            "Status",
        "col_date":              "Date",
        "projects_empty":        "No projects yet",
        "btn_create_first":      "Create first project",
        "confirm_delete_project":"Delete this project and all its proposals? This cannot be undone.",

        # Agent — upload
        "agent_title":           "New Project",
        "agent_desc":            "Upload your floor plans and Alex — your AI lighting specialist — will analyze them, discuss requirements, and build a proposal from your catalog.",
        "agent_drop_title":      "Drop your floor plans here",
        "agent_drop_sub":        "PDF, DWG, or DXF · up to 3 files · max 50 MB each",
        "agent_files_selected":  "file(s) selected",
        "agent_analyze_btn":     "Analyze File",
        "agent_analyze_n_btn":   "Analyze {n} Files",

        # Agent — analyzing
        "agent_analyzing_title": "Analyzing your project…",
        "agent_analyzing_sub":   "Claude is reading the floor plans",

        # Agent — chat
        "agent_specialist":      "Alex · AI Lighting Specialist",
        "agent_generate_brief":  "Generate Requirements Brief →",
        "agent_chat_ph":         "e.g. The kitchen is 25m², add a terrace with IP65 lighting…",

        # Agent — brief
        "agent_brief_title":     "Lighting Requirements Brief",
        "agent_brief_generating":"Generating requirements brief…",
        "agent_brief_compiling": "Compiling the full lighting specification",
        "agent_fixture_groups":  "fixture groups",
        "agent_fixtures_total":  "fixtures total",
        "btn_edit_brief":        "← Edit",
        "agent_find_products":   "Find Products in Catalog →",

        # Agent — proposal
        "agent_proposal_title":  "Lighting Proposal",
        "agent_line_items":      "line items",
        "agent_searching":       "Searching the catalog…",
        "agent_matching":        "Matching your requirements to available products",
        "btn_to_brief":          "← Brief",
        "agent_required":        "Required",
        "agent_closest":         ", closest match is",
        "agent_fixtures_across": "fixtures across",
        "agent_groups":          "groups",
        "agent_est_total":       "Estimated Total",
        "agent_no_catalog":      "No matching products found in the catalog.",
        "agent_import_first":    "Import a catalog first, then come back to generate a proposal.",
        "agent_import_btn":      "Import Catalog",

        # Agent — save
        "agent_save_title":      "Save this project",
        "agent_save_desc":       "Saved projects appear in your dashboard with the full proposal",
        "agent_name_label":      "Project name",
        "agent_name_ph":         "e.g. Villa Rossi — Main Residence",
        "agent_client_label":    "Client name",
        "agent_client_ph":       "e.g. Marco Rossi",
        "agent_save_btn":        "Save Project & View Full Proposal →",

        # Alert messages
        "alert_upload_failed":   "Upload failed",
        "alert_no_content":      "No content could be read. Check the file has readable text.",
        "alert_analysis_failed": "Analysis failed",
        "alert_conn_lost":       "Connection lost during analysis.",
        "alert_chat_failed":     "Something went wrong",
        "alert_brief_failed":    "Failed to generate brief",
        "alert_proposal_failed": "Failed to search catalog",
        "alert_save_failed":     "Failed to save project",

        # Lamps catalog
        "lamps_title":           "Lamp Catalog",
        "lamps_import_btn":      "Import",
        "lamps_add_btn":         "Add Lamp",
        "lamps_reload_seed":     "Reload Seed",
        "lamps_clear_all":       "Clear All",
        "lamps_empty":           "Catalog is empty",
        "lamps_import_cta":      "Import catalog",
        "lamps_col_brand":       "Brand / Model",
        "lamps_col_category":    "Category",
        "lamps_col_specs":       "Specs",
        "lamps_col_price":       "Price",
        "lamps_col_actions":     "",

        # Import
        "import_title":          "Import Catalog",
        "import_drop":           "Drop your Excel or CSV file here",
        "import_formats":        "XLSX or CSV",
        "import_btn":            "Import Catalog",
        "import_importing":      "Importing…",

        # Settings
        "settings_title":        "AI Settings",
        "settings_save_btn":     "Save Settings",

        # Auth — login
        "login_heading":         "Sign in to your account",
        "login_email":           "Email",
        "login_password":        "Password",
        "login_btn":             "Sign In",
        "login_no_account":      "Don't have an account?",
        "login_request_access":  "Request access",

        # Auth — register
        "register_heading":      "Create account",
        "register_name":         "Full name",
        "register_email":        "Email address",
        "register_password":     "Password",
        "register_btn":          "Create account",
        "register_have_account": "Already have an account?",
        "register_login_link":   "Sign in",

        # Pending
        "pending_title":         "Account pending approval",
        "pending_msg":           "Your account is being reviewed by an administrator. You will be notified when approved.",
        "pending_logout":        "Logout",

        # Language names
        "lang_es": "Español",
        "lang_en": "English",
    },
}
